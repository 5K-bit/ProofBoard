"""Errors that are reported to the user without a traceback."""

from __future__ import annotations

from pathlib import Path


class ProofBoardError(Exception):
    """A problem with the claims file, the lock, a path or the command line."""


def below_a_file(path: Path) -> bool:
    """True if some parent of path is a regular file, so it can never exist (ENOTDIR).

    POSIX reports that as NotADirectoryError, Windows as FileNotFoundError; callers use this
    to give both the same "cannot read" answer instead of "not found".
    """
    return any(parent.is_file() for parent in path.parents)
