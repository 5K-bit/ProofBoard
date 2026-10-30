"""Content checks on one evidence file. Standard library only, nothing is executed."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .model import Rule

MAX_INSPECT = 8 * 1024 * 1024


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _short(text: str, limit: int = 60) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _parse_xml(data: bytes) -> ET.Element | None:
    """Parse XML, refusing documents that declare entities or a doctype (billion laughs, XXE).

    The document must be UTF-8 text. Screening bytes would miss a UTF-16 or EBCDIC document that
    declares entities, so anything that is not valid UTF-8 (or holds a NUL) is refused, and the
    parser is given the decoded text, which it always reads as UTF-8 whatever the file declares.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    lowered = text.lower()
    if "\x00" in text or "<!doctype" in lowered or "<!entity" in lowered:
        return None
    try:
        return ET.fromstring(text)  # noqa: S314 - doctype and entities were refused above
    except ET.ParseError:
        return None


def coverage_percent(name: str, data: bytes, text: str) -> float | None:
    """Read a line-coverage percentage from coverage.xml, coverage.json or a TOTAL text line."""
    lower = name.lower()
    if lower.endswith(".xml"):
        root = _parse_xml(data)
        if root is None or root.tag != "coverage":
            return None
        try:
            return round(float(root.attrib["line-rate"]) * 100, 2)
        except (KeyError, ValueError):
            return None
    if lower.endswith(".json"):
        try:
            value = json.loads(text)["totals"]["percent_covered"]
            return round(float(value), 2)
        except (ValueError, KeyError, TypeError):
            return None
    found = re.findall(r"(?m)^TOTAL\b.*?(\d+(?:\.\d+)?)%\s*$", text)
    return float(found[-1]) if found else None


def junit_totals(data: bytes) -> tuple[int, int, int] | None:
    """Return (tests, failures, errors) summed over a JUnit XML file."""
    root = _parse_xml(data)
    if root is None:
        return None
    if root.tag not in ("testsuite", "testsuites"):
        return None
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    if not suites:
        return None
    tests = failures = errors = 0
    try:
        for suite in suites:
            tests += int(suite.attrib.get("tests", 0))
            failures += int(suite.attrib.get("failures", 0))
            errors += int(suite.attrib.get("errors", 0))
    except ValueError:
        return None
    return tests, failures, errors


def inspect(path: Path, rule: Rule) -> list[CheckResult]:
    """Run every rule on the file. Returns one result per check; empty if no rules."""
    if rule.is_empty():
        return []
    size = path.stat().st_size
    if size > MAX_INSPECT:
        return [
            CheckResult(
                "inspect", False, f"larger than the {MAX_INSPECT >> 20} MiB inspection limit"
            )
        ]
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    out: list[CheckResult] = []
    for needle in rule.contains:
        out.append(CheckResult("contains", needle in text, f'contains "{_short(needle)}"'))
    for needle in rule.not_contains:
        out.append(
            CheckResult("not_contains", needle not in text, f'does not contain "{_short(needle)}"')
        )
    for pattern in rule.matches:
        hit = re.search(pattern, text, re.MULTILINE) is not None
        out.append(CheckResult("matches", hit, f"matches /{_short(pattern)}/"))
    if rule.coverage_min is not None:
        pct = coverage_percent(path.name, data, text)
        if pct is None:
            out.append(CheckResult("coverage_min", False, "no coverage figure could be read"))
        else:
            out.append(
                CheckResult(
                    "coverage_min",
                    pct >= rule.coverage_min,
                    f"coverage {pct:g}% (needs at least {rule.coverage_min:g}%)",
                )
            )
    if rule.junit_clean:
        totals = junit_totals(data)
        if totals is None:
            out.append(CheckResult("junit_clean", False, "not a readable JUnit XML file"))
        else:
            tests, failures, errors = totals
            out.append(
                CheckResult(
                    "junit_clean",
                    tests > 0 and failures == 0 and errors == 0,
                    f"{tests} tests, {failures} failures, {errors} errors",
                )
            )
    return out
