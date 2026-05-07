"""Productivity 확장 — alarm, stopwatch, world clock, eye-break, breathing, meditation, sun/moon."""
from __future__ import annotations

import json
import math
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool

_DATA_DIR = Path.home() / ".jarvis"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_ALARMS_FILE = _DATA_DIR / "alarms.json"
_STOPWATCH_FILE = _DATA_DIR / "stopwatch.json"


def _load(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(p: Path, data) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Alarm ─────────────────────────────────────────────────────────────────
def _alarm_set(at_iso: str, message: str = "Alarm") -> str:
    """at_iso: 'YYYY-MM-DD HH:MM'. 백그라운드 thread로 sleep 후 알림."""
    try:
        target = datetime.strptime(at_iso, "%Y-%m-%d %H:%M")
    except ValueError:
        return "ERROR: at_iso 형식은 'YYYY-MM-DD HH:MM'"
    delay = (target - datetime.now()).total_seconds()
    if delay <= 0:
        return "ERROR: 과거 시각"
    alarms = _load(_ALARMS_FILE, [])
    alarms.append({"at": at_iso, "msg": message, "set_at": datetime.now().isoformat(timespec="seconds")})
    _save(_ALARMS_FILE, alarms)

    def _fire():
        time.sleep(delay)
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "⏰ Alarm" sound name "Glass"'],
            capture_output=True,
        )
        subprocess.run(["say", "-v", "Yuna", message], capture_output=True)

    threading.Thread(target=_fire, daemon=True).start()
    return f"OK: alarm set at {at_iso} — '{message}' (in {int(delay/60)}m)"


def _alarm_list() -> str:
    alarms = _load(_ALARMS_FILE, [])
    upcoming = []
    now = datetime.now()
    for a in alarms:
        try:
            t = datetime.strptime(a["at"], "%Y-%m-%d %H:%M")
            if t > now:
                upcoming.append(f"{a['at']} — {a['msg']}")
        except Exception:
            continue
    return "\n".join(upcoming) or "(no upcoming alarms)"


def _alarm_clear() -> str:
    _save(_ALARMS_FILE, [])
    return "OK: alarm history cleared (in-memory threads는 process 종료까지 살아있음)"


