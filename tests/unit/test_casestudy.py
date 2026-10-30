from __future__ import annotations

import base64
import random
import tomllib
from pathlib import Path
from typing import Any

import pytest

from proofboard import casestudy
from proofboard.cli import main
from proofboard.errors import ProofBoardError
from proofboard.evaluate import evaluate
from proofboard.ledger import load_lock, parse_time
from proofboard.model import load_board, parse_board

NOW = "2026-10-29T17:00:00Z"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def story_toml(*, items: str | None = None, head_extra: str = "") -> str:
    body = items if items is not None else _ITEMS
    return (
        '[board]\ntitle = "B"\n\n[casestudy]\ntitle = "My case study"\nsubject = "thing 1.0"\n'
        f'author = "Pat Example"\nsummary = "What it is."\n{head_extra}\n{body}'
    )


def item(section: str, text: str, extra: str = '[[story.evidence]]\npath = "ev/log.txt"\n') -> str:
    return f'[[story]]\nsection = "{section}"\ntext = "{text}"\n{extra}\n'


_ITEMS = (
    item("problem", "Restores were never tried.")
    + item("evidence", "The drill failed once.")
    + item("decision", "Hash every chunk.")
    + item("implementation", "Chunks plus a manifest.")
    + item(
        "verification",
        "Tests passed.",
        '[[story.evidence]]\npath = "ev/log.txt"\nmatches = "\\\\d+ passed"\n'
        '[[story.image]]\npath = "ev/shot.png"\nalt = "A screenshot"\n',
    )
    + item("limits", "Only tried on small folders.")
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "ev").mkdir()
    (tmp_path / "ev" / "log.txt").write_text("5 passed in 0.2s\n", encoding="utf-8")
    (tmp_path / "ev" / "shot.png").write_bytes(PNG)
    (tmp_path / "proofboard.toml").write_text(story_toml(), encoding="utf-8")
    return tmp_path


def run(project: Path, *args: str) -> int:
    return main([*args, "-C", str(project)])


# ---- parsing ----------------------------------------------------------------------------------


def test_story_statements_become_claims() -> None:
    board = parse_board(tomllib.loads(story_toml()))
    assert board.story is not None and board.story.author == "Pat Example"
    assert [c.id for c in board.claims] == [
        "story-problem-1",
        "story-evidence-1",
        "story-decision-1",
        "story-implementation-1",
        "story-verification-1",
        "story-limits-1",
    ]
    verification = board.claims[4]
    assert [e.path for e in verification.evidence] == ["ev/log.txt", "ev/shot.png"]  # image added
    assert board.story.items[4].images[0].alt == "A screenshot"


def test_a_file_without_a_story_is_unchanged() -> None:
    board = parse_board(tomllib.loads('[board]\ntitle = "T"\n'))
    assert board.story is None and board.claims == ()


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (item("problem", "x", ""), "needs evidence"),
        (item("nonsense", "x"), "section"),
        (item("problem", "TODO: write this"), "TODO"),
        (item("problem", "   "), "non-empty"),
        (item("problem", "x", '[[story.evidence]]\npath = "../etc/passwd"\n'), "must not contain"),
        (
            item(
                "problem",
                "x",
                'links = ["http://insecure.example"]\n[[story.evidence]]\npath = "a"\n',
            ),
            "https",
        ),
        (
            item(
                "problem",
                "x",
                'links = ["https://a.example/<b>"]\n[[story.evidence]]\npath = "a"\n',
            ),
            "https",
        ),
        (
            item("problem", "x", '[[story.image]]\npath = "ev/run.exe"\nalt = "a"\n'),
            "must be one of",
        ),
        (item("problem", "x", '[[story.image]]\npath = "ev/a.png"\nalt = ""\n'), "non-empty"),
        (item("problem", "x", '[[story.evidence]]\npath = "a"\nbogus = 1\n'), "unknown"),
        (item("problem", "x", 'colour = "red"\n[[story.evidence]]\npath = "a"\n'), "unknown"),
    ],
)
def test_bad_statements(items: str, message: str) -> None:
    with pytest.raises(ProofBoardError, match=message):
        parse_board(tomllib.loads(story_toml(items=items)))


