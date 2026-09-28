# Implementation status

An honest map of what is built, what was actually executed, and what still has to be
validated on a Snapdragon X device. "Executed" means I ran it (Linux, CPU, Python 3.12)
while building this repo; it does not mean it has been benchmarked on the Hexagon NPU.

| Area | Ref | State | Evidence |
|---|---|---|---|
| Overlapping 30 s / 5 s audio windows | Fix #2 | Implemented, tested | `tests/test_audio_stitch.py` |
| Overlap-aware transcript stitching | Fix #2, R17 | Implemented (text alignment), tested | same. Word-timestamp alignment is roadmap |
| Regex detectors (SSN, phone, card+Luhn, email, MRN, dosage, Aadhaar, PAN, IP) | Fix #3 | Implemented, tested | `tests/test_detectors.py` |
| Spoken-number detection, length-specific | R16, R24 | Implemented, tested | "one two three ..." -> SSN/PHONE; PINs and counts left alone |
| Literal-only keyword dictionary | R28 | Implemented, tested | `.*` rejected; `\w+` matches only itself |
| Over-matching warning (>50% flagged) | R28 | Implemented, tested | `test_over_matching_warning` |
| Windowed token-classification NER (static 512 window, overlap, edge-aware merge, BIO decode) | Fix #2 | Logic implemented, tested with a stand-in model | entity straddling a window boundary is found |
| Loading a real DistilBERT-NER ONNX (`TokenClassifierNER.from_dir`) | Fix #4 | Written, **not executed** | needs a model folder; no model download in my sandbox |
| Consistent pseudonyms + exact re-identification | Fix #7 | Implemented, tested | byte-identical round trip on the sample |
| Encrypted vault, passphrase mode + passphrase backup | Fix #7, R21 | Implemented, tested | wrong passphrase fails |
| Encrypted vault, Windows DPAPI mode | Fix #7, R11 | Written, **not executed** | needs Windows; ctypes calls unverified |
| Metadata-free DOCX export | R20 | Implemented, tested | author/modified-by blank, dates fixed |
| Secure delete + post-export prompt | R29 | Implemented, tested | SSD/journaling caveat documented in code |
| Grouped review, ambiguous names never bulk-decided, no global accept-all | R10, R23, R27 | Implemented, tested (injected input) | `tests/test_review_pipeline.py` |
| ASR via AI Hub Whisper (`HfWhisperApp`, CPU reference + ONNX/QNN NPU) | Fix #1, #5 | Written against Qualcomm's source, **not executed** | needs model download; NPU path needs the device |
| Running on the Hexagon NPU, latency, power, op coverage | hardware hook | **Not measured** | to do on the OmniBook X (see SETUP_SNAPDRAGON.md) |

## Not implemented (roadmap)

* **R18 context clustering.** Today only a heuristic exists: bare single-token names are
  flagged "ambiguous" and reviewed one by one. "John" and "John Smith" therefore get
  different tags even when they are the same person.
* **R17 word-timestamp stitching** (text alignment is used instead).
* **R22 domain profiles** (HIPAA / legal / generic entity sets). One generic profile ships.
* **R19 quasi-identifiers** ("the defendant's 8-year-old daughter"). No automated
  de-identification tool catches these; human review is the safeguard.
* **English-only forcing.** AI Hub's `whisper_base` is multilingual and `HfWhisperApp` does
  not force a language. The NER model is English.
* **Desktop GUI / installer.** The prototype is a CLI plus an optional HTML review report.
* **Live microphone processing** is out of scope by design (R13).

## Known limitations seen while testing

* On the sample transcript the stand-in NER (spaCy small) missed the first name "Priya".
  A miss like this is exactly why review is mandatory. It is not a compliance tool.
* A bare first name and a full name of the same person get separate pseudonyms.
* The label word "MRN" can be flagged as an organisation by a generic NER; review removes it.
