"""개발자 도구 — git status/log, json prettify, base64, hash, port check."""
from __future__ import annotations

import base64 as _b64
import json as _json
import socket
import subprocess
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _git_status(repo: str = ".") -> str:
    """git status (porcelain + branch)."""
    p = Path(repo).expanduser()
    if not (p / ".git").exists():
        return f"NOT_GIT: {p}"
    try:
        result = subprocess.run(
            ["git", "-C", str(p), "status", "--short", "--branch"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return result.stdout.strip() or "(clean)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip() if e.stderr else e}"


def _git_log(repo: str = ".", n: int = 10) -> str:
    """최근 n개 커밋 (oneline)."""
    p = Path(repo).expanduser()
    try:
        result = subprocess.run(
            ["git", "-C", str(p), "log", f"-{n}", "--oneline", "--decorate"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return result.stdout.strip() or "(no commits)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {e.stderr.strip() if e.stderr else e}"


def _git_diff(repo: str = ".", staged: bool = False) -> str:
    """변경 사항 diff."""
    p = Path(repo).expanduser()
    cmd = ["git", "-C", str(p), "diff", "--stat"]
    if staged:
        cmd.append("--staged")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or "(no changes)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="git_status",
    description="git status (현재 브랜치 + 변경 파일).",
    input_schema={
        "type": "object",
        "properties": {"repo": {"type": "string", "description": "리포 경로, 기본 '.'"}},
        "required": [],
    },
    handler=_git_status,
))

REGISTRY.register(Tool(
    name="git_log",
    description="최근 n개 git 커밋 (oneline).",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "n": {"type": "integer", "description": "기본 10"},
        },
        "required": [],
    },
    handler=_git_log,
))

REGISTRY.register(Tool(
    name="git_diff",
    description="git diff --stat (변경 통계). staged=true면 staged만.",
    input_schema={
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "staged": {"type": "boolean"},
        },
        "required": [],
    },
    handler=_git_diff,
))


# ── JSON utils ────────────────────────────────────────────────────────────
def _json_format(text: str, indent: int = 2) -> str:
    """JSON pretty-print."""
    try:
        obj = _json.loads(text)
        return _json.dumps(obj, indent=indent, ensure_ascii=False)
    except Exception as e:
        return f"INVALID_JSON: {e}"


def _json_extract(text: str, path: str) -> str:
    """JSON 경로 추출 ('foo.bar.0.baz')."""
    try:
        obj = _json.loads(text)
    except Exception as e:
        return f"INVALID_JSON: {e}"
    for key in path.split("."):
        try:
            if key.isdigit():
                obj = obj[int(key)]
            else:
                obj = obj[key]
        except Exception:
            return f"PATH_NOT_FOUND: {path}"
    return _json.dumps(obj, ensure_ascii=False) if isinstance(obj, (dict, list)) else str(obj)


REGISTRY.register(Tool(
    name="json_format",
    description="JSON 텍스트를 pretty-print (indent 옵션).",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "indent": {"type": "integer", "description": "기본 2"},
        },
        "required": ["text"],
    },
    handler=_json_format,
))

REGISTRY.register(Tool(
    name="json_extract",
    description="JSON에서 경로로 값 추출 (예: 'foo.bar.0.baz').",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["text", "path"],
    },
    handler=_json_extract,
))


# ── Base64 ────────────────────────────────────────────────────────────────
def _base64_encode(text: str) -> str:
    return _b64.b64encode(text.encode("utf-8")).decode("ascii")


def _base64_decode(text: str) -> str:
    try:
        return _b64.b64decode(text).decode("utf-8", errors="replace")
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="base64_encode",
    description="텍스트를 base64로 인코딩.",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_base64_encode,
))

REGISTRY.register(Tool(
    name="base64_decode",
    description="base64를 텍스트로 디코딩.",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_base64_decode,
))


# ── URL encode/decode ─────────────────────────────────────────────────────
def _url_encode(text: str) -> str:
    from urllib.parse import quote

    return quote(text, safe="")


def _url_decode(text: str) -> str:
    from urllib.parse import unquote

    return unquote(text)


REGISTRY.register(Tool(
    name="url_encode",
    description="URL 인코딩 (퍼센트 이스케이프).",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_url_encode,
))

REGISTRY.register(Tool(
    name="url_decode",
    description="URL 디코딩.",
    input_schema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
    handler=_url_decode,
))


# ── Port check ────────────────────────────────────────────────────────────
def _port_check(host: str = "127.0.0.1", port: int = 80) -> str:
    """TCP 포트 열려있는지."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect((host, port))
        sock.close()
        return f"OPEN: {host}:{port}"
    except (TimeoutError, ConnectionRefusedError, OSError) as e:
        return f"CLOSED: {host}:{port} ({type(e).__name__})"


REGISTRY.register(Tool(
    name="port_check",
    description="TCP 포트 열려있는지 확인 (2초 timeout).",
    input_schema={
        "type": "object",
        "properties": {
            "host": {"type": "string", "description": "기본 127.0.0.1"},
            "port": {"type": "integer"},
        },
        "required": ["port"],
    },
    handler=_port_check,
))


# ── Math/conversion ────────────────────────────────────────────────────
def _calc(expr: str) -> str:
    """안전한 수식 평가 — 사칙연산/지수/괄호만."""
    import re

    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.%\^]+", expr):
        return "ERROR: 허용되지 않는 문자 포함 (사칙연산/지수만)"
    expr = expr.replace("^", "**")
    try:
        # eval은 위험하지만 위 regex로 산술만 통과
        result = eval(expr, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="calc",
    description="안전한 산술 계산 (사칙연산 + 지수 ^ + 괄호).",
    input_schema={
        "type": "object",
        "properties": {"expr": {"type": "string", "description": "수식 (예: '2+3*4', '10^3')"}},
        "required": ["expr"],
    },
    handler=_calc,
))
