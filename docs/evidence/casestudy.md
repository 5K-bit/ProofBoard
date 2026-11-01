# ProofBoard: claims tied to evidence you can re-check

proofboard 0.1.0 · By Louis Boddie · [repository](https://github.com/5K-bit/ProofBoard)

A small command-line tool that links each claim about a project to the evidence files behind it, seals their SHA-256, and reports when that evidence changes, goes missing, fails a rule or goes stale.

> As of 2026-11-01T19:21:47Z, all 11 statements are backed by sealed, unchanged evidence.

## The problem

1. The evidence behind a claim can be edited, deleted or left to age while the claim keeps being repeated, and nothing in a normal repository notices. The recorded demo walks one made-up project through exactly those three failures. **[CHECKS PASSED]**
   - evidence: [`docs/evidence/acceptance-transcript.txt`](docs/evidence/acceptance-transcript.txt), sha256 5bd675e35f3a

## What the evidence showed

2. In that recording all four claims read passed after sealing; after the restore drill is edited one reads drifted and a repeat seal is refused; after enough time all four read stale. **[CHECKS PASSED]**
   - evidence: [`docs/evidence/acceptance-transcript.txt`](docs/evidence/acceptance-transcript.txt), sha256 5bd675e35f3a

## Decisions

3. Evidence is sealed by SHA-256 rather than by file time, because modification times change on every checkout and can be set by anyone. **[CHECKS PASSED]**
   - evidence: [`docs/adr/0001-seal-by-hash-not-by-timestamp.md`](docs/adr/0001-seal-by-hash-not-by-timestamp.md), sha256 b904e054f54b
4. Sealing refuses to overwrite a changed hash unless told the change is expected, so the seal command cannot be used to turn a red board green by accident. **[CHECKS PASSED]**
   - evidence: [`docs/adr/0002-seal-refuses-silent-changes.md`](docs/adr/0002-seal-refuses-silent-changes.md), sha256 65f3f2239da2
5. Rules are data, not code: a claims file cannot run a command, so editing it in a pull request is not the same as running code in CI. **[CHECKS PASSED]**
   - evidence: [`docs/adr/0003-rules-are-data-not-code.md`](docs/adr/0003-rules-are-data-not-code.md), sha256 5264b129bc47

## Implementation

6. A strict claims-file parser, a hash ledger with its own digest, a pure planner for sealing, and an evaluator that gives each claim the worst status among its evidence, with text, Markdown, HTML and JSON reports. **[CHECKS PASSED]**
   - evidence: [`docs/architecture.md`](docs/architecture.md), sha256 384dc50499cf

## Verification

7. The recorded run of the test suite passed with coverage above 90%. **[CHECKS PASSED]**
   - evidence: [`docs/evidence/test-run.txt`](docs/evidence/test-run.txt), sha256 c2c38bca2ceb
8. Hostile claims files and evidence are covered by tests: unsafe paths, XML with entities \(also when re-encoded as UTF-16\), markup in text, and mutated claims files. **[CHECKS PASSED]**
   - evidence: [`tests/unit/test_render_fuzz.py`](tests/unit/test_render_fuzz.py), sha256 cf1401d414b4
   - evidence: [`tests/unit/test_model_checks.py`](tests/unit/test_model_checks.py), sha256 996e4a55dd1c
   - evidence: [`tests/unit/test_xml_encodings.py`](tests/unit/test_xml_encodings.py), sha256 610d0c1cf6e5

## Remaining limits

9. A seal proves a file is what it was when sealed, not that it was honest; a sealed false log reads as passed. **[CHECKS PASSED]**
   - evidence: [`README.md`](README.md), sha256 d12cd7844c86
10. The lock is tamper-evident, not signed: anyone who can rewrite both the lock and the evidence can make a board green. **[CHECKS PASSED]**
   - evidence: [`README.md`](README.md), sha256 d12cd7844c86
11. It has only been tried on made-up projects, and not yet by hand on Windows. **[CHECKS PASSED]**
   - evidence: [`README.md`](README.md), sha256 d12cd7844c86

## Development practice

AI tools assist with implementation, debugging, tests, and documentation.

Louis Boddie owns project direction and acceptance decisions; linked tests and release evidence document what has been verified.

_Built with ProofBoard 0.1.0. Each statement is checked against evidence files recorded in a lock; that shows the evidence is unchanged, not that it is true._
