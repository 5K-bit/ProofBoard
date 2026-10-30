# ADR 0005: A case study is a set of claims

**Status:** accepted

A portfolio write-up makes statements (a problem existed, a decision was taken, tests passed) that go stale like any README. Instead of a second mechanism, each `[[story]]` sentence is parsed into an ordinary claim (`story-<section>-<n>`) with its evidence, so sealing, drift detection, staleness and the lock all apply unchanged.

- Every sentence must cite at least one evidence file, so nothing can be asserted without something to point at.
- The six sections are fixed (problem, evidence, decision, implementation, verification, limits) so write-ups are comparable.
- `scaffold` writes structure from files that already exist and leaves `TODO` for human sentences; a draft with `TODO` will not load, so an unfinished draft cannot be sealed or published by accident.
- Links to commits or issues are shown but never fetched, and are labelled as unchecked.

**Consequence:** a case study appears as claims in `check` and `board` output. That is intended: the write-up is held to the same standard as the project.
