"""개인 재무 추적 — expense / income / networth (~/.jarvis/finance.jsonl)."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool

_DATA = Path.home() / ".jarvis"
_DATA.mkdir(parents=True, exist_ok=True)
_LOG = _DATA / "finance.jsonl"


def _append(entry: dict) -> None:
    entry["ts"] = datetime.now().isoformat(timespec="seconds")
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_all() -> list:
    if not _LOG.exists():
        return []
    out = []
    for line in _LOG.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _expense_log(amount: float, category: str = "misc", note: str = "", currency: str = "KRW") -> str:
    _append({"kind": "expense", "amount": float(amount), "category": category,
             "note": note, "currency": currency})
    return f"OK: -{amount} {currency} ({category}) {note}"


def _income_log(amount: float, source: str = "misc", note: str = "", currency: str = "KRW") -> str:
    _append({"kind": "income", "amount": float(amount), "source": source,
             "note": note, "currency": currency})
    return f"OK: +{amount} {currency} ({source}) {note}"


def _finance_summary(days: int = 30, currency: str = "KRW") -> str:
    entries = _read_all()
    if not entries:
        return "(no entries)"
    cutoff = datetime.now().timestamp() - days * 86400
    cat_in: dict = defaultdict(float)
    cat_out: dict = defaultdict(float)
    total_in = total_out = 0.0
    for e in entries:
        if e.get("currency") != currency:
            continue
        try:
            ts = datetime.fromisoformat(e["ts"]).timestamp()
        except Exception:
            continue
        if ts < cutoff:
            continue
        amt = float(e.get("amount", 0))
        if e.get("kind") == "expense":
            total_out += amt
            cat_out[e.get("category", "misc")] += amt
        elif e.get("kind") == "income":
            total_in += amt
            cat_in[e.get("source", "misc")] += amt
    out = [f"=== Last {days} days ({currency}) ===",
           f"income:   +{total_in:,.0f}",
           f"expense:  -{total_out:,.0f}",
           f"net:      {total_in - total_out:+,.0f}", ""]
    if cat_in:
        out.append("[income by source]")
        for k, v in sorted(cat_in.items(), key=lambda x: -x[1]):
            out.append(f"  {k:15s} +{v:,.0f}")
    if cat_out:
        out.append("[expense by category]")
        for k, v in sorted(cat_out.items(), key=lambda x: -x[1]):
            out.append(f"  {k:15s} -{v:,.0f}")
    return "\n".join(out)


def _networth_set(amount: float, label: str = "total", currency: str = "KRW") -> str:
    _append({"kind": "networth", "amount": float(amount),
             "label": label, "currency": currency})
    return f"OK: networth snapshot — {label}: {amount:,.0f} {currency}"


def _networth_history(currency: str = "KRW", limit: int = 20) -> str:
    rows = [e for e in _read_all() if e.get("kind") == "networth"
            and e.get("currency") == currency]
    rows = rows[-limit:]
    if not rows:
        return "(no networth snapshots)"
    return "\n".join(f"{r['ts']}  {r.get('label','total'):10s}  {r['amount']:>15,.0f} {currency}"
                     for r in rows)


REGISTRY.register(Tool(
    name="expense_log",
    description="지출 기록 (~/.jarvis/finance.jsonl).",
    input_schema={
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "category": {"type": "string", "description": "예: food, transport, rent"},
            "note": {"type": "string"},
            "currency": {"type": "string", "description": "기본 KRW"},
        },
        "required": ["amount"],
    },
    handler=_expense_log,
))
REGISTRY.register(Tool(
    name="income_log",
    description="수입 기록.",
    input_schema={
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "source": {"type": "string"},
            "note": {"type": "string"},
            "currency": {"type": "string"},
        },
        "required": ["amount"],
    },
    handler=_income_log,
))
REGISTRY.register(Tool(
    name="finance_summary",
    description="최근 N일 수입/지출 요약 (카테고리별).",
    input_schema={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "기본 30"},
            "currency": {"type": "string"},
        },
        "required": [],
    },
    handler=_finance_summary,
))
REGISTRY.register(Tool(
    name="networth_set",
    description="순자산 스냅샷 기록.",
    input_schema={
        "type": "object",
        "properties": {
            "amount": {"type": "number"},
            "label": {"type": "string", "description": "예: total, stocks, cash"},
            "currency": {"type": "string"},
        },
        "required": ["amount"],
    },
    handler=_networth_set,
))
REGISTRY.register(Tool(
    name="networth_history",
    description="순자산 스냅샷 history (최근 N).",
    input_schema={
        "type": "object",
        "properties": {
            "currency": {"type": "string"},
            "limit": {"type": "integer", "description": "기본 20"},
        },
        "required": [],
    },
    handler=_networth_history,
))
