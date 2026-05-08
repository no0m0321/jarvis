"""생산성 도구 — 포모도로 / Focus 모드 / DND / 데일리 브리핑."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from jarvis.platform import mac_only
from jarvis.tools.registry import REGISTRY, Tool


@mac_only
def _focus_mode(mode: str = "do_not_disturb") -> str:
    """macOS Focus 모드 토글. mode: 'do_not_disturb' / 'work' / 'personal' / 'off'.

    Shortcuts.app 자동화 사용 (사용자가 'Set Focus' shortcut 등록 필요).
    """
    if mode == "off":
        script = 'tell application "System Events" to tell process "ControlCenter" to keystroke "f" using {control down, shift down}'
    else:
        # macOS Shortcut 호출
        try:
            r = subprocess.run(
                ["shortcuts", "run", f"Set Focus to {mode}"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return f"OK: Focus → {mode}"
        except FileNotFoundError:
            pass
        # fallback: focus.json toggle (단순 표시)
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to tell application process "ControlCenter" to '
             '(menu bar items of menu bar 1)'],
            capture_output=True, text=True, timeout=5,
        )
        return f"Focus 토글 시도 — Shortcuts.app에 'Set Focus to {mode}' 등록하면 직접 제어 가능"
    except Exception as e:
        return f"실패: {e}"


@mac_only
def _pomodoro_start(minutes: int = 25, label: str = "Pomodoro") -> str:
    """포모도로 타이머 시작 — 백그라운드 실행 (subprocess 분리).

    macOS notification + 종료 사운드. 실행 후 즉시 반환.
    """
    secs = max(60, minutes * 60)
    script = f'''
import time, subprocess
time.sleep({secs})
subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
subprocess.run(["osascript", "-e",
    'display notification "{label} 종료 ({minutes}분)" with title "포모도로"'], check=False)
'''
    import sys
    p = subprocess.Popen(
        [sys.executable, "-c", script],
        start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return json.dumps({"started": True, "minutes": minutes, "pid": p.pid, "label": label}, ensure_ascii=False)


@mac_only
def _pomodoro_session(work: int = 25, rest: int = 5, cycles: int = 4) -> str:
    """전체 포모도로 사이클 시작 — work/rest 반복."""
    import sys
    script = f'''
import time, subprocess
def notify(t, b):
    subprocess.run(["osascript", "-e", f'display notification "{{b}}" with title "{{t}}"'], check=False)
    subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=False)
for i in range({cycles}):
    notify("포모도로 시작", f"세션 {{i+1}}/{cycles} — {work}분 집중")
    time.sleep({work} * 60)
    notify("포모도로 휴식", f"{rest}분 쉬세요 ({{i+1}}/{cycles})")
    if i < {cycles}-1:
        time.sleep({rest} * 60)
notify("포모도로 완료", f"{cycles}사이클 완료")
'''
    p = subprocess.Popen(
        [sys.executable, "-c", script],
        start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return json.dumps({"started": True, "cycles": cycles, "work_min": work, "rest_min": rest, "pid": p.pid}, ensure_ascii=False)


@mac_only
def _daily_briefing(location: str = "Seoul") -> str:
    """오늘 브리핑: 날짜 + 날씨 + 캘린더 + 미완료 TODO + 최근 무드."""
    out: list[str] = []
    out.append(f"# 오늘 — {datetime.now().strftime('%Y-%m-%d (%A) %H:%M')}")

    # 날씨
    try:
        from jarvis.tools.info import _weather
        w = json.loads(_weather(location))
        if "current" in w:
            c = w["current"]
            out.append(f"\n## 날씨 ({w['location']})")
            out.append(f"- 현재: {c['temp']}°C, {c['condition']}, 습도 {c['humidity']}%")
            for d in w.get("forecast", [])[:3]:
                out.append(f"- {d['date']}: {d['low']}~{d['high']}°C, {d['condition']}, 강수확률 {d['rain_prob']}%")
    except Exception as e:
        out.append(f"\n## 날씨\n- 조회 실패: {e}")

    # 오늘 캘린더
    try:
        from jarvis.tools.macos_extra import _calendar_list_today
        cal = _calendar_list_today()
        out.append(f"\n## 오늘 캘린더\n{cal[:1000]}")
    except Exception as e:
        out.append(f"\n## 오늘 캘린더\n- 실패: {e}")

    # 미완료 TODO
    try:
        from jarvis.tools.personal import _todo_list
        tdl = _todo_list()
        out.append(f"\n## TODO\n{tdl[:1000]}")
    except Exception:
        pass

    # 최근 무드
    try:
        from jarvis.tools.personal import _mood_list
        out.append(f"\n## 최근 무드 (5)\n{_mood_list(5)}")
    except Exception:
        pass

    return "\n".join(out)


@mac_only
def _calendar_today_summary() -> str:
    """오늘 캘린더 요약 (osascript)."""
    script = '''
tell application "Calendar"
    set today to current date
    set hh to time of today
    set today to today - hh
    set tomorrow to today + 1 * days
    set evList to {}
    repeat with c in calendars
        try
            set evs to (every event of c whose start date >= today and start date < tomorrow)
            repeat with e in evs
                set end of evList to (start date of e as string) & " | " & (summary of e)
            end repeat
        end try
    end repeat
    return evList
end tell
'''
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout.strip() or "(오늘 일정 없음)"
    except Exception as e:
        return f"실패: {e}"


REGISTRY.register(Tool(
    name="pomodoro_start",
    description="단일 포모도로 타이머 시작 (백그라운드, 종료 시 알림+사운드). 즉시 반환.",
    input_schema={
        "type": "object",
        "properties": {
            "minutes": {"type": "integer", "default": 25},
            "label": {"type": "string", "default": "Pomodoro"},
        },
    },
    handler=_pomodoro_start,
))

REGISTRY.register(Tool(
    name="pomodoro_session",
    description="포모도로 N사이클 자동 진행 (work/rest 반복). 백그라운드 실행.",
    input_schema={
        "type": "object",
        "properties": {
            "work": {"type": "integer", "default": 25},
            "rest": {"type": "integer", "default": 5},
            "cycles": {"type": "integer", "default": 4},
        },
    },
    handler=_pomodoro_session,
))

REGISTRY.register(Tool(
    name="focus_mode",
    description=(
        "macOS Focus 모드 전환 (Shortcuts.app에 'Set Focus to <mode>' 단축어 등록 필요). "
        "off는 Focus 자체 해제."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "description": "Focus 모드",
                "enum": ["do_not_disturb", "work", "personal", "off"],
                "default": "do_not_disturb",
            },
        },
    },
    handler=_focus_mode,
))

REGISTRY.register(Tool(
    name="daily_briefing",
    description="오늘 브리핑 — 날짜 + 날씨 + 캘린더 + TODO + 무드 종합. '아침에 보고해줘'에 사용.",
    input_schema={
        "type": "object",
        "properties": {"location": {"type": "string", "default": "Seoul"}},
    },
    handler=_daily_briefing,
))

REGISTRY.register(Tool(
    name="calendar_today",
    description="오늘 캘린더 일정 list (시간 + 제목).",
    input_schema={"type": "object", "properties": {}},
    handler=_calendar_today_summary,
))
