"""AppleScript general runner + macOS Shortcuts integration."""
from __future__ import annotations

import subprocess

from jarvis.tools.registry import REGISTRY, Tool


def _apple_script(script: str, timeout: int = 30) -> str:
    """임의 AppleScript 실행. 결과 stdout 반환."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return f"ERROR: {result.stderr.strip() or 'failed'}"
        return result.stdout.strip() or "(empty)"
    except subprocess.TimeoutExpired:
        return f"TIMEOUT (>{timeout}s)"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="apple_script",
    description="임의 AppleScript 실행. 광범위한 macOS 자동화 (앱 제어/시스템/UI 등).",
    input_schema={
        "type": "object",
        "properties": {
            "script": {"type": "string", "description": "AppleScript 코드"},
            "timeout": {"type": "integer", "description": "초, 기본 30"},
        },
        "required": ["script"],
    },
    handler=_apple_script,
))


def _shortcuts_run(name: str, input_text: str = "") -> str:
    """macOS Shortcuts.app 단축어 실행 (Sonoma+ shortcuts CLI)."""
    cmd = ["shortcuts", "run", name]
    try:
        if input_text:
            result = subprocess.run(
                cmd, input=input_text, capture_output=True,
                text=True, timeout=60, check=True,
            )
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, check=True,
            )
        return result.stdout.strip() or f"OK: ran '{name}'"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"
    except FileNotFoundError:
        return "ERROR: 'shortcuts' CLI 미설치 (macOS Monterey+ 필요)"


def _shortcuts_list() -> str:
    """등록된 shortcuts 목록."""
    try:
        result = subprocess.run(
            ["shortcuts", "list"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        lines = result.stdout.strip().splitlines()[:50]
        return "\n".join(lines) if lines else "(no shortcuts)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="shortcuts_run",
    description="macOS Shortcuts.app 단축어 실행 (이름으로 호출).",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "단축어 이름"},
            "input_text": {"type": "string", "description": "stdin으로 전달할 입력"},
        },
        "required": ["name"],
    },
    handler=_shortcuts_run,
))

REGISTRY.register(Tool(
    name="shortcuts_list",
    description="등록된 macOS Shortcuts 목록.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_shortcuts_list,
))


def _frontmost_app() -> str:
    """현재 frontmost (활성) 앱 이름."""
    return _apple_script(
        'tell application "System Events" to name of first process whose frontmost is true'
    )


REGISTRY.register(Tool(
    name="frontmost_app",
    description="현재 frontmost 앱 이름.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_frontmost_app,
))


def _running_apps() -> str:
    """실행 중인 앱 list (visible)."""
    return _apple_script(
        'tell application "System Events" to name of every process whose visible is true'
    )


REGISTRY.register(Tool(
    name="running_apps",
    description="현재 visible (도크에 보이는) 실행 중 앱 목록.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_running_apps,
))


def _quit_app(name: str) -> str:
    """앱 종료."""
    safe = name.replace('"', '\\"')
    return _apple_script(f'tell application "{safe}" to quit')


REGISTRY.register(Tool(
    name="quit_app",
    description="macOS 앱 종료.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
    handler=_quit_app,
))
