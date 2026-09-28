import docx

doc = docx.Document(r"C:\WhisperVault\WhisperVault_Proposal (3).docx")
print("Tables count:", len(doc.tables))
for i, table in enumerate(doc.tables):
    print(f"\n--- TABLE {i} ---")
    for r_idx, row in enumerate(table.rows):
        cells = [c.text.replace("\n", " ").strip() for c in row.cells]
        print(f"Row {r_idx}: {cells}")
