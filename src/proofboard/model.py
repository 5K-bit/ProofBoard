"""The claims file: what is claimed, and which evidence is said to support it."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ProofBoardError

MAX_CONFIG_BYTES = 1 << 20
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_TITLE = 200
MAX_STATEMENT = 1000
MAX_RULE_TEXT = 500
MAX_PATH = 240
DEFAULT_MAX_AGE_DAYS = 90


@dataclass(frozen=True)
class Rule:
    """Checks run on the content of one evidence file. All must hold."""

    contains: tuple[str, ...] = ()
    not_contains: tuple[str, ...] = ()
    matches: tuple[str, ...] = ()
    coverage_min: float | None = None
    junit_clean: bool = False

    def is_empty(self) -> bool:
        return not (
            self.contains
            or self.not_contains
            or self.matches
            or self.coverage_min is not None
            or self.junit_clean
        )


@dataclass(frozen=True)
class Evidence:
    path: str
    rule: Rule


@dataclass(frozen=True)
class Claim:
    id: str
    title: str
    statement: str
    max_age_days: int
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class Board:
    title: str
    subject: str
    claims: tuple[Claim, ...]

    def evidence_paths(self) -> list[str]:
        seen: dict[str, None] = {}
        for claim in self.claims:
            for ev in claim.evidence:
                seen.setdefault(ev.path, None)
        return sorted(seen)


def safe_relpath(path: str, where: str = "evidence path") -> str:
    """Accept only a plain relative path with forward slashes that stays inside the project."""
    if not isinstance(path, str) or not path:
        raise ProofBoardError(f"{where}: must be a non-empty string")
    if len(path) > MAX_PATH or "\x00" in path:
        raise ProofBoardError(f"{where}: too long or contains a NUL byte")
    if path.startswith("/") or "\\" in path or re.match(r"^[A-Za-z]:", path):
        raise ProofBoardError(f"{where}: {path!r} must be relative and use forward slashes")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise ProofBoardError(f"{where}: {path!r} must not contain empty, '.' or '..' parts")
    return path


def _only(table: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ProofBoardError(
            f"{where}: unknown key(s) {', '.join(unknown)} (allowed: {', '.join(sorted(allowed))})"
        )


def _text(value: Any, where: str, limit: int, *, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise ProofBoardError(f"{where}: must be a non-empty string")
    if len(value) > limit:
        raise ProofBoardError(f"{where}: longer than {limit} characters")
    return value


def _strings(value: Any, where: str) -> tuple[str, ...]:
    items = [value] if isinstance(value, str) else value
    if not isinstance(items, list) or not items:
        raise ProofBoardError(f"{where}: must be a string or a non-empty list of strings")
    out: list[str] = []
    for item in items:
        out.append(_text(item, where, MAX_RULE_TEXT))
    return tuple(out)


def _rule(table: dict[str, Any], where: str) -> Rule:
    matches = _strings(table["matches"], f"{where}.matches") if "matches" in table else ()
    for pattern in matches:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ProofBoardError(f"{where}.matches: invalid regular expression: {exc}") from None
    coverage = table.get("coverage_min")
    if coverage is not None and (
        isinstance(coverage, bool)
        or not isinstance(coverage, int | float)
        or not 0 <= coverage <= 100
    ):
        raise ProofBoardError(f"{where}.coverage_min: must be a number from 0 to 100")
    junit = table.get("junit_clean", False)
    if not isinstance(junit, bool):
        raise ProofBoardError(f"{where}.junit_clean: must be true or false")
    return Rule(
        contains=_strings(table["contains"], f"{where}.contains") if "contains" in table else (),
        not_contains=(
            _strings(table["not_contains"], f"{where}.not_contains")
            if "not_contains" in table
            else ()
        ),
        matches=matches,
        coverage_min=None if coverage is None else float(coverage),
        junit_clean=junit,
    )


def parse_board(raw: dict[str, Any]) -> Board:
    _only(raw, {"board", "claim"}, "file")
    head = raw.get("board")
    if not isinstance(head, dict):
        raise ProofBoardError("file: a [board] table is required")
    _only(head, {"title", "subject", "default_max_age_days"}, "[board]")
    default_age = head.get("default_max_age_days", DEFAULT_MAX_AGE_DAYS)
    title = _text(head.get("title"), "[board].title", MAX_TITLE)
    subject = _text(head.get("subject"), "[board].subject", MAX_TITLE, required=False)

    def age(value: Any, where: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 3650:
            raise ProofBoardError(f"{where}: must be a whole number of days from 1 to 3650")
        return value

    default_age = age(default_age, "[board].default_max_age_days")
    claims_raw = raw.get("claim", [])
    if not isinstance(claims_raw, list):
        raise ProofBoardError("file: claims must be written as [[claim]] tables")
    claims: list[Claim] = []
    seen: set[str] = set()
    for index, table in enumerate(claims_raw, start=1):
        where = f"claim #{index}"
        if not isinstance(table, dict):
            raise ProofBoardError(f"{where}: must be a table")
        _only(table, {"id", "title", "statement", "max_age_days", "evidence"}, where)
        cid = _text(table.get("id"), f"{where}.id", 64)
        if not ID_RE.match(cid):
            raise ProofBoardError(f"{where}.id: {cid!r} must be lowercase letters, digits, dashes")
        if cid in seen:
            raise ProofBoardError(f"{where}.id: duplicate id {cid!r}")
        seen.add(cid)
        where = f"claim {cid}"
        ev_raw = table.get("evidence", [])
        if not isinstance(ev_raw, list):
            raise ProofBoardError(f"{where}.evidence: must be [[claim.evidence]] tables")
        evidence: list[Evidence] = []
        for n, ev in enumerate(ev_raw, start=1):
            ewhere = f"{where}.evidence #{n}"
            if not isinstance(ev, dict):
                raise ProofBoardError(f"{ewhere}: must be a table")
            _only(
                ev,
                {"path", "contains", "not_contains", "matches", "coverage_min", "junit_clean"},
                ewhere,
            )
            evidence.append(
                Evidence(safe_relpath(ev.get("path", ""), f"{ewhere}.path"), _rule(ev, ewhere))
            )
        claims.append(
            Claim(
                id=cid,
                title=_text(table.get("title"), f"{where}.title", MAX_TITLE),
                statement=_text(
                    table.get("statement"), f"{where}.statement", MAX_STATEMENT, required=False
                ),
                max_age_days=age(table.get("max_age_days", default_age), f"{where}.max_age_days"),
                evidence=tuple(evidence),
            )
        )
    return Board(title=title, subject=subject, claims=tuple(claims))


def load_board(path: Path) -> Board:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        raise ProofBoardError(
            f"claims file not found: {path} (create one with 'proofboard init')"
        ) from None
    except OSError as exc:
        raise ProofBoardError(f"cannot read {path}: {exc.strerror or exc}") from None
    if size > MAX_CONFIG_BYTES:
        raise ProofBoardError(f"{path}: larger than {MAX_CONFIG_BYTES >> 10} KiB")
    try:
        raw = tomllib.loads(path.read_bytes().decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ProofBoardError(f"{path}: not valid TOML: {exc}") from None
    return parse_board(raw)
