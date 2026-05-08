"""Window/App management — list, focus, position, mission control."""
from __future__ import annotations

import subprocess

from jarvis.platform import mac_only
from jarvis.tools.registry import REGISTRY, Tool


def _osa(script: str, timeout: int = 8) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
        return r.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"
    except Exception as e:
        return f"ERROR: {e}"


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


@mac_only
def _window_list() -> str:
    """모든 visible app의 window 제목 + 위치/크기."""
    s = '''
tell application "System Events"
    set out to ""
    repeat with p in (every process whose visible is true)
        set pname to name of p
        try
            repeat with w in windows of p
                set out to out & pname & " | " & (name of w) & " | " & ((position of w) as string) & " | " & ((size of w) as string) & linefeed
            end repeat
        end try
    end repeat
    return out
end tell
'''
    return _osa(s, timeout=10) or "(none)"


@mac_only
def _window_focus(app_name: str) -> str:
    """앱 활성화 + 가장 앞 window를 frontmost로."""
    s = f'tell application "{_esc(app_name)}" to activate'
    out = _osa(s)
    return out if out.startswith("ERROR") else f"OK: focused {app_name}"


@mac_only
def _window_position(app_name: str, x: int, y: int, w: int = 0, h: int = 0) -> str:
    """앞 window 이동/크기조정. w=0이면 크기 유지."""
    if w > 0 and h > 0:
        size_line = f"set size of front window to {{{w}, {h}}}"
    else:
        size_line = ""
    s = f'''
tell application "System Events" to tell process "{_esc(app_name)}"
    set position of front window to {{{x}, {y}}}
    {size_line}
end tell
'''
    out = _osa(s)
    return out if out.startswith("ERROR") else f"OK: moved {app_name} → ({x},{y}){' '+str(w)+'x'+str(h) if w else ''}"


@mac_only
def _window_minimize(app_name: str) -> str:
    s = f'''
tell application "System Events" to tell process "{_esc(app_name)}"
    set value of attribute "AXMinimized" of front window to true
end tell
'''
    out = _osa(s)
    return out if out.startswith("ERROR") else f"OK: minimized {app_name}"


@mac_only
def _mission_control() -> str:
    try:
        subprocess.run(
            ["open", "-a", "Mission Control"],
            capture_output=True, timeout=5, check=True,
        )
        return "OK: Mission Control"
    except Exception as e:
        return f"ERROR: {e}"


@mac_only
def _show_desktop() -> str:
    """F11 / showDesktop"""
    s = '''
tell application "System Events"
    key code 103 using {fn down}
end tell
'''
    return _osa(s) or "OK"


@mac_only
def _hide_app(app_name: str) -> str:
    s = f'tell application "System Events" to set visible of process "{_esc(app_name)}" to false'
    out = _osa(s)
    return out if out.startswith("ERROR") else f"OK: hidden {app_name}"


REGISTRY.register(Tool(
    name="window_list",
    description="모든 보이는 앱의 window 제목 + 위치/크기.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_window_list,
))
REGISTRY.register(Tool(
    name="window_focus",
    description="특정 앱을 frontmost로 활성화.",
    input_schema={
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"],
    },
    handler=_window_focus,
))
REGISTRY.register(Tool(
    name="window_position",
    description="앱 앞 window를 (x,y)로 이동, 옵션: w/h 크기 지정.",
    input_schema={
        "type": "object",
        "properties": {
            "app_name": {"type": "string"},
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "w": {"type": "integer", "description": "옵션 width"},
            "h": {"type": "integer", "description": "옵션 height"},
        },
        "required": ["app_name", "x", "y"],
    },
    handler=_window_position,
))
REGISTRY.register(Tool(
    name="window_minimize",
    description="앱 앞 window 최소화.",
    input_schema={
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"],
    },
    handler=_window_minimize,
))
REGISTRY.register(Tool(
    name="mission_control",
    description="Mission Control 열기.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_mission_control,
))
REGISTRY.register(Tool(
    name="show_desktop",
    description="모든 창 숨기기 + 데스크톱 보이기 (F11).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_show_desktop,
))
REGISTRY.register(Tool(
    name="hide_app",
    description="앱을 hide (Cmd+H 동등).",
    input_schema={
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"],
    },
    handler=_hide_app,
))
