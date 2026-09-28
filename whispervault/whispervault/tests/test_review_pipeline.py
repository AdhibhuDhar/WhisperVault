import pytest
from whispervault.detect import KeywordDictionary
from whispervault.pipeline import detect, summarize
from whispervault.pseudonymize import redact
from whispervault.review import group_spans, is_ambiguous, review_interactive
from whispervault.spans import Span


def test_grouping_and_bulk_decision_R23():
    text = "John Smith spoke. Then John Smith left."
    spans = [Span(0, 10, "PERSON", "John Smith", "ner"), Span(23, 33, "PERSON", "John Smith", "ner")]
    assert len(group_spans(spans)) == 1
    answers = iter(["a"])                      # one decision covers both occurrences
    acc = review_interactive(text, spans, input_fn=lambda _: next(answers), out_fn=lambda *_: None)
    assert acc == {0, 1}


def test_ambiguous_names_are_never_bulk_decided_R27():
    text = "John left. John stayed."
    spans = [Span(0, 4, "PERSON", "John", "ner"), Span(11, 15, "PERSON", "John", "ner")]
    assert all(is_ambiguous(s) for s in spans)
    prompts = []
    answers = iter(["y", "n"])                 # must be asked twice, individually
    def fake(p):
        prompts.append(p); return next(answers)
    acc = review_interactive(text, spans, input_fn=fake, out_fn=lambda *_: None)
    assert len(prompts) == 2 and "redact all" not in prompts[0]
    assert acc == {0}


def test_no_global_accept_all_shortcut_R10():
    import inspect
    from whispervault import review
    assert "accept all" not in inspect.getsource(review.review_interactive).lower().replace("[a] redact all", "")


def test_end_to_end_without_models():
    text = open("examples/sample_transcript.txt", encoding="utf-8").read()
    d = KeywordDictionary(["Project SILVERHAWK", "Acme Robotics"])
    spans = detect(text, dictionary=d)
    red, mapping = redact(text, spans)
    for leaked in ["123-45-6789", "48213907", "312-555-0187", "john.smith@example.com",
                   "4111 1111 1111 1111", "SILVERHAWK", "Acme Robotics",
                   "one two three four five six seven eight nine",
                   "nine eight seven six five four three two one zero", "50 mg"]:
        assert leaked not in red, leaked
    assert summarize(spans, set(range(len(spans))))["redacted"] == len(spans)


def test_over_matching_warning(caplog):
    with caplog.at_level("WARNING", logger="whispervault"):
        detect("Acme Acme Acme Acme", dictionary=KeywordDictionary(["Acme"]))
    assert "flagged" in caplog.text
