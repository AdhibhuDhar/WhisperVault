import numpy as np
from whispervault.audio import chunk_bounds, chunk_audio
from whispervault.stitch import stitch, stitch_pair

SR = 16000


def test_short_audio_single_window():
    assert chunk_bounds(10 * SR) == [(0, 10 * SR)]


def test_windows_cover_everything_with_5s_overlap():
    n = 100 * SR
    b = chunk_bounds(n)
    assert b[0][0] == 0 and b[-1][1] == n
    for (s1, e1), (s2, e2) in zip(b, b[1:]):
        assert e1 - s2 == 5 * SR          # exactly 5 s shared
        assert e1 - s1 <= 30 * SR         # never longer than Whisper's window
    assert all(e - s <= 30 * SR for s, e in b)


def test_last_window_never_tiny_and_chunks_match_bounds():
    audio = np.zeros(61 * SR, dtype=np.float32)
    chunks = chunk_audio(audio)
    assert sum(len(c) for c in chunks) >= len(audio)
    assert len(chunks[-1]) >= 5 * SR


def test_stitch_removes_overlap_and_repairs_cut_word():
    a = "the meeting was attended by Doctor Emily Che"          # cut mid-word at the edge
    b = "attended by Doctor Emily Chen and the patient John Smith"
    assert stitch_pair(a, b) == "the meeting was attended by Doctor Emily Chen and the patient John Smith"


def test_stitch_no_overlap_falls_back_to_concat():
    assert stitch(["hello there", "completely different words"]) == "hello there completely different words"


def test_stitch_many_windows():
    words = [f"w{i}" for i in range(120)]
    texts = [" ".join(words[i:i + 40]) for i in range(0, 80, 30)]  # 10-word overlaps
    assert stitch(texts).split() == words[:100]
