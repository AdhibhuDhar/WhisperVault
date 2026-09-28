import os
import pytest
from whispervault.export import offer_source_deletion, secure_delete, write_docx
from whispervault.pseudonymize import redact, reidentify
from whispervault.spans import Span
from whispervault.vault import (PassphraseProtector, export_backup, load_vault, save_vault)


def _spans(text, items):
    out = []
    for label, s in items:
        i = text.index(s)
        out.append(Span(i, i + len(s), label, s, "ner"))
    return out


TEXT = "John Smith met Dr. Chen. Later john smith called 312-555-0187."


def test_consistent_pseudonyms_and_no_leak():
    sp = _spans(TEXT, [("PERSON", "John Smith"), ("PERSON", "Dr. Chen"), ("PHONE", "312-555-0187")])
    sp.append(Span(TEXT.index("john smith"), TEXT.index("john smith") + 10, "PERSON", "john smith", "ner"))
    red, mapping = redact(TEXT, sp)
    assert red.count("[PERSON_001]") == 2          # same person -> same tag
    assert "Smith" not in red and "312" not in red
    assert reidentify(red, mapping) == TEXT         # exact round trip


def test_reidentify_falls_back_to_canonical_when_text_edited():
    sp = _spans(TEXT, [("PERSON", "John Smith")])
    red, mapping = redact(TEXT, sp)
    edited = red.replace("Later", "Afterwards") + " [PERSON_001] again"
    assert "John Smith" in reidentify(edited, mapping)


def test_vault_roundtrip_and_wrong_passphrase():
    p = PassphraseProtector("correct horse")
    blob = p.encrypt(b'{"a":1}')
    assert p.decrypt(blob) == b'{"a":1}'
    assert b'"a"' not in blob
    with pytest.raises(Exception):
        PassphraseProtector("wrong").decrypt(blob)


def test_vault_backup_R21(tmp_path):
    mapping = {"entities": {"[PERSON_001]": {"label": "PERSON", "canonical": "John"}}, "occurrences": []}
    v, b = tmp_path / "a.vault", tmp_path / "a.backup"
    save_vault(v, mapping, PassphraseProtector("machine-bound-stand-in"))
    export_backup(v, b, PassphraseProtector("machine-bound-stand-in"), "portable pass")
    assert load_vault(b, PassphraseProtector("portable pass")) == mapping


def test_docx_metadata_is_blank_R20(tmp_path):
    from docx import Document
    f = tmp_path / "o.docx"
    write_docx(f, "line one\nline two")
    cp = Document(str(f)).core_properties
    assert cp.author == "" and cp.last_modified_by == "" and cp.title == ""
    assert cp.created.year == 2000 and cp.modified.year == 2000


def test_secure_delete_and_prompt_R29(tmp_path):
    f = tmp_path / "audio.wav"
    f.write_bytes(b"RIFF" + os.urandom(5000))
    assert offer_source_deletion(f, input_fn=lambda _: "n", out_fn=lambda *_: None) is False
    assert f.exists()                               # user keeps control
    assert offer_source_deletion(f, input_fn=lambda _: "y", out_fn=lambda *_: None) is True
    assert not f.exists()
