"""Human-in-the-loop review (Fix #8, R10, R23, R27).

Flagged spans are grouped by entity so a name that appears 14 times is decided
once (R23). Groups the tool considers ambiguous - e.g. a bare first name that
could be several different people (R18, R27) - are NEVER bulk-decided: every
occurrence is reviewed individually. There is no global 'accept everything'
shortcut in interactive mode (R10).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

from .spans import Span


def _key(s: Span) -> tuple[str, str]:
    return s.label, re.sub(r"[^\w\s]", "", " ".join(s.text.lower().split()))


def is_ambiguous(s: Span) -> bool:
    """Heuristic (not clustering): a single-token name may be several people."""
    return s.label == "PERSON" and len(s.text.split()) == 1


@dataclass
class Group:
    label: str
    key: str
    indices: list[int] = field(default_factory=list)
    ambiguous: bool = False


def group_spans(spans: list[Span]) -> list[Group]:
    groups: dict[tuple[str, str], Group] = {}
    for i, s in enumerate(spans):
        g = groups.setdefault(_key(s), Group(s.label, _key(s)[1]))
        g.indices.append(i)
        g.ambiguous = g.ambiguous or is_ambiguous(s)
    return sorted(groups.values(), key=lambda g: min(g.indices))


def _context(text: str, s: Span, width: int = 40) -> str:
    a, b = max(0, s.start - width), min(len(text), s.end + width)
    return ("..." if a else "") + text[a:s.start] + "[[" + text[s.start:s.end] + "]]" + \
        text[s.end:b] + ("..." if b < len(text) else "")


def review_interactive(text: str, spans: list[Span], input_fn=input, out_fn=print) -> set[int]:
    accepted: set[int] = set()
    groups = group_spans(spans)
    out_fn(f"\nReview {len(spans)} flagged span(s) in {len(groups)} group(s). "
           "Default answer is to REDACT (press Enter).")

    def ask(i: int) -> bool:
        out_fn("   " + _context(text, spans[i]).replace("\n", " "))
        return input_fn("   redact this? [Y/n]: ").strip().lower() not in ("n", "no")

    for n, g in enumerate(groups, 1):
        s0 = spans[g.indices[0]]
        out_fn(f"\n({n}/{len(groups)}) {g.label}  '{s0.text}'  x{len(g.indices)}"
               + ("   [ambiguous - reviewed one by one]" if g.ambiguous else ""))
        if len(g.indices) > 1 and not g.ambiguous:
            choice = input_fn("   [a] redact all  [r] keep all  [i] one by one  (a/r/i) [a]: ").strip().lower()
            if choice in ("", "a"):
                accepted.update(g.indices)
                continue
            if choice == "r":
                continue
        for i in g.indices:
            if ask(i):
                accepted.add(i)
    return accepted


def write_html_report(path: str, text: str, spans: list[Span], accepted: set[int],
                      redacted: str) -> None:
    """Side-by-side diff. WARNING: contains the ORIGINAL text - opt-in only."""
    parts, cur = [], 0
    for i, s in sorted(enumerate(spans), key=lambda t: t[1].start):
        parts.append(html.escape(text[cur:s.start]))
        cls = "on" if i in accepted else "off"
        parts.append(f'<mark class="{cls}" title="{s.label} ({s.source})">{html.escape(s.text)}</mark>')
        cur = s.end
    parts.append(html.escape(text[cur:]))
    doc = f"""<!doctype html><meta charset="utf-8"><title>WhisperVault review</title>
<style>body{{font:15px/1.5 Calibri,Segoe UI,sans-serif;margin:24px}}
.warn{{background:#fff3cd;border:1px solid #d39e00;padding:10px;margin-bottom:16px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
pre{{white-space:pre-wrap;background:#f7f7f7;padding:12px;border-radius:6px}}
mark.on{{background:#ffd6d6}} mark.off{{background:#d6ffd6}}</style>
<div class="warn"><b>Contains the original, unredacted text.</b> Review, then delete this file.</div>
<div class="cols"><div><h3>Original (red = will be redacted, green = kept)</h3><pre>{''.join(parts)}</pre></div>
<div><h3>Output</h3><pre>{html.escape(redacted)}</pre></div></div>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
