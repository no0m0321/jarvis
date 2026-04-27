from __future__ import annotations

from typing import Any, Optional

import numpy as np

_model: Optional[Any] = None
_model_name: Optional[str] = None


def _get_model(name: str) -> Any:
    global _model, _model_name
    if _model is None or _model_name != name:
        from faster_whisper import WhisperModel

        _model = WhisperModel(name, device="cpu", compute_type="int8")
        _model_name = name
    return _model


def transcribe(
    audio: "np.ndarray",
    language: str = "ko",
    model_name: str = "small",
    beam_size: int = 5,
    initial_prompt: Optional[str] = None,
) -> str:
    """numpy float32 오디오를 텍스트로 전사. 빈 오디오는 빈 문자열 반환.

    initial_prompt: Whisper에 어휘 hint. 짧은 wake word 인식률 크게 향상.
    """
    if audio.size == 0:
        return ""
    model = _get_model(model_name)
    segments, _info = model.transcribe(
        audio,
        language=language,
        beam_size=beam_size,
        vad_filter=False,
        initial_prompt=initial_prompt,
    )
    return "".join(seg.text for seg in segments).strip()
