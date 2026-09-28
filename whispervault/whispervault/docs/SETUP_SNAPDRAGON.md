# Running WhisperVault on a Snapdragon X PC (HP OmniBook X)

Everything below the "one-time online step" runs offline. Nothing about your audio, transcript
or vault ever leaves the machine.

## 1. Python and packages
* Python 3.11 (`onnxruntime-qnn` publishes cp311 wheels for both `win_arm64` and `win_amd64`;
  the AI Hub models package supports 3.10 to 3.13).
* ```powershell
  py -3.11 -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt onnxruntime-qnn
  python -m whispervault info
  ```
  `info` must print `NPU (QNN) available: True`. If it prints `False`, you are on the CPU.

## 2. One-time online step: get the models
Model compilation happens on Qualcomm AI Hub Workbench (cloud) and touches **no user data**.

```powershell
pip install qai-hub-models
qai-hub-models install whisper_base
qai-hub configure --api_token <YOUR_TOKEN>          # AI Hub Workbench -> Account -> Settings
qai-hub-models export whisper_base                  # or: qai-hub-models fetch Whisper-Base --runtime onnx
```
This produces the encoder and decoder ONNX files. Note their paths.

For NER, take an open-source token-classification checkpoint (for example a DistilBERT NER
model from Hugging Face), export it to ONNX with a **fixed sequence length of 512**, and put
`model.onnx`, `tokenizer.json`, `config.json` in one folder. Quantize/compile it with the AI
Hub toolchain to run it on the NPU. (`config.json` must contain `id2label`.)

## 3. Run
```powershell
# CPU reference path first, to prove the pipeline works
python -m whispervault run --audio interview.wav --dict codenames.txt --ner onnx --ner-dir models\ner --out out

# Hexagon NPU. --require-npu turns a silent CPU fallback into an error
python -m whispervault run --audio interview.wav --asr npu ^
   --encoder models\whisper_base\encoder\model.onnx --decoder models\whisper_base\decoder\model.onnx ^
   --ner onnx --ner-dir models\ner --require-npu --dict codenames.txt --out out
```
The vault uses Windows DPAPI automatically (no passphrase). Use
`python -m whispervault backup-vault --vault out\x.vault --out x.backup` to make a
passphrase-protected copy that survives a Windows profile reset.

## 4. Validate on the device (this is the part I could not do without hardware)
1. `info` shows the QNN provider.
2. Run with `--require-npu`; a fallback raises an error instead of hiding.
3. Watch NPU load in Task Manager (Performance -> NPU) during ASR and NER.
4. Compare wall-clock and battery against the CPU run with the same audio; record the numbers.
5. Note which ops fall back to CPU (ONNX Runtime verbose logging) and put the result in your deck.
6. Test on a real 30-minute recording, review the flagged spans, and record the false-negative rate.
7. Test the DPAPI vault: create, close, reopen, and run `reveal`.

## Security notes
* DPAPI protects the vault only as well as the Windows account is protected (same model as
  Windows Credential Manager). Use BitLocker.
* After export the tool offers to overwrite and delete the source audio. On SSDs this is best
  effort; full-disk encryption is the real protection.
* `--html-report` and `--keep-raw` write the original text to disk. They are opt-in for that reason.
