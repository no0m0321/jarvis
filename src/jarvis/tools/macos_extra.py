"""macOS 추가 도구 — calendar, screen capture, clipboard."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _escape_as(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ── Calendar ──────────────────────────────────────────────────────────────
def _calendar_add(title: str, start_iso: str, duration_minutes: int = 60, notes: str = "") -> str:
    """기본 캘린더에 이벤트 추가. start_iso 형식: 2026-04-29 14:00."""
    script = f'''
on parseDate(s)
    set y to (text 1 thru 4 of s) as integer
    set mo to (text 6 thru 7 of s) as integer
    set d to (text 9 thru 10 of s) as integer
    set h to (text 12 thru 13 of s) as integer
    set mi to (text 15 thru 16 of s) as integer
    set theDate to current date
    set year of theDate to y
    set month of theDate to mo
    set day of theDate to d
    set hours of theDate to h
    set minutes of theDate to mi
    set seconds of theDate to 0
    return theDate
end parseDate

set startDate to parseDate("{_escape_as(start_iso)}")
set endDate to startDate + ({duration_minutes} * minutes)

tell application "Calendar"
    tell calendar 1
        make new event with properties {{summary:"{_escape_as(title)}", start date:startDate, end date:endDate, description:"{_escape_as(notes)}"}}
    end tell
end tell
return "OK"
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return f"OK: '{title}' @ {start_iso} ({duration_minutes}min)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"


def _calendar_list_today() -> str:
    """오늘 일정 list."""
    script = '''
set today to current date
set hours of today to 0
set minutes of today to 0
set seconds of today to 0
set tomorrow to today + 1 * days

tell application "Calendar"
    set output to ""
    repeat with c in calendars
        set evts to (every event of c whose start date >= today and start date < tomorrow)
        repeat with e in evts
            set output to output & (summary of e) & " | " & (start date of e as string) & linefeed
        end repeat
    end repeat
end tell
return output
'''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15, check=True,
        )
        return result.stdout.strip() or "(오늘 일정 없음)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"


REGISTRY.register(Tool(
    name="calendar_add",
    description="macOS Calendar.app 기본 캘린더에 일정 추가.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "일정 제목"},
            "start_iso": {"type": "string", "description": "시작 시각, '2026-04-29 14:00' 형식"},
            "duration_minutes": {"type": "integer", "description": "지속 시간 (분), 기본 60"},
            "notes": {"type": "string", "description": "메모 (옵션)"},
        },
        "required": ["title", "start_iso"],
    },
    handler=_calendar_add,
))

REGISTRY.register(Tool(
    name="calendar_list_today",
    description="오늘 등록된 모든 캘린더 일정 list.",
    input_schema={
        "type": "object",
        "properties": {},
        "required": [],
    },
    handler=_calendar_list_today,
))


# ── Screen Capture ─────────────────────────────────────────────────────────
def _screen_capture(path: str = "", region: str = "") -> str:
    """macOS screencapture. path 빈값이면 임시 파일. region은 'X,Y,W,H' 또는 빈값(전체)."""
    if not path:
        path = str(Path(tempfile.gettempdir()) / "jarvis-screen.png")
    cmd = ["screencapture", "-x"]  # -x: 사운드 끔
    if region:
        cmd += ["-R", region]
    cmd += [path]
    try:
        subprocess.run(cmd, timeout=10, check=True)
        size = Path(path).stat().st_size
        return f"OK: saved to {path} ({size} bytes)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="screen_capture",
    description="macOS 화면 캡처. 전체 화면 또는 region (예: '0,0,1920,1080').",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "저장 경로, 비우면 임시 파일"},
            "region": {"type": "string", "description": "X,Y,W,H 형식 region (옵션)"},
        },
        "required": [],
    },
    handler=_screen_capture,
))


# ── Clipboard ──────────────────────────────────────────────────────────────
def _clipboard_read() -> str:
    """클립보드 텍스트 읽기."""
    try:
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5, check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


def _clipboard_write(text: str) -> str:
    """클립보드에 텍스트 쓰기."""
    try:
        subprocess.run(
            ["pbcopy"], input=text, text=True, timeout=5, check=True,
        )
        return f"OK: copied {len(text)} chars"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="clipboard_read",
    description="macOS 클립보드의 현재 텍스트 읽기.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_clipboard_read,
))

REGISTRY.register(Tool(
    name="clipboard_write",
    description="텍스트를 macOS 클립보드에 복사.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
        },
        "required": ["text"],
    },
    handler=_clipboard_write,
))
