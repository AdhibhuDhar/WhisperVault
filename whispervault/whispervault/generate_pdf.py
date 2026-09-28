import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# 1. GENERATE PROJECT DESCRIPTION PDF
def create_project_description(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#004b87"),
        spaceAfter=20,
        alignment=1 # Center
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor("#2a2a2a"),
        spaceBefore=15,
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontSize=11,
        leading=15,
        spaceAfter=10
    )

    story = []

    # Title
    story.append(Paragraph("WhisperVault: Air-Gapped PII Redaction Engine", title_style))
    story.append(Paragraph("SNAPDRAGON® AI LAB — BUILD & PRESENT CHALLENGE | Adhibhu Dhar", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    # Exec Summary
    story.append(Paragraph("Executive Summary", heading_style))
    exec_desc = (
        "Legal, medical, and enterprise professionals rely on transcription, but cloud-based APIs are "
        "frequently disqualified by HIPAA regulations, attorney-client privilege, and corporate policy. "
        "Local transcription solves the cloud problem but produces unprotected plaintext documents riddled "
        "with sensitive PII, creating severe liabilities.\n\n"
        "WhisperVault is a fully robust, file-in/file-out application driving a zero-network, purely on-device "
        "transcription and redaction pipeline utilizing the Hexagon NPU on Snapdragon hardware. It seamlessly transcribes audio "
        "and immediately pseudonymizes sensitive spans, securely logging the encryption keys into a DPAPI vault."
    )
    story.append(Paragraph(exec_desc.replace('\n', '<br/>'), body_style))

    # Architecture
    story.append(Paragraph("Technical Pipeline & Hexagon Implementation", heading_style))
    arch_desc = (
        "WhisperVault deliberately leverages static-graph AI compilation over dynamic execution. "
        "By enforcing fixed 30-second bounded chunking for ASR (Whisper-Base-EN) and a 512-token overlap for NLP "
        "(DistilBERT-NER), the platform completely sidesteps the bottlenecks commonly associated with open-ended LLMs "
        "running on NPU."
    )
    story.append(Paragraph(arch_desc, body_style))

    # Insert Image
    img_path = r'C:\WhisperVault\whispervault\whispervault\docs\architecture.png'
    if os.path.exists(img_path):
        story.append(Spacer(1, 0.1*inch))
        img = Image(img_path, width=6*inch, height=3.5*inch)
        # Preserve Aspect Ratio
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 0.1*inch))

    # Real Metrics
    story.append(Paragraph("Qualcomm AI Hub Verified Profiling", heading_style))
    metrics_desc = (
        "Targeting the Snapdragon X Elite CRD (Compile: jgddymx6g, Profile: jpxl8zk8p), the Hexagon NPU "
        "powers WhisperVault with exceptional performance metrics:\n"
        "• <b>Inference Latency:</b> ~44.5ms forward-pass on 512 tokens.\n"
        "• <b>Peak Memory Footprint:</b> ~168MB enabling seamless real-time operation."
    )
    story.append(Paragraph(metrics_desc.replace('\n', '<br/>'), body_style))

    # Security
    story.append(Paragraph("Reversible DPAPI Vault & Honest Compliance", heading_style))
    sec_desc = (
        "WhisperVault replaces sensitive entities with consistent tokens (e.g., 'John Smith' -> [PERSON_001]). "
        "The relational cryptographic mappings are backed via the native Windows Data Protection API (DPAPI). "
        "A 30-point adversarial failure matrix was established and mitigated—proving architectural mastery and an honest, "
        "no-vaporware deployment strategy ready for enterprise adoption."
    )
    story.append(Paragraph(sec_desc, body_style))

    doc.build(story)

