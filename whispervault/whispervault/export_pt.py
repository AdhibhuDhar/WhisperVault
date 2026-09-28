import os
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

model_id = 'dslim/distilbert-NER'
out_dir = r'C:\WhisperVault\whispervault\whispervault\models\ner'

print('Loading model...')
model = AutoModelForTokenClassification.from_pretrained(model_id)
model.eval()

seq_length = 512
dummy_input_ids = torch.ones(1, seq_length, dtype=torch.long)
dummy_attn_mask = torch.ones(1, seq_length, dtype=torch.long)
dummy_inputs = (dummy_input_ids, dummy_attn_mask)

print('Tracing model via TorchScript...')
# QAI Hub explicitly supports TorchScript for best compatibility
traced_model = torch.jit.trace(model, dummy_inputs, strict=False)

pt_path = os.path.join(out_dir, 'model.pt')
torch.jit.save(traced_model, pt_path)
print(f'Saved traced PyTorch model to: {pt_path}')
