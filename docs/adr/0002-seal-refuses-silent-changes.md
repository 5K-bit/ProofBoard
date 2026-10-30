# ADR 0002: `seal` refuses to overwrite a changed hash

**Status:** accepted

If sealing always wrote the current hashes, "seal" would be a button that turns any red board green. `seal` therefore stops (exit 2, nothing written) when a file already in the lock has a different hash, and lists the files. `--accept-changes` is the explicit statement that the change is expected, and it shows up in the command history and the lock diff.

`--refresh` re-dates unchanged evidence without touching hashes; it is the deliberate answer to "stale".