REGISTRY.register(Tool(
    name="alarm_set",
    description="특정 시각에 alarm — 알림 + TTS. at_iso='2026-05-04 14:30'.",
    input_schema={
        "type": "object",
        "properties": {
            "at_iso": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["at_iso"],
    },
    handler=_alarm_set,
))
REGISTRY.register(Tool(
    name="alarm_list",
    description="설정된 alarm list (미래 시각만).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_alarm_list,
))
REGISTRY.register(Tool(
    name="alarm_clear",
    description="alarm history 파일 비우기 (이미 예약된 thread는 유지).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_alarm_clear,
))


# ── Stopwatch ─────────────────────────────────────────────────────────────
def _stopwatch_start() -> str:
    state = {"started_at": time.time(), "laps": []}
    _save(_STOPWATCH_FILE, state)
    return "OK: stopwatch started"


def _stopwatch_lap(label: str = "") -> str:
    state = _load(_STOPWATCH_FILE, None)
    if not state or "started_at" not in state:
        return "ERROR: stopwatch not running"
    elapsed = time.time() - state["started_at"]
    state["laps"].append({"at": elapsed, "label": label})
    _save(_STOPWATCH_FILE, state)
    return f"LAP {len(state['laps'])}: {elapsed:.2f}s — {label}"


def _stopwatch_stop() -> str:
    state = _load(_STOPWATCH_FILE, None)
    if not state or "started_at" not in state:
        return "ERROR: stopwatch not running"
    elapsed = time.time() - state["started_at"]
    laps = state.get("laps", [])
    out = [f"TOTAL: {elapsed:.2f}s ({elapsed/60:.2f}m)"]
    for i, lap in enumerate(laps, 1):
        out.append(f"  lap {i}: {lap['at']:.2f}s — {lap.get('label','')}")
    _save(_STOPWATCH_FILE, {})
    return "\n".join(out)


REGISTRY.register(Tool(
    name="stopwatch_start",
    description="스톱워치 시작.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_stopwatch_start,
))
REGISTRY.register(Tool(
    name="stopwatch_lap",
    description="스톱워치 lap 기록 (label 옵션).",
    input_schema={
        "type": "object",
        "properties": {"label": {"type": "string"}},
        "required": [],
    },
    handler=_stopwatch_lap,
))
REGISTRY.register(Tool(
    name="stopwatch_stop",
    description="스톱워치 종료 + 모든 lap 출력.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_stopwatch_stop,
))


# ── World clock ───────────────────────────────────────────────────────────
def _world_clock(zones: str = "Asia/Seoul,UTC,America/New_York,Europe/London,Asia/Tokyo") -> str:
    """쉼표 구분 zone — 각 zone의 현재 시각."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        return "ERROR: zoneinfo 미지원 (Python 3.9+)"
    out = []
    now_utc = datetime.now(timezone.utc)
    for z in zones.split(","):
        z = z.strip()
        if not z:
            continue
        try:
            t = now_utc.astimezone(ZoneInfo(z))
            out.append(f"{z:25s} {t.strftime('%Y-%m-%d %H:%M %Z')}")
        except Exception as e:
            out.append(f"{z:25s} ERROR: {e}")
    return "\n".join(out)


REGISTRY.register(Tool(
    name="world_clock",
    description="여러 timezone 현재 시각 한 번에. 쉼표 구분.",
    input_schema={
        "type": "object",
        "properties": {"zones": {"type": "string", "description": "기본 Seoul/UTC/NY/London/Tokyo"}},
        "required": [],
    },
    handler=_world_clock,
))


# ── Eye break (20-20-20) ─────────────────────────────────────────────────
def _eye_break_start(interval_minutes: int = 20) -> str:
    """20분마다 알림으로 눈 휴식 권장. daemon thread."""
    state_file = _DATA_DIR / "eye_break.json"
    state = {"started_at": time.time(), "interval": interval_minutes, "active": True}
    _save(state_file, state)

    def _loop():
        while True:
            time.sleep(interval_minutes * 60)
            cur = _load(state_file, {})
            if not cur.get("active"):
                break
            subprocess.run(
                ["osascript", "-e",
                 'display notification "20초간 6m(20ft) 거리 응시 — 눈 피로 완화" with title "👁 20-20-20" sound name "Hero"'],
                capture_output=True,
            )

    threading.Thread(target=_loop, daemon=True).start()
    return f"OK: eye break loop started ({interval_minutes}min interval)"


def _eye_break_stop() -> str:
    state_file = _DATA_DIR / "eye_break.json"
    s = _load(state_file, {})
    s["active"] = False
    _save(state_file, s)
    return "OK: eye break loop will exit on next tick"


REGISTRY.register(Tool(
    name="eye_break_start",
    description="20-20-20 눈 휴식 알림 시작 (interval 분마다).",
    input_schema={
        "type": "object",
        "properties": {"interval_minutes": {"type": "integer", "description": "기본 20"}},
        "required": [],
    },
    handler=_eye_break_start,
))
REGISTRY.register(Tool(
    name="eye_break_stop",
    description="20-20-20 눈 휴식 loop 중지 (다음 tick에 종료).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_eye_break_stop,
))


# ── Breathing exercise (4-7-8) ───────────────────────────────────────────
def _breathing_478(cycles: int = 4) -> str:
    """4초 흡기 → 7초 정지 → 8초 호기, N회 반복."""
    def _run():
        for i in range(cycles):
            subprocess.run(["say", "-v", "Yuna", f"{i+1}회 — 들이마시고"], capture_output=True)
            time.sleep(4)
            subprocess.run(["say", "-v", "Yuna", "멈추고"], capture_output=True)
            time.sleep(7)
            subprocess.run(["say", "-v", "Yuna", "내쉬세요"], capture_output=True)
            time.sleep(8)
        subprocess.run(["say", "-v", "Yuna", "호흡 운동을 마쳤습니다"], capture_output=True)

    threading.Thread(target=_run, daemon=True).start()
    return f"OK: 4-7-8 호흡 시작 ({cycles}회 — 약 {cycles*19}초)"


REGISTRY.register(Tool(
    name="breathing_478",
    description="4-7-8 호흡 운동 (TTS 가이드, 백그라운드).",
    input_schema={
        "type": "object",
        "properties": {"cycles": {"type": "integer", "description": "기본 4회"}},
        "required": [],
    },
    handler=_breathing_478,
))


# ── Meditation timer ─────────────────────────────────────────────────────
def _meditation(minutes: int = 10) -> str:
    def _run():
        subprocess.run(["afplay", "/System/Library/Sounds/Tink.aiff"], capture_output=True)
        subprocess.run(["say", "-v", "Yuna", f"{minutes}분 명상을 시작합니다"], capture_output=True)
        time.sleep(minutes * 60)
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], capture_output=True)
        subprocess.run(["osascript", "-e",
                        f'display notification "명상 완료" with title "🧘 Meditation" sound name "Glass"'],
                       capture_output=True)
        subprocess.run(["say", "-v", "Yuna", "명상을 마쳤습니다"], capture_output=True)

    threading.Thread(target=_run, daemon=True).start()
    return f"OK: {minutes}분 명상 시작"


REGISTRY.register(Tool(
    name="meditation",
    description="N분 명상 timer (시작/종료 종소리 + TTS).",
    input_schema={
        "type": "object",
        "properties": {"minutes": {"type": "integer", "description": "기본 10"}},
        "required": [],
    },
    handler=_meditation,
))


# ── Sunrise/Sunset (lat/lon) ─────────────────────────────────────────────
def _sun_times(lat: float = 37.5665, lon: float = 126.9780, date: str = "") -> str:
    """간단한 NOAA solar 알고리즘. 기본 서울."""
    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return "ERROR: date='YYYY-MM-DD'"
    else:
        d = datetime.now()
    # NOAA solar position approximation
    n = d.toordinal() - datetime(d.year, 1, 1).toordinal() + 1
    lat_r = math.radians(lat)
    decl = math.radians(23.44 * math.sin(math.radians(360/365 * (n - 81))))
    try:
        cos_h = -math.tan(lat_r) * math.tan(decl)
        if cos_h > 1 or cos_h < -1:
            return f"({d.date()}) 극야/백야 (lat={lat})"
        h = math.degrees(math.acos(cos_h))
    except Exception as e:
        return f"ERROR: {e}"
    # Solar noon approx
    eqt_minutes = 9.87 * math.sin(math.radians(2 * 360/365 * (n - 81))) - 7.53 * math.cos(math.radians(360/365 * (n - 81))) - 1.5 * math.sin(math.radians(360/365 * (n - 81)))
    solar_noon_min = 720 - 4 * lon - eqt_minutes
    sunrise_min = solar_noon_min - 4 * h
    sunset_min = solar_noon_min + 4 * h

    # 현재 utc → local 시각으로 변환 (사용자 시스템 TZ로 표시)
    def _fmt(minutes_utc: float) -> str:
        if minutes_utc < 0:
            minutes_utc += 1440
        if minutes_utc >= 1440:
            minutes_utc -= 1440
        utc_dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(minutes=minutes_utc)
        local_dt = utc_dt.astimezone()
        return local_dt.strftime("%H:%M %Z")

    return (f"date: {d.date()} (lat={lat}, lon={lon})\n"
            f"sunrise: {_fmt(sunrise_min)}\n"
            f"sunset:  {_fmt(sunset_min)}\n"
            f"day length: {2*h*4/60:.2f}h")


REGISTRY.register(Tool(
    name="sun_times",
    description="일출/일몰 시각 (lat/lon, 기본 서울 37.5665, 126.9780).",
    input_schema={
        "type": "object",
        "properties": {
            "lat": {"type": "number"},
            "lon": {"type": "number"},
            "date": {"type": "string", "description": "YYYY-MM-DD, 기본 오늘"},
        },
        "required": [],
    },
    handler=_sun_times,
))


# ── Moon phase ───────────────────────────────────────────────────────────
def _moon_phase(date: str = "") -> str:
    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return "ERROR: date='YYYY-MM-DD'"
    else:
        d = datetime.now()
    # Conway's algorithm
    y, m = d.year, d.month
    if m < 3:
        y -= 1
        m += 12
    c = (47 * y) % 4000
    s = c * 12 + m * 30 + d.day
    phase_days = ((s - 694039.09) / 29.5305882) % 1 * 29.5305882
    names = [
        (1.84, "🌑 New Moon"),
        (5.53, "🌒 Waxing Crescent"),
        (9.22, "🌓 First Quarter"),
        (12.91, "🌔 Waxing Gibbous"),
        (16.61, "🌕 Full Moon"),
        (20.30, "🌖 Waning Gibbous"),
        (23.99, "🌗 Last Quarter"),
        (27.68, "🌘 Waning Crescent"),
        (29.53, "🌑 New Moon"),
    ]
    label = "🌑 New Moon"
    for cutoff, name in names:
        if phase_days < cutoff:
            label = name
            break
    illum = (1 - math.cos(2 * math.pi * phase_days / 29.5305882)) / 2
    return f"{d.date()} — {label} (age {phase_days:.1f}일, illum {illum*100:.0f}%)"


REGISTRY.register(Tool(
    name="moon_phase",
    description="달 위상 + 조도 (Conway algorithm 근사).",
    input_schema={
        "type": "object",
        "properties": {"date": {"type": "string", "description": "YYYY-MM-DD, 기본 오늘"}},
        "required": [],
    },
    handler=_moon_phase,
))
