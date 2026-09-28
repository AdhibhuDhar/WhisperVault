import os
import json
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch

model_id = "dslim/distilbert-NER"
out_dir = "models/ner"
os.makedirs(out_dir, exist_ok=True)

print("Loading tokenizer and model...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForTokenClassification.from_pretrained(model_id)

print("Saving tokenizer and config...")
tokenizer.save_pretrained(out_dir)
# tokenizer.save_pretrained() already saves tokenizer.json for fast tokenizers

model.config.save_pretrained(out_dir)

print("Exporting ONNX...")
dummy_input = torch.zeros(1, 512, dtype=torch.long)
torch.onnx.export(
    model, 
    (dummy_input, dummy_input), 
    os.path.join(out_dir, "model.onnx"),
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    dynamic_axes={
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "logits": {0: "batch_size", 1: "sequence_length"}
    },
    opset_version=14
)
print("Done!")
