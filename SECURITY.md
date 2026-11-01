# Security Policy

## Intended use

ProofBoard checks files in a project folder you control against a claims file you wrote. It makes no network connections and sends nothing anywhere. It never runs a command from a claims file or from evidence.

## What ProofBoard protects, and what it does not

- **It detects change, not dishonesty.** A seal shows a file is byte-for-byte what it was when sealed. It cannot show the file was true then. A person (or a script) who writes a false test log and seals it gets a board that reads CHECKS PASSED. Treat the board as a way to notice silent change and missing proof, not as an audit.
- **The lock is tamper-evident, not tamper-proof.** The lock carries a digest of its own contents, so a hand edit or damage is caught. Anyone who can write both the lock and the evidence can regenerate both consistently. Commit the lock to version control and review changes to it like code; ProofBoard does no signing.
- **Sealing never changes a recorded hash silently.** `seal` refuses to overwrite a hash that changed unless you pass `--accept-changes`.
- **Paths stay inside the project.** Absolute paths, `..`, backslashes and drive letters are rejected when the claims file is read, and a symlink that leads outside the folder makes that evidence fail rather than being followed.
- **Evidence is hostile input.** Files are streamed to hash them; content rules read at most 8 MiB. XML with a doctype or entity declaration is refused (no entity expansion), and so is any XML that is not UTF-8 text (a UTF-16 or EBCDIC file could otherwise hide a declaration from the check). No file is executed or imported.
- **Reports are escaped.** Text from claims and evidence is escaped for Markdown and HTML; JSON is written by the standard library.
- **Regular expressions are yours.** `matches` runs a regular expression you wrote against a file; a pathological pattern can be slow. Only the claims file's author controls patterns.

The full analysis is in [docs/threat-model.md](docs/threat-model.md).

## Reporting a vulnerability

If you find a way to make a crafted claims file, lock or evidence file crash or stall ProofBoard, escape the project folder, inject markup into a report, or make a changed file read as unchanged, please report it privately through GitHub's **Security → Report a vulnerability** on this repository rather than a public issue.

Include the ProofBoard version (`proofboard --version`), your OS and Python version, and the smallest claims file and evidence that reproduce it. Use made-up content only. Expect an initial response within a few days.