@pytest.mark.parametrize(
    ("head", "message"),
    [
        ('repo = "http://x.example"', "https"),
        ('repo = "javascript:alert(1)"', "https"),
        ("bogus = 1", "unknown"),
    ],
)
def test_bad_header(head: str, message: str) -> None:
    with pytest.raises(ProofBoardError, match=message):
        parse_board(tomllib.loads(story_toml(head_extra=head)))


def test_story_needs_a_casestudy_table_and_a_real_title() -> None:
    with pytest.raises(ProofBoardError, match=r"\[casestudy\]"):
        parse_board(tomllib.loads('[board]\ntitle = "B"\n' + item("problem", "x")))
    raw = story_toml().replace('title = "My case study"', 'title = "TODO"')
    with pytest.raises(ProofBoardError, match="TODO"):
        parse_board(tomllib.loads(raw))
    raw = story_toml().replace('author = "Pat Example"', 'author = ""')
    with pytest.raises(ProofBoardError, match="non-empty"):
        parse_board(tomllib.loads(raw))


def test_too_many_statements() -> None:
    many = item("problem", "x") * 201
    with pytest.raises(ProofBoardError, match="at most 200"):
        parse_board(tomllib.loads(story_toml(items=many)))


# ---- rendering --------------------------------------------------------------------------------


def sealed(project: Path) -> None:
    assert main(["seal", "-C", str(project), "--now", NOW]) == 0


