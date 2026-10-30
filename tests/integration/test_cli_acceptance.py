from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from proofboard.cli import main

from ..conftest import DEMO, NOW

ROOT = Path(__file__).resolve().parent.parent.parent


def run(*argv: str) -> int:
    return main(list(argv))


def test_init_check_seal_flow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert run("init", "-C", str(tmp_path)) == 0
    assert run("init", "-C", str(tmp_path)) == 1  # refuses to overwrite
    assert run("init", "-C", str(tmp_path), "--force") == 0
    (tmp_path / "docs" / "evidence").mkdir(parents=True)
    (tmp_path / "docs" / "evidence" / "test-run.txt").write_text(
        "10 passed\nTOTAL 100 5 95%\n", encoding="utf-8"
    )
    assert run("check", "-C", str(tmp_path), "--now", NOW) == 2
    assert run("seal", "-C", str(tmp_path), "--now", NOW) == 0
    assert run("check", "-C", str(tmp_path), "--now", NOW) == 0
    capsys.readouterr()
    assert run("check", "-C", str(tmp_path), "--now", NOW, "--format", "json") == 0
    assert json.loads(capsys.readouterr().out)["all_proven"] is True


def test_seal_refuses_changes_until_accepted(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run("seal", "-C", str(project), "--now", NOW) == 0
    (project / "ev" / "run.txt").write_text("4 passed\n", encoding="utf-8")
    before = (project / "proofboard.lock.json").read_text(encoding="utf-8")
    assert run("seal", "-C", str(project), "--now", NOW) == 2
    assert (project / "proofboard.lock.json").read_text(encoding="utf-8") == before
    assert "changed: ev/run.txt" in capsys.readouterr().err
    assert run("seal", "-C", str(project), "--now", NOW, "--accept-changes") == 0
    assert run("check", "-C", str(project), "--now", NOW) == 0


def test_dropped_evidence_is_reported(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run("seal", "-C", str(project), "--now", NOW)
    (project / "proofboard.toml").write_text(
        '[board]\ntitle = "T"\n[[claim]]\nid = "a"\ntitle = "A"\n', encoding="utf-8"
    )
    capsys.readouterr()
    assert run("seal", "-C", str(project), "--now", NOW) == 0
    assert "dropped: ev/run.txt" in capsys.readouterr().out


def test_errors_exit_1(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    empty = project / "empty"
    empty.mkdir()
    assert run("check", "-C", str(empty)) == 1
    assert run("check", "-C", str(project / "nope")) == 1
    assert run("check", "-C", str(project), "--now", "soon") == 1
    (project / "proofboard.lock.json").write_text("garbage", encoding="utf-8")
    assert run("check", "-C", str(project), "--now", NOW) == 1
    assert "proofboard:" in capsys.readouterr().err
    assert run("board", "-C", str(project), "--out", str(project / "no" / "dir" / "x.md")) == 1


def test_board_formats_and_strict(
    project: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run("board", "-C", str(project), "--now", NOW, "--strict") == 2  # nothing sealed
    run("seal", "-C", str(project), "--now", NOW)
    for fmt, marker in (("md", "# ProofBoard"), ("html", "<!doctype html>"), ("json", '"claims"')):
        capsys.readouterr()
        assert run("board", "-C", str(project), "--format", fmt, "--now", NOW, "--strict") == 0
        assert marker in capsys.readouterr().out
    out = tmp_path / "board.md"
    assert run("board", "-C", str(project), "--now", NOW, "--out", str(out)) == 0
    assert out.read_text(encoding="utf-8").startswith("# ProofBoard")


def test_custom_config_and_lock(project: Path) -> None:
    cfg, lock = project / "alt.toml", project / "alt.lock"
    shutil.copy(project / "proofboard.toml", cfg)
    args = ["-C", str(project), "--config", str(cfg), "--lock", str(lock), "--now", NOW]
    assert run("seal", *args) == 0 and lock.exists()
    assert run("check", *args) == 0


def test_python_dash_m_and_version() -> None:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "proofboard", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and proc.stdout.startswith("proofboard 0.1.0")


@pytest.mark.skipif(sys.platform == "win32", reason="transcript records POSIX line endings only")
def test_acceptance_reproduces_recorded_evidence(tmp_path: Path) -> None:
    subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "examples" / "acceptance.py"), "--out", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    recorded = ROOT / "docs" / "evidence"
    for name in ("acceptance-transcript.txt", "board.md", "board.html", "board.json"):
        assert (tmp_path / name).read_text(encoding="utf-8") == (recorded / name).read_text(
            encoding="utf-8"
        ), name


def test_demo_project_is_untouched_by_tests() -> None:
    assert not (DEMO / "proofboard.lock.json").exists()
