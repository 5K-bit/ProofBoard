# ADR 0001: Seal evidence by SHA-256, not by file time

**Status:** accepted

File modification times change on every checkout, copy and download, and can be set by anyone. A SHA-256 recorded in a lock file does not move unless the content does. The lock records when each file was sealed (for staleness), but "has it changed" is always decided by the hash.

**Consequence:** a re-run that produces a different log needs a deliberate re-seal. That friction is the point.
