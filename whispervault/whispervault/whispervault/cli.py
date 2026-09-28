"""Command line interface: `python -m whispervault ...`"""
from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import sys
import time
from pathlib import Path

from . import __version__
from .detect import KeywordDictionary, load_terms
from .export import offer_source_deletion, write_docx, write_text
from .pipeline import detect, summarize, transcribe_audio
from .pseudonymize import redact, reidentify
from .review import review_interactive, write_html_report
from .vault import (PassphraseProtector, default_protector, export_backup,
                    load_vault, save_vault)


def _passphrase(args, confirm: bool = False) -> str | None:
    if args.passphrase_env and os.environ.get(args.passphrase_env):
        return os.environ[args.passphrase_env]
    if sys.platform == "win32":
        return None  # DPAPI needs no passphrase
    p = getpass.getpass("Vault passphrase: ")
    if confirm and getpass.getpass("Repeat passphrase: ") != p:
        sys.exit("Passphrases do not match.")
    return p


def _build_ner(args):
    if args.ner == "none":
        return None
    if args.ner == "spacy":
        from .detect.ner import SpacyNER

        print("[ner] spaCy CPU fallback (development only - not the NPU path)")
        return SpacyNER()
    from .detect.ner import TokenClassifierNER

    if not args.ner_dir:
        sys.exit("--ner onnx needs --ner-dir (folder with model.onnx, tokenizer.json, config.json)")
    ner = TokenClassifierNER.from_dir(args.ner_dir, require_npu=args.require_npu or None)
    from .ort_qnn import describe_session

    print(f"[ner] ONNX Runtime providers: {describe_session(ner.session)}")
    return ner


def cmd_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    stem = Path(args.audio or args.transcript).stem
    if args.audio:
        from .asr import QAIHubWhisper

        asr = QAIHubWhisper(args.asr, args.encoder, args.decoder, args.require_npu)
        text = transcribe_audio(args.audio, asr,
                                progress=lambda i, n: print(f"[asr] window {i}/{n}", end="\r"))
        print()
    else:
        text = Path(args.transcript).read_text(encoding="utf-8")
    t_asr = time.time() - t0

    dictionary = None
    if args.dict:
        dictionary = KeywordDictionary(load_terms(args.dict))
    spans = detect(text, _build_ner(args), dictionary)
    print(f"[detect] {len(spans)} span(s) flagged")

    if args.yes:
        print("[review] --yes: UNATTENDED mode. Not recommended for regulated data.")
        accepted = set(range(len(spans)))
    elif sys.stdin.isatty():
        accepted = review_interactive(text, spans)
    else:
        sys.exit("Interactive review needs a terminal. Use --yes for unattended runs.")

    redacted, mapping = redact(text, [s for i, s in enumerate(spans) if i in accepted])
    write_text(out / f"{stem}.redacted.txt", redacted)
    if args.docx:
        write_docx(out / f"{stem}.redacted.docx", redacted)
    if args.html_report:
        write_html_report(str(out / f"{stem}.review.html"), text, spans, accepted, redacted)
        print("[warn] review.html contains the ORIGINAL text - delete it after review.")
    if args.keep_raw:
        write_text(out / f"{stem}.raw.txt", text)
        print("[warn] --keep-raw wrote the UNREDACTED transcript to disk.")

    protector = default_protector(_passphrase(args, confirm=True))
    save_vault(out / f"{stem}.vault", mapping, protector)
    summary = {"version": __version__, **summarize(spans, accepted),
               "seconds_asr": round(t_asr, 2), "seconds_total": round(time.time() - t0, 2)}
    (out / f"{stem}.summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[done] {out}/{stem}.redacted.txt  +  encrypted vault  +  summary.json")

    if args.audio and not args.no_delete_prompt and sys.stdin.isatty():
        offer_source_deletion(args.audio)
    return 0


def cmd_reveal(args) -> int:
    try:
        mapping = load_vault(args.vault, default_protector(_passphrase(args)))
    except Exception:
        sys.exit("Could not unlock the vault: wrong passphrase, a different Windows "
                 "account than the one that created it, or a damaged file.")
    text = reidentify(Path(args.input).read_text(encoding="utf-8"), mapping)
    if args.out:
        write_text(args.out, text)
        print(f"Wrote re-identified text to {args.out} (contains PII - handle accordingly).")
    else:
        sys.stdout.write(text)
    return 0


def cmd_backup(args) -> int:
    src = default_protector(_passphrase(args))
    pw = getpass.getpass("Backup passphrase: ")
    export_backup(args.vault, args.out, src, pw)
    print(f"Passphrase-protected backup written to {args.out}")
    return 0


def cmd_info(_args) -> int:
    print(f"WhisperVault {__version__}")
    try:
        import onnxruntime as ort

        print("ONNX Runtime providers:", ", ".join(ort.get_available_providers()))
        print("NPU (QNN) available:", "QNNExecutionProvider" in ort.get_available_providers())
    except ImportError:
        print("onnxruntime not installed - NER/ASR on NPU unavailable")
    print("Platform:", sys.platform, "| vault backend:",
          "DPAPI" if sys.platform == "win32" else "passphrase")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(prog="whispervault", description=__doc__)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="transcribe (or read a transcript) and redact")
    src = r.add_mutually_exclusive_group(required=True)
    src.add_argument("--audio")
    src.add_argument("--transcript", help="skip ASR, use an existing text file")
    r.add_argument("--out", default="out")
    r.add_argument("--dict", help="text file of literal keywords, one per line")
    r.add_argument("--asr", choices=["cpu", "npu"], default="cpu")
    r.add_argument("--encoder"); r.add_argument("--decoder")
    r.add_argument("--ner", choices=["none", "onnx", "spacy"], default="none")
    r.add_argument("--ner-dir")
    r.add_argument("--require-npu", action="store_true",
                   help="fail instead of silently falling back to CPU")
    r.add_argument("--yes", action="store_true", help="skip review (unattended)")
    r.add_argument("--docx", action="store_true")
    r.add_argument("--html-report", action="store_true")
    r.add_argument("--keep-raw", action="store_true")
    r.add_argument("--no-delete-prompt", action="store_true")
    r.add_argument("--passphrase-env", default="WHISPERVAULT_PASSPHRASE")
    r.set_defaults(func=cmd_run)

    v = sub.add_parser("reveal", help="re-identify a redacted file using its vault")
    v.add_argument("--vault", required=True); v.add_argument("--input", required=True)
    v.add_argument("--out"); v.add_argument("--passphrase-env", default="WHISPERVAULT_PASSPHRASE")
    v.set_defaults(func=cmd_reveal)

    b = sub.add_parser("backup-vault", help="passphrase-protected vault backup (R21)")
    b.add_argument("--vault", required=True); b.add_argument("--out", required=True)
    b.add_argument("--passphrase-env", default="WHISPERVAULT_PASSPHRASE")
    b.set_defaults(func=cmd_backup)

    i = sub.add_parser("info", help="show NPU / provider availability")
    i.set_defaults(func=cmd_info)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
