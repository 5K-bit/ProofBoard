"""The lock file: SHA-256 of every evidence file at the moment it was sealed."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import ProofBoardError

LOCK_NAME = "proofboard.lock.json"
MAX_LOCK_BYTES = 4 << 20
HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Entry:
    sha256: str
    size: int
    sealed_at: str


def now_utc() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def parse_time(text: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ProofBoardError(f"not an ISO 8601 time: {text!r}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0)


def format_time(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _canonical(body: dict[str, Any]) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _body(entries: dict[str, Entry]) -> dict[str, Any]:
    return {
        "format": 1,
        "entries": {
            path: {"sha256": e.sha256, "size": e.size, "sealed_at": e.sealed_at}
            for path, e in sorted(entries.items())
        },
    }


def load_lock(path: Path) -> dict[str, Entry] | None:
    """Read the lock. None if there is no lock; ProofBoardError if it is damaged or edited."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ProofBoardError(f"cannot read {path}: {exc.strerror or exc}") from None
    if size > MAX_LOCK_BYTES:
        raise ProofBoardError(f"{path}: larger than {MAX_LOCK_BYTES >> 20} MiB")
    try:
        raw = json.loads(path.read_bytes())
        entries_raw = raw["entries"]
        if raw["format"] != 1 or not isinstance(entries_raw, dict):
            raise ValueError("unsupported format")
        entries: dict[str, Entry] = {}
        for name, item in entries_raw.items():
            sha, length, when = item["sha256"], item["size"], item["sealed_at"]
            if not (isinstance(sha, str) and HEX64.match(sha) and isinstance(length, int)):
                raise ValueError(f"bad entry for {name}")
            parse_time(when)
            entries[name] = Entry(sha, length, when)
        expected = hashlib.sha256(_canonical(_body(entries))).hexdigest()
        if raw.get("digest") != expected:
            raise ProofBoardError(
                f"{path}: its digest does not match its contents, so it was edited by hand or "
                "damaged. Restore it from version control, or re-seal deliberately."
            )
    except ProofBoardError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ProofBoardError(f"{path}: not a valid ProofBoard lock ({exc})") from None
    return entries


def write_lock(path: Path, entries: dict[str, Entry]) -> None:
    body = _body(entries)
    body["digest"] = hashlib.sha256(
        _canonical({k: body[k] for k in ("format", "entries")})
    ).hexdigest()
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temp, path)
