import os
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

model_id = 'dslim/distilbert-NER'
out_dir = r'C:\WhisperVault\whispervault\whispervault\models\ner'
os.makedirs(out_dir, exist_ok=True)

print('Loading model...')
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForTokenClassification.from_pretrained(model_id)
model.eval()

# Fixed shape for QAI Hub NPU compiling
seq_length = 512
dummy_input_ids = torch.ones(1, seq_length, dtype=torch.long)
dummy_attn_mask = torch.ones(1, seq_length, dtype=torch.long)

print('Exporting static ONNX...')
torch.onnx.export(
    model, 
    (dummy_input_ids, dummy_attn_mask), 
    os.path.join(out_dir, 'model.onnx'),
    input_names=['input_ids', 'attention_mask'],
    output_names=['logits'],
    opset_version=14,
    do_constant_folding=True
)
print('Static model exported successfully.')
