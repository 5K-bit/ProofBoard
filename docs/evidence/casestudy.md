# ProofBoard: claims tied to evidence you can re-check

proofboard 0.1.0 · By Louis Boddie · [repository](https://github.com/5K-bit/ProofBoard)

A small command-line tool that links each claim about a project to the evidence files behind it, seals their SHA-256, and reports when that evidence changes, goes missing, fails a rule or goes stale.

> As of 2026-10-30T12:00:00Z, all 11 statements are backed by sealed, unchanged evidence.

## The problem

1. The evidence behind a claim can be edited, deleted or left to age while the claim keeps being repeated, and nothing in a normal repository notices. The recorded demo walks one made-up project through exactly those three failures. **[PROVEN]**
   - evidence: [`docs/evidence/acceptance-transcript.txt`](docs/evidence/acceptance-transcript.txt), sha256 07ae788e57ae

## What the evidence showed

2. In that recording all four claims read proven after sealing; after the restore drill is edited one reads drifted and a repeat seal is refused; after enough time all four read stale. **[PROVEN]**
   - evidence: [`docs/evidence/acceptance-transcript.txt`](docs/evidence/acceptance-transcript.txt), sha256 07ae788e57ae

## Decisions

3. Evidence is sealed by SHA-256 rather than by file time, because modification times change on every checkout and can be set by anyone. **[PROVEN]**
   - evidence: [`docs/adr/0001-seal-by-hash-not-by-timestamp.md`](docs/adr/0001-seal-by-hash-not-by-timestamp.md), sha256 b904e054f54b
4. Sealing refuses to overwrite a changed hash unless told the change is expected, so the seal command cannot be used to turn a red board green by accident. **[PROVEN]**
   - evidence: [`docs/adr/0002-seal-refuses-silent-changes.md`](docs/adr/0002-seal-refuses-silent-changes.md), sha256 65f3f2239da2
5. Rules are data, not code: a claims file cannot run a command, so editing it in a pull request is not the same as running code in CI. **[PROVEN]**
   - evidence: [`docs/adr/0003-rules-are-data-not-code.md`](docs/adr/0003-rules-are-data-not-code.md), sha256 5264b129bc47

## Implementation

6. A strict claims-file parser, a hash ledger with its own digest, a pure planner for sealing, and an evaluator that gives each claim the worst status among its evidence, with text, Markdown, HTML and JSON reports. **[PROVEN]**
   - evidence: [`docs/architecture.md`](docs/architecture.md), sha256 85a520dbefcc

## Verification

7. The recorded run of the test suite passed with coverage above 90%. **[PROVEN]**
   - evidence: [`docs/evidence/test-run.txt`](docs/evidence/test-run.txt), sha256 501f4af5842d
8. Hostile claims files and evidence are covered by tests: unsafe paths, XML with entities, markup in text, and mutated claims files. **[PROVEN]**
   - evidence: [`tests/unit/test_render_fuzz.py`](tests/unit/test_render_fuzz.py), sha256 cf1401d414b4
   - evidence: [`tests/unit/test_model_checks.py`](tests/unit/test_model_checks.py), sha256 e69a0e53e1e8

## Remaining limits

9. A seal proves a file is what it was when sealed, not that it was honest; a sealed false log reads as proven. **[PROVEN]**
   - evidence: [`README.md`](README.md), sha256 370a27104b3f
10. The lock is tamper-evident, not signed: anyone who can rewrite both the lock and the evidence can make a board green. **[PROVEN]**
   - evidence: [`README.md`](README.md), sha256 370a27104b3f
11. It has only been tried on made-up projects, and not yet by hand on Windows. **[PROVEN]**
   - evidence: [`README.md`](README.md), sha256 370a27104b3f

## Development practice

AI tools assist with implementation, debugging, tests, and documentation.

Louis Boddie owns project direction and acceptance decisions; linked tests and release evidence document what has been verified.

_Built with ProofBoard 0.1.0. Each statement is checked against evidence files recorded in a lock; that shows the evidence is unchanged, not that it is true._
