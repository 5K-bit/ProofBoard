# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- A claim whose checks all pass is now reported as `passed` / **CHECKS PASSED** (was `proven`), and `all_proven` in the JSON report is now `all_passed`. Matching a sealed file and the configured rules does not establish that a claim is true.

### Fixed

- `junit_clean` counted tests from the summary attributes, which default to zero, so a report with a `<failure>` element could pass. Totals now come from the `<testcase>` elements, and a report whose declared totals disagree with them is rejected.
- The XML entity filter matched ASCII byte patterns, so a UTF-16 document with an internal entity got through. Expat now screens every document for doctype and entity declarations before it is parsed.
- A path below a regular file reads as "cannot read" on Windows as well as POSIX (Windows reported it as missing), for the claims file and the lock.

## [0.1.0] - 2026-10-31

First working version.

### Added

- A claims file (`proofboard.toml`) that links each claim to evidence files, with strict validation (unknown keys, bad paths and duplicate ids are errors).
- Content rules per evidence file: `contains`, `not_contains`, `matches`, `coverage_min` (coverage.xml, coverage.json or a pytest-cov `TOTAL` line) and `junit_clean`.
- A lock file recording the SHA-256 of every evidence file, with its own digest so hand edits are caught.
- Claim statuses: passed, stale, unsealed, drifted, missing, failed, no evidence.
- `proofboard init`, `seal` (refuses silent changes; `--accept-changes`, `--refresh`), `check` (exit 2 unless every claim passes its checks; text or JSON) and `board` (Markdown, HTML or JSON; `--strict`).
- A demo project and an acceptance script whose transcript is recorded in `docs/evidence/`.
- Case studies. A `[casestudy]` table and `[[story]]` tables describe a write-up in six fixed sections; every sentence must cite evidence and becomes a claim that `seal` and `check` already cover.
- `proofboard casestudy` renders Markdown or one self-contained HTML page (screenshots embedded, text escaped) with each sentence's evidence status; `--strict` exits 2 unless all are proven.
- `proofboard scaffold` drafts a case study from ADRs, test logs, screenshots and README limitations, leaving `TODO` where a human sentence is needed.
- This repository's own case study.

### Fixed

- **Security:** the XML guard for JUnit and coverage files only looked for ASCII `<!DOCTYPE` and `<!ENTITY`, so the same declarations in a UTF-16 (or other non-UTF-8) file reached the parser. XML must now be valid UTF-8 and is parsed from decoded text. Regression tests in `tests/unit/test_xml_encodings.py`.
