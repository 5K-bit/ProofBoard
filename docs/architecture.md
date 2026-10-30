# Architecture

```
proofboard.toml ─► model ─► evaluate ─► render ─► text · Markdown · HTML · JSON
 (claims, rules)   validate   │  ▲
                              │  └── checks (content rules on each file)
proofboard.lock.json ─► ledger ┘
 (sealed SHA-256s)      digest-verified
```

| Module | Job |
|---|---|
| `model.py` | Parse and strictly validate the claims file into frozen dataclasses. Unknown keys, unsafe paths, duplicate ids and bad rules are errors. |
| `checks.py` | Content rules for one file: text, regex, coverage figure, JUnit totals. XML with a doctype or entities is refused. |
| `ledger.py` | Hash files, read and write the lock, verify the lock's own digest, parse times. |
| `seal.py` | Plan a seal: new, changed, unchanged, refreshed and dropped evidence. Pure; the CLI decides whether to write. |
| `evaluate.py` | Combine claims, files and lock into a status per evidence file and per claim. |
| `render.py` | Text, Markdown, HTML and JSON. All text from the claims or evidence is escaped. |
| `cli.py` | `init`, `seal`, `check`, `board` and the exit codes. |

## Statuses

Each evidence file gets one status, and a claim takes the worst of its files.

| Status | Meaning |
|---|---|
| `failed` | A content rule is not met, or the path leaves the project through a link |
| `missing` | The file is not there |
| `drifted` | The file's hash differs from the sealed one |
| `unsealed` | The file is not in the lock yet |
| `stale` | Sealed longer ago than the claim's `max_age_days` |
| `ok` | Present, rules met, hash matches, fresh enough |

A claim with no evidence is `unsupported` ("no evidence"); a board with no claims is never "all proven".

## Why a lock and not just rules

Rules say what the evidence must contain *now*. The lock says it is the same file that was accepted *then*. Together they catch both a log edited after the fact (drift) and a fresh run that no longer meets the claim (failed). Time is injected (`--now`), so every report is reproducible.

## Adding a rule

1. Add the field to `Rule` and `_rule()` in `model.py` (and to the allowed keys in `parse_board`).
2. Implement it in `inspect()` in `checks.py`, returning a `CheckResult` with a short `detail`.
3. Test both sides of its threshold in `tests/unit/test_model_checks.py`, and add a case to the fuzz test if it parses structured input.
4. Document it in the README table.
