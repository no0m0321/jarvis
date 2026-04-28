"""단위 변환 도구 — 온도, 길이, 무게, 시간대, 텍스트 변환."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from jarvis.tools.registry import REGISTRY, Tool


def _temp_convert(value: float, from_unit: str, to_unit: str) -> str:
    """온도 변환 C/F/K."""
    f = from_unit.upper()
    t = to_unit.upper()
    # to celsius first
    if f == "C":
        c = value
    elif f == "F":
        c = (value - 32) * 5 / 9
    elif f == "K":
        c = value - 273.15
    else:
        return f"INVALID: {f}"
    # from celsius
    if t == "C":
        return f"{c:.2f}°C"
    if t == "F":
        return f"{c * 9 / 5 + 32:.2f}°F"
    if t == "K":
        return f"{c + 273.15:.2f}K"
    return f"INVALID: {t}"


REGISTRY.register(Tool(
    name="temp_convert",
    description="온도 변환 C/F/K (예: value=100, from='C', to='F').",
    input_schema={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from_unit": {"type": "string", "description": "C|F|K"},
            "to_unit": {"type": "string", "description": "C|F|K"},
        },
        "required": ["value", "from_unit", "to_unit"],
    },
    handler=_temp_convert,
))


def _length_convert(value: float, from_unit: str, to_unit: str) -> str:
    """길이 변환: m/cm/km/in/ft/mi."""
    # to meters
    to_m = {
        "m": 1, "cm": 0.01, "mm": 0.001, "km": 1000,
        "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
    }
    f, t = from_unit.lower(), to_unit.lower()
    if f not in to_m or t not in to_m:
        return f"INVALID: 사용 가능한 단위 — {list(to_m)}"
    meters = value * to_m[f]
    return f"{meters / to_m[t]:.4f} {t}"


REGISTRY.register(Tool(
    name="length_convert",
    description="길이 변환 (m/cm/mm/km/in/ft/yd/mi).",
    input_schema={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from_unit": {"type": "string"},
            "to_unit": {"type": "string"},
        },
        "required": ["value", "from_unit", "to_unit"],
    },
    handler=_length_convert,
))


def _weight_convert(value: float, from_unit: str, to_unit: str) -> str:
    """무게 변환: g/kg/oz/lb."""
    to_g = {"g": 1, "kg": 1000, "mg": 0.001, "oz": 28.3495, "lb": 453.592}
    f, t = from_unit.lower(), to_unit.lower()
    if f not in to_g or t not in to_g:
        return f"INVALID: {list(to_g)}"
    return f"{value * to_g[f] / to_g[t]:.4f} {t}"


REGISTRY.register(Tool(
    name="weight_convert",
    description="무게 변환 (g/kg/mg/oz/lb).",
    input_schema={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from_unit": {"type": "string"},
            "to_unit": {"type": "string"},
        },
        "required": ["value", "from_unit", "to_unit"],
    },
    handler=_weight_convert,
))


def _slugify(text: str, sep: str = "-") -> str:
    """텍스트 → URL-safe slug."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s가-힣-]", "", text)
    text = re.sub(r"[\s_]+", sep, text)
    return text.strip(sep)


REGISTRY.register(Tool(
    name="slugify",
    description="텍스트를 URL-safe slug으로 변환 (kebab-case 기본).",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "sep": {"type": "string", "description": "구분자, 기본 '-'"},
        },
        "required": ["text"],
    },
    handler=_slugify,
))


def _timezone_convert(iso: str, from_tz: str = "Asia/Seoul", to_tz: str = "UTC") -> str:
    """ISO 시각을 다른 timezone으로 변환."""
    try:
        from zoneinfo import ZoneInfo

        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(from_tz))
        else:
            dt = dt.astimezone(ZoneInfo(from_tz))
        converted = dt.astimezone(ZoneInfo(to_tz))
        return converted.strftime("%Y-%m-%d %H:%M:%S %Z")
    except ImportError:
        return "ERROR: zoneinfo 미지원 (Python 3.9+ + tzdata 필요)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="timezone_convert",
    description="시각을 다른 timezone으로 변환 (예: 'Asia/Seoul' → 'America/New_York').",
    input_schema={
        "type": "object",
        "properties": {
            "iso": {"type": "string"},
            "from_tz": {"type": "string", "description": "기본 Asia/Seoul"},
            "to_tz": {"type": "string", "description": "기본 UTC"},
        },
        "required": ["iso"],
    },
    handler=_timezone_convert,
))


def _regex_test(pattern: str, text: str, flags: str = "") -> str:
    """정규식 매칭 테스트. flags: i (ignorecase), m (multiline), s (dotall)."""
    f = 0
    if "i" in flags.lower():
        f |= re.IGNORECASE
    if "m" in flags.lower():
        f |= re.MULTILINE
    if "s" in flags.lower():
        f |= re.DOTALL
    try:
        matches = re.findall(pattern, text, f)
        if not matches:
            return "(no matches)"
        return f"{len(matches)} match(es):\n" + "\n".join(str(m)[:200] for m in matches[:20])
    except re.error as e:
        return f"INVALID_REGEX: {e}"


REGISTRY.register(Tool(
    name="regex_test",
    description="정규식 패턴 테스트. flags: 'i' (ignorecase), 'm' (multiline), 's' (dotall).",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "text": {"type": "string"},
            "flags": {"type": "string"},
        },
        "required": ["pattern", "text"],
    },
    handler=_regex_test,
))


def _now_utc() -> str:
    """UTC 현재 시각 (ISO + Unix)."""
    dt = datetime.now(timezone.utc)
    return f"{dt.isoformat()}\nunix: {int(dt.timestamp())}"


REGISTRY.register(Tool(
    name="now_utc",
    description="UTC 현재 시각 (ISO 8601 + unix timestamp).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_now_utc,
))
