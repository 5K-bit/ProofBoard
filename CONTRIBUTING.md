# Contributing

Thanks for your interest in PacketStory.

## Ways to help

- Report a status that was wrong (a claim shown as proven when it should not be, or the reverse) with a minimal claims file and made-up evidence.
- Add a content rule (see [docs/architecture.md](docs/architecture.md#adding-a-rule)) or improve the report wording and docs.

## Development

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy
python -m pytest --cov                            # must pass before you open a PR
python examples/acceptance.py --out /tmp/evidence # the demo workflow end to end
proofboard check                                  # this repository's own claims
```

## Guidelines

- The core uses only the Python standard library.
- No network calls, and nothing from a claims file or evidence is ever executed.
- Treat claims files, locks and evidence as hostile: validate paths, cap sizes, refuse XML entities.
- A new rule needs a named failure message and tests on both sides of its threshold.
- Changing output on purpose? Regenerate the golden files with `UPDATE_GOLDEN=1 python -m pytest tests/unit/test_render_fuzz.py` and the evidence with `python examples/acceptance.py --out docs/evidence`, review the diff, then re-seal this repository (`proofboard seal --accept-changes`) and review the lock diff.
- Demo content must be made up. Never commit real logs, reports or customer data.
- Do not add claims (performance, platform support, security) that a test or recorded evidence does not back up. Add the claim to `proofboard.toml` instead.
- Use clear commit messages and keep pull requests focused.
