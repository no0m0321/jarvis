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


def _say(text: str, voice: str = "Yuna") -> str:
    try:
        subprocess.run(["say", "-v", voice, text], timeout=120, check=True)
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
    description="macOS TTS로 텍스트 음성 출력. 한국어 음성 'Yuna' 기본.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "voice": {"type": "string", "description": "voice 이름, 기본 Yuna"},
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
