"""추가 macOS 도구 — Mail compose, Spotlight, App activate, sound effect."""
from __future__ import annotations

import shlex
import subprocess

from jarvis.tools.registry import REGISTRY, Tool


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _mail_compose(to: str, subject: str = "", body: str = "") -> str:
    """Mail.app 새 메시지 창을 띄움 (발송은 사용자 직접). 안전을 위해 자동 발송 X."""
    script = f'''
tell application "Mail"
    set newMessage to make new outgoing message with properties {{subject:"{_esc(subject)}", content:"{_esc(body)}", visible:true}}
    tell newMessage
        make new to recipient with properties {{address:"{_esc(to)}"}}
    end tell
    activate
end tell
return "OK"
'''
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return f"OK: drafted to {to} (창 열림, 발송은 직접 ⌘+⇧+D)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"


def _spotlight_search(query: str, max_results: int = 20) -> str:
    """macOS Spotlight (mdfind) 검색. 파일/문서/앱 위치 list."""
    try:
        result = subprocess.run(
            ["mdfind", query],
            capture_output=True, text=True, timeout=15, check=True,
        )
        lines = [l for l in result.stdout.splitlines() if l.strip()][:max_results]
        if not lines:
            return f"(no matches for '{query}')"
        truncated = " (truncated)" if len(result.stdout.splitlines()) > max_results else ""
        return "\n".join(lines) + truncated
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


def _activate_app(name: str) -> str:
    """macOS 앱 활성화 (frontmost). 미실행이면 시작."""
    try:
        subprocess.run(["open", "-a", name], timeout=8, check=True)
        return f"OK: activated '{name}'"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


def _play_sound(sound: str = "Glass") -> str:
    """macOS 시스템 사운드 재생 (Tink/Glass/Hero/Pop/Submarine 등)."""
    path = f"/System/Library/Sounds/{sound}.aiff"
    try:
        subprocess.Popen(
            ["afplay", "-v", "0.6", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"OK: playing {sound}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="mail_compose",
    description="Mail.app 새 메시지 창을 띄움. 받는 사람/제목/본문 설정. 발송은 사용자 직접.",
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "받는 사람 이메일"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["to"],
    },
    handler=_mail_compose,
))

REGISTRY.register(Tool(
    name="spotlight_search",
    description="macOS Spotlight 인덱스 검색 (mdfind). 파일명/콘텐츠 매칭 결과 반환.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "검색어 (자연어 또는 mdfind 구문)"},
            "max_results": {"type": "integer", "description": "최대 결과, 기본 20"},
        },
        "required": ["query"],
    },
    handler=_spotlight_search,
))

REGISTRY.register(Tool(
    name="activate_app",
    description="macOS 앱을 frontmost로 활성화. 미실행이면 시작 (예: 'Safari', 'Music', 'Calendar').",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "앱 이름"},
        },
        "required": ["name"],
    },
    handler=_activate_app,
))

REGISTRY.register(Tool(
    name="play_sound",
    description="macOS 시스템 사운드 재생 (Tink/Glass/Hero/Pop/Submarine 등).",
    input_schema={
        "type": "object",
        "properties": {
            "sound": {"type": "string", "description": "사운드 이름, 기본 Glass"},
        },
        "required": [],
    },
    handler=_play_sound,
))
