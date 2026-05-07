"""개인 트래킹 — 저널 / 습관 / 무드 / 수면 / 운동 / 식사 (file-based, ~/.jarvis/)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


_HOME = Path.home() / ".jarvis"
_HOME.mkdir(parents=True, exist_ok=True)


def _append_md(filename: str, line: str) -> str:
    p = _HOME / filename
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- [{ts}] {line}\n")
    return str(p)


def _read_md(filename: str, n: int = 20) -> str:
    p = _HOME / filename
    if not p.exists():
        return f"(empty — {p})"
    lines = p.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n:])


def _journal_add(text: str) -> str:
    """일기/저널 — ~/.jarvis/journal.md에 timestamp 추가."""
    return f"OK: {_append_md('journal.md', text)}"


def _journal_list(n: int = 20) -> str:
    return _read_md("journal.md", n)


def _mood_log(mood: str, note: str = "") -> str:
    """무드 트래킹. mood 예: '좋음', '보통', '피곤', '5/10', 이모지."""
    line = f"{mood}" + (f" — {note}" if note else "")
    return f"OK: {_append_md('mood.md', line)}"


def _mood_list(n: int = 30) -> str:
    return _read_md("mood.md", n)


def _habit_log(habit: str, status: str = "done") -> str:
    """습관 완료 기록. status='done'/'skip'/'partial'."""
    return f"OK: {_append_md('habits.md', f'[{status}] {habit}')}"


def _habit_list(n: int = 30) -> str:
    return _read_md("habits.md", n)


def _habit_streak(habit: str) -> str:
    """특정 습관의 연속 일수 계산."""
    p = _HOME / "habits.md"
    if not p.exists():
        return "0"
    from datetime import date, timedelta
    days_with_habit: set[date] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        if habit in line and "[done]" in line:
            try:
                ts = line.split("[", 1)[1].split("]", 1)[0]
                d = datetime.strptime(ts.split(" ")[0], "%Y-%m-%d").date()
                days_with_habit.add(d)
            except Exception:
                continue
    if not days_with_habit:
        return "0"
    today = date.today()
    streak = 0
    cursor = today
    while cursor in days_with_habit:
        streak += 1
        cursor -= timedelta(days=1)
    return json.dumps({"habit": habit, "streak_days": streak, "total_days": len(days_with_habit)}, ensure_ascii=False)


def _sleep_log(hours: float, quality: str = "") -> str:
    """수면 기록 (시간 + 품질)."""
    line = f"{hours}h" + (f" ({quality})" if quality else "")
    return f"OK: {_append_md('sleep.md', line)}"


def _sleep_avg(days: int = 7) -> str:
    """최근 N일 평균 수면 시간."""
    p = _HOME / "sleep.md"
    if not p.exists():
        return "0 (no data)"
    import re
    hours = []
    for line in p.read_text(encoding="utf-8").splitlines()[-days * 3:]:
        m = re.search(r"(\d+(?:\.\d+)?)h", line)
        if m:
            hours.append(float(m.group(1)))
    hours = hours[-days:]
    if not hours:
        return "0 (no data)"
    return json.dumps({"avg_hours": round(sum(hours) / len(hours), 2), "samples": len(hours)}, ensure_ascii=False)


def _workout_log(activity: str, duration_min: int = 0, note: str = "") -> str:
    """운동 기록."""
    line = f"{activity}" + (f" {duration_min}분" if duration_min else "") + (f" — {note}" if note else "")
    return f"OK: {_append_md('workout.md', line)}"


def _meal_log(meal: str, calories: int = 0) -> str:
    """식사 기록."""
    line = f"{meal}" + (f" ({calories} kcal)" if calories else "")
    return f"OK: {_append_md('meals.md', line)}"


def _water_log(ml: int = 250) -> str:
    """물 섭취 기록."""
    return f"OK: {_append_md('water.md', f'{ml}ml')}"


def _water_today() -> str:
    """오늘 마신 물 총량."""
    p = _HOME / "water.md"
    if not p.exists():
        return "0ml"
    import re
    today = datetime.now().strftime("%Y-%m-%d")
    total = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if today in line:
            m = re.search(r"(\d+)ml", line)
            if m:
                total += int(m.group(1))
    return f"{total}ml"


def _todo_add(text: str, priority: str = "normal") -> str:
    """TODO 추가 — ~/.jarvis/todos.md (priority: high/normal/low)."""
    return f"OK: {_append_md('todos.md', f'[ ] [{priority}] {text}')}"


def _todo_list() -> str:
    """미완료 TODO 목록."""
    p = _HOME / "todos.md"
    if not p.exists():
        return "(empty)"
    out = [line for line in p.read_text(encoding="utf-8").splitlines() if "[ ]" in line]
    return "\n".join(out) if out else "(모두 완료)"


def _todo_done(text_match: str) -> str:
    """TODO 완료 표시 — text_match가 포함된 첫 미완료 라인."""
    p = _HOME / "todos.md"
    if not p.exists():
        return "TODO 파일 없음"
    lines = p.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if "[ ]" in line and text_match in line:
            lines[i] = line.replace("[ ]", "[x]", 1)
            found = True
            break
    if not found:
        return f"매칭 없음: {text_match}"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "OK: 완료 표시"


REGISTRY.register(Tool(
    name="journal_add",
    description="일기/저널 한 줄 추가 (~/.jarvis/journal.md, timestamp 자동).",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_journal_add,
))
REGISTRY.register(Tool(
    name="journal_list",
    description="최근 저널 N개 (기본 20).",
    input_schema={"type": "object", "properties": {"n": {"type": "integer", "default": 20}}},
    handler=_journal_list,
))

REGISTRY.register(Tool(
    name="mood_log",
    description="무드 기록 ('좋음'/'5/10'/이모지 등).",
    input_schema={
        "type": "object",
        "properties": {"mood": {"type": "string"}, "note": {"type": "string", "default": ""}},
        "required": ["mood"],
    },
    handler=_mood_log,
))
REGISTRY.register(Tool(
    name="mood_list",
    description="최근 무드 기록.",
    input_schema={"type": "object", "properties": {"n": {"type": "integer", "default": 30}}},
    handler=_mood_list,
))

REGISTRY.register(Tool(
    name="habit_log",
    description="습관 완료 기록. status: done/skip/partial.",
    input_schema={
        "type": "object",
        "properties": {"habit": {"type": "string"}, "status": {"type": "string", "default": "done"}},
        "required": ["habit"],
    },
    handler=_habit_log,
))
REGISTRY.register(Tool(
    name="habit_streak",
    description="특정 습관의 연속 일수 (오늘 기준).",
    input_schema={"type": "object", "properties": {"habit": {"type": "string"}}, "required": ["habit"]},
    handler=_habit_streak,
))
REGISTRY.register(Tool(
    name="habit_list",
    description="최근 습관 기록 N개.",
    input_schema={"type": "object", "properties": {"n": {"type": "integer", "default": 30}}},
    handler=_habit_list,
))

REGISTRY.register(Tool(
    name="sleep_log",
    description="수면 기록 — 시간(hours) + 품질.",
    input_schema={
        "type": "object",
        "properties": {"hours": {"type": "number"}, "quality": {"type": "string", "default": ""}},
        "required": ["hours"],
    },
    handler=_sleep_log,
))
REGISTRY.register(Tool(
    name="sleep_avg",
    description="최근 N일 평균 수면 시간.",
    input_schema={"type": "object", "properties": {"days": {"type": "integer", "default": 7}}},
    handler=_sleep_avg,
))

REGISTRY.register(Tool(
    name="workout_log",
    description="운동 기록.",
    input_schema={
        "type": "object",
        "properties": {
            "activity": {"type": "string"},
            "duration_min": {"type": "integer", "default": 0},
            "note": {"type": "string", "default": ""},
        },
        "required": ["activity"],
    },
    handler=_workout_log,
))

REGISTRY.register(Tool(
    name="meal_log",
    description="식사/간식 기록 + 선택적 칼로리.",
    input_schema={
        "type": "object",
        "properties": {"meal": {"type": "string"}, "calories": {"type": "integer", "default": 0}},
        "required": ["meal"],
    },
    handler=_meal_log,
))

REGISTRY.register(Tool(
    name="water_log",
    description="물 섭취 기록 (ml).",
    input_schema={"type": "object", "properties": {"ml": {"type": "integer", "default": 250}}},
    handler=_water_log,
))
REGISTRY.register(Tool(
    name="water_today",
    description="오늘 총 물 섭취량.",
    input_schema={"type": "object", "properties": {}},
    handler=_water_today,
))

REGISTRY.register(Tool(
    name="todo_add",
    description="TODO 추가. priority: high/normal/low.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}, "priority": {"type": "string", "default": "normal"}},
        "required": ["text"],
    },
    handler=_todo_add,
))
REGISTRY.register(Tool(
    name="todo_list",
    description="미완료 TODO 목록 (~/.jarvis/todos.md).",
    input_schema={"type": "object", "properties": {}},
    handler=_todo_list,
))
REGISTRY.register(Tool(
    name="todo_done",
    description="TODO 완료 처리 (text_match가 포함된 첫 미완료 라인 [x] 처리).",
    input_schema={"type": "object", "properties": {"text_match": {"type": "string"}}, "required": ["text_match"]},
    handler=_todo_done,
))
