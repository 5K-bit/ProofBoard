"""Command line: init, seal, check, board, casestudy, scaffold."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, casestudy, render
from .errors import ProofBoardError
from .evaluate import evaluate
from .ledger import LOCK_NAME, load_lock, now_utc, parse_time, write_lock
from .model import load_board
from .seal import plan_seal

CONFIG_NAME = "proofboard.toml"

STARTER = """\
# ProofBoard claims file. Each claim names evidence files in this project.
# Run 'proofboard seal' once the evidence is in place, then 'proofboard check' any time.

[board]
title = "My project"
subject = "my-project 0.1.0"
default_max_age_days = 90

[[claim]]
id = "tests-pass"
title = "The test suite passes"
statement = "The recorded run of the whole suite finished with no failures."

  [[claim.evidence]]
  path = "docs/evidence/test-run.txt"
  contains = "passed"
  not_contains = "failed"
  coverage_min = 80
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proofboard", description="Tie every claim to evidence you can re-check."
    )
    parser.add_argument("--version", action="version", version=f"proofboard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser, *, now: bool = True) -> None:
        p.add_argument("-C", "--root", default=".", help="project folder (default: .)")
        p.add_argument("--config", help=f"claims file (default: ROOT/{CONFIG_NAME})")
        p.add_argument("--lock", help=f"lock file (default: ROOT/{LOCK_NAME})")
        if now:
            p.add_argument("--now", help="treat this ISO 8601 time as the current time")

    init = sub.add_parser("init", help="write a starter claims file")
    init.add_argument("-C", "--root", default=".")
    init.add_argument("--force", action="store_true", help="overwrite an existing file")

    seal = sub.add_parser("seal", help="record the SHA-256 of every evidence file")
    common(seal)
    seal.add_argument("--accept-changes", action="store_true", help="allow sealed files to change")
    seal.add_argument("--refresh", action="store_true", help="re-date unchanged evidence too")

    check = sub.add_parser("check", help="verify every claim; exit 2 if any has not passed")
    common(check)
    check.add_argument("--format", choices=["text", "json"], default="text")

    board = sub.add_parser("board", help="write the full board as Markdown, HTML or JSON")
    common(board)
    board.add_argument("--format", choices=["md", "html", "json"], default="md")
    board.add_argument("--out", help="write to this file instead of the screen")
    board.add_argument("--strict", action="store_true", help="exit 2 if any claim has not passed")

    story = sub.add_parser(
        "casestudy", help="render the case study: every sentence next to its evidence status"
    )
    common(story)
    story.add_argument("--format", choices=["md", "html"], default="md")
    story.add_argument("--out", help="write to this file instead of the screen")
    story.add_argument("--strict", action="store_true", help="exit 2 unless every statement passed")
    story.add_argument("--allow-missing", action="store_true", help="allow an empty section")

    scaffold = sub.add_parser(
        "scaffold", help="draft a case study from the ADRs, test logs, screenshots and README"
    )
    scaffold.add_argument("-C", "--root", default=".")
    scaffold.add_argument("--out", help="draft file (default: ROOT/casestudy.draft.toml)")
    scaffold.add_argument("--force", action="store_true", help="overwrite an existing draft")
    return parser


def _paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    root = Path(args.root)
    if not root.is_dir():
        raise ProofBoardError(f"not a folder: {root}")
    config = Path(args.config) if args.config else root / CONFIG_NAME
    lock = Path(args.lock) if args.lock else root / LOCK_NAME
    return root, config, lock


def _now(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    return parse_time(args.now) if getattr(args, "now", None) else now_utc()


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _init(args: argparse.Namespace) -> int:
    target = Path(args.root) / CONFIG_NAME
    if target.exists() and not args.force:
        raise ProofBoardError(f"{target} already exists (use --force to overwrite)")
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_text(target, STARTER)
    print(f"wrote {target}")
    return 0


def _seal(args: argparse.Namespace) -> int:
    root, config, lock_path = _paths(args)
    board = load_board(config)
    outcome = plan_seal(root, board, load_lock(lock_path), _now(args), refresh=args.refresh)
    if outcome.changed and not args.accept_changes:
        print("These sealed files have changed. Nothing was written.", file=sys.stderr)
        for path in outcome.changed:
            print(f"  changed: {path}", file=sys.stderr)
        print("If the change is expected, run again with --accept-changes.", file=sys.stderr)
        return 2
    write_lock(lock_path, outcome.entries)
    print(
        f"sealed {len(outcome.entries)} files: {len(outcome.new)} new, {len(outcome.changed)} "
        f"changed, {len(outcome.refreshed)} refreshed, {len(outcome.unchanged)} unchanged"
    )
    for path in outcome.dropped:
        print(f"  no longer referenced, dropped: {path}")
    return 0


def _report(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    root, config, lock_path = _paths(args)
    board = load_board(config)
    return evaluate(root, board, load_lock(lock_path), _now(args))


def _check(args: argparse.Namespace) -> int:
    report = _report(args)
    sys.stdout.write(render.as_json(report) if args.format == "json" else render.text(report))
    return 0 if report.all_passed else 2


def _board(args: argparse.Namespace) -> int:
    report = _report(args)
    body = {"md": render.markdown, "html": render.html_page, "json": render.as_json}[args.format](
        report
    )
    if args.out:
        _write_text(Path(args.out), body)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(body)
    return 2 if args.strict and not report.all_passed else 0


def _casestudy(args: argparse.Namespace) -> int:
    root, _, _ = _paths(args)
    report = _report(args)
    if args.format == "html":
        body = casestudy.html_page(report, root, allow_missing=args.allow_missing)
    else:
        body = casestudy.markdown(report, allow_missing=args.allow_missing)
    if args.out:
        _write_text(Path(args.out), body)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(body)
    return 2 if args.strict and not casestudy.all_story_proven(report) else 0


def _scaffold(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.is_dir():
        raise ProofBoardError(f"not a folder: {root}")
    target = Path(args.out) if args.out else root / "casestudy.draft.toml"
    if target.exists() and not args.force:
        raise ProofBoardError(f"{target} already exists (use --force to overwrite)")
    _write_text(target, casestudy.draft(root))
    print(f"wrote {target}")
    print("Replace each TODO with a sentence you can stand behind, then merge it into the claims.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    handlers = {
        "init": _init,
        "seal": _seal,
        "check": _check,
        "board": _board,
        "casestudy": _casestudy,
        "scaffold": _scaffold,
    }
    try:
        return handlers[args.command](args)
    except ProofBoardError as exc:
        print(f"proofboard: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"proofboard: {exc.strerror or exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:  # pragma: no cover - reader closed the pipe
        os._exit(1)
