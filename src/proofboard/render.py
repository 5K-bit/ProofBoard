"""Render a report as plain text, Markdown, HTML or JSON. Text from the files is escaped."""

from __future__ import annotations

import html
import json
import re
from typing import Any

from . import __version__
from .evaluate import CLAIM_ORDER, ClaimResult, Report
from .ledger import format_time

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+!|~])")
LABEL = {
    "proven": "PROVEN",
    "stale": "STALE",
    "unsealed": "UNSEALED",
    "drifted": "DRIFTED",
    "missing": "MISSING",
    "failed": "FAILED",
    "unsupported": "NO EVIDENCE",
}


def md(text: str) -> str:
    """Make arbitrary text inert in Markdown: no tags, no links, no emphasis, one line."""
    flat = " ".join(text.split())
    flat = flat.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _MD_SPECIAL.sub(r"\\\1", flat)


def code(text: str) -> str:
    """Inline code span: no backticks or line breaks, tags neutralised."""
    flat = " ".join(text.split()).replace("`", "'")
    return "`" + flat.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "`"


def _summary_line(report: Report) -> str:
    counts = report.counts()
    parts = [f"{counts[s]} {s}" for s in CLAIM_ORDER if s in counts]
    return f"{len(report.results)} claims: " + (", ".join(parts) if parts else "none")


def text(report: Report) -> str:
    head = report.board.title + (f" ({report.board.subject})" if report.board.subject else "")
    lines = [f"ProofBoard: {head}", f"checked {format_time(report.now)}"]
    if not report.sealed:
        lines.append("no lock file yet: nothing has been sealed")
    width = max((len(r.claim.id) for r in report.results), default=0)
    for res in report.results:
        lines.append(f"  {res.status:<11} {res.claim.id:<{width}}  {res.claim.title}")
        for ev in res.evidence:
            if ev.status != "ok":
                lines.append(f"      ! {ev.path}: {ev.note}")
    lines.append(_summary_line(report))
    return "\n".join(lines) + "\n"


def markdown(report: Report) -> str:
    board = report.board
    out = [f"# ProofBoard: {md(board.title)}", ""]
    if board.subject:
        out += [f"Subject: {md(board.subject)}", ""]
    out += [f"Checked {format_time(report.now)} · {_summary_line(report)}", ""]
    out += ["| Status | Claim | Evidence |", "|---|---|---|"]
    for res in report.results:
        ok = sum(1 for e in res.evidence if e.status == "ok")
        out.append(
            f"| {LABEL[res.status]} | {md(res.claim.title)} "
            f"| {ok} of {len(res.evidence)} in order |"
        )
    out.append("")
    for res in report.results:
        out += _claim_markdown(res)
    out.append(
        f"_ProofBoard {__version__}. Checks what is recorded; it cannot tell whether the "
        "evidence itself was honest._"
    )
    return "\n".join(out) + "\n"


def _claim_markdown(res: ClaimResult) -> list[str]:
    out = [f"## {md(res.claim.title)}", "", f"`{res.claim.id}` · **{LABEL[res.status]}**", ""]
    if res.claim.statement:
        out += [md(res.claim.statement), ""]
    if not res.evidence:
        out += ["No evidence is linked to this claim.", ""]
    for ev in res.evidence:
        sha = f" · sha256 {ev.sha256[:12]}" if ev.sha256 else ""
        sealed = f" · sealed {ev.sealed_at}" if ev.sealed_at else ""
        out.append(f"- **{ev.status}** {code(ev.path)}{sha}{sealed}: {md(ev.note)}")
        for chk in ev.checks:
            out.append(f"  - {'met' if chk.ok else 'not met'}: {md(chk.detail)}")
    out.append("")
    return out


_CSS = """
:root{--bg:#0c1220;--fg:#f3f5fa;--mute:#99a7bc;--line:#283345;--accent:#60a5fa}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:56rem;margin:0 auto;padding:2rem 1rem}
h1{margin:0 0 .25rem}.mute{color:var(--mute)}
table{border-collapse:collapse;width:100%;margin:1rem 0}
td,th{border-bottom:1px solid var(--line);padding:.4rem .6rem;text-align:left}
.tag{font:700 .75rem ui-monospace,monospace;padding:.15rem .5rem;border:1px solid var(--mute);
border-radius:.25rem}.proven,.ok{color:#3ddc97;border-color:#3ddc97}
.failed,.missing,.drifted{color:#ff7a59;border-color:#ff7a59}
.stale,.unsealed,.unsupported{color:#ff9f1c;border-color:#ff9f1c}
code{font-family:ui-monospace,monospace;color:var(--accent)}li{margin:.2rem 0}
"""


def html_page(report: Report) -> str:
    e = html.escape
    board = report.board
    rows: list[str] = []
    sections: list[str] = []
    for res in report.results:
        rows.append(
            f'<tr><td><span class="tag {res.status}">{e(LABEL[res.status])}</span></td>'
            f"<td>{e(res.claim.title)}</td></tr>"
        )
        items: list[str] = []
        for ev in res.evidence:
            checks = "".join(
                f"<li>{'met' if c.ok else 'not met'}: {e(c.detail)}</li>" for c in ev.checks
            )
            sha = f" · sha256 {e(ev.sha256[:12])}" if ev.sha256 else ""
            items.append(
                f'<li><span class="tag {ev.status}">{e(ev.status)}</span> <code>{e(ev.path)}</code>'
                f"{sha}: {e(ev.note)}" + (f"<ul>{checks}</ul>" if checks else "") + "</li>"
            )
        body = "".join(items) or "<li>No evidence is linked to this claim.</li>"
        stmt = f"<p>{e(res.claim.statement)}</p>" if res.claim.statement else ""
        tag = f'<span class="tag {res.status}">{e(LABEL[res.status])}</span>'
        sections.append(
            f"<section><h2>{e(res.claim.title)}</h2>"
            f'<p class="mute"><code>{e(res.claim.id)}</code> · {tag}</p>'
            f"{stmt}<ul>{body}</ul></section>"
        )
    subject = f'<p class="mute">{e(board.subject)}</p>' if board.subject else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>ProofBoard: {e(board.title)}</title><style>{_CSS}</style></head><body><main>"
        f"<h1>ProofBoard: {e(board.title)}</h1>{subject}"
        f'<p class="mute">Checked {e(format_time(report.now))} · {e(_summary_line(report))}</p>'
        f"<table><thead><tr><th>Status</th><th>Claim</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
        f"{''.join(sections)}"
        f'<p class="mute">ProofBoard {e(__version__)}. It checks what is recorded; it cannot tell '
        "whether the evidence itself was honest.</p></main></body></html>\n"
    )


def as_json(report: Report) -> str:
    claims: list[dict[str, Any]] = []
    for res in report.results:
        claims.append(
            {
                "id": res.claim.id,
                "title": res.claim.title,
                "status": res.status,
                "evidence": [
                    {
                        "path": ev.path,
                        "status": ev.status,
                        "note": ev.note,
                        "sha256": ev.sha256,
                        "sealed_sha256": ev.sealed_sha256,
                        "sealed_at": ev.sealed_at,
                        "checks": [
                            {"name": c.name, "ok": c.ok, "detail": c.detail} for c in ev.checks
                        ],
                    }
                    for ev in res.evidence
                ],
            }
        )
    doc = {
        "proofboard": __version__,
        "title": report.board.title,
        "subject": report.board.subject,
        "checked": format_time(report.now),
        "sealed": report.sealed,
        "all_proven": report.all_proven,
        "counts": report.counts(),
        "claims": claims,
    }
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
