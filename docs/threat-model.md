# Threat model

ProofBoard is a local command line tool. Its inputs are a claims file, a lock file and the evidence files the claims name, all inside one project folder.

## Assets

- The meaning of a CHECKS PASSED status: *these files are the ones that were sealed, and they meet the stated rules.*
- The project folder outside the evidence paths (it must not be read or changed).
- The reader of a report (it must not be able to run script from a claim title).

## Actors

- **A careless editor** who changes evidence or the lock without noticing.
- **A hurried releaser** who wants a green board and re-seals changed evidence without looking.
- **A hostile contributor** who adds a pull request with crafted claims or evidence.
- **A hostile evidence file** (log, XML) produced by a tool in a pipeline.

## Threats and mitigations

| Threat | Mitigation | Test |
|---|---|---|
| Markup or script in a case-study sentence, summary or alt text | Markdown is escaped; the HTML page escapes everything; links must be plain `https://` URLs without `<>"'` or spaces | `test_html_is_self_contained_and_escaped`, `test_markdown_text_is_inert` |
| A screenshot path leads outside the project or is huge | Same path rules as evidence; symlinks that leave the folder are not embedded; images over 2 MiB are not embedded | `test_images_that_cannot_be_embedded` |
| A page keeps looking confident after its evidence changed | Each sentence shows its status; `casestudy --strict` exits 2 unless all pass | `test_drift_is_flagged_in_the_page_and_fails_strict` |
| A half-written draft is published | A draft with `TODO` does not load | `test_scaffold_drafts_from_what_the_repo_holds` |
| Entity declaration hidden by re-encoding the XML (UTF-16, EBCDIC) | XML must be valid UTF-8 without NULs; the guard runs on decoded text and the parser is given text, so the file's declared encoding is ignored | `test_entities_are_refused_in_every_encoding`, `test_ebcdic_declared_encoding_is_refused` |
| Evidence changes silently after sealing | Hash compared on every `check`; status `drifted` | `test_status_walk` |
| Hand edit to the lock | Lock carries a digest of its contents; mismatch is an error | `test_lock_roundtrip_and_tamper` |
| `seal` rubber-stamps a changed file | `seal` writes nothing if a recorded hash changed, unless `--accept-changes` | `test_seal_refuses_changes_until_accepted` |
| Evidence path escapes the folder (`../`, absolute, drive letter, backslash) | Rejected when the claims file is read | `test_unsafe_paths_rejected` |
| Symlink inside the folder points outside | Resolved path must stay inside; otherwise `failed` and `seal` refuses | `test_symlink_escape_is_failed` |
| XML bomb or external entity in JUnit or coverage XML | Documents with a doctype or entity declaration are refused; no entity expansion | `test_xml_with_doctype_or_entities_refused` |
| Huge evidence file exhausts memory | Hashing streams in 1 MiB blocks; content rules read at most 8 MiB | `test_inspect_size_limit` |
| Markup or script in claim text or evidence reaches a report | Markdown is entity- and backslash-escaped; HTML is escaped; JSON is serialised | `test_hostile_text_is_inert` |
| Damaged claims file crashes the tool | Strict parser; 300 mutated files end in a clean error or a report | `test_fuzzed_claims_files_never_crash` |
| A claim is quietly left with no proof | Status "no evidence"; an empty board is never "all passed" | `test_claim_without_evidence_is_unsupported` |

## Not covered

- **Honesty of the evidence.** A false log, sealed, shows CHECKS PASSED. ProofBoard shows that something is unchanged and meets stated rules, nothing more.
- **Authenticity of the lock.** There is no signing. An attacker who can rewrite both the lock and the evidence wins. Version control with review is the control.
- **Timestamps.** `sealed_at` is the clock of the machine that sealed. Staleness is only as good as that clock.
- **Regular-expression cost.** `matches` patterns come from the claims file's author and are not sandboxed.
- **The meaning of a rule.** `contains = "passed"` is satisfied by the word anywhere in the file. Write rules that would fail if the claim were false.
