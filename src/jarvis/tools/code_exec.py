"""Python REPL 실행 — 격리된 subprocess. 위험: 사용자 동의 후 사용.

타임아웃 + 메모리 제한. stdin 미지원.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _python_exec(code: str, timeout: int = 10) -> str:
    """Python 코드 실행 (subprocess). stdin 없음, stdout/stderr 캡처."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=max(1, min(timeout, 60)),
        )
        return json.dumps({
            "stdout": r.stdout[-5000:],
            "stderr": r.stderr[-2000:],
            "returncode": r.returncode,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return f"timeout {timeout}s 초과"
    except Exception as e:
        return f"실행 실패: {e}"
    finally:
        try:
            Path(tmp).unlink()
        except Exception:
            pass


def _bash_exec(command: str, timeout: int = 10) -> str:
    """간단한 bash one-liner. shell.py의 run_shell과 동일하나 격리 강화."""
    try:
        r = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True, text=True, timeout=max(1, min(timeout, 60)),
        )
        return json.dumps({
            "stdout": r.stdout[-5000:],
            "stderr": r.stderr[-2000:],
            "returncode": r.returncode,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return f"timeout {timeout}s 초과"


def _node_exec(code: str, timeout: int = 10) -> str:
    """Node.js 코드 실행 (node 설치 필요)."""
    with tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            ["node", tmp],
            capture_output=True, text=True, timeout=max(1, min(timeout, 60)),
        )
        return json.dumps({
            "stdout": r.stdout[-5000:],
            "stderr": r.stderr[-2000:],
            "returncode": r.returncode,
        }, ensure_ascii=False)
    except FileNotFoundError:
        return "node 미설치"
    except subprocess.TimeoutExpired:
        return f"timeout"
    finally:
        try:
            Path(tmp).unlink()
        except Exception:
            pass


REGISTRY.register(Tool(
    name="python_exec",
    description="Python 코드 실행 (격리 subprocess, 타임아웃). stdout/stderr/returncode JSON.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer", "default": 10},
        },
        "required": ["code"],
    },
    handler=_python_exec,
))

REGISTRY.register(Tool(
    name="bash_exec",
    description="bash one-liner 실행 (격리 subprocess, 타임아웃).",
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 10},
        },
        "required": ["command"],
    },
    handler=_bash_exec,
))

REGISTRY.register(Tool(
    name="node_exec",
    description="Node.js 코드 실행 (node CLI 필요).",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "timeout": {"type": "integer", "default": 10},
        },
        "required": ["code"],
    },
    handler=_node_exec,
))
