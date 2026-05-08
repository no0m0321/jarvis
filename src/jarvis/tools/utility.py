"""유틸리티 도구 — QR / password / hash / encrypt / regex / color / unit conversion."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import string
import uuid
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _qr_generate(text: str, output: str = "") -> str:
    """QR 코드 PNG 생성 — qrcode 패키지 또는 macOS 폴백 없음."""
    try:
        import qrcode  # type: ignore
    except ImportError:
        return "qrcode 미설치 — pip install qrcode[pil]"
    out = Path(output).expanduser() if output else Path.home() / "Desktop" / f"qr_{uuid.uuid4().hex[:8]}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        img = qrcode.make(text)
        img.save(out)
        return f"OK: {out}"
    except Exception as e:
        return f"실패: {e}"


def _password_generate(length: int = 16, symbols: bool = True) -> str:
    """안전한 random password (secrets.choice). length 12-64 권장."""
    length = max(8, min(length, 128))
    alphabet = string.ascii_letters + string.digits
    if symbols:
        alphabet += "!@#$%^&*()-_=+[]{}"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _password_strength(pw: str) -> str:
    """패스워드 강도 평가."""
    score = 0
    if len(pw) >= 8:
        score += 1
    if len(pw) >= 12:
        score += 1
    if len(pw) >= 16:
        score += 1
    if re.search(r"[a-z]", pw):
        score += 1
    if re.search(r"[A-Z]", pw):
        score += 1
    if re.search(r"\d", pw):
        score += 1
    if re.search(r"[^a-zA-Z0-9]", pw):
        score += 1
    label = ["매우 약함", "약함", "보통", "보통", "양호", "강함", "매우 강함", "최고"][min(score, 7)]
    return json.dumps({"score": score, "max": 7, "label": label, "length": len(pw)}, ensure_ascii=False)


def _hash_text(text: str, algo: str = "sha256") -> str:
    """텍스트 해시. algo: md5/sha1/sha256/sha512."""
    if algo not in {"md5", "sha1", "sha256", "sha512", "blake2b"}:
        return f"지원: md5/sha1/sha256/sha512/blake2b"
    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def _hmac_sign(text: str, secret: str, algo: str = "sha256") -> str:
    """HMAC 서명 (key + 메시지 → hex)."""
    return hmac.new(secret.encode(), text.encode(), getattr(hashlib, algo)).hexdigest()


def _uuid_v4() -> str:
    return str(uuid.uuid4())


def _regex_match(pattern: str, text: str, flags: str = "") -> str:
    """regex 모든 매치 반환. flags: 'i'(ignorecase) / 'm'(multiline) / 's'(dotall)."""
    f = 0
    if "i" in flags.lower():
        f |= re.I
    if "m" in flags.lower():
        f |= re.M
    if "s" in flags.lower():
        f |= re.S
    try:
        matches = re.findall(pattern, text, f)
        return json.dumps(matches, ensure_ascii=False)
    except re.error as e:
        return f"패턴 오류: {e}"


def _regex_replace(pattern: str, replacement: str, text: str, flags: str = "") -> str:
    """regex 치환."""
    f = 0
    if "i" in flags.lower():
        f |= re.I
    if "m" in flags.lower():
        f |= re.M
    try:
        return re.sub(pattern, replacement, text, flags=f)
    except re.error as e:
        return f"패턴 오류: {e}"


def _color_convert(value: str) -> str:
    """색상 변환 — hex ↔ rgb. '#ff0000' → rgb(255,0,0) 또는 'rgb(255,0,0)' → '#ff0000'."""
    v = value.strip()
    if v.startswith("#"):
        v = v.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        if len(v) != 6:
            return "잘못된 hex"
        try:
            r, g, b = int(v[:2], 16), int(v[2:4], 16), int(v[4:], 16)
            return json.dumps({"hex": f"#{v}", "rgb": f"rgb({r}, {g}, {b})", "r": r, "g": g, "b": b}, ensure_ascii=False)
        except ValueError:
            return "잘못된 hex"
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", v)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return json.dumps({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": f"rgb({r}, {g}, {b})", "r": r, "g": g, "b": b}, ensure_ascii=False)
    return "지원: '#rrggbb' 또는 'rgb(r,g,b)'"


def _unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    """단위 변환 — 길이/무게/온도/시간."""
    # 정규화
    f, t = from_unit.lower(), to_unit.lower()
    # 길이 (m 기준)
    length = {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
    weight = {"mg": 0.001, "g": 1, "kg": 1000, "ton": 1e6, "oz": 28.3495, "lb": 453.592}
    time_s = {"ms": 0.001, "s": 1, "min": 60, "h": 3600, "d": 86400, "w": 604800}
    # 온도
    temps = {"c", "f", "k"}
    if f in temps and t in temps:
        # to celsius first
        if f == "c":
            c = value
        elif f == "f":
            c = (value - 32) * 5 / 9
        else:
            c = value - 273.15
        if t == "c":
            return f"{round(c, 4)} °C"
        if t == "f":
            return f"{round(c * 9 / 5 + 32, 4)} °F"
        return f"{round(c + 273.15, 4)} K"
    for table in (length, weight, time_s):
        if f in table and t in table:
            return f"{round(value * table[f] / table[t], 6)} {to_unit}"
    return f"지원 안 함: {from_unit} → {to_unit}"


def _word_count(text: str) -> str:
    """텍스트 통계 — 문자/단어/줄 수."""
    return json.dumps({
        "chars": len(text),
        "chars_no_space": len(text.replace(" ", "").replace("\n", "")),
        "words": len(text.split()),
        "lines": text.count("\n") + 1,
    }, ensure_ascii=False)


def _slug(text: str) -> str:
    """URL slug — 영문 소문자/하이픈."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9가-힣\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return re.sub(r"-+", "-", s)


