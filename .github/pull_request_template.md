## Summary

## Testing
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `mypy` passes
- [ ] `python -m pytest --cov` passes
- [ ] Changes to claims, rules, locks or paths have a test with a hostile or damaged input
- [ ] No network calls (ProofBoard reads files and writes a report)
- [ ] Golden files and `docs/evidence` regenerated and reviewed (if output changed)
- [ ] `proofboard check` still passes on this repository (re-seal on purpose if evidence changed)
