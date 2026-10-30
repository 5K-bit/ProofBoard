# ADR 0004: Time is an input

**Status:** accepted

Staleness depends on "now". Every command that needs it accepts `--now`, and reports print the time they were checked at. This makes golden files and the recorded acceptance transcript reproducible, and lets CI re-check an old lock as of a chosen date.