def _base64_url_encode(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def _base64_url_decode(text: str) -> str:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad).decode()


REGISTRY.register(Tool(
    name="qr_generate",
    description="[DEPRECATED v0.7.0] QR 코드 PNG 생성. 'qrcode' 도구 사용 권장 (동일 기능). 호환성 alias.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "QR로 인코딩할 텍스트/URL"},
            "output": {"type": "string", "description": "PNG 파일 경로 (옵션, 비우면 ~/Desktop/qr_*.png)", "default": ""},
        },
        "required": ["text"],
    },
    handler=_qr_generate,
))
REGISTRY.register(Tool(
    name="password_generate",
    description="[DEPRECATED v0.7.0] 안전한 random password. 'password_gen' 도구 사용 권장 (동일 기능). 호환성 alias. length 8-128.",
    input_schema={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "description": "비밀번호 길이 (8-128)", "default": 16},
            "symbols": {"type": "boolean", "description": "특수기호 포함 여부", "default": True},
        },
    },
    handler=_password_generate,
))
REGISTRY.register(Tool(
    name="password_strength",
    description="패스워드 강도 평가 (0-7).",
    input_schema={"type": "object", "properties": {"pw": {"type": "string"}}, "required": ["pw"]},
    handler=_password_strength,
))
REGISTRY.register(Tool(
    name="hash_text",
    description="텍스트 해시. algo: md5/sha1/sha256/sha512/blake2b.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}, "algo": {"type": "string", "default": "sha256"}},
        "required": ["text"],
    },
    handler=_hash_text,
))
REGISTRY.register(Tool(
    name="hmac_sign",
    description="HMAC 서명. text + secret → hex digest.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "secret": {"type": "string"},
            "algo": {"type": "string", "default": "sha256"},
        },
        "required": ["text", "secret"],
    },
    handler=_hmac_sign,
))
REGISTRY.register(Tool(
    name="uuid_v4",
    description="UUID v4 생성.",
    input_schema={"type": "object", "properties": {}},
    handler=_uuid_v4,
))
REGISTRY.register(Tool(
    name="regex_match",
    description="regex 매치 — 모든 결과 list 반환. flags='i'/'m'/'s'.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "text": {"type": "string"},
            "flags": {"type": "string", "default": ""},
        },
        "required": ["pattern", "text"],
    },
    handler=_regex_match,
))
REGISTRY.register(Tool(
    name="regex_replace",
    description="regex 치환.",
    input_schema={
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "replacement": {"type": "string"},
            "text": {"type": "string"},
            "flags": {"type": "string", "default": ""},
        },
        "required": ["pattern", "replacement", "text"],
    },
    handler=_regex_replace,
))
REGISTRY.register(Tool(
    name="color_convert",
    description="색상 hex ↔ rgb 변환. '#ff0000' 또는 'rgb(255,0,0)'.",
    input_schema={"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"]},
    handler=_color_convert,
))
REGISTRY.register(Tool(
    name="unit_convert",
    description="단위 변환 — 길이(mm/cm/m/km/in/ft/yd/mi) / 무게(mg/g/kg/ton/oz/lb) / 시간(ms/s/min/h/d/w) / 온도(c/f/k).",
    input_schema={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from_unit": {"type": "string"},
            "to_unit": {"type": "string"},
        },
        "required": ["value", "from_unit", "to_unit"],
    },
    handler=_unit_convert,
))
REGISTRY.register(Tool(
    name="word_count",
    description="텍스트 통계 — 문자/단어/줄 수.",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_word_count,
))
REGISTRY.register(Tool(
    name="slug",
    description="[DEPRECATED v0.7.0] URL slug 생성. 'slugify' 도구 사용 권장. 호환성 alias.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "slug로 변환할 텍스트"}},
        "required": ["text"],
    },
    handler=_slug,
))
REGISTRY.register(Tool(
    name="base64_url_encode",
    description="URL-safe base64 encode (padding 제거).",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_base64_url_encode,
))
REGISTRY.register(Tool(
    name="base64_url_decode",
    description="URL-safe base64 decode.",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_base64_url_decode,
))
