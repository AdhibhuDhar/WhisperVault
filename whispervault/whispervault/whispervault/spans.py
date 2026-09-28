"""Span type shared by every detector, plus overlap resolution."""
from __future__ import annotations

from dataclasses import dataclass

# Deterministic detectors outrank the statistical one when they collide.
PRIORITY = {"regex": 3, "spoken": 3, "dictionary": 2, "ner": 1}


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    label: str
    text: str
    source: str  # regex | spoken | dictionary | ner
    score: float = 1.0

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Keep the strongest span in every overlapping cluster.

    Order of preference: source priority, then longer span, then score.
    """
    ordered = sorted(
        spans,
        key=lambda s: (-PRIORITY.get(s.source, 0), -(s.end - s.start), -s.score, s.start),
    )
    kept: list[Span] = []
    for s in ordered:
        if not any(s.overlaps(k) for k in kept):
            kept.append(s)
    return sorted(kept, key=lambda s: s.start)
