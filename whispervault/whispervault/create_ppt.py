from pptx import Presentation
from pptx.util import Inches, Pt
import os

prs = Presentation()

title_slide_layout = prs.slide_layouts[0]
bullet_slide_layout = prs.slide_layouts[1]
image_slide_layout = prs.slide_layouts[5] # usually Title Only

# Slide 1: Title
slide_1 = prs.slides.add_slide(title_slide_layout)
slide_1.shapes.title.text = "WhisperVault"
slide_1.placeholders[1].text = "Air-Gapped PII Redaction Engine\nSNAPDRAGON® AI LAB — BUILD & PRESENT CHALLENGE\nAdhibhu Dhar | KIIT"

# Slide 2: The Problem
slide_2 = prs.slides.add_slide(bullet_slide_layout)
slide_2.shapes.title.text = "The Problem: Liability in Plaintext"
body_2 = slide_2.shapes.placeholders[1].text_frame
body_2.text = "Organizations face a catch-22 in sensitive transcription:"
p1 = body_2.add_paragraph()
p1.text = "Cloud APIs are prohibited by policy/regulations (HIPAA, attorney-client privilege)."
p2 = body_2.add_paragraph()
p2.text = "Local transcription leaves behind plaintext PII, making the file a liability."
p3 = body_2.add_paragraph()
p3.text = "Existing offline tools permanently destroy data (irreversible text blanking) preventing owners from re-identifying legitimate information."

# Slide 3: The Solution
slide_3 = prs.slides.add_slide(bullet_slide_layout)
slide_3.shapes.title.text = "WhisperVault: Reversible, Air-Gapped Redaction"
body_3 = slide_3.shapes.placeholders[1].text_frame
body_3.text = "A fully offline, on-device pipeline transcribing and pseudonymizing automatically."
p_3_1 = body_3.add_paragraph()
p_3_1.text = "Hexagon NPU Accelerated: Whisper-Base-EN (ASR) + DistilBERT-NER (NLP)"
p_3_2 = body_3.add_paragraph()
p_3_2.text = "Two-Stage Architecture:"
p_3_3 = body_3.add_paragraph()
p_3_3.text = "Stage 1: ASR transcribes in overlapping 30s statically-compiled chunks to utilize the NPU without dynamic-shape decoding bottlenecks."
p_3_3.level = 1
p_3_4 = body_3.add_paragraph()
p_3_4.text = "Stage 2: Hybrid detection engine pseudonymizes spans consistently across the file."
p_3_4.level = 1

# Slide 4: Architecture Diagram
slide_4 = prs.slides.add_slide(image_slide_layout)
slide_4.shapes.title.text = "WhisperVault Architecture"
img_path = r'C:\WhisperVault\whispervault\whispervault\docs\architecture.png'
if os.path.exists(img_path):
    # Add image to slide
    left = Inches(1)
    top = Inches(2)
    height = Inches(4.5)
    slide_4.shapes.add_picture(img_path, left, top, height=height)

# Slide 5: Hexagon Implementation
slide_6 = prs.slides.add_slide(bullet_slide_layout)
slide_6.shapes.title.text = "Hexagon Implementation & Hardware Profiling"
body_6 = slide_6.shapes.placeholders[1].text_frame
body_6.text = "Designed specifically for static-graph NPU constraints."
p_6_1 = body_6.add_paragraph()
p_6_1.text = "No Dynamic Overheads: Both AI models use strictly static tensors."
p_6_2 = body_6.add_paragraph()
p_6_2.text = "Real Qualcomm AI Hub Profiling Metrics (Job: jpxl8zk8p):"
p_6_3 = body_6.add_paragraph()
p_6_3.text = "Target Device: Snapdragon X Elite CRD"
p_6_3.level = 1
p_6_4 = body_6.add_paragraph()
p_6_4.text = "~44.5ms inference latency per 512-token forward-pass."
p_6_4.level = 1
p_6_5 = body_6.add_paragraph()
p_6_5.text = "~168MB peak memory footprint on-device."
p_6_5.level = 1

pptx_path = r'C:\WhisperVault\WhisperVault_Presentation.pptx'
prs.save(pptx_path)
print(f"Presentation saved successfully to {pptx_path}")
