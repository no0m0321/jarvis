"""추가 macOS 도구 — Music control, Volume, Brightness, Reminders, Note search, etc."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


# ── Music.app control ─────────────────────────────────────────────────────
def _music_control(action: str, query: str = "") -> str:
    """Music.app 재생 제어. action: play|pause|next|previous|search."""
    actions = {
        "play": 'tell application "Music" to play',
        "pause": 'tell application "Music" to pause',
        "next": 'tell application "Music" to next track',
        "previous": 'tell application "Music" to previous track',
        "stop": 'tell application "Music" to stop',
    }
    if action == "search" and query:
        script = f'''
tell application "Music"
    set results to (every track of library playlist 1 whose name contains "{_esc(query)}")
    if (count of results) > 0 then
        set firstTrack to item 1 of results
        play firstTrack
        return "PLAYING: " & (name of firstTrack) & " - " & (artist of firstTrack)
    else
        return "NOT_FOUND"
    end if
end tell
'''
    elif action in actions:
        script = actions[action]
    elif action == "current":
        script = '''
tell application "Music"
    if player state is playing or player state is paused then
        set t to current track
        return (name of t) & " - " & (artist of t) & " [" & (player state as string) & "]"
    else
        return "Music app idle"
    end if
end tell
'''
    else:
        return f"ERROR: invalid action '{action}'. valid: play|pause|next|previous|stop|search|current"
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=8, check=True,
        )
        return result.stdout.strip() or f"OK: {action}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"


REGISTRY.register(Tool(
    name="music_control",
    description="Music.app 재생 제어. play/pause/next/previous/stop/current/search.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "description": "play|pause|next|previous|stop|current|search"},
            "query": {"type": "string", "description": "search 액션 시 곡/아티스트명"},
        },
        "required": ["action"],
    },
    handler=_music_control,
))


# ── System Volume ─────────────────────────────────────────────────────────
def _set_volume(level: int) -> str:
    """시스템 출력 볼륨. level: 0~100."""
    level = max(0, min(100, int(level)))
    try:
        subprocess.run(
            ["osascript", "-e", f"set volume output volume {level}"],
            capture_output=True, timeout=5, check=True,
        )
        return f"OK: volume = {level}%"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e}"


def _get_volume() -> str:
    try:
        result = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return f"{result.stdout.strip()}%"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="set_volume",
    description="시스템 출력 볼륨 설정 (0-100).",
    input_schema={
        "type": "object",
        "properties": {"level": {"type": "integer", "description": "0~100"}},
        "required": ["level"],
    },
    handler=_set_volume,
))

REGISTRY.register(Tool(
    name="get_volume",
    description="현재 시스템 출력 볼륨 조회.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_get_volume,
))


# ── Display Brightness (M1+ via brightness CLI; fallback osascript) ───────
def _set_brightness(level: float) -> str:
    """디스플레이 밝기 설정. level: 0.0~1.0."""
    level = max(0.0, min(1.0, float(level)))
    if subprocess.run(["which", "brightness"], capture_output=True).returncode == 0:
        try:
            subprocess.run(["brightness", str(level)], capture_output=True, timeout=5, check=True)
            return f"OK: brightness = {level:.2f}"
        except Exception as e:
            return f"ERROR: {e}"
    return ("WARN: 'brightness' CLI 미설치. `brew install brightness` 필요. "
            "또는 시스템 환경설정 > 디스플레이에서 수동 조정.")


REGISTRY.register(Tool(
    name="set_brightness",
    description="디스플레이 밝기 설정 (0.0~1.0). 'brightness' CLI 필요.",
    input_schema={
        "type": "object",
        "properties": {"level": {"type": "number", "description": "0.0~1.0"}},
        "required": ["level"],
    },
    handler=_set_brightness,
))


# ── Reminders.app ────────────────────────────────────────────────────────
def _reminder_add(title: str, due_iso: str = "", body: str = "") -> str:
    """Reminders.app에 미리알림 추가."""
    if due_iso:
        date_setter = f'''
set y to (text 1 thru 4 of "{_esc(due_iso)}") as integer
set mo to (text 6 thru 7 of "{_esc(due_iso)}") as integer
set d to (text 9 thru 10 of "{_esc(due_iso)}") as integer
set hh to (text 12 thru 13 of "{_esc(due_iso)}") as integer
set mi to (text 15 thru 16 of "{_esc(due_iso)}") as integer
set theDate to current date
set year of theDate to y
set month of theDate to mo
set day of theDate to d
set hours of theDate to hh
set minutes of theDate to mi
set seconds of theDate to 0
'''
        props = '{name:"' + _esc(title) + '", body:"' + _esc(body) + '", remind me date:theDate}'
    else:
        date_setter = ""
        props = '{name:"' + _esc(title) + '", body:"' + _esc(body) + '"}'

    script = f'''
{date_setter}
tell application "Reminders"
    tell list 1
        make new reminder with properties {props}
    end tell
end tell
return "OK"
'''
    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return f"OK: reminder '{title}' added{' @ ' + due_iso if due_iso else ''}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or '').strip()}"


REGISTRY.register(Tool(
    name="reminder_add",
    description="Reminders.app 첫 번째 list에 미리알림 추가.",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "due_iso": {"type": "string", "description": "due 시각 '2026-04-29 14:00' (옵션)"},
            "body": {"type": "string", "description": "메모 (옵션)"},
        },
        "required": ["title"],
    },
    handler=_reminder_add,
))


# ── Note search (자비스 메모) ─────────────────────────────────────────────
def _note_search(query: str, max_results: int = 10) -> str:
    """~/.jarvis/notes.md에서 query 매칭 라인 검색."""
    path = Path.home() / ".jarvis" / "notes.md"
    if not path.exists():
        return "(no notes file)"
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR: {e}"
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    matches = [line for line in text.splitlines() if pattern.search(line)][:max_results]
    if not matches:
        return f"(no matches for '{query}' in {path})"
    return "\n".join(matches)


REGISTRY.register(Tool(
    name="note_search",
    description="~/.jarvis/notes.md 메모 검색 (대소문자 무시).",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "description": "기본 10"},
        },
        "required": ["query"],
    },
    handler=_note_search,
))


def _note_list(max_results: int = 20) -> str:
    """최근 메모 list (최근순)."""
    path = Path.home() / ".jarvis" / "notes.md"
    if not path.exists():
        return "(no notes file)"
    lines = path.read_text(encoding="utf-8").splitlines()
    recent = [l for l in lines if l.strip()][-max_results:]
    return "\n".join(recent) if recent else "(empty)"


REGISTRY.register(Tool(
    name="note_list",
    description="최근 자비스 메모 list.",
    input_schema={
        "type": "object",
        "properties": {"max_results": {"type": "integer"}},
        "required": [],
    },
    handler=_note_list,
))


# ── Battery info ──────────────────────────────────────────────────────────
def _battery_info() -> str:
    """배터리 잔량 + 충전 상태 (pmset)."""
    try:
        result = subprocess.run(
            ["pmset", "-g", "batt"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        m = re.search(r"(\d+)%;\s*(\w+);\s*(.+?)(?:\s+present|;)", result.stdout)
        if m:
            pct, status, time_left = m.groups()
            return f"battery: {pct}% ({status}, {time_left.strip()})"
        return result.stdout.strip()[:200]
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="battery_info",
    description="배터리 잔량 + 충전 상태 + 남은 시간 (pmset 기반).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_battery_info,
))


# ── Wifi info ─────────────────────────────────────────────────────────────
def _wifi_info() -> str:
    """현재 Wifi 정보 (ssid, signal)."""
    try:
        result = subprocess.run(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            capture_output=True, text=True, timeout=5,
        )
        # 비공식 도구 — fail시 networksetup 폴백
        if result.returncode != 0 or not result.stdout.strip():
            ns = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True, text=True, timeout=5,
            )
            return ns.stdout.strip() or "wifi: unknown"
        keys = ("agrCtlRSSI", "SSID", "channel")
        out = []
        for k in keys:
            m = re.search(rf"\b{k}: (.+)", result.stdout)
            if m:
                out.append(f"{k}={m.group(1).strip()}")
        return ", ".join(out) or "(no wifi)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="wifi_info",
    description="현재 Wifi SSID + 시그널 + 채널.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_wifi_info,
))


# ── Bookmark add (URL → bookmarks.md) ────────────────────────────────────
def _bookmark_add(url: str, title: str = "", tags: str = "") -> str:
    """~/.jarvis/bookmarks.md 에 URL 북마크."""
    from datetime import datetime as _dt

    path = Path.home() / ".jarvis" / "bookmarks.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = _dt.now().strftime("%Y-%m-%d")
    entry = f"- [{ts}]({url})"
    if title:
        entry = f"- [{ts}] [{title}]({url})"
    if tags:
        entry += f" #{tags.replace(',', ' #')}"
    with path.open("a", encoding="utf-8") as f:
        f.write(entry + "\n")
    return f"OK: bookmarked → {path}"


REGISTRY.register(Tool(
    name="bookmark_add",
    description="URL을 ~/.jarvis/bookmarks.md 에 북마크 (제목/태그 옵션).",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "title": {"type": "string"},
            "tags": {"type": "string", "description": "쉼표 구분 태그"},
        },
        "required": ["url"],
    },
    handler=_bookmark_add,
))


# ── Process monitor ─────────────────────────────────────────────────────
def _top_processes(n: int = 10) -> str:
    """CPU 사용률 상위 N개 프로세스."""
    try:
        result = subprocess.run(
            ["ps", "-arcwwwxo", "command %cpu %mem"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        lines = result.stdout.splitlines()[:n + 1]
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="top_processes",
    description="CPU 사용률 상위 N개 프로세스 (기본 10).",
    input_schema={
        "type": "object",
        "properties": {"n": {"type": "integer", "description": "기본 10"}},
        "required": [],
    },
    handler=_top_processes,
))


# ── Sleep / Lock screen / Eject ──────────────────────────────────────────
def _system_action(action: str) -> str:
    """system: sleep|lock|logout."""
    actions = {
        "sleep": ["pmset", "sleepnow"],
        "lock": ["pmset", "displaysleepnow"],
        "screensaver": ["open", "/System/Library/CoreServices/ScreenSaverEngine.app"],
    }
    if action not in actions:
        return f"ERROR: invalid action. valid: {list(actions)}"
    try:
        subprocess.run(actions[action], capture_output=True, timeout=5, check=True)
        return f"OK: {action}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="system_action",
    description="시스템 동작: sleep|lock|screensaver.",
    input_schema={
        "type": "object",
        "properties": {"action": {"type": "string"}},
        "required": ["action"],
    },
    handler=_system_action,
))