# 2. GENERATE PITCH PRESENTATION PDF
def create_pitch_presentation(filename):
    doc = SimpleDocTemplate(filename, pagesize=landscape(letter),
                            leftMargin=0.5*inch, rightMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    title_slide_style = ParagraphStyle(
        'TitleSlide',
        parent=styles['Heading1'],
        fontSize=36,
        textColor=colors.HexColor("#004b87"),
        spaceAfter=30,
        alignment=1 # Center
    )

    slide_heading_style = ParagraphStyle(
        'SlideHeading',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor("#004b87"),
        spaceAfter=20,
        alignment=0
    )

    slide_body_style = ParagraphStyle(
        'SlideBody',
        parent=styles['Normal'],
        fontSize=18,
        leading=24,
        spaceAfter=15,
        bulletIndent=20,
        leftIndent=40
    )

    story = []

    def add_page_break():
        story.append(PageBreak())

    # SLIDE 1
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("WhisperVault", title_slide_style))
    story.append(Paragraph("<font size=20>Air-Gapped PII Redaction Engine</font>", ParagraphStyle('Sub', alignment=1)))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("SNAPDRAGON® AI LAB — BUILD & PRESENT CHALLENGE<br/>Adhibhu Dhar | KIIT", ParagraphStyle('SubSub', alignment=1, fontSize=14)))
    add_page_break()

    # SLIDE 2
    story.append(Paragraph("The Problem: Liability in Plaintext", slide_heading_style))
    story.append(Spacer(1, 0.5*inch))
    problem_points = [
        "Cloud APIs are prohibited by policy & regulations (HIPAA, attorney-client privilege).",
        "Local transcription leaves behind plaintext PII, making offline files a corporate liability.",
        "Existing offline tools physically destroy data (irreversible text blanking), preventing legitimate access."
    ]
    for p in problem_points:
        story.append(Paragraph(f"• {p}", slide_body_style))
    add_page_break()

    # SLIDE 3
    story.append(Paragraph("The Solution: WhisperVault", slide_heading_style))
    story.append(Paragraph("A fully offline, on-device pipeline transcribing and pseudonymizing automatically.", slide_body_style))
    story.append(Spacer(1, 0.3*inch))
    img_path = r'C:\WhisperVault\whispervault\whispervault\docs\architecture.png'
    if os.path.exists(img_path):
        img = Image(img_path, width=7*inch, height=4*inch)
        img.hAlign = 'CENTER'
        story.append(img)
    add_page_break()

    # SLIDE 4
    story.append(Paragraph("Hexagon Implementation & Hardware Profiling", slide_heading_style))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("<b>No Dynamic Overheads:</b> WhisperVault uses strictly static tensors, resolving typical edge-LLM compilation blocks.", slide_body_style))
    story.append(Paragraph("<b>Verified Qualcomm AI Hub Profiling Metrics (Job: jpxl8zk8p):</b>", slide_body_style))
    story.append(Paragraph("— Target Device: Snapdragon X Elite CRD", slide_body_style))
    story.append(Paragraph("— ~44.5ms inference latency per 512-token forward-pass.", slide_body_style))
    story.append(Paragraph("— ~168MB peak memory footprint on-device.", slide_body_style))
    add_page_break()

    # SLIDE 5
    story.append(Paragraph("DPAPI Vault & Honest Deployment", slide_heading_style))
    story.append(Spacer(1, 0.5*inch))
    deploy_points = [
        "<b>Tri-Layer Accuracy:</b> Matches Name/Orgs (NPU), standard IDs via Regex (CPU), and Codenames via dictionaries (CPU).",
        "<b>Reversible Pseudonymization:</b> Encrypted tokens map original entities inside the native Windows DPAPI architecture.",
        "<b>Zero Deployment Overhead:</b> Simple Python MSIX file-in/file-out app without virtual driver configurations.",
        "<b>Robust Architecture:</b> 30+ adversarial edge cases tracked and mitigated."
    ]
    for p in deploy_points:
        story.append(Paragraph(f"• {p}", slide_body_style))

    doc.build(story)

if __name__ == '__main__':
    create_project_description(r"C:\WhisperVault\WhisperVault_Project_Description.pdf")
    create_pitch_presentation(r"C:\WhisperVault\WhisperVault_Pitch_Presentation.pdf")
    print("Successfully generated beautifully styled professional PDFs.")
