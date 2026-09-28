import pytest
from whispervault.detect import KeywordDictionary, detect_patterns, detect_spoken_numbers
from whispervault.detect.patterns import classify_digits, luhn_ok
from whispervault.spans import Span, resolve_overlaps


def labels(text):
    spans = resolve_overlaps(detect_patterns(text) + detect_spoken_numbers(text))
    return {(s.label, s.text) for s in spans}


def test_written_ids():
    got = labels("SSN 123-45-6789, phone 312-555-0187, mail a.b@example.com, MRN: 48213907")
    assert ("SSN", "123-45-6789") in got
    assert ("PHONE", "312-555-0187") in got
    assert ("EMAIL", "a.b@example.com") in got
    assert ("MRN", "48213907") in got


def test_card_needs_luhn():
    assert ("CARD", "4111 1111 1111 1111") in labels("card 4111 1111 1111 1111 declined")
    assert not any(l == "CARD" for l, _ in labels("number 1234 5678 9012 3456 here"))
    assert luhn_ok("4111111111111111")


def test_dosage():
    assert ("DOSAGE", "50 mg twice daily") in labels("prescribed 50 mg twice daily today")


def test_spoken_ssn_and_phone_R16():
    got = labels("my social is one two three four five six seven eight nine ok")
    assert ("SSN", "one two three four five six seven eight nine") in got
    got = labels("call double nine eight seven six five four three two one")
    assert any(l == "PHONE" for l, _ in got)


def test_spoken_numbers_are_length_specific_R24():
    # 4-digit PINs, extensions and plain counts must NOT be flagged
    assert labels("the pin is one two three four") == set()
    assert labels("it was one or two things, maybe three") == set()
    assert classify_digits("12345") is None and classify_digits("123456789") == "SSN"


def test_overlap_resolution_prefers_longer_card_over_aadhaar():
    spans = resolve_overlaps(detect_patterns("4111 1111 1111 1111"))
    assert [s.label for s in spans] == ["CARD"]


def test_dictionary_is_literal_R28():
    d = KeywordDictionary(["Proj.*t X", "Project SILVERHAWK"])
    assert d.detect("see Project Xylophone") == []           # '.*' is NOT a wildcard
    assert len(d.detect("about proj.*t x today")) == 1       # matched literally
    assert d.detect("the project silverhawk plan")[0].label == "CODENAME"  # case-insensitive


@pytest.mark.parametrize("bad", [".*", "a", "   ", "***"])
def test_dictionary_rejects_dangerous_entries_R28(bad):
    with pytest.raises(ValueError):
        KeywordDictionary([bad])


def test_dictionary_word_boundaries():
    d = KeywordDictionary(["Acme"])
    assert d.detect("Acmet and Acme.")[0].start == 10


def test_regex_metacharacters_match_only_literally_R28():
    d = KeywordDictionary([r"\w+"])          # accepted, but escaped: NOT "every word"
    assert d.detect("hello brave new world") == []
    assert len(d.detect(r"the token \w+ appears")) == 1


def test_card_span_does_not_swallow_trailing_space():
    text = "card 4111 1111 1111 1111 was declined"
    spans = [s for s in detect_patterns(text) if s.label == "CARD"]
    assert spans and text[spans[0].start:spans[0].end] == "4111 1111 1111 1111"


def test_mrn_captures_the_id_not_the_word_number():
    got = labels("his medical record number is 48213907 today")
    assert ("MRN", "48213907") in got
    assert not any(t == "number" for _, t in got)
