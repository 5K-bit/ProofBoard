"""Render a case study from a claims file, and draft one from what a repository already holds.

A case study is a list of sentences ([[story]]) in six fixed sections. Every sentence cites
evidence files; each sentence is a claim that ProofBoard seals and checks like any other, so the
finished page shows, next to every sentence, whether its evidence is still sealed and unchanged.
"""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from . import __version__
from .checks import coverage_percent
from .errors import ProofBoardError
from .evaluate import ClaimResult, Report, resolve_inside
from .ledger import format_time
from .model import IMAGE_TYPES, SECTIONS, Story, StoryItem
from .render import _CSS, LABEL, code, md

TITLES = {
    "problem": "The problem",
    "evidence": "What the evidence showed",
    "decision": "Decisions",
    "implementation": "Implementation",
    "verification": "Verification",
    "limits": "Remaining limits",
}
MAX_EMBED_BYTES = 2 << 20
LINE_ONE = "AI tools assist with implementation, debugging, tests, and documentation."


def disclosure(author: str) -> tuple[str, str]:
    return (
        LINE_ONE,
        f"{author} owns project direction and acceptance decisions; linked tests and release "
        "evidence document what has been verified.",
    )


def _story(report: Report) -> Story:
    story = report.board.story
    if story is None:
        raise ProofBoardError("no [casestudy] table in the claims file (try 'proofboard scaffold')")
    return story


def _by_section(story: Story, *, allow_missing: bool) -> dict[str, list[StoryItem]]:
    groups: dict[str, list[StoryItem]] = {name: [] for name in SECTIONS}
    for item in story.items:
        groups[item.section].append(item)
    missing = [name for name in SECTIONS if not groups[name]]
    if missing and not allow_missing:
        raise ProofBoardError(
            "the case study has no statement in: "
            + ", ".join(missing)
            + " (add one, or pass --allow-missing)"
        )
    return groups


def results_by_id(report: Report) -> dict[str, ClaimResult]:
    return {r.claim.id: r for r in report.results}


def story_counts(report: Report) -> tuple[int, int]:
    """(proven, total) over the case study's own statements."""
    story = _story(report)
    index = results_by_id(report)
    proven = sum(1 for i in story.items if index[i.claim_id].status == "proven")
    return proven, len(story.items)


def all_story_proven(report: Report) -> bool:
    proven, total = story_counts(report)
    return total > 0 and proven == total


def _lead(report: Report) -> str:
    proven, total = story_counts(report)
    when = format_time(report.now)
    if proven == total:
        return f"As of {when}, all {total} statements are backed by sealed, unchanged evidence."
    return (
        f"As of {when}, only {proven} of {total} statements are backed by sealed, unchanged "
        "evidence. The others are flagged below."
    )


def _href(path: str) -> str:
    return quote(path, safe="/")


# ---- Markdown ---------------------------------------------------------------------------------


def markdown(report: Report, *, allow_missing: bool = False) -> str:
    story = _story(report)
    groups = _by_section(story, allow_missing=allow_missing)
    index = results_by_id(report)
    byline = f"By {md(story.author)}"
    if story.subject:
        byline = f"{md(story.subject)} · {byline}"
    if story.repo:
        byline += f" · [repository]({story.repo})"
    out = [f"# {md(story.title)}", "", byline, ""]
    if story.summary:
        out += [md(story.summary), ""]
    out += [f"> {_lead(report)}", ""]
    number = 0
    for name in SECTIONS:
        out += [f"## {TITLES[name]}", ""]
        if not groups[name]:
            out += ["_No statement in this section yet._", ""]
        for item in groups[name]:
            number += 1
            res = index[item.claim_id]
            out += [f"{number}. {md(item.text)} **[{LABEL[res.status]}]**"]
            for ev in res.evidence:
                state = "" if ev.status == "ok" else f" ({ev.status}: {md(ev.note)})"
                sha = f", sha256 {ev.sha256[:12]}" if ev.sha256 else ""
                out.append(f"   - evidence: [{code(ev.path)}]({_href(ev.path)}){sha}{state}")
            for url in item.links:
                out.append(f"   - link (not checked by ProofBoard): <{url}>")
            for img in item.images:
                out.append(f"   - ![{md(img.alt)}]({_href(img.path)})")
        out.append("")
    first, second = disclosure(story.author)
    out += ["## Development practice", "", md(first), "", md(second), ""]
    out.append(
        f"_Built with ProofBoard {__version__}. Each statement is checked against evidence files "
        "recorded in a lock; that shows the evidence is unchanged, not that it is true._"
    )
    return "\n".join(out) + "\n"


