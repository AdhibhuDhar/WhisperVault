"""Speech-to-text backends built on Qualcomm AI Hub's Whisper implementation.

We reuse `HfWhisperApp` from `qai_hub_models` (the same fixed-shape encoder +
bounded decoder loop Qualcomm profiles: 30 s window, MEAN_DECODE_LEN = 200) and
only choose where the encoder/decoder run:

  mode="cpu"  reference PyTorch implementation, works anywhere (dev / CI)
  mode="npu"  AI Hub-exported ONNX encoder/decoder on the Hexagon NPU through
              ONNX Runtime's QNN provider (`OnnxModelTorchWrapper.OnNPU`)

See docs/SETUP_SNAPDRAGON.md. The NPU path needs a Snapdragon X device and is
the part of this repo that has to be validated on real hardware.
"""
from __future__ import annotations

import numpy as np

from .audio import SAMPLE_RATE, WINDOW_S


class QAIHubWhisper:
    def __init__(self, mode: str = "cpu", encoder: str | None = None,
                 decoder: str | None = None, require_npu: bool = False):
        from qai_hub_models.models.whisper_base import App, Model

        if mode == "npu":
            if not (encoder and decoder):
                raise ValueError("npu mode needs --encoder and --decoder ONNX paths")
            if require_npu:
                from .ort_qnn import npu_available

                if not npu_available():
                    raise RuntimeError("NPU required but QNNExecutionProvider is unavailable")
            from qai_hub_models.utils.onnx.torch_wrapper import OnnxModelTorchWrapper

            enc = OnnxModelTorchWrapper.OnNPU(encoder)
            dec = OnnxModelTorchWrapper.OnNPU(decoder)
        elif mode == "cpu":
            collection = Model.from_pretrained()
            enc, dec = [collection.components[n] for n in collection.component_names]
        else:
            raise ValueError(f"unknown ASR mode {mode!r}")
        self.mode = mode
        self.app = App(enc, dec, Model.get_hf_whisper_version())

    def transcribe_chunk(self, audio: np.ndarray) -> str:
        # AI Hub's chunker appends an empty trailing chunk when the audio is
        # exactly 30 s, so keep windows one sample short of that boundary.
        limit = int(WINDOW_S * SAMPLE_RATE) - 1
        return self.app.transcribe(audio[:limit].astype(np.float32), SAMPLE_RATE)
