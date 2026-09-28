"""ONNX Runtime session helper that targets the Hexagon NPU via the QNN provider.

Silent CPU fallback is the classic way a 'NPU demo' quietly stops being one, so
`require_npu=True` turns a missing QNN provider into a hard error, and
`describe_session` reports which providers are actually active.
"""
from __future__ import annotations

import os


def npu_available() -> bool:
    try:
        import onnxruntime as ort
    except ImportError:
        return False
    return "QNNExecutionProvider" in ort.get_available_providers()


def make_session(model_path: str, prefer_npu: bool = True, require_npu: bool | None = None,
                 backend_path: str = "QnnHtp.dll"):
    import onnxruntime as ort

    if require_npu is None:
        require_npu = os.environ.get("WHISPERVAULT_REQUIRE_NPU") == "1"
    providers: list = []
    if prefer_npu and npu_available():
        providers.append(("QNNExecutionProvider", {"backend_path": backend_path}))
    elif require_npu:
        raise RuntimeError(
            "NPU required but QNNExecutionProvider is not available. "
            "Install 'onnxruntime-qnn' on a Snapdragon X PC (see docs/SETUP_SNAPDRAGON.md)."
        )
    providers.append("CPUExecutionProvider")
    return ort.InferenceSession(model_path, providers=providers)


def describe_session(session) -> str:
    return ", ".join(session.get_providers())