# ---- HTML -------------------------------------------------------------------------------------

_EXTRA_CSS = """
h2{margin-top:2rem;border-bottom:1px solid var(--line);padding-bottom:.3rem}
ol{padding-left:1.4rem}ol>li{margin:1rem 0}ul.ev{list-style:none;padding:0;margin:.4rem 0;
font-size:.9rem;color:var(--mute)}
figure{margin:.6rem 0}img{max-width:100%;border:1px solid var(--line);border-radius:.4rem}
figcaption{color:var(--mute);font-size:.85rem}blockquote{border-left:3px solid var(--accent);
margin:1rem 0;padding:.2rem 1rem;color:var(--mute)}a{color:var(--accent)}
"""


def _image_tag(root: Path, path: str, alt: str) -> str:
    e = html.escape
    target = resolve_inside(root, path)
    suffix = "." + path.rsplit(".", 1)[-1].lower()
    mime = IMAGE_TYPES.get(suffix)
    if target is None or mime is None or not target.is_file():
        return f"<p class='mute'>[image not found: {e(path)}]</p>"
    if target.stat().st_size > MAX_EMBED_BYTES:
        return (
            f"<p class='mute'>[image over {MAX_EMBED_BYTES >> 20} MiB, not embedded: {e(path)}]</p>"
        )
    data = base64.b64encode(target.read_bytes()).decode("ascii")
    return (
        f'<figure><img alt="{e(alt)}" src="data:{mime};base64,{data}">'
        f"<figcaption>{e(alt)} · <code>{e(path)}</code></figcaption></figure>"
    )


def html_page(report: Report, root: Path, *, allow_missing: bool = False) -> str:
    e = html.escape
    story = _story(report)
    groups = _by_section(story, allow_missing=allow_missing)
    index = results_by_id(report)
    parts: list[str] = []
    for name in SECTIONS:
        parts.append(f"<h2>{e(TITLES[name])}</h2>")
        if not groups[name]:
            parts.append("<p class='mute'>No statement in this section yet.</p>")
            continue
        items: list[str] = []
        for item in groups[name]:
            res = index[item.claim_id]
            ev_lines = []
            for ev in res.evidence:
                state = "" if ev.status == "ok" else f" · {e(ev.status)}: {e(ev.note)}"
                sha = f" · sha256 {e(ev.sha256[:12])}" if ev.sha256 else ""
                ev_lines.append(
                    f'<li><span class="tag {ev.status}">{e(ev.status)}</span> '
                    f"<code>{e(ev.path)}</code>{sha}{state}</li>"
                )
            for url in item.links:
                ev_lines.append(
                    f'<li>link, not checked by ProofBoard: <a href="{e(url)}" '
                    f'rel="noopener noreferrer">{e(url)}</a></li>'
                )
            pics = "".join(_image_tag(root, i.path, i.alt) for i in item.images)
            tag = f'<span class="tag {res.status}">{e(LABEL[res.status])}</span>'
            items.append(
                f'<li>{e(item.text)} {tag}<ul class="ev">{"".join(ev_lines)}</ul>{pics}</li>'
            )
        first_number = sum(len(groups[n]) for n in SECTIONS[: SECTIONS.index(name)]) + 1
        parts.append(f"<ol start='{first_number}'>{''.join(items)}</ol>")
    first, second = disclosure(story.author)
    byline = (
        f"{e(story.subject)} · by {e(story.author)}" if story.subject else f"By {e(story.author)}"
    )
    if story.repo:
        byline += f' · <a href="{e(story.repo)}" rel="noopener noreferrer">repository</a>'
    summary = f"<p>{e(story.summary)}</p>" if story.summary else ""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{e(story.title)}</title><style>{_CSS}{_EXTRA_CSS}</style></head><body><main>"
        f"<h1>{e(story.title)}</h1><p class='mute'>{byline}</p>{summary}"
        f"<blockquote>{e(_lead(report))}</blockquote>{''.join(parts)}"
        f"<h2>Development practice</h2><p>{e(first)}</p><p>{e(second)}</p>"
        f"<p class='mute'>Built with ProofBoard {e(__version__)}. Each statement is checked "
        "against evidence files recorded in a lock; that shows the evidence is unchanged, not "
        "that it is true.</p></main></body></html>\n"
    )


# ---- drafting from a repository ---------------------------------------------------------------

