"""User-supplied keyword dictionary (bring-your-own codenames).

R28: entries are LITERAL strings. They are escaped, never compiled as regex,
so a stray '.*' or '\\w+' cannot flag the whole transcript.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..spans import Span

MAX_TERMS = 10_000


def load_terms(path: str | Path) -> list[str]:
    terms = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line)
    return terms


class KeywordDictionary:
    def __init__(self, terms: list[str], label: str = "CODENAME",
                 case_sensitive: bool = False, min_len: int = 2):
        clean = []
        for t in terms:
            t = " ".join(t.split())
            if len(t) < min_len:
                raise ValueError(f"dictionary entry too short to be safe: {t!r}")
            if not re.search(r"\w", t):
                raise ValueError(f"dictionary entry has no letters or digits: {t!r}")
            clean.append(t)
        if len(clean) > MAX_TERMS:
            raise ValueError(f"too many dictionary entries (max {MAX_TERMS})")
        self.label = label
        self.terms = sorted(set(clean), key=len, reverse=True)
        self._rx = None
        if self.terms:
            body = "|".join(re.escape(t) for t in self.terms)  # literal, not regex
            flags = 0 if case_sensitive else re.IGNORECASE
            self._rx = re.compile(rf"(?<!\w)(?:{body})(?!\w)", flags)

    def detect(self, text: str) -> list[Span]:
        if self._rx is None:
            return []
        return [Span(m.start(), m.end(), self.label, m.group(), "dictionary")
                for m in self._rx.finditer(text)]
