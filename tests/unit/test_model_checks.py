from __future__ import annotations

from pathlib import Path

import pytest

from proofboard.checks import coverage_percent, inspect, junit_totals
from proofboard.errors import ProofBoardError
from proofboard.model import Rule, load_board, parse_board, safe_relpath


def board(extra: str = "", claim_extra: str = "") -> dict:
    import tomllib

    return tomllib.loads(
        f'[board]\ntitle = "T"\n{extra}\n[[claim]]\nid = "a"\ntitle = "A"\n{claim_extra}\n'
    )


@pytest.mark.parametrize(
    "bad", ["", "/etc/passwd", "a\\b", "C:/x", "../x", "a/../b", "a//b", "./a", "a\x00b", "x" * 300]
)
def test_unsafe_paths_rejected(bad: str) -> None:
    with pytest.raises(ProofBoardError):
        safe_relpath(bad)


def test_safe_path_accepted() -> None:
    assert safe_relpath("docs/evidence/run.txt") == "docs/evidence/run.txt"


def test_valid_board_parses() -> None:
    parsed = parse_board(
        board(
            claim_extra='max_age_days = 5\n[[claim.evidence]]\npath = "x.txt"\ncontains = ["a", "b"]\ncoverage_min = 90\njunit_clean = true\nmatches = "^x"\nnot_contains = "bad"\n'
        )
    )
    claim = parsed.claims[0]
    assert claim.max_age_days == 5
    ev = claim.evidence[0]
    assert ev.rule.contains == ("a", "b") and ev.rule.coverage_min == 90.0 and ev.rule.junit_clean
    assert parsed.evidence_paths() == ["x.txt"]
    assert not ev.rule.is_empty() and Rule().is_empty()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(extra=1),
        lambda d: d.pop("board"),
        lambda d: d["board"].update(title=""),
        lambda d: d["board"].update(wat=1),
        lambda d: d["board"].update(default_max_age_days=0),
        lambda d: d["board"].update(default_max_age_days=True),
        lambda d: d.update(claim={"id": "x"}),
        lambda d: d["claim"][0].update(id="Bad Id"),
        lambda d: d["claim"].append(dict(d["claim"][0])),
        lambda d: d["claim"][0].update(evidence="x"),
        lambda d: d["claim"][0].update(evidence=["x"]),
        lambda d: d["claim"][0].update(evidence=[{"path": "../x"}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "wat": 1}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "matches": "("}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "coverage_min": 101}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "coverage_min": True}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "junit_clean": "yes"}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "contains": []}]),
        lambda d: d["claim"][0].update(evidence=[{"path": "x", "contains": [""]}]),
        lambda d: d["claim"][0].update(title="x" * 300),
        lambda d: d["claim"].__setitem__(0, "nope"),
    ],
)
def test_invalid_boards_rejected(mutate) -> None:
    data = board()
    mutate(data)
    with pytest.raises(ProofBoardError):
        parse_board(data)


def test_load_board_errors(tmp_path: Path) -> None:
    with pytest.raises(ProofBoardError, match="not found"):
        load_board(tmp_path / "none.toml")
    bad = tmp_path / "bad.toml"
    bad.write_text("[board\n", encoding="utf-8")
    with pytest.raises(ProofBoardError, match="not valid TOML"):
        load_board(bad)
    bad.write_bytes(b"\xff\xfe")
    with pytest.raises(ProofBoardError, match="not valid TOML"):
        load_board(bad)
    bad.write_text("#" * (2 << 20), encoding="utf-8")
    with pytest.raises(ProofBoardError, match="larger"):
        load_board(bad)
    # a path below a file: Linux reports "not a directory", Windows "not found"
    with pytest.raises(ProofBoardError, match="cannot read|not found"):
        load_board(tmp_path / "bad.toml" / "x")


JUNIT_OK = b'<testsuites><testsuite tests="3" failures="0" errors="0"/><testsuite tests="2" failures="0" errors="0"/></testsuites>'


def test_junit_totals() -> None:
    assert junit_totals(JUNIT_OK) == (5, 0, 0)
    assert junit_totals(b'<testsuite tests="2" failures="1" errors="1"/>') == (2, 1, 1)
    assert junit_totals(b"<other/>") is None
    assert junit_totals(b"<testsuites/>") is None
    assert junit_totals(b'<testsuite tests="x"/>') is None
    assert junit_totals(b"not xml") is None


def test_xml_with_doctype_or_entities_refused() -> None:
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><testsuite tests="&a;"/>'
    assert junit_totals(bomb) is None
    assert coverage_percent("c.xml", bomb, "") is None


def test_coverage_sources() -> None:
    assert coverage_percent("coverage.xml", b'<coverage line-rate="0.925"/>', "") == 92.5
    assert coverage_percent("coverage.xml", b"<coverage/>", "") is None
    assert coverage_percent("coverage.xml", b"<other line-rate='1'/>", "") is None
    assert coverage_percent("coverage.xml", b'<coverage line-rate="x"/>', "") is None
    assert coverage_percent("c.json", b"", '{"totals": {"percent_covered": 88.123}}') == 88.12
    assert coverage_percent("c.json", b"", "{}") is None
    assert coverage_percent("c.json", b"", "nope") is None
    assert coverage_percent("t.txt", b"", "TOTAL  10 1 90%\nTOTAL 20 1 94.5%\n") == 94.5
    assert coverage_percent("t.txt", b"", "nothing") is None


def test_inspect_rules(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("alpha passed\nTOTAL 1 0 91%\n", encoding="utf-8")
    assert inspect(f, Rule()) == []
    res = inspect(
        f,
        Rule(contains=("passed",), not_contains=("failed",), matches=("^alpha",), coverage_min=90),
    )
    assert [r.name for r in res] == ["contains", "not_contains", "matches", "coverage_min"]
    assert all(r.ok for r in res)
    bad = inspect(
        f, Rule(contains=("zzz",), not_contains=("alpha",), matches=("^zzz",), coverage_min=95)
    )
    assert not any(r.ok for r in bad)
    assert not inspect(f, Rule(junit_clean=True))[0].ok
    nocov = tmp_path / "n.txt"
    nocov.write_text("hi", encoding="utf-8")
    assert "no coverage figure" in inspect(nocov, Rule(coverage_min=1))[0].detail
    j = tmp_path / "j.xml"
    j.write_bytes(JUNIT_OK)
    assert inspect(j, Rule(junit_clean=True))[0].ok
    j.write_bytes(b'<testsuite tests="0"/>')
    assert not inspect(j, Rule(junit_clean=True))[0].ok


def test_inspect_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import proofboard.checks as checks

    monkeypatch.setattr(checks, "MAX_INSPECT", 4)
    f = tmp_path / "big.txt"
    f.write_text("0123456789", encoding="utf-8")
    assert "inspection limit" in checks.inspect(f, Rule(contains=("0",)))[0].detail


def test_long_rule_text_is_shortened(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("a", encoding="utf-8")
    detail = inspect(f, Rule(contains=("a" * 200,)))[0].detail
    assert len(detail) < 100 and "…" in detail
