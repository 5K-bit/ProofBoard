# ProofBoard: Orchard Sync

Subject: orchard-sync 2.4.0 \(a made-up project used to demonstrate ProofBoard\)

Checked 2026-10-29T17:00:00Z · 4 claims: 4 passed

| Status | Claim | Evidence |
|---|---|---|
| CHECKS PASSED | The test suite passes with strong coverage | 2 of 2 in order |
| CHECKS PASSED | A backup can be restored | 1 of 1 in order |
| CHECKS PASSED | No runtime dependencies | 1 of 1 in order |
| CHECKS PASSED | The threat model was reviewed this quarter | 1 of 1 in order |

## The test suite passes with strong coverage

`tests-pass` · **CHECKS PASSED**

Every test in the recorded run passed, and line coverage is at least 90%.

- **ok** `evidence/junit.xml` · sha256 06415b637fb1 · sealed 2026-10-29T17:00:00Z: matches the sealed record
  - met: 148 tests, 0 failures, 0 errors
- **ok** `evidence/coverage.xml` · sha256 8635e19b1441 · sealed 2026-10-29T17:00:00Z: matches the sealed record
  - met: coverage 93.4% \(needs at least 90%\)

## A backup can be restored

`restore-drill` · **CHECKS PASSED**

The last restore drill rebuilt the data and every checksum matched.

- **ok** `evidence/restore-drill.txt` · sha256 dc0beaca0e6d · sealed 2026-10-29T17:00:00Z: matches the sealed record
  - met: contains "drill: ok"
  - met: contains "checksums matched: 214 of 214"
  - met: does not contain "mismatch"

## No runtime dependencies

`no-runtime-deps` · **CHECKS PASSED**

The package installs nothing besides itself.

- **ok** `evidence/pyproject-excerpt.toml` · sha256 e1e75b2f84eb · sealed 2026-10-29T17:00:00Z: matches the sealed record
  - met: matches /^dependencies = \\\[\\\]$/

## The threat model was reviewed this quarter

`threat-model-reviewed` · **CHECKS PASSED**

- **ok** `docs/threat-model-review.md` · sha256 00400a3209a5 · sealed 2026-10-29T17:00:00Z: matches the sealed record
  - met: contains "Reviewed by"

_ProofBoard 0.1.1. Checks what is recorded; it cannot tell whether the evidence itself was honest._
