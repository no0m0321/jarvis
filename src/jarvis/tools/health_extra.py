"""Health/Wellness 확장 — weight, BP, heart rate, steps, BMI."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool

_DATA = Path.home() / ".jarvis"
_DATA.mkdir(parents=True, exist_ok=True)
_LOG = _DATA / "health.jsonl"


def _append(entry: dict) -> None:
    entry["ts"] = datetime.now().isoformat(timespec="seconds")
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read(kind: str = "", limit: int = 0) -> list:
    if not _LOG.exists():
        return []
    out = []
    for line in _LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if not kind or e.get("kind") == kind:
                out.append(e)
        except Exception:
            continue
    return out[-limit:] if limit else out


def _weight_log(kg: float, note: str = "") -> str:
    _append({"kind": "weight", "kg": float(kg), "note": note})
    return f"OK: weight {kg}kg logged"


def _weight_history(limit: int = 30) -> str:
    rows = _read("weight", limit)
    if not rows:
        return "(no weight entries)"
    return "\n".join(f"{r['ts'][:10]}  {r['kg']:>5.1f}kg  {r.get('note','')}" for r in rows)


def _bp_log(systolic: int, diastolic: int, pulse: int = 0, note: str = "") -> str:
    """혈압 기록. systolic/diastolic mmHg."""
    _append({"kind": "bp", "sys": int(systolic), "dia": int(diastolic),
             "pulse": int(pulse), "note": note})
    cat = "정상"
    if systolic >= 140 or diastolic >= 90:
        cat = "고혈압"
    elif systolic >= 130 or diastolic >= 80:
        cat = "주의"
    elif systolic < 90 or diastolic < 60:
        cat = "저혈압"
    return f"OK: BP {systolic}/{diastolic} ({cat}){' pulse '+str(pulse) if pulse else ''}"


def _bp_history(limit: int = 30) -> str:
    rows = _read("bp", limit)
    if not rows:
        return "(no BP entries)"
    return "\n".join(f"{r['ts'][:16]}  {r['sys']}/{r['dia']}  pulse={r.get('pulse',0)}  {r.get('note','')}" for r in rows)


def _hr_log(bpm: int, context: str = "rest") -> str:
    """심박수 수동 기록. context: rest|exercise|recovery."""
    _append({"kind": "hr", "bpm": int(bpm), "context": context})
    return f"OK: HR {bpm}bpm ({context})"


def _steps_log(count: int, note: str = "") -> str:
    _append({"kind": "steps", "count": int(count), "note": note})
    return f"OK: {count} steps logged"


def _steps_summary(days: int = 7) -> str:
    rows = _read("steps")
    if not rows:
        return "(no step entries)"
    cutoff = datetime.now().timestamp() - days * 86400
    recent = []
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["ts"]).timestamp()
            if ts >= cutoff:
                recent.append(r)
        except Exception:
            continue
    if not recent:
        return f"(no entries in last {days}d)"
    total = sum(r["count"] for r in recent)
    return f"{days}일 합계: {total:,} steps (avg {total/days:,.0f}/일, {len(recent)}회 기록)"


def _bmi(weight_kg: float, height_cm: float) -> str:
    h = height_cm / 100
    if h <= 0:
        return "ERROR: height_cm > 0"
    bmi = weight_kg / (h * h)
    cat = ("저체중" if bmi < 18.5 else
           "정상" if bmi < 25 else
           "과체중" if bmi < 30 else
           "비만")
    return f"BMI: {bmi:.2f} ({cat})"


REGISTRY.register(Tool(
    name="weight_log",
    description="체중 기록 (kg).",
    input_schema={
        "type": "object",
        "properties": {
            "kg": {"type": "number"},
            "note": {"type": "string"},
        },
        "required": ["kg"],
    },
    handler=_weight_log,
))
REGISTRY.register(Tool(
    name="weight_history",
    description="체중 기록 history (최근 N).",
    input_schema={
        "type": "object",
        "properties": {"limit": {"type": "integer", "description": "기본 30"}},
        "required": [],
    },
    handler=_weight_history,
))
REGISTRY.register(Tool(
    name="bp_log",
    description="혈압 기록 (수축기/이완기 mmHg, pulse 옵션).",
    input_schema={
        "type": "object",
        "properties": {
            "systolic": {"type": "integer"},
            "diastolic": {"type": "integer"},
            "pulse": {"type": "integer"},
            "note": {"type": "string"},
        },
        "required": ["systolic", "diastolic"],
    },
    handler=_bp_log,
))
REGISTRY.register(Tool(
    name="bp_history",
    description="혈압 기록 history.",
    input_schema={
        "type": "object",
        "properties": {"limit": {"type": "integer"}},
        "required": [],
    },
    handler=_bp_history,
))
REGISTRY.register(Tool(
    name="hr_log",
    description="심박수 수동 기록 (bpm, context: rest|exercise|recovery).",
    input_schema={
        "type": "object",
        "properties": {
            "bpm": {"type": "integer"},
            "context": {"type": "string"},
        },
        "required": ["bpm"],
    },
    handler=_hr_log,
))
REGISTRY.register(Tool(
    name="steps_log",
    description="걸음수 수동 기록.",
    input_schema={
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "note": {"type": "string"},
        },
        "required": ["count"],
    },
    handler=_steps_log,
))
REGISTRY.register(Tool(
    name="steps_summary",
    description="최근 N일 걸음수 합계.",
    input_schema={
        "type": "object",
        "properties": {"days": {"type": "integer", "description": "기본 7"}},
        "required": [],
    },
    handler=_steps_summary,
))
REGISTRY.register(Tool(
    name="bmi_calc",
    description="BMI 계산 (kg, cm) + 분류.",
    input_schema={
        "type": "object",
        "properties": {
            "weight_kg": {"type": "number"},
            "height_cm": {"type": "number"},
        },
        "required": ["weight_kg", "height_cm"],
    },
    handler=_bmi,
))