def test_markdown_shows_every_sentence_with_its_status(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sealed(project)
    capsys.readouterr()
    assert main(["casestudy", "-C", str(project), "--now", NOW, "--strict"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# My case study")
    assert "all 6 statements are backed by sealed, unchanged evidence" in out
    for title in casestudy.TITLES.values():
        assert f"## {title}" in out
    assert "1. Restores were never tried. **[PROVEN]**" in out
    assert "![A screenshot](ev/shot.png)" in out
    assert "AI tools assist with implementation, debugging, tests, and documentation." in out
    assert "Pat Example owns project direction and acceptance decisions" in out


def test_drift_is_flagged_in_the_page_and_fails_strict(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sealed(project)
    (project / "ev" / "log.txt").write_text("5 passed in 0.2s\n(edited later)\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["casestudy", "-C", str(project), "--now", NOW, "--strict"]) == 2
    out = capsys.readouterr().out
    assert "**[DRIFTED]**" in out and "changed since it was sealed" in out
    assert "only 0 of 6 statements" in out or "of 6 statements are backed" in out


def test_unsealed_is_not_proven(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["casestudy", "-C", str(project), "--now", NOW, "--strict"]) == 2
    assert "UNSEALED" in capsys.readouterr().out


def test_html_is_self_contained_and_escaped(project: Path, tmp_path: Path) -> None:
    raw = (project / "proofboard.toml").read_text(encoding="utf-8")
    raw = raw.replace("Restores were never tried.", "<script>alert(1)</script> & more")
    raw = raw.replace('summary = "What it is."', 'summary = "<b>bold</b>"')
    (project / "proofboard.toml").write_text(raw, encoding="utf-8")
    sealed(project)
    out_file = project / "cs.html"
    assert (
        main(
            [
                "casestudy",
                "-C",
                str(project),
                "--now",
                NOW,
                "--format",
                "html",
                "--out",
                str(out_file),
            ]
        )
        == 0
    )
    page = out_file.read_text(encoding="utf-8")
    assert "<script>" not in page and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; more" in page
    assert "&lt;b&gt;bold&lt;/b&gt;" in page
    assert 'src="data:image/png;base64,' in page and "http://" not in page.replace(
        "http://www.w3.org", ""
    )
    assert page.count("<h2>") == 7  # six sections plus Development practice


def test_markdown_text_is_inert(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raw = (project / "proofboard.toml").read_text(encoding="utf-8")
    raw = raw.replace("Hash every chunk.", "[click](http://evil.example) <img src=x onerror=1>")
    (project / "proofboard.toml").write_text(raw, encoding="utf-8")
    capsys.readouterr()
    main(["casestudy", "-C", str(project), "--now", NOW])
    out = capsys.readouterr().out
    assert "<img" not in out and "](http://evil.example)" not in out.replace("\\]\\(http", "")


def test_links_are_listed_but_labelled_unchecked(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = (project / "proofboard.toml").read_text(encoding="utf-8")
    raw = raw.replace(
        'text = "Hash every chunk."\n',
        'text = "Hash every chunk."\nlinks = ["https://github.com/o/r/commit/abc123"]\n',
    )
    (project / "proofboard.toml").write_text(raw, encoding="utf-8")
    capsys.readouterr()
    main(["casestudy", "-C", str(project), "--now", NOW])
    out = capsys.readouterr().out
    assert "link (not checked by ProofBoard): <https://github.com/o/r/commit/abc123>" in out
    main(["casestudy", "-C", str(project), "--now", NOW, "--format", "html"])
    assert 'rel="noopener noreferrer"' in capsys.readouterr().out


def test_missing_section_is_an_error_unless_allowed(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = (project / "proofboard.toml").read_text(encoding="utf-8")
    start = raw.index('[[story]]\nsection = "limits"')
    (project / "proofboard.toml").write_text(raw[:start], encoding="utf-8")
    assert main(["casestudy", "-C", str(project), "--now", NOW]) == 1
    assert "no statement in: limits" in capsys.readouterr().err
    assert main(["casestudy", "-C", str(project), "--now", NOW, "--allow-missing"]) == 0
    assert "No statement in this section yet." in capsys.readouterr().out


def test_no_casestudy_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "proofboard.toml").write_text('[board]\ntitle = "T"\n', encoding="utf-8")
    assert main(["casestudy", "-C", str(tmp_path)]) == 1
    assert "no [casestudy] table" in capsys.readouterr().err


def test_images_that_cannot_be_embedded(project: Path) -> None:
    lock = load_lock(project / "proofboard.lock.json")
    report = evaluate(project, load_board(project / "proofboard.toml"), lock, parse_time(NOW))
    (project / "ev" / "shot.png").write_bytes(b"x" * ((2 << 20) + 1))
    assert "not embedded" in casestudy.html_page(report, project)
    (project / "ev" / "shot.png").unlink()
    assert "image not found" in casestudy.html_page(report, project)
    link = project / "ev" / "shot.png"
    outside = project.parent / "outside.png"
    outside.write_bytes(PNG)
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):  # pragma: no cover - Windows without privilege
        return
    assert "image not found" in casestudy.html_page(report, project)


# ---- drafting ---------------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    (docs / "adr").mkdir(parents=True)
    (docs / "evidence" / "screens").mkdir(parents=True)
    (docs / "adr" / "0001-use-hashes.md").write_text(
        "# ADR 0001: Use hashes\n\nBecause.\n", encoding="utf-8"
    )
    (docs / "adr" / "0002-plain.md").write_text("# 2. Plain numbered title\n", encoding="utf-8")
    (docs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (docs / "evidence" / "test-run.txt").write_text(
        "TOTAL 100 5 95%\n12 passed in 0.5s\n", encoding="utf-8"
    )
    (docs / "evidence" / "notes.txt").write_text("not a test log\n", encoding="utf-8")
    (docs / "evidence" / "screens" / "main-view.png").write_bytes(PNG)
    (docs / "evidence" / "screens" / "logo.png").write_bytes(PNG)
    (tmp_path / "README.md").write_text(
        "# X\n\n## Limitations\n\n- **Estimates only.** Not a payslip, so do not rely on it.\n- short\n\n## Roadmap\n\n- later item here\n",
        encoding="utf-8",
    )
    return tmp_path


def test_scaffold_drafts_from_what_the_repo_holds(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scaffold", "-C", str(repo)]) == 0
    text = (repo / "casestudy.draft.toml").read_text(encoding="utf-8")
    assert "docs/adr/0001-use-hashes.md" in text and "TODO: why — Use hashes" in text
    assert "TODO: why — Plain numbered title" in text  # ADR number prefixes are dropped
    assert "docs/architecture.md" in text
    assert 'matches = "\\\\b\\\\d+ passed\\\\b"' in text and "coverage_min = 95" in text
    assert "notes.txt" not in text and "logo.png" not in text
    assert 'path = "docs/evidence/screens/main-view.png"' in text and 'alt = "Main view"' in text
    assert 'text = "Estimates only. Not a payslip, so do not rely on it."' in text
    assert 'contains = "**Estimates only.** Not a payslip, so do not rely "' in text
    assert "later item" not in text and '"short"' not in text
    # a draft refuses to load until its TODOs are written
    with pytest.raises(ProofBoardError, match="TODO"):
        load_board(repo / "casestudy.draft.toml")
    # and refuses to overwrite itself
    assert main(["scaffold", "-C", str(repo)]) == 1
    assert main(["scaffold", "-C", str(repo), "--force", "--out", str(repo / "d2.toml")]) == 0
    assert "wrote" in capsys.readouterr().out


def test_a_finished_draft_loads_and_every_limit_is_checkable(repo: Path) -> None:
    main(["scaffold", "-C", str(repo)])
    text = (repo / "casestudy.draft.toml").read_text(encoding="utf-8")
    text = text.replace('title = "TODO"', 'title = "Done"').replace(
        'subject = "TODO"', 'subject = "S"'
    )
    text = text.replace('author = "TODO"', 'author = "Pat Example"')
    for n, line in enumerate(
        [ln for ln in text.splitlines() if ln.startswith("text = ") and "TODO" in ln]
    ):
        text = text.replace(line, f'text = "Finished sentence number {n}."', 1)
    (repo / "proofboard.toml").write_text(text, encoding="utf-8")
    board = load_board(repo / "proofboard.toml")
    assert board.story is not None
    assert main(["seal", "-C", str(repo), "--now", NOW]) == 0
    assert (
        main(["check", "-C", str(repo), "--now", NOW]) == 0
    )  # the README limit text really is in README


def test_scaffold_on_an_empty_folder_and_bad_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scaffold", "-C", str(tmp_path)]) == 0
    assert "TODO" in (tmp_path / "casestudy.draft.toml").read_text(encoding="utf-8")
    assert main(["scaffold", "-C", str(tmp_path / "nope")]) == 1
    assert "not a folder" in capsys.readouterr().err


def test_unreadable_readme_and_adr_are_skipped(repo: Path) -> None:
    (repo / "docs" / "adr" / "0003-binary.md").write_bytes(b"\xff\xfe\x00bad")
    (repo / "README.md").unlink()
    (repo / "README.md").mkdir()  # a directory where a file should be
    assert main(["scaffold", "-C", str(repo)]) == 0


# ---- fuzz -------------------------------------------------------------------------------------


def test_mutated_story_files_end_cleanly(project: Path) -> None:
    rng = random.Random(7)
    base = story_toml()
    for _ in range(200):
        chars = list(base)
        for _ in range(rng.randrange(1, 6)):
            chars[rng.randrange(len(chars))] = rng.choice('"[]=\\\n#xTODO\x00é')
        raw: Any = "".join(chars)
        (project / "proofboard.toml").write_text(raw, encoding="utf-8")
        for argv in (["check"], ["casestudy"], ["casestudy", "--format", "html"]):
            code = main([*argv, "-C", str(project), "--now", NOW])
            assert code in (0, 1, 2)
