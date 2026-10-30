# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-29

First working version.

### Added

- A claims file (`proofboard.toml`) that links each claim to evidence files, with strict validation (unknown keys, bad paths and duplicate ids are errors).
- Content rules per evidence file: `contains`, `not_contains`, `matches`, `coverage_min` (coverage.xml, coverage.json or a pytest-cov `TOTAL` line) and `junit_clean`.
- A lock file recording the SHA-256 of every evidence file, with its own digest so hand edits are caught.
- Claim statuses: proven, stale, unsealed, drifted, missing, failed, no evidence.
- `proofboard init`, `seal` (refuses silent changes; `--accept-changes`, `--refresh`), `check` (exit 2 unless every claim is proven; text or JSON) and `board` (Markdown, HTML or JSON; `--strict`).
- A demo project and an acceptance script whose transcript is recorded in `docs/evidence/`.
