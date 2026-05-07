"""JARVIS HUD state writer + sound effects + voice level streaming.

Cross-platform:
- macOS: ~/Library/Caches/ (Übersicht widget이 읽는 경로 호환)
- Windows/Linux: ~/.jarvis/cache/
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from jarvis.platform import IS_MACOS, IS_WINDOWS

# 캐시 디렉토리 — macOS는 Übersicht/JarvisHUD.app 호환을 위해 Library/Caches
if IS_MACOS:
    _CACHE_DIR = Path.home() / "Library" / "Caches"
else:
    _CACHE_DIR = Path.home() / ".jarvis" / "cache"

_STATE_PATH = _CACHE_DIR / "jarvis-hud.json"
_VOICE_LEVEL_PATH = _CACHE_DIR / "jarvis-voice.json"

# state → sci-fi sound (fire-and-forget)
# macOS: aiff via afplay
# Windows: winsound 시스템 사운드
# Linux: paplay 또는 비활성
_SOUND_MAP_MACOS = {
    "listening": "/System/Library/Sounds/Tink.aiff",
    "analyzing": "/System/Library/Sounds/Glass.aiff",
}
_SOUND_MAP_WINDOWS = {
    # winsound.MessageBeep type 또는 .wav 경로 — 여기는 winmm system events 사용
    "listening": "SystemAsterisk",
    "analyzing": "SystemNotification",
}
_SOUND_ENABLED = os.environ.get("JARVIS_HUD_SOUNDS", "1") != "0"
_last_state: Optional[str] = None


def _play_sound(state: str) -> None:
    """state 진입 시 사운드. 실패해도 silently skip."""
    if not _SOUND_ENABLED:
        return

    if IS_MACOS:
        sound = _SOUND_MAP_MACOS.get(state)
        if not sound:
            return
        try:
            subprocess.Popen(
                ["afplay", "-v", "0.4", sound],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
        return

    if IS_WINDOWS:
        # winsound는 표준 라이브러리 (Windows 한정) — 비동기 재생
        sound_name = _SOUND_MAP_WINDOWS.get(state)
        if not sound_name:
            return
        try:
            import winsound  # type: ignore
            # MB_OK=0, MB_ICONHAND=16, MB_ICONQUESTION=32, MB_ICONEXCLAMATION=48, MB_ICONASTERISK=64
            beep_type = {
                "SystemAsterisk": winsound.MB_ICONASTERISK,
                "SystemNotification": winsound.MB_ICONEXCLAMATION,
            }.get(sound_name, winsound.MB_OK)
            winsound.MessageBeep(beep_type)
        except Exception:
            pass
        return

    # Linux: paplay 시도 (대부분 미설치, 그냥 skip)
    return


def set_state(state: str, message: str = "") -> None:
    """HUD 상태 쓰기. state 변경 시 sci-fi sound 재생."""
    global _last_state
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(
            json.dumps({"state": state, "message": message[:64], "ts": time.time()})
        )
    except Exception:
        pass
    if state != _last_state:
        _play_sound(state)
        _last_state = state


_voice_history: list[float] = []  # 최근 RMS 32개 (waveform strip)


def set_voice_level(rms: float, peak: float = 0.0) -> None:
    """마이크 RMS를 voice file에 dump + 32-sample history."""
    global _voice_history
    _voice_history.append(rms)
    if len(_voice_history) > 32:
        _voice_history = _voice_history[-32:]
    try:
        _VOICE_LEVEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        _VOICE_LEVEL_PATH.write_text(json.dumps({
            "rms": rms,
            "peak": peak,
            "history": _voice_history,
            "ts": time.time(),
        }))
    except Exception:
        pass


def reset() -> None:
    set_state("idle")


class _StateScope:
    """`with hud.analyzing("..."):` 패턴. exit 시 자동으로 idle 복귀."""

    def __init__(self, state: str, message: str = "") -> None:
        self._state = state
        self._message = message

    def __enter__(self) -> _StateScope:
        set_state(self._state, self._message)
        return self

    def __exit__(self, *exc: object) -> None:
        set_state("idle")


def analyzing(message: str = "") -> _StateScope:
    return _StateScope("analyzing", message)


def listening(message: str = "") -> _StateScope:
    return _StateScope("listening", message)


def speaking(message: str = "") -> _StateScope:
    return _StateScope("speaking", message)
