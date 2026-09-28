Write-Host "=========================================================="
Write-Host "  WhisperVault: Snapdragon AI Lab Hackathon Deployment"
Write-Host "=========================================================="
Write-Host ""
Write-Host "[1/3] Activating Virtual Environment..."
.\venv\Scripts\activate
Write-Host "Environment enabled."
Write-Host ""

Write-Host "[2/3] Demonstrating CPU (Reference) Run on transcript..."
python -m whispervault run --transcript examples/sample_transcript.txt --dict examples/codenames.txt --ner onnx --ner-dir models/ner --yes --out out
Write-Host "Successfully generated redacted transcript and Vault output!"
Write-Host ""

Write-Host "[3/3] Reversing redaction (Secure Re-identification)..."
python -m whispervault reveal --vault out/sample_transcript.vault --input out/sample_transcript.redacted.txt

Write-Host ""
Write-Host "=========================================================="
Write-Host "To test Snapdragon NPU execution using AI-Hub Whisper Base:"
Write-Host "1. qai-hub configure --api_token <YOUR_TOKEN>"
Write-Host "2. qai-hub-models export whisper_base"
Write-Host "3. Run with --require-npu (See docs\SETUP_SNAPDRAGON.md)"
Write-Host "=========================================================="
