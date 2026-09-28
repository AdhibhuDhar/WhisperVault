"""Metadata-free export (R20) and source-file deletion (R29)."""
from __future__ import annotations

import os
import secrets
from datetime import datetime
from pathlib import Path


def write_text(path: str | Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def write_docx(path: str | Path, text: str) -> None:
    """Write a .docx with all identifying document properties blanked."""
    from docx import Document

    doc = Document()
    for para in text.split("\n"):
        doc.add_paragraph(para)
    cp = doc.core_properties
    fixed = datetime(2000, 1, 1)
    cp.author = ""
    cp.last_modified_by = ""
    cp.title = ""
    cp.subject = ""
    cp.comments = ""
    cp.keywords = ""
    cp.category = ""
    cp.created = fixed
    cp.modified = fixed
    cp.last_printed = fixed
    cp.revision = 1
    doc.save(str(path))


def secure_delete(path: str | Path, passes: int = 1) -> None:
    """Overwrite then delete. Best effort: SSD wear-levelling and journaling
    filesystems can keep old blocks, so pair this with full-disk encryption
    (BitLocker)."""
    p = Path(path)
    size = p.stat().st_size
    with open(p, "r+b") as f:
        for _ in range(passes):
            f.seek(0)
            remaining = size
            while remaining > 0:
                n = min(remaining, 1 << 20)
                f.write(secrets.token_bytes(n))
                remaining -= n
            f.flush()
            os.fsync(f.fileno())
    p.unlink()


def offer_source_deletion(path: str | Path, assume_yes: bool = False,
                          input_fn=input, out_fn=print) -> bool:
    """R29: the redacted transcript is clean, but the audio still holds the PII."""
    out_fn(f"\nThe original recording still contains raw spoken PII:\n  {path}")
    if assume_yes:
        answer = "y"
    else:
        answer = input_fn("Securely delete the original audio file? (cannot be undone) [y/N]: ")
    if answer.strip().lower() in ("y", "yes"):
        secure_delete(path)
        out_fn("Original audio overwritten and deleted.")
        return True
    out_fn("Kept. Remember to delete it yourself once you no longer need it.")
    return False
