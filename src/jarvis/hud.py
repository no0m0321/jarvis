"""JARVIS HUD state writer + sound effects + voice level streaming."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

_STATE_PATH = Path.home() / "Library" / "Caches" / "jarvis-hud.json"
_VOICE_LEVEL_PATH = Path.home() / "Library" / "Caches" / "jarvis-voice.json"

# state → sci-fi sound (afplay async, fire-and-forget)
_SOUND_MAP = {
    "listening": "/System/Library/Sounds/Tink.aiff",
    "analyzing": "/System/Library/Sounds/Glass.aiff",
    "speaking": None,
    "idle": None,
}
_SOUND_ENABLED = os.environ.get("JARVIS_HUD_SOUNDS", "1") != "0"
_last_state: Optional[str] = None


def _play_sound(state: str) -> None:
    if not _SOUND_ENABLED:
        return
    sound = _SOUND_MAP.get(state)
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


_voice_history: "list[float]" = []  # 최근 RMS 32개 (waveform strip)


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

    def __enter__(self) -> "_StateScope":
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
