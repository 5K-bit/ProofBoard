"""Compare the claims file, the files on disk and the lock, and decide what is proven."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .checks import CheckResult, inspect
from .ledger import Entry, hash_file, parse_time
from .model import Board, Claim, safe_relpath

# Worst first. A claim takes the worst status among its evidence.
EVIDENCE_ORDER = ("failed", "missing", "drifted", "unsealed", "stale", "ok")
CLAIM_ORDER = ("failed", "missing", "drifted", "unsealed", "stale", "unsupported", "proven")


@dataclass(frozen=True)
class EvidenceResult:
    path: str
    status: str
    note: str
    sha256: str | None
    sealed_sha256: str | None
    sealed_at: str | None
    size: int | None
    checks: tuple[CheckResult, ...] = ()


@dataclass(frozen=True)
class ClaimResult:
    claim: Claim
    status: str
    evidence: tuple[EvidenceResult, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Report:
    board: Board
    now: datetime
    sealed: bool
    results: tuple[ClaimResult, ...]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for res in self.results:
            out[res.status] = out.get(res.status, 0) + 1
        return out

    @property
    def all_proven(self) -> bool:
        return bool(self.results) and all(r.status == "proven" for r in self.results)


def resolve_inside(root: Path, rel: str) -> Path | None:
    """The file for a relative path, or None if it escapes the root through a link."""
    candidate = root / safe_relpath(rel)
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return candidate


def _evidence(
    root: Path, path: str, rule_claim: Claim, lock: dict[str, Entry] | None, now: datetime
) -> EvidenceResult:
    target = resolve_inside(root, path)
    if target is None:
        return EvidenceResult(
            path, "failed", "resolves outside the project folder", None, None, None, None
        )
    sealed = lock.get(path) if lock is not None else None
    sealed_sha = sealed.sha256 if sealed else None
    sealed_at = sealed.sealed_at if sealed else None
    if not target.is_file():
        return EvidenceResult(path, "missing", "file not found", None, sealed_sha, sealed_at, None)
    sha, size = hash_file(target)
    rule = next(e.rule for e in rule_claim.evidence if e.path == path)
    checks = tuple(inspect(target, rule))
    failed = [c for c in checks if not c.ok]
    if failed:
        status, note = "failed", "; ".join(f"not met: {c.detail}" for c in failed)
    elif sealed is None:
        status, note = "unsealed", "not recorded in the lock yet (run 'proofboard seal')"
    elif sealed.sha256 != sha:
        status = "drifted"
        note = f"changed since it was sealed (sealed {sealed.sha256[:12]}, now {sha[:12]})"
    else:
        age_days = (now - parse_time(sealed.sealed_at)).total_seconds() / 86400
        if age_days > rule_claim.max_age_days:
            status = "stale"
            note = f"sealed {int(age_days)} days ago; this claim allows {rule_claim.max_age_days}"
        else:
            status, note = "ok", "matches the sealed record"
    return EvidenceResult(path, status, note, sha, sealed_sha, sealed_at, size, checks)


def evaluate(root: Path, board: Board, lock: dict[str, Entry] | None, now: datetime) -> Report:
    results: list[ClaimResult] = []
    for claim in board.claims:
        evidence = tuple(_evidence(root, ev.path, claim, lock, now) for ev in claim.evidence)
        if not evidence:
            status = "unsupported"
        else:
            worst = min((e.status for e in evidence), key=EVIDENCE_ORDER.index)
            status = "proven" if worst == "ok" else worst
        results.append(ClaimResult(claim, status, evidence))
    return Report(board, now, lock is not None, tuple(results))
