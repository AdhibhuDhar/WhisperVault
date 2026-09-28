"""Consistent, reversible pseudonymization (Fix #7).

'John Smith' becomes [PERSON_001] everywhere. The original strings go to an
encrypted vault (vault.py) so the professional can re-identify later; the
shareable text contains no re-identifiable value.
"""
from __future__ import annotations

import re
from collections import defaultdict

from .spans import Span

TAG_RX = re.compile(r"\[[A-Z_]+_\d{3}\]")


def _key(label: str, text: str) -> tuple[str, str]:
    return label, re.sub(r"[^\w\s]", "", " ".join(text.lower().split()))


def redact(text: str, spans: list[Span]) -> tuple[str, dict]:
    """Replace accepted spans with stable tags. Returns (text, mapping)."""
    tags: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = defaultdict(int)
    canonical: dict[str, dict] = {}
    occurrences: list[dict] = []
    out, cursor = [], 0
    for s in sorted(spans, key=lambda s: s.start):
        k = _key(s.label, s.text)
        if k not in tags:
            counters[s.label] += 1
            tags[k] = f"[{s.label}_{counters[s.label]:03d}]"
            canonical[tags[k]] = {"label": s.label, "canonical": s.text}
        out.append(text[cursor:s.start])
        out.append(tags[k])
        occurrences.append({"tag": tags[k], "original": s.text})
        cursor = s.end
    out.append(text[cursor:])
    return "".join(out), {"version": 1, "entities": canonical, "occurrences": occurrences}


def reidentify(redacted: str, mapping: dict) -> str:
    """Restore originals. Exact (order-based) when the tag sequence is intact,
    otherwise falls back to each tag's canonical value."""
    found = TAG_RX.findall(redacted)
    occ = mapping.get("occurrences", [])
    if [o["tag"] for o in occ] == found:
        it = iter(o["original"] for o in occ)
        return TAG_RX.sub(lambda m: next(it), redacted)
    ent = mapping["entities"]
    return TAG_RX.sub(lambda m: ent.get(m.group(), {}).get("canonical", m.group()), redacted)
