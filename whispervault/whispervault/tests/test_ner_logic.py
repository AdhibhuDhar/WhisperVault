import numpy as np
from whispervault.detect.ner import (TokenClassifierNER, decode_entities,
                                     merge_window_predictions, plan_windows)

ID2LABEL = {0: "O", 1: "B-PER", 2: "I-PER", 3: "B-ORG", 4: "I-ORG"}


def test_plan_windows_overlap_and_coverage():
    w = plan_windows(1000, 510, 64)
    assert w[0][0] == 0 and w[-1][1] == 1000
    assert all(b - a <= 510 for a, b in w)
    assert w[0][1] - w[1][0] == 64
    assert plan_windows(100, 510, 64) == [(0, 100)]


def test_decode_bio_merges_wordpieces_and_splits_entities():
    text = "Emily Chen visited Acme"
    offsets = [(0, 5), (6, 10), (11, 18), (19, 23)]
    spans = decode_entities(["B-PER", "I-PER", "O", "B-ORG"], [0.9] * 4, offsets, text)
    assert [(s.label, s.text) for s in spans] == [("PERSON", "Emily Chen"), ("ORG", "Acme")]


def test_low_confidence_dropped_and_misc_ignored():
    text = "Foo Bar"
    offs = [(0, 3), (4, 7)]
    assert decode_entities(["B-PER", "I-PER"], [0.2, 0.3], offs, text) == []
    assert decode_entities(["B-MISC", "I-MISC"], [0.9, 0.9], offs, text) == []


def test_merge_prefers_window_with_most_context():
    windows = [(0, 6), (3, 9)]
    labs = [["O"] * 6, ["B-PER", "I-PER", "O", "O", "O", "O"]]
    scs = [[0.9] * 6, [0.9] * 6]
    # token 3 sits at the edge of window 0 but the centre of... window 1's start edge
    merged, _ = merge_window_predictions(9, windows, labs, scs)
    assert len(merged) == 9


def _fake_ner(seq_len, overlap):
    """Word-level 'model': marks the two tokens 'Emily','Chen' as a PERSON."""
    vocab = {"Emily": 10, "Chen": 11}

    def tokenize(text):
        ids, offs, pos = [], [], 0
        for w in text.split(" "):
            ids.append(vocab.get(w, 5)); offs.append((pos, pos + len(w))); pos += len(w) + 1
        return ids, offs

    def predict(ids, mask):
        logits = np.zeros((len(ids), 5)); logits[:, 0] = 5.0
        for k, t in enumerate(ids):
            if t == 10: logits[k] = [0, 5, 0, 0, 0]
            if t == 11: logits[k] = [0, 0, 5, 0, 0]
        assert len(ids) == seq_len            # static shape: always padded to seq_len
        return logits

    return TokenClassifierNER(tokenize, predict, ID2LABEL, seq_len=seq_len, overlap=overlap)


def test_entity_straddling_a_window_boundary_is_found_R2():
    seq_len, overlap = 22, 6                   # body window = 20 tokens
    words = ["x"] * 19 + ["Emily", "Chen"] + ["y"] * 30   # name crosses the 20-token cut
    text = " ".join(words)
    spans = _fake_ner(seq_len, overlap).detect(text)
    assert [(s.label, s.text) for s in spans] == [("PERSON", "Emily Chen")]


def test_no_tokens_no_spans():
    assert _fake_ner(22, 6).detect("") == []
