from __future__ import annotations

from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "examples" / "demo"
NOW = "2026-10-29T17:00:00Z"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A small project with one claim and one evidence file."""
    (tmp_path / "ev").mkdir()
    (tmp_path / "ev" / "run.txt").write_text(
        "3 passed in 0.1s\nTOTAL 100 5 95%\n", encoding="utf-8"
    )
    (tmp_path / "proofboard.toml").write_text(
        '[board]\ntitle = "T"\n\n[[claim]]\nid = "a"\ntitle = "A"\n\n'
        '  [[claim.evidence]]\n  path = "ev/run.txt"\n  contains = "passed"\n',
        encoding="utf-8",
    )
    return tmp_path
