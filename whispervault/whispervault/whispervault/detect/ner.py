"""Token-classification NER with static 512-token windows (Fix #2 for text).

The model is compiled for a FIXED sequence length (static graph = NPU friendly).
Long transcripts are cut into overlapping windows; each token keeps the
prediction from the window where it sits furthest from an edge, so an entity
that straddles a window boundary is still read with context on both sides.

The pure functions here (plan_windows, merge, decode) are unit-tested without
any model. `OnnxTokenClassifier.from_dir` wires them to an ONNX model, which
runs on the NPU through the QNN provider when available.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from ..spans import Span

DEFAULT_LABEL_MAP = {
    "PER": "PERSON", "PERSON": "PERSON",
    "ORG": "ORG",
    "LOC": "LOCATION", "GPE": "LOCATION", "LOCATION": "LOCATION",
}


def plan_windows(n_tokens: int, size: int, overlap: int) -> list[tuple[int, int]]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than window size")
    if n_tokens <= size:
        return [(0, n_tokens)]
    hop = size - overlap
    out, start = [], 0
    while True:
        end = min(start + size, n_tokens)
        out.append((start, end))
        if end == n_tokens:
            break
        start += hop
    return out


def merge_window_predictions(n_tokens: int, windows: Sequence[tuple[int, int]],
                             window_labels: Sequence[Sequence[str]],
                             window_scores: Sequence[Sequence[float]]):
    """Per token, keep the prediction from the window with the most context."""
    labels = ["O"] * n_tokens
    scores = [0.0] * n_tokens
    best = [-1] * n_tokens
    for (ws, we), labs, scs in zip(windows, window_labels, window_scores):
        for k in range(we - ws):
            i = ws + k
            edge_dist = min(k, (we - ws - 1) - k)
            if edge_dist > best[i]:
                best[i], labels[i], scores[i] = edge_dist, labs[k], scs[k]
    return labels, scores


def decode_entities(labels: Sequence[str], scores: Sequence[float],
                    offsets: Sequence[tuple[int, int]], text: str,
                    label_map: dict[str, str] | None = None,
                    min_score: float = 0.5) -> list[Span]:
    label_map = DEFAULT_LABEL_MAP if label_map is None else label_map
    ents: list[list] = []  # [start, end, type, [scores]]
    cur = None
    for lab, sc, (s, e) in zip(labels, scores, offsets):
        if lab == "O":
            cur = None
            continue
        prefix, _, etype = lab.partition("-")
        if not etype:  # labels without B-/I- prefix
            prefix, etype = "B", lab
        if prefix == "B" or cur is None or cur[2] != etype:
            cur = [s, e, etype, [sc]]
            ents.append(cur)
        else:
            cur[1] = e
            cur[3].append(sc)
    spans = []
    for s, e, etype, scs in ents:
        mapped = label_map.get(etype)
        mean = float(np.mean(scs))
        if mapped and mean >= min_score:
            spans.append(Span(s, e, mapped, text[s:e], "ner", mean))
    return spans


class TokenClassifierNER:
    """Model-agnostic driver: give it a tokenizer and a fixed-shape predictor."""

    def __init__(self, tokenize: Callable[[str], tuple[list[int], list[tuple[int, int]]]],
                 predict_window: Callable[[list[int], list[int]], np.ndarray],
                 id2label: dict[int, str], seq_len: int = 512, overlap: int = 64,
                 cls_id: int = 101, sep_id: int = 102, pad_id: int = 0,
                 label_map: dict[str, str] | None = None, min_score: float = 0.5):
        self.tokenize, self.predict_window, self.id2label = tokenize, predict_window, id2label
        self.seq_len, self.overlap = seq_len, overlap
        self.cls_id, self.sep_id, self.pad_id = cls_id, sep_id, pad_id
        self.label_map, self.min_score = label_map, min_score

    def detect(self, text: str) -> list[Span]:
        ids, offsets = self.tokenize(text)
        if not ids:
            return []
        body = self.seq_len - 2  # room for [CLS] and [SEP]
        windows = plan_windows(len(ids), body, self.overlap)
        w_labels, w_scores = [], []
        for ws, we in windows:
            chunk = [self.cls_id] + ids[ws:we] + [self.sep_id]
            mask = [1] * len(chunk)
            pad = self.seq_len - len(chunk)  # always pad to the static length
            chunk, mask = chunk + [self.pad_id] * pad, mask + [0] * pad
            logits = np.asarray(self.predict_window(chunk, mask))
            logits = logits[1: 1 + (we - ws)]
            e = np.exp(logits - logits.max(axis=-1, keepdims=True))
            probs = e / e.sum(axis=-1, keepdims=True)
            idx = probs.argmax(axis=-1)
            w_labels.append([self.id2label[int(i)] for i in idx])
            w_scores.append([float(probs[k, i]) for k, i in enumerate(idx)])
        labels, scores = merge_window_predictions(len(ids), windows, w_labels, w_scores)
        return decode_entities(labels, scores, offsets, text, self.label_map, self.min_score)

    @classmethod
    def from_dir(cls, model_dir: str, seq_len: int = 512, overlap: int = 64,
                 prefer_npu: bool = True, require_npu: bool | None = None, **kw):
        """Load model.onnx + tokenizer.json + config.json from a directory."""
        from tokenizers import Tokenizer

        from ..ort_qnn import make_session

        d = Path(model_dir)
        tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
        id2label = {int(k): v for k, v in cfg["id2label"].items()}
        session = make_session(str(d / "model.onnx"), prefer_npu, require_npu)
        in_meta = {i.name: i.type for i in session.get_inputs()}
        int_dtype = np.int32 if "int32" in in_meta.get("input_ids", "") else np.int64

        def tokenize(text):
            enc = tok.encode(text, add_special_tokens=False)
            return list(enc.ids), list(enc.offsets)

        def predict(ids, mask):
            feeds = {"input_ids": np.array([ids], dtype=int_dtype),
                     "attention_mask": np.array([mask], dtype=int_dtype)}
            if "token_type_ids" in in_meta:
                feeds["token_type_ids"] = np.zeros((1, len(ids)), dtype=int_dtype)
            return session.run(None, feeds)[0][0]

        def tid(name, default):
            v = tok.token_to_id(name)
            return default if v is None else v

        obj = cls(tokenize, predict, id2label, seq_len, overlap,
                  cls_id=tid("[CLS]", 101), sep_id=tid("[SEP]", 102),
                  pad_id=tid("[PAD]", 0), **kw)
        obj.session = session
        return obj


class SpacyNER:
    """CPU development fallback so the pipeline can be demoed without an ONNX model.

    NOT the NPU path. Requires `pip install spacy` and the en_core_web_sm model.
    """

    def __init__(self, model: str = "en_core_web_sm"):
        import spacy

        self.nlp = spacy.load(model, disable=["lemmatizer"])
        self.nlp.max_length = 5_000_000

    def detect(self, text: str) -> list[Span]:
        out = []
        for ent in self.nlp(text).ents:
            label = DEFAULT_LABEL_MAP.get(ent.label_)
            if label:
                out.append(Span(ent.start_char, ent.end_char, label, ent.text, "ner", 0.9))
        return out
