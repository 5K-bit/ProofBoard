from __future__ import annotations

import json
import os
import random
from pathlib import Path

import pytest

from proofboard import render
from proofboard.evaluate import evaluate
from proofboard.ledger import parse_time
from proofboard.model import load_board
from proofboard.seal import plan_seal

from ..conftest import DEMO

NOW = parse_time("2026-10-29T17:00:00Z")
GOLDEN = Path(__file__).resolve().parent.parent / "fixtures"


def demo_report(root: Path = DEMO):  # type: ignore[no-untyped-def]
    board = load_board(root / "proofboard.toml")
    lock = plan_seal(root, board, None, NOW).entries
    return evaluate(root, board, lock, NOW)


@pytest.mark.parametrize(
    ("name", "make"),
    [
        ("demo.board.md", render.markdown),
        ("demo.board.html", render.html_page),
        ("demo.board.json", render.as_json),
        ("demo.check.txt", render.text),
    ],
)
def test_golden(name: str, make) -> None:  # type: ignore[no-untyped-def]
    got = make(demo_report())
    path = GOLDEN / name
    if os.environ.get("UPDATE_GOLDEN"):
        path.parent.mkdir(exist_ok=True)
        path.write_text(got, encoding="utf-8", newline="\n")
    assert got == path.read_text(encoding="utf-8")


HOSTILE = (
    "<script>alert(1)</script> [x](javascript:alert(1)) | **bold** `code` & <img src=x onerror=1>"
)


def hostile_project(tmp_path: Path) -> Path:
    (tmp_path / "e.txt").write_text("ok", encoding="utf-8")
    (tmp_path / "p.toml").write_text(
        f"[board]\ntitle = {json.dumps(HOSTILE)}\nsubject = {json.dumps(HOSTILE)}\n"
        f'[[claim]]\nid = "a"\ntitle = {json.dumps(HOSTILE)}\nstatement = {json.dumps(HOSTILE)}\n'
        f'[[claim.evidence]]\npath = "e.txt"\ncontains = {json.dumps(HOSTILE)}\n',
        encoding="utf-8",
    )
    return tmp_path


def test_hostile_text_is_inert(tmp_path: Path) -> None:
    root = hostile_project(tmp_path)
    board = load_board(root / "p.toml")
    report = evaluate(root, board, {}, NOW)
    page = render.html_page(report)
    assert "<script>" not in page and "<img" not in page
    body = render.markdown(report)
    assert "<script" not in body and "<img" not in body
    assert "](javascript" not in body and "\\[x\\]\\(javascript" in body
    assert "\n" not in render.md("a\nb\r\nc") and render.md("a|b") == "a\\|b"
    doc = json.loads(render.as_json(report))
    assert doc["title"] == HOSTILE


def test_fuzzed_claims_files_never_crash(tmp_path: Path) -> None:
    """Random byte-level damage to a valid claims file ends in a clean error or a report."""
    from proofboard.errors import ProofBoardError

    rng = random.Random(7)
    seed = (DEMO / "proofboard.toml").read_bytes()
    for _ in range(300):
        data = bytearray(seed)
        for _ in range(rng.randint(1, 6)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        cfg = tmp_path / "f.toml"
        cfg.write_bytes(bytes(data))
        try:
            board = load_board(cfg)
        except ProofBoardError:
            continue
        report = evaluate(DEMO, board, {}, NOW)
        for make in (render.markdown, render.html_page, render.as_json, render.text):
            assert make(report)
