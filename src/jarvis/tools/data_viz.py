"""ASCII 데이터 시각화 — bar/line chart, sparkline, heatmap."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool

_DATA = Path.home() / ".jarvis"


def _bar_chart(values_csv: str, labels_csv: str = "", width: int = 40, title: str = "") -> str:
    """쉼표 구분 숫자 → 가로 ASCII 막대."""
    try:
        values = [float(x) for x in values_csv.split(",") if x.strip()]
    except ValueError:
        return "ERROR: values_csv는 쉼표 구분 숫자"
    labels = [s.strip() for s in labels_csv.split(",") if s.strip()] if labels_csv else \
             [str(i + 1) for i in range(len(values))]
    if len(labels) < len(values):
        labels += [str(i + 1) for i in range(len(labels), len(values))]
    mx = max(values) if values else 1
    if mx == 0:
        mx = 1
    out = [title] if title else []
    label_w = max(len(l) for l in labels[:len(values)])
    for label, v in zip(labels, values):
        bar_len = int(v / mx * width)
        out.append(f"{label:>{label_w}} │{'█' * bar_len:<{width}}│ {v:g}")
    return "\n".join(out)


def _sparkline(values_csv: str) -> str:
    """쉼표 구분 숫자 → ▁▂▃▄▅▆▇█ 스파크라인."""
    try:
        values = [float(x) for x in values_csv.split(",") if x.strip()]
    except ValueError:
        return "ERROR: values_csv는 쉼표 구분 숫자"
    if not values:
        return ""
    mn, mx = min(values), max(values)
    if mx == mn:
        return "▄" * len(values)
    chars = "▁▂▃▄▅▆▇█"
    return "".join(chars[min(7, int((v - mn) / (mx - mn) * 7))] for v in values)


def _habit_heatmap(habit: str, days: int = 30) -> str:
    """habit_log → 30일 heatmap (■=실행, ·=미실행)."""
    log = _DATA / "habits.jsonl"
    if not log.exists():
        return "(no habit log)"
    by_day: dict = defaultdict(int)
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if e.get("habit") == habit:
                d = e.get("ts", "")[:10]
                if d:
                    by_day[d] += 1
        except Exception:
            continue
    today = datetime.now().date()
    out = [f"=== {habit} (last {days}d) ==="]
    row = []
    for i in range(days, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        row.append("■" if by_day.get(d) else "·")
        if (days - i + 1) % 7 == 0:
            out.append(" ".join(row))
            row = []
    if row:
        out.append(" ".join(row))
    out.append(f"\n실행 일수: {sum(1 for v in by_day.values() if v > 0)}/{days}")
    return "\n".join(out)


def _weight_chart(limit: int = 30) -> str:
    """health.jsonl 의 weight 항목 → 라인 차트(스파크라인 + 텍스트)."""
    log = _DATA / "health.jsonl"
    if not log.exists():
        return "(no health log)"
    rows = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if e.get("kind") == "weight":
                rows.append((e["ts"][:10], float(e["kg"])))
        except Exception:
            continue
    rows = rows[-limit:]
    if len(rows) < 2:
        return "(체중 기록이 2개 미만)"
    values = [v for _, v in rows]
    spark = _sparkline(",".join(str(v) for v in values))
    return (f"체중 추이 (최근 {len(rows)}회)\n"
            f"{rows[0][0]} → {rows[-1][0]}\n"
            f"min={min(values):.1f} max={max(values):.1f} avg={sum(values)/len(values):.1f}\n"
            f"{spark}")


def _finance_chart(days: int = 30, currency: str = "KRW") -> str:
    """일자별 지출 합계 sparkline."""
    log = _DATA / "finance.jsonl"
    if not log.exists():
        return "(no finance log)"
    by_day: dict = defaultdict(float)
    cutoff = datetime.now().timestamp() - days * 86400
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if e.get("kind") != "expense" or e.get("currency") != currency:
                continue
            ts = datetime.fromisoformat(e["ts"]).timestamp()
            if ts < cutoff:
                continue
            d = e["ts"][:10]
            by_day[d] += float(e["amount"])
        except Exception:
            continue
    if not by_day:
        return f"(no expense entries in last {days}d)"
    today = datetime.now().date()
    series = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        series.append(by_day.get(d, 0))
    spark = _sparkline(",".join(str(v) for v in series))
    return (f"일별 지출 ({currency}, 최근 {days}일)\n"
            f"min={min(series):,.0f} max={max(series):,.0f} avg={sum(series)/len(series):,.0f}\n"
            f"total={sum(series):,.0f}\n"
            f"{spark}")


def _calendar_view(year: int = 0, month: int = 0) -> str:
    """ASCII 달력. 빈 인자 → 이번 달."""
    import calendar as _cal
    now = datetime.now()
    y = year or now.year
    m = month or now.month
    cal = _cal.TextCalendar(firstweekday=6)  # Sunday-first
    return cal.formatmonth(y, m).rstrip()


REGISTRY.register(Tool(
    name="bar_chart",
    description="ASCII 가로 막대 차트. values_csv='10,20,30', labels_csv 옵션.",
    input_schema={
        "type": "object",
        "properties": {
            "values_csv": {"type": "string"},
            "labels_csv": {"type": "string"},
            "width": {"type": "integer", "description": "기본 40"},
            "title": {"type": "string"},
        },
        "required": ["values_csv"],
    },
    handler=_bar_chart,
))
REGISTRY.register(Tool(
    name="sparkline",
    description="쉼표 구분 숫자를 ▁▂▃▄▅▆▇█ 스파크라인으로.",
    input_schema={
        "type": "object",
        "properties": {"values_csv": {"type": "string"}},
        "required": ["values_csv"],
    },
    handler=_sparkline,
))
REGISTRY.register(Tool(
    name="habit_heatmap",
    description="습관 30일 heatmap (■=실행 ·=미실행).",
    input_schema={
        "type": "object",
        "properties": {
            "habit": {"type": "string"},
            "days": {"type": "integer", "description": "기본 30"},
        },
        "required": ["habit"],
    },
    handler=_habit_heatmap,
))
REGISTRY.register(Tool(
    name="weight_chart",
    description="체중 기록 sparkline + 통계.",
    input_schema={
        "type": "object",
        "properties": {"limit": {"type": "integer", "description": "기본 30"}},
        "required": [],
    },
    handler=_weight_chart,
))
REGISTRY.register(Tool(
    name="finance_chart",
    description="일별 지출 sparkline (N일).",
    input_schema={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "기본 30"},
            "currency": {"type": "string", "description": "기본 KRW"},
        },
        "required": [],
    },
    handler=_finance_chart,
))
REGISTRY.register(Tool(
    name="calendar_view",
    description="ASCII 달력. 인자 없으면 이번 달.",
    input_schema={
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "month": {"type": "integer"},
        },
        "required": [],
    },
    handler=_calendar_view,
))
