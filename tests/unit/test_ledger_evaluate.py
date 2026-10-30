from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from proofboard.errors import ProofBoardError
from proofboard.evaluate import evaluate, resolve_inside
from proofboard.ledger import (
    Entry,
    format_time,
    hash_file,
    load_lock,
    now_utc,
    parse_time,
    write_lock,
)
from proofboard.model import load_board
from proofboard.seal import plan_seal

NOW = parse_time("2026-10-29T17:00:00Z")


def test_times() -> None:
    assert format_time(parse_time("2026-10-29T13:00:00-04:00")) == "2026-10-29T17:00:00Z"
    assert format_time(parse_time("2026-10-29T17:00:00")) == "2026-10-29T17:00:00Z"
    with pytest.raises(ProofBoardError):
        parse_time("yesterday")
    assert now_utc().microsecond == 0


def test_hash_file(tmp_path: Path) -> None:
    f = tmp_path / "f"
    f.write_bytes(b"abc")
    sha, size = hash_file(f)
    assert size == 3 and sha.startswith("ba7816bf")


def test_lock_roundtrip_and_tamper(tmp_path: Path) -> None:
    path = tmp_path / "l.json"
    assert load_lock(path) is None
    entries = {"a.txt": Entry("0" * 64, 1, "2026-10-29T17:00:00Z")}
    write_lock(path, entries)
    assert load_lock(path) == entries
    assert not (tmp_path / "l.json.tmp").exists()
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["entries"]["a.txt"]["sha256"] = "1" * 64
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ProofBoardError, match="digest"):
        load_lock(path)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"format": 2, "entries": {}}',
        '{"format": 1, "entries": []}',
        '{"format": 1, "entries": {"a": {"sha256": "zz", "size": 1, "sealed_at": "2026-01-01T00:00:00Z"}}}',
        '{"format": 1, "entries": {"a": {"sha256": "%s", "size": 1, "sealed_at": "never"}}}'
        % ("0" * 64),
        '{"format": 1, "entries": {"a": 5}}',
    ],
)
def test_damaged_locks_rejected(tmp_path: Path, text: str) -> None:
    path = tmp_path / "l.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ProofBoardError):
        load_lock(path)


def test_lock_too_large(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import proofboard.ledger as ledger

    monkeypatch.setattr(ledger, "MAX_LOCK_BYTES", 3)
    path = tmp_path / "l.json"
    path.write_text("{}" * 5, encoding="utf-8")
    with pytest.raises(ProofBoardError, match="larger"):
        ledger.load_lock(path)
    # below a file: an error on Linux, simply "no lock" on Windows
    try:
        assert ledger.load_lock(path / "x") is None
    except ProofBoardError as exc:
        assert "cannot read" in str(exc)


def _lock(project: Path, when: str = "2026-10-29T17:00:00Z") -> dict[str, Entry]:
    board = load_board(project / "proofboard.toml")
    out = plan_seal(project, board, None, parse_time(when))
    write_lock(project / "proofboard.lock.json", out.entries)
    return out.entries


def test_status_walk(project: Path) -> None:
    board = load_board(project / "proofboard.toml")
    ev = project / "ev" / "run.txt"
    assert evaluate(project, board, None, NOW).results[0].status == "unsealed"
    lock = _lock(project)
    assert evaluate(project, board, lock, NOW).all_proven
    later = parse_time("2027-01-29T17:00:00Z")
    stale = evaluate(project, board, lock, later)
    assert stale.results[0].status == "stale" and not stale.all_proven
    ev.write_text("changed passed\n", encoding="utf-8")
    assert evaluate(project, board, lock, NOW).results[0].status == "drifted"
    ev.write_text("nothing here\n", encoding="utf-8")
    assert evaluate(project, board, lock, NOW).results[0].status == "failed"
    ev.unlink()
    res = evaluate(project, board, lock, NOW).results[0]
    assert res.status == "missing" and res.evidence[0].sealed_sha256


def test_claim_without_evidence_is_unsupported(tmp_path: Path) -> None:
    (tmp_path / "p.toml").write_text(
        '[board]\ntitle = "T"\n[[claim]]\nid = "a"\ntitle = "A"\n', encoding="utf-8"
    )
    report = evaluate(tmp_path, load_board(tmp_path / "p.toml"), None, NOW)
    assert report.results[0].status == "unsupported" and not report.all_proven


def test_empty_board_is_not_proven(tmp_path: Path) -> None:
    (tmp_path / "p.toml").write_text('[board]\ntitle = "T"\n', encoding="utf-8")
    assert not evaluate(tmp_path, load_board(tmp_path / "p.toml"), None, NOW).all_proven


def test_worst_status_wins(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "p.toml").write_text(
        '[board]\ntitle = "T"\n[[claim]]\nid = "a"\ntitle = "A"\n'
        '[[claim.evidence]]\npath = "a.txt"\n[[claim.evidence]]\npath = "b.txt"\n',
        encoding="utf-8",
    )
    report = evaluate(tmp_path, load_board(tmp_path / "p.toml"), {}, NOW)
    assert report.results[0].status == "missing"
    assert report.counts() == {"missing": 1}


@pytest.mark.skipif(os.name == "nt", reason="symlinks need privileges on Windows")
def test_symlink_escape_is_failed(project: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    outside = tmp_path_factory.mktemp("outside") / "secret.txt"
    outside.write_text("passed", encoding="utf-8")
    (project / "ev" / "run.txt").unlink()
    (project / "ev" / "run.txt").symlink_to(outside)
    board = load_board(project / "proofboard.toml")
    assert resolve_inside(project, "ev/run.txt") is None
    assert evaluate(project, board, {}, NOW).results[0].status == "failed"
    with pytest.raises(ProofBoardError, match="outside"):
        plan_seal(project, board, None, NOW)


def test_seal_plan_new_changed_unchanged_refresh_dropped(project: Path) -> None:
    board = load_board(project / "proofboard.toml")
    first = plan_seal(project, board, None, NOW)
    assert first.new == ["ev/run.txt"]
    later = parse_time("2026-11-30T00:00:00Z")
    again = plan_seal(project, board, first.entries, later)
    assert again.unchanged == ["ev/run.txt"]
    assert again.entries["ev/run.txt"].sealed_at == "2026-10-29T17:00:00Z"
    refreshed = plan_seal(project, board, first.entries, later, refresh=True)
    assert refreshed.entries["ev/run.txt"].sealed_at == "2026-11-30T00:00:00Z"
    (project / "ev" / "run.txt").write_text("x passed", encoding="utf-8")
    assert plan_seal(project, board, first.entries, later).changed == ["ev/run.txt"]
    old = dict(first.entries) | {"gone.txt": Entry("0" * 64, 1, "2026-10-29T17:00:00Z")}
    assert plan_seal(project, board, old, later).dropped == ["gone.txt"]


def test_seal_reports_every_problem(project: Path) -> None:
    (project / "ev" / "run.txt").unlink()
    with pytest.raises(ProofBoardError, match="file not found"):
        plan_seal(project, load_board(project / "proofboard.toml"), None, NOW)
