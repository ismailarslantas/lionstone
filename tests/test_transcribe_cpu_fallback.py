import sys
import types

import pytest

from lionstone import transcribe as tr


class _W:
    def __init__(self, word, start, end):
        self.word, self.start, self.end, self.probability = word, start, end, 0.9


class _Seg:
    words = [_W(" merhaba", 0.0, 0.4), _W(" dünya", 0.5, 0.9)]


def _fake_module(fail_with: str | None, calls: list[str]):
    class WhisperModel:
        def __init__(self, model, device, compute_type):
            calls.append(device)
            self.device = device

        def transcribe(self, *a, **k):
            def gen():
                if fail_with and self.device != "cpu":
                    raise RuntimeError(fail_with)  # like faster-whisper: fails on first decode
                yield _Seg()
            return gen(), None

    return types.SimpleNamespace(WhisperModel=WhisperModel)


def test_missing_cuda_libs_fall_back_to_cpu(monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(sys.modules, "faster_whisper",
                        _fake_module("Library cublas64_12.dll is not found or cannot be loaded", calls))
    words = tr.transcribe("x.mp4")
    assert [w.text for w in words] == ["merhaba", "dünya"]
    assert calls == ["auto", "cpu"]


def test_other_errors_are_not_swallowed(monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(sys.modules, "faster_whisper", _fake_module("disk full", calls))
    with pytest.raises(RuntimeError, match="disk full"):
        tr.transcribe("x.mp4")
    assert calls == ["auto"]
