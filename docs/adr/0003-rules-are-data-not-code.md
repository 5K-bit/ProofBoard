# ADR 0003: Rules are data, never code

**Status:** accepted

A claims file could have allowed a shell command per claim ("run this and see"). That would make a pull request that edits `proofboard.toml` equivalent to running code in CI. Instead each evidence file has a fixed set of declarative rules (`contains`, `matches`, `coverage_min`, `junit_clean`), implemented in the standard library. Nothing from the claims file or from evidence is executed or imported.

**Consequence:** ProofBoard does not run your tests. You run them, keep the output, and ProofBoard checks the output.
