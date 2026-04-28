from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Tuple

from jarvis.voice.recorder import capture_phrase
from jarvis.voice.transcribe import transcribe

_DEBUG = os.environ.get("JARVIS_WAKE_DEBUG", "0") == "1"
# JARVIS_HOVER_GATE=0 으로 끄면 항상 마이크 listening (이전 동작)
# 기본은 hover gate ON — 카메라 영역 마우스 호버 시에만 마이크 사용
_HOVER_GATE = os.environ.get("JARVIS_HOVER_GATE", "1") == "1"
_HOVER_FILE = Path.home() / "Library" / "Caches" / "jarvis-hover.json"


def _is_hover_active() -> bool:
    """JarvisHUD.app이 카메라 hover 신호를 file에 쓴 경우만 True."""
    try:
        if not _HOVER_FILE.exists():
            return False
        data = json.loads(_HOVER_FILE.read_text())
        return bool(data.get("hover", False)) and (time.time() - data.get("ts", 0) < 5)
    except Exception:
        return False

# 한국어 small/base 모델은 "자비스"를 다양하게 전사 — 변종 폭넓게 허용
DEFAULT_WAKE_WORDS: Tuple[str, ...] = (
    # Korean
    "자비스",
    "쟈비스",
    "재비스",
    "자뷔스",
    "헤이 자비스",
    # English
    "jarvis",
    "javis",
    "jervis",
    "hey jarvis",
    "hi jarvis",
)
# 'jarvis' substring 매칭이라 "Hey Jarvis"는 자동 인식됨

_WAKE_PROMPT = "자비스. 헤이 자비스. Hey Jarvis. Hi Jarvis."


def detect_wake_word(
    audio: Any,
    wake_words: Sequence[str] = DEFAULT_WAKE_WORDS,
    detection_model: str = "base",
    language: Optional[str] = None,  # None/auto → ko/en 둘 다 매칭
) -> Tuple[bool, str]:
    """오디오 → 전사 (약한 initial_prompt) → 매칭. (matched, text).

    language=None: Whisper auto-detect (한국어/영어 둘 다 가능).
    너무 짧은(≤2자) 또는 빈 전사는 false positive 우려로 reject.
    """
    text = transcribe(
        audio,
        language=language,  # None → auto-detect
        model_name=detection_model,
        initial_prompt=_WAKE_PROMPT,
    )
    stripped = text.strip().rstrip(".!?,·")
    if len(stripped) < 3:
        return False, text
    lower = text.lower()
    for w in wake_words:
        if w.lower() in lower:
            return True, text
    return False, text


def listen_for_wake(
    wake_words: Sequence[str] = DEFAULT_WAKE_WORDS,
    detection_model: str = "base",
    language: str = "ko",
    chunk_silence_duration: float = 0.5,
    chunk_max_duration: float = 2.0,
    silence_threshold: float = 0.015,
    on_chunk_rms: Any = None,
) -> str:
    """발화 무한 대기 → 짧은 캡처 → 전사 → wake word 검사. 매칭될 때까지 반복.

    튜닝 가이드:
    - silence_threshold 0.015 (capture_phrase 기본 0.012보다 약간 높음) — 사용자 환경 마이크 RMS ~0.0066 기준 발화는 0.02+, 배경 영상 음성은 0.01~0.02 범위라 0.015가 sweet spot
    - chunk_max_duration 2.0 (이전 4.0) — wake word는 짧음. 긴 캡처는 배경 음성에 묻힘

    Returns:
        wake word를 포함한 전사 텍스트. 호출자가 strip_wake로 명령 부분 추출 가능.
    """
    while True:
        # Hover gate — JarvisHUD.app이 카메라 hover 신호 안 보내면 마이크 안 씀
        if _HOVER_GATE and not _is_hover_active():
            time.sleep(0.4)
            continue
        audio = capture_phrase(
            silence_duration=chunk_silence_duration,
            max_speech_duration=chunk_max_duration,
            silence_threshold=silence_threshold,
            on_chunk_rms=on_chunk_rms,
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


def strip_wake(text: str, wake_words: Sequence[str] = DEFAULT_WAKE_WORDS) -> str:
    """전사 텍스트에서 **모든** wake word 등장을 제거 → 순수 명령만 반환.

    반복 호출 ("자비스 자비스 자비스") 시에도 빈 문자열 반환 → 단독 호출 분기 진입.

    "자비스 시계 알려줘" → "시계 알려줘"
    "자비스. 자비스. 자비스." → ""
    "자비스 메모 자비스 적어줘" → "메모 적어줘"
    "hello world" (wake word 없음) → "hello world"
    """
    pattern = "|".join(re.escape(w) for w in wake_words)
    if not pattern:
        return text.strip()
    cleaned = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,.!?·")
