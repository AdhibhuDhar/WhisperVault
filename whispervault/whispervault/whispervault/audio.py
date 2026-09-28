"""Audio loading and overlapping 30-second windowing (Fix #2).

Whisper always consumes a fixed 30 s window, which is what makes its graph
static and NPU-friendly. We add a 5 s overlap between consecutive windows so
that a word or name never sits only on a hard cut edge.
"""
from __future__ import annotations

import shutil
import subprocess
from math import gcd

import numpy as np

SAMPLE_RATE = 16_000
WINDOW_S = 30.0
OVERLAP_S = 5.0


def load_audio(path: str, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Load any audio file as mono float32 at target_sr.

    WAV/FLAC/OGG go through soundfile. Anything else (mp3, m4a, ...) needs
    ffmpeg on PATH.
    """
    try:
        import soundfile as sf

        data, sr = sf.read(path, dtype="float32", always_2d=False)
        if data.ndim == 2:
            data = data.mean(axis=1)
        if sr != target_sr:
            from scipy.signal import resample_poly

            g = gcd(sr, target_sr)
            data = resample_poly(data, target_sr // g, sr // g).astype(np.float32)
        return data
    except Exception as exc:  # soundfile cannot decode mp3/m4a on all builds
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                f"Could not decode {path!r} with soundfile ({exc}) and ffmpeg "
                "is not on PATH. Install ffmpeg or convert to WAV."
            ) from exc
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1",
             "-ar", str(target_sr), "-"],
            capture_output=True, check=True,
        )
        return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def chunk_bounds(
    n_samples: int,
    sr: int = SAMPLE_RATE,
    window_s: float = WINDOW_S,
    overlap_s: float = OVERLAP_S,
) -> list[tuple[int, int]]:
    """(start, end) sample indices of overlapping windows covering the audio."""
    if overlap_s >= window_s:
        raise ValueError("overlap must be smaller than the window")
    win = int(window_s * sr)
    hop = int((window_s - overlap_s) * sr)
    if n_samples <= win:
        return [(0, n_samples)]
    bounds, start = [], 0
    while True:
        end = min(start + win, n_samples)
        bounds.append((start, end))
        if end == n_samples:
            break
        start += hop
    return bounds


def chunk_audio(audio: np.ndarray, **kw) -> list[np.ndarray]:
    return [audio[a:b] for a, b in chunk_bounds(len(audio), **kw)]