_PASSED = re.compile(r"\b\d+ passed\b")
_ADR_PREFIX = re.compile(r"^(ADR\s*\d+\s*[:.-]?\s*|\d+\.\s*)", re.I)
_SKIP_IMAGE = re.compile(r"(logo|banner|social|icon|favicon)", re.I)


def _q(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _snippet(text: str, limit: int = 50) -> str:
    return text.strip()[:limit]


def _first_heading(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
            if line.startswith("#"):
                return line.lstrip("#").strip()
    except OSError:
        return None
    return None


def _limitations(readme: Path) -> list[str]:
    try:
        lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip().lower().startswith("limitations")
            continue
        if inside and line.startswith("- ") and len(line) > 12:
            out.append(line[2:].strip())
    return out[:12]


def draft(root: Path) -> str:
    """A [casestudy] draft built from files already in the project.

    Statements that need a human sentence say TODO and stop the file from loading until they are
    written; statements taken from the project's own text (README limitations) are left as they are.
    """
    docs = root / "docs"
    adrs = sorted((docs / "adr").glob("*.md")) if (docs / "adr").is_dir() else []
    evidence_dir = docs / "evidence"
    logs = (
        sorted(
            p
            for p in evidence_dir.glob("*.txt")
            if re.search(r"(test|unit|e2e)[-_]?run", p.name) or p.name.startswith("test")
        )
        if evidence_dir.is_dir()
        else []
    )
    shots = sorted(
        p
        for p in docs.rglob("*")
        if p.suffix.lower() in IMAGE_TYPES and not _SKIP_IMAGE.search(p.name)
    )[:6]

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    out = [
        "# Draft case study. Replace every TODO with a sentence you can stand behind, then merge",
        "# the [casestudy] and [[story]] tables into proofboard.toml (it needs its own [board]).",
        "# Until no TODO is left this file will not load. Every statement must cite evidence;",
        "# a problem should cite a log that reproduces it, not a description of it.",
        "",
        '[board]\ntitle = "TODO"',
        "",
        '[casestudy]\ntitle = "TODO"\nsubject = "TODO"\nauthor = "TODO"',
        '# summary = "One or two sentences."\n# repo = "https://github.com/OWNER/REPO"',
        "",
        "# --- problem: cite a reproduction (command output, failing test, transcript) ---",
        '# [[story]]\n# section = "problem"\n# text = "..."',
        '#   [[story.evidence]]\n#   path = "docs/evidence/..."',
        "",
    ]
    for log in shots:
        out += [
            '[[story]]\nsection = "evidence"\n'
            f"text = {_q('TODO: what this screenshot shows')}\n"
            f"  [[story.image]]\n  path = {_q(rel(log))}\n"
            f"  alt = {_q(re.sub(r'[-_]+', ' ', log.stem).strip().capitalize())}\n"
        ]
    for adr in adrs:
        title = _first_heading(adr) or adr.stem
        shown = _ADR_PREFIX.sub("", title)
        out += [
            '[[story]]\nsection = "decision"\n'
            f"text = {_q('TODO: why — ' + shown)}\n"
            f"  [[story.evidence]]\n  path = {_q(rel(adr))}\n  contains = {_q(_snippet(title))}\n"
        ]
    arch = docs / "architecture.md"
    if arch.is_file():
        out += [
            '[[story]]\nsection = "implementation"\ntext = "TODO: how it is built"\n'
            f"  [[story.evidence]]\n  path = {_q(rel(arch))}\n"
        ]
    for log in logs:
        text = log.read_text(encoding="utf-8", errors="replace")
        if not _PASSED.search(text):
            continue
        rules = [f"  matches = {_q(_PASSED.pattern)}"]
        cov = coverage_percent(log.name, log.read_bytes(), text)
        if cov is not None:
            rules.append(f"  coverage_min = {int(cov)}")
        out += [
            '[[story]]\nsection = "verification"\n'
            f"text = {_q('TODO: what the recorded run (' + log.name + ') shows')}\n"
            f"  [[story.evidence]]\n  path = {_q(rel(log))}\n" + "\n".join(rules) + "\n"
        ]
    readme = root / "README.md"
    for bullet in _limitations(readme):
        out += [
            '[[story]]\nsection = "limits"\n'
            f"text = {_q(bullet.replace('**', ''))}\n"
            f"  [[story.evidence]]\n  path = {_q(rel(readme))}\n"
            f"  contains = {_q(_snippet(bullet))}\n"
        ]
    return "\n".join(out).rstrip() + "\n"
