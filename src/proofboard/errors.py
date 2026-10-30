"""Errors that are reported to the user without a traceback."""

from __future__ import annotations


class ProofBoardError(Exception):
    """A problem with the claims file, the lock, a path or the command line."""
