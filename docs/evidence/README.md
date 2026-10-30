# Evidence

Recorded outputs that the claims in [`proofboard.toml`](../../proofboard.toml) point at. ProofBoard checks them with `proofboard check`.

| File | What it is | How to reproduce |
|---|---|---|
| `test-run.txt` | The full test run with coverage (Linux, Python 3.13) | `python -m pytest --cov` |
| `acceptance-transcript.txt` | The demo workflow: seal, drift, failure, missing, stale | `python examples/acceptance.py --out docs/evidence` |
| `casestudy.md`, `casestudy.html` | This repository's own case study, rendered | `proofboard casestudy --format html --out docs/evidence/casestudy.html` (and `--format md`), after sealing |
| `board.md`, `board.html`, `board.json` | The demo project's board when everything is proven | same command |

Everything in the demo is made up (a fictional project called Orchard Sync). Nothing here was recorded on Windows or macOS; CI runs the tests on Windows.
