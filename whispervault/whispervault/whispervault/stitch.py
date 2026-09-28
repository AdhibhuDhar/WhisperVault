"""Merge the transcripts of overlapping audio windows (Fix #2 / R17).

Each window's transcript repeats the words spoken in the 5 s overlap. We align
the tail of the running transcript with the head of the next one and keep the
next window's version from the match onward, because the words at a hard cut
edge are the least reliable ones.

This is text alignment, not timestamp alignment; word-level timestamps are on
the roadmap (see docs/IMPLEMENTATION_STATUS.md).
"""
from __future__ import annotations

import difflib
import re


def _norm(word: str) -> str:
    return re.sub(r"\W", "", word.lower())


def stitch_pair(a: str, b: str, tail_words: int = 40, min_overlap: int = 3,
                edge_slack: int = 6) -> str:
    aw, bw = a.split(), b.split()
    if not aw:
        return b
    if not bw:
        return a
    at, bh = aw[-tail_words:], bw[:tail_words]
    an, bn = [_norm(w) for w in at], [_norm(w) for w in bh]
    sm = difflib.SequenceMatcher(None, an, bn, autojunk=False)
    best = None
    for blk in sm.get_matching_blocks():
        if blk.size < min_overlap:
            continue
        if len(an) - (blk.a + blk.size) > edge_slack:  # must reach the end of A
            continue
        if blk.b > edge_slack:                          # and start near the top of B
            continue
        if best is None or blk.size > best.size:
            best = blk
    if best is None:  # no trustworthy overlap: plain concatenation is the safe fallback
        return a + " " + b
    keep_a = aw[: len(aw) - len(at) + best.a + best.size]
    return " ".join(keep_a + bw[best.b + best.size:])


def stitch(texts: list[str], **kw) -> str:
    out = ""
    for t in texts:
        out = t if not out else stitch_pair(out, t, **kw)
    return out.strip()
