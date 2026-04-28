"""생성기 — UUID, password, lorem, color, date math."""
from __future__ import annotations

import random
import secrets
import string
import uuid
from datetime import datetime, timedelta

from jarvis.tools.registry import REGISTRY, Tool


def _uuid_gen(version: int = 4, count: int = 1) -> str:
    """UUID 생성 (version 4 기본)."""
    if version not in (1, 4):
        return "ERROR: version must be 1 or 4"
    fn = uuid.uuid1 if version == 1 else uuid.uuid4
    return "\n".join(str(fn()) for _ in range(min(count, 50)))


REGISTRY.register(Tool(
    name="uuid_gen",
    description="UUID 생성 (v1 또는 v4, count 만큼).",
    input_schema={
        "type": "object",
        "properties": {
            "version": {"type": "integer", "description": "1 or 4 (기본 4)"},
            "count": {"type": "integer", "description": "기본 1, 최대 50"},
        },
        "required": [],
    },
    handler=_uuid_gen,
))


def _password_gen(length: int = 16, symbols: bool = True, digits: bool = True) -> str:
    """안전한 랜덤 패스워드 (secrets 모듈 사용)."""
    chars = string.ascii_letters
    if digits:
        chars += string.digits
    if symbols:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    length = max(4, min(128, length))
    return "".join(secrets.choice(chars) for _ in range(length))


REGISTRY.register(Tool(
    name="password_gen",
    description="안전한 랜덤 패스워드 (secrets 기반). symbols/digits 옵션.",
    input_schema={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "description": "기본 16"},
            "symbols": {"type": "boolean"},
            "digits": {"type": "boolean"},
        },
        "required": [],
    },
    handler=_password_gen,
))


def _random_int(min_val: int = 0, max_val: int = 100, count: int = 1) -> str:
    """랜덤 정수."""
    return ", ".join(str(random.randint(min_val, max_val)) for _ in range(min(count, 100)))


REGISTRY.register(Tool(
    name="random_int",
    description="랜덤 정수 (min~max 범위, count 개).",
    input_schema={
        "type": "object",
        "properties": {
            "min_val": {"type": "integer", "description": "기본 0"},
            "max_val": {"type": "integer", "description": "기본 100"},
            "count": {"type": "integer", "description": "기본 1"},
        },
        "required": [],
    },
    handler=_random_int,
))


def _date_add(iso: str = "", days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    """ISO 날짜에 시간 더하기. iso 비우면 현재."""
    base = datetime.fromisoformat(iso) if iso else datetime.now()
    result = base + timedelta(days=days, hours=hours, minutes=minutes)
    return result.strftime("%Y-%m-%d %H:%M:%S")


REGISTRY.register(Tool(
    name="date_add",
    description="ISO 날짜에 days/hours/minutes 더하기 (iso 비우면 현재 시각).",
    input_schema={
        "type": "object",
        "properties": {
            "iso": {"type": "string"},
            "days": {"type": "integer"},
            "hours": {"type": "integer"},
            "minutes": {"type": "integer"},
        },
        "required": [],
    },
    handler=_date_add,
))


def _date_diff(iso1: str, iso2: str = "") -> str:
    """두 ISO 날짜 차이 (초/분/시/일)."""
    d1 = datetime.fromisoformat(iso1)
    d2 = datetime.fromisoformat(iso2) if iso2 else datetime.now()
    delta = abs((d2 - d1).total_seconds())
    return (f"days: {delta / 86400:.2f}\n"
            f"hours: {delta / 3600:.2f}\n"
            f"minutes: {delta / 60:.1f}\n"
            f"seconds: {int(delta)}")


REGISTRY.register(Tool(
    name="date_diff",
    description="두 ISO 날짜 차이 (iso2 비우면 현재 시각과의 차이).",
    input_schema={
        "type": "object",
        "properties": {
            "iso1": {"type": "string"},
            "iso2": {"type": "string"},
        },
        "required": ["iso1"],
    },
    handler=_date_diff,
))


def _color_convert(value: str) -> str:
    """색상 변환 (hex → RGB, RGB → hex)."""
    s = value.strip().lstrip("#")
    if len(s) == 6 and all(c in "0123456789abcdefABCDEF" for c in s):
        # hex → rgb
        r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        return f"#{s.upper()}\nrgb({r}, {g}, {b})\nrgb {r/255:.3f} {g/255:.3f} {b/255:.3f}"
    if "," in s:
        # rgb → hex
        try:
            parts = [int(p.strip()) for p in s.replace("rgb", "").replace("(", "").replace(")", "").split(",")]
            r, g, b = parts[:3]
            return f"#{r:02X}{g:02X}{b:02X}\nrgb({r}, {g}, {b})"
        except Exception:
            return f"INVALID: cannot parse '{value}'"
    return f"INVALID: '{value}' (사용: '#FF7B00' 또는 '255,123,0')"


REGISTRY.register(Tool(
    name="color_convert",
    description="색상 hex ↔ RGB 변환 ('#FF7B00' 또는 '255,123,0').",
    input_schema={
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    },
    handler=_color_convert,
))


def _qrcode(text: str, output: str = "") -> str:
    """QR 코드 생성 (qrencode CLI 필요. 미설치면 텍스트 안내)."""
    import subprocess
    from pathlib import Path
    import tempfile

    if subprocess.run(["which", "qrencode"], capture_output=True).returncode != 0:
        return ("WARN: qrencode 미설치. `brew install qrencode` 필요. "
                "또는 https://qrserver.com 같은 web 서비스 사용.")
    if not output:
        output = str(Path(tempfile.gettempdir()) / "qr.png")
    try:
        subprocess.run(
            ["qrencode", "-o", output, "-s", "8", text],
            timeout=10, check=True,
        )
        return f"OK: QR saved to {output}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="qrcode",
    description="QR 코드 생성 (qrencode CLI 필요).",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "output": {"type": "string", "description": "PNG 경로, 비우면 임시"},
        },
        "required": ["text"],
    },
    handler=_qrcode,
))
