"""Glue: transcript -> detectors -> merged spans (-> review -> pseudonymize)."""
from __future__ import annotations

import logging
from collections import Counter

from .audio import OVERLAP_S, WINDOW_S, chunk_audio, load_audio
from .detect import detect_patterns, detect_spoken_numbers
from .spans import Span, resolve_overlaps
from .stitch import stitch

log = logging.getLogger("whispervault")


def transcribe_audio(path: str, asr, window_s: float = WINDOW_S, overlap_s: float = OVERLAP_S,
                     progress=None) -> str:
    """Load -> overlapping 30 s windows -> ASR per window -> stitch. In memory only."""
    audio = load_audio(path)
    chunks = chunk_audio(audio, window_s=window_s, overlap_s=overlap_s)
    texts = []
    for i, c in enumerate(chunks, 1):
        if progress:
            progress(i, len(chunks))
        texts.append(asr.transcribe_chunk(c))
    return stitch(texts)


def detect(text: str, ner=None, dictionary=None) -> list[Span]:
    """Run all detectors and resolve overlaps. Hybrid on purpose (Fix #3)."""
    spans = detect_patterns(text) + detect_spoken_numbers(text)
    if dictionary is not None:
        spans += dictionary.detect(text)
    if ner is not None:
        spans += ner.detect(text)
    spans = resolve_overlaps(spans)
    covered = sum(s.end - s.start for s in spans)
    if text and covered / len(text) > 0.5:  # R28 safety net: something is over-matching
        log.warning("More than 50%% of the transcript is flagged (%.0f%%). "
                    "Check your keyword dictionary.", 100 * covered / len(text))
    return spans


def summarize(spans: list[Span], accepted: set[int]) -> dict:
    return {
        "flagged": len(spans),
        "redacted": len(accepted),
        "kept": len(spans) - len(accepted),
        "by_label": dict(Counter(s.label for i, s in enumerate(spans) if i in accepted)),
        "by_source": dict(Counter(s.source for s in spans)),
    }
