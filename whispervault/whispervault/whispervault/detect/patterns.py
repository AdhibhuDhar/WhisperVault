"""Deterministic detectors: written-form regexes plus spoken-number runs.

NER models find semantic entities (people, orgs, places). They do NOT find
structured identifiers, so those are handled here with explicit rules (Fix #3).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..spans import Span


def luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


# (label, compiled regex, capture group to redact - 0 means the whole match)
RULES: list[tuple[str, re.Pattern, int]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), 0),
    # SSN with separators, e.g. 123-45-6789
    ("SSN", re.compile(r"\b(?!000|666|9\d\d)\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b"), 0),
    # 9 unseparated digits only when an SSN-ish keyword is nearby
    ("SSN", re.compile(r"(?i)\b(?:ssn|social(?:\s+security)?(?:\s+number)?)\D{0,15}(\d{9})\b"), 1),
    # US phone: separators required, keeps false positives down
    ("PHONE", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"), 0),
    # Indian mobile numbers
    ("PHONE", re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{9}(?!\d)"), 0),
    ("AADHAAR", re.compile(r"(?<!\d)[2-9]\d{3}\s\d{4}\s\d{4}(?!\d)"), 0),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 0),
    # the ID must contain a digit, otherwise the word "number" itself would match
    ("MRN", re.compile(r"(?i)\b(?:mrn|medical record(?:\s+number)?|patient id)\b(?:\s+is)?[\s:#-]*"
                       r"(?=[A-Z0-9-]*\d)([A-Z0-9-]{5,12})\b"), 1),
    ("DOSAGE", re.compile(
        r"(?i)\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|ml|units?|iu)\b"
        r"(?:\s+(?:once|twice|two times|three times)\s+(?:a\s+day|daily)|\s+(?:daily|bid|tid|qid))?"), 0),
    ("IP_ADDRESS", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"), 0),
]

_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def detect_patterns(text: str) -> list[Span]:
    spans: list[Span] = []
    for label, rx, grp in RULES:
        for m in rx.finditer(text):
            s, e = m.span(grp)
            spans.append(Span(s, e, label, text[s:e], "regex"))
    for m in _CARD.finditer(text):  # card numbers must pass the Luhn check
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            raw = m.group()
            body = raw.rstrip(" -")  # never swallow the separator after the number
            spans.append(Span(m.start(), m.start() + len(body), "CARD", body, "regex"))
    return spans


# ---------------------------------------------------------------- spoken digits
_DIGITS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "niner": "9",
}
_MULT = {"double": 2, "triple": 3}
_TOK = re.compile(r"\S+")


@dataclass
class DigitRun:
    start: int
    end: int
    digits: str


def _token_digits(tok: str) -> str | None:
    core = tok.strip(".,;:!?\"'()").lower()
    if not core:
        return None
    if core.isdigit() and len(core) == 1:
        return core
    parts = core.split("-")
    if all(p in _DIGITS for p in parts):
        return "".join(_DIGITS[p] for p in parts)
    return None


def find_digit_runs(text: str, min_digits: int = 4) -> list[DigitRun]:
    """Runs of spoken (or single written) digits: 'one two three' / 'double five'."""
    toks = list(_TOK.finditer(text))
    runs: list[DigitRun] = []
    i = 0
    while i < len(toks):
        j, digits, first = i, "", None
        while j < len(toks):
            core = toks[j].group().strip(".,;:!?\"'()").lower()
            if core in _MULT and j + 1 < len(toks):
                nxt = _token_digits(toks[j + 1].group())
                if nxt and len(nxt) == 1:
                    digits += nxt * _MULT[core]
                    first = toks[j].start() if first is None else first
                    j += 2
                    continue
            d = _token_digits(toks[j].group())
            if d is None:
                break
            digits += d
            first = toks[j].start() if first is None else first
            j += 1
        # a bare run of 'oh' is an interjection, not a number
        if len(digits) >= min_digits and set(digits) != {"0"}:
            last_tok = toks[j - 1]
            end = last_tok.start() + len(last_tok.group().rstrip(".,;:!?\"')"))
            runs.append(DigitRun(first, end, digits))
        i = max(j, i + 1)
    return runs


def classify_digits(digits: str) -> str | None:
    """Format-specific classification (R24): only exact known lengths are flagged."""
    n = len(digits)
    if n == 9:
        return "SSN"
    if n == 10:
        return "PHONE"
    if n == 12:
        return "AADHAAR"
    if 13 <= n <= 19 and luhn_ok(digits):
        return "CARD"
    return None  # 4-digit PINs, extensions, counts etc. are left alone


def detect_spoken_numbers(text: str) -> list[Span]:
    spans = []
    for run in find_digit_runs(text):
        label = classify_digits(run.digits)
        if label:
            spans.append(Span(run.start, run.end, label, text[run.start:run.end], "spoken"))
    return spans
