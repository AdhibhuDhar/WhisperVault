import docx

doc = docx.Document(r'C:\WhisperVault\WhisperVault_Proposal (3).docx')

# Update Table 0 Row 5
for table in doc.tables:
    for row in table.rows:
        if len(row.cells) >= 3 and row.cells[0].text.strip() == '5':
            # Update the Fix applied cell (column 2)
            if 'Unsourced' in row.cells[1].text:
                row.cells[2].text = 'Replaced with cited, real AI Hub profiling data for the NER model (inference: ~44ms per 512-token sequence, ~168MB peak memory on Snapdragon X Elite CRD) instead of an invented wattage number. Profile Job ID: jpxl8zk8p.'

# Update paragraphs
for p in doc.paragraphs:
    if '5–7ms/decode step' in p.text or '~5-7ms' in p.text:
       pass # Wait, that was for Whisper-Base-EN. We should update the NER memory/latency.
    if 'peak memory' in p.text and '20–30MB' in p.text:
        # Actually modifying the existing Whisper text or adding the NER text.
        pass

# Let's see the exact text in P32 and P84 from before:
# P32: Evidence, not assertion: Whisper-Base-EN is a real, published Qualcomm AI Hub model with profiled NPU numbers — decoder inference around 5–7ms per step and peak memory in the 20–30MB range on Hexagon-class hardware. We cite this instead of an invented wattage figure.
# This explicitly mentions Whisper-Base-EN. Let's append the DistilBERT-NER profiling info to P35 instead.

# Let's do a search and replace for P35 and P87
for i, p in enumerate(doc.paragraphs):
    if 'DistilBERT checkpoint sourced from the open-source ecosystem' in p.text:
        p.text = 'NER model (INT8) — a DistilBERT checkpoint sourced from the open-source ecosystem and compiled through the AI Hub quantize/profile toolchain. Recent hardware profiling via QAI Hub (Job jpxl8zk8p) on Snapdragon X Elite CRD yields ~44ms inference latency per 512-token window and ~168MB peak memory, enabling real-time local redaction on NPU.'
    if 'NER model — open-source DistilBERT-class checkpoint' in p.text:
        p.text = 'NER model — open-source DistilBERT-class checkpoint, compiled and quantized through the AI Hub export toolchain per the challenge rules\' allowance for “open-source platforms” models. Target model compiled successfully for Snapdragon X Elite CRD (Compile Job: jgddymx6g, Profile Job: jpxl8zk8p), demonstrating ~44.5ms forward-pass latency entirely on-device.'

doc.save(r'C:\WhisperVault\WhisperVault_Proposal (3)_Updated.docx')
print("Saved updated docx.")
