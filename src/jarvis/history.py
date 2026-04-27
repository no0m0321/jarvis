"""대화 히스토리 영구 저장 — JSONL append-only."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict

_HISTORY_PATH = Path(os.environ.get(
    "JARVIS_HISTORY_PATH",
    str(Path.home() / ".jarvis" / "history.jsonl"),
))


def _ensure_dir() -> None:
    _HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def append(role: str, content: str, metadata: Dict[str, Any] = None) -> None:
    """한 turn 추가. role: user|assistant. content: 평문 텍스트."""
    try:
        _ensure_dir()
        entry = {
            "ts": time.time(),
            "role": role,
            "content": content[:8000],
        }
        if metadata:
            entry["meta"] = metadata
        with _HISTORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # best-effort


def tail(n: int = 20) -> list[Dict[str, Any]]:
    """마지막 n개 turn."""
    if not _HISTORY_PATH.exists():
        return []
    lines = _HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-n:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def path() -> Path:
    return _HISTORY_PATH
