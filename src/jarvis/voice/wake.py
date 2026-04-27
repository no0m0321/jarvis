from __future__ import annotations

import os
import re
import sys
from typing import Any, Sequence, Tuple

from jarvis.voice.recorder import capture_phrase
from jarvis.voice.transcribe import transcribe

_DEBUG = os.environ.get("JARVIS_WAKE_DEBUG", "0") == "1"

# 한국어 small/base 모델은 "자비스"를 다양하게 전사 — 변종 폭넓게 허용
DEFAULT_WAKE_WORDS: "Tuple[str, ...]" = (
    "자비스",
    "쟈비스",
    "지비스",
    "재비스",
    "자뷔스",
    "자비슨",
    "서비스",  # base Whisper가 "자비스"를 자주 "서비스"로 오인식 (ㅈ↔ㅅ)
    "jarvis",
)


_WAKE_PROMPT = "자비스. 자비스. jarvis."


def detect_wake_word(
    audio: "Any",
    wake_words: "Sequence[str]" = DEFAULT_WAKE_WORDS,
    detection_model: str = "base",
    language: str = "ko",
) -> "Tuple[bool, str]":
    """오디오 → 전사 (wake word를 initial_prompt로 hint) → 매칭. (matched, text)."""
    text = transcribe(
        audio,
        language=language,
        model_name=detection_model,
        initial_prompt=_WAKE_PROMPT,
    )
    lower = text.lower()
    for w in wake_words:
        if w.lower() in lower:
            return True, text
    return False, text


def listen_for_wake(
    wake_words: "Sequence[str]" = DEFAULT_WAKE_WORDS,
    detection_model: str = "base",
    language: str = "ko",
    chunk_silence_duration: float = 0.5,
    chunk_max_duration: float = 2.0,
    silence_threshold: float = 0.015,
) -> str:
    """발화 무한 대기 → 짧은 캡처 → 전사 → wake word 검사. 매칭될 때까지 반복.

    튜닝 가이드:
    - silence_threshold 0.015 (capture_phrase 기본 0.012보다 약간 높음) — 사용자 환경 마이크 RMS ~0.0066 기준 발화는 0.02+, 배경 영상 음성은 0.01~0.02 범위라 0.015가 sweet spot
    - chunk_max_duration 2.0 (이전 4.0) — wake word는 짧음. 긴 캡처는 배경 음성에 묻힘

    Returns:
        wake word를 포함한 전사 텍스트. 호출자가 strip_wake로 명령 부분 추출 가능.
    """
    while True:
        audio = capture_phrase(
            silence_duration=chunk_silence_duration,
            max_speech_duration=chunk_max_duration,
            silence_threshold=silence_threshold,
        )
        if audio.size == 0:
            if _DEBUG:
                print("[wake] (no speech in window)", file=sys.stderr, flush=True)
            continue
        matched, text = detect_wake_word(audio, wake_words, detection_model, language)
        if _DEBUG:
            print(
                f"[wake] heard={text!r} (samples={audio.size}) matched={matched}",
                file=sys.stderr,
                flush=True,
            )
        if matched:
            return text


def strip_wake(text: str, wake_words: "Sequence[str]" = DEFAULT_WAKE_WORDS) -> str:
    """전사 텍스트에서 첫 wake word 등장 위치 이후를 명령으로 반환.

    "자비스 시계 알려줘" → "시계 알려줘"
    "자비스" → ""
    "hello world" (wake word 없음) → "hello world"
    """
    for w in wake_words:
        m = re.search(re.escape(w), text, re.IGNORECASE)
        if m:
            return text[m.end():].lstrip(" ,.!?·")
    return text
