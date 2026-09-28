import docx

doc = docx.Document(r"C:\WhisperVault\WhisperVault_Proposal (3).docx")
for i, para in enumerate(doc.paragraphs):
    if para.text.strip():
        print(f"[{i}] {para.text}")
