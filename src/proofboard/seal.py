"""Seal evidence: record each referenced file's SHA-256, refusing silent changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .errors import ProofBoardError
from .evaluate import resolve_inside
from .ledger import Entry, format_time, hash_file
from .model import Board


@dataclass
class SealOutcome:
    entries: dict[str, Entry]
    new: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    refreshed: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def plan_seal(
    root: Path,
    board: Board,
    lock: dict[str, Entry] | None,
    now: datetime,
    *,
    refresh: bool = False,
) -> SealOutcome:
    """Work out the new lock. Raises if any evidence file is missing or outside the folder."""
    old = lock or {}
    stamp = format_time(now)
    problems: list[str] = []
    outcome = SealOutcome(entries={})
    for path in board.evidence_paths():
        target = resolve_inside(root, path)
        if target is None:
            problems.append(f"{path}: resolves outside the project folder")
            continue
        if not target.is_file():
            problems.append(f"{path}: file not found")
            continue
        sha, size = hash_file(target)
        before = old.get(path)
        if before is None:
            outcome.new.append(path)
            outcome.entries[path] = Entry(sha, size, stamp)
        elif before.sha256 != sha:
            outcome.changed.append(path)
            outcome.entries[path] = Entry(sha, size, stamp)
        elif refresh:
            outcome.refreshed.append(path)
            outcome.entries[path] = Entry(sha, size, stamp)
        else:
            outcome.unchanged.append(path)
            outcome.entries[path] = before
    if problems:
        raise ProofBoardError("cannot seal:\n  " + "\n  ".join(problems))
    outcome.dropped = sorted(set(old) - set(outcome.entries))
    return outcome
