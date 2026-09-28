import os
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

model_id = 'dslim/distilbert-NER'
out_dir = r'C:\WhisperVault\whispervault\whispervault\models\ner'
os.makedirs(out_dir, exist_ok=True)

print('Loading model...')
model = AutoModelForTokenClassification.from_pretrained(model_id)
model.eval()

# Create a wrapper class that returns only the logits tensor
class DistilBertNERWrapper(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
    
    def forward(self, input_ids, attention_mask):
        return self.model(input_ids=input_ids, attention_mask=attention_mask).logits

wrapper = DistilBertNERWrapper(model)
wrapper.eval()

seq_length = 512
dummy_input_ids = torch.ones(1, seq_length, dtype=torch.long)
dummy_attn_mask = torch.ones(1, seq_length, dtype=torch.long)
dummy_inputs = (dummy_input_ids, dummy_attn_mask)

print('Tracing model via TorchScript...')
traced_model = torch.jit.trace(wrapper, dummy_inputs, strict=False)

pt_path = os.path.join(out_dir, 'model_wrapper.pt')
torch.jit.save(traced_model, pt_path)
print(f'Saved traced PyTorch model to: {pt_path}')
