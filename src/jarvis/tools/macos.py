from __future__ import annotations

import subprocess

from jarvis.tools.registry import REGISTRY, Tool


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _notify(title: str, message: str, subtitle: str = "") -> str:
    script = f'display notification "{_escape(message)}" with title "{_escape(title)}"'
    if subtitle:
        script += f' subtitle "{_escape(subtitle)}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5, check=True,
        )
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode(errors="replace") if e.stderr else str(e)
        return f"ERROR: {err.strip()}"
    return "OK"


import os as _os


def _say(text: str, voice: str = "", rate: int = 180) -> str:
    """macOS TTS. JARVIS_VOICE 환경변수로 default override 가능.

    한국어 native voice (자연스러운 발음):
    - Yuna (여성, 기본) — 가장 자연스러운 한국어 native
    - Sandy (여성) / Shelley (여성) — Premium 다운로드 시 신경망 voice
    - Eddy (중성, 톤 살짝 낮음)
    - Reed (남성) — 한국어 발음 어색
    """
    voice = voice or _os.environ.get("JARVIS_VOICE", "Yuna")
    try:
        subprocess.run(
            ["say", "-v", voice, "-r", str(rate), text],
            timeout=180, check=True,
        )
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"
    return "OK"


def _open_url(url: str) -> str:
    try:
        subprocess.run(["open", url], timeout=5, check=True)
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"
    return f"OK: opened {url}"


REGISTRY.register(Tool(
    name="notify",
    description="macOS 알림 센터에 알림 표시.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"},
            "subtitle": {"type": "string"},
        },
        "required": ["title", "message"],
    },
    handler=_notify,
))

REGISTRY.register(Tool(
    name="say",
    description="macOS TTS로 텍스트 음성 출력. 한국어 voice (Reed/Yuna/Eddy/Reed/Sandy 등). 기본 Reed.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "voice": {"type": "string", "description": "voice 이름, 기본 Reed"},
            "rate": {"type": "integer", "description": "WPM, 기본 175"},
        },
        "required": ["text"],
    },
    handler=_say,
))

REGISTRY.register(Tool(
    name="open_url",
    description="기본 브라우저/앱으로 URL 또는 파일 경로 열기.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL 또는 경로"},
        },
        "required": ["url"],
    },
    handler=_open_url,
))
