"""JARVIS HUD state writer — best-effort Übersicht widget channel.

자비스의 현재 상태(idle / listening / analyzing / speaking)를
~/Library/Caches/jarvis-hud.json 에 기록. HUD widget이 1초 polling.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

_STATE_PATH = Path.home() / "Library" / "Caches" / "jarvis-hud.json"


def set_state(state: str, message: str = "") -> None:
    """HUD 상태 쓰기. state: idle|listening|analyzing|speaking. 실패해도 무해."""
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(
            json.dumps({"state": state, "message": message[:64], "ts": time.time()})
        )
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
