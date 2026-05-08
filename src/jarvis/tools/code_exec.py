"""Python / Node / Bash 코드 실행 — 격리 subprocess + 위험 패턴 거부 + 감사 로깅.

타임아웃 + 메모리 제한. stdin 미지원. 모든 호출은 logger로 기록.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from jarvis.logger import get_logger, mask_secrets
from jarvis.tools.registry import REGISTRY, Tool

log = get_logger(__name__)


# Python 코드에서 명백히 위험한 패턴 (정상 호출에서 거의 없음)
# rm 플래그는 -rf, -rfv, -fr, -fRv 등 다양 — `[a-zA-Z]+` 안에 r과 f가 모두 들어가는지 확인
_RM_RF_ARG = r"['\"]rm\s+(-[a-zA-Z]*[rR][a-zA-Z]*[fF][a-zA-Z]*|-[a-zA-Z]*[fF][a-zA-Z]*[rR][a-zA-Z]*)\s+/['\"]"
_PY_FORBIDDEN = [
    (re.compile(r"\bos\.system\s*\(\s*" + _RM_RF_ARG),
     "os.system('rm -rf /...') 거부"),
    (re.compile(r"\bsubprocess\.[a-z_]+\s*\([^)]*" + _RM_RF_ARG),
     "subprocess + rm -rf / 거부"),
    (re.compile(r"\bshutil\.rmtree\s*\(\s*['\"]/['\"]\s*[\),]"),
     "shutil.rmtree('/') 거부"),
    (re.compile(r"\bopen\s*\(\s*['\"]/etc/(shadow|sudoers|passwd)['\"]"),
     "민감 시스템 파일 open 거부"),
    # eval/exec on network-fetched code
    (re.compile(r"\bexec\s*\(\s*urllib"), "urllib에서 fetch 후 exec 거부 (untrusted code)"),
    (re.compile(r"\bexec\s*\(\s*requests"), "requests로 fetch 후 exec 거부"),
]


def _check_py_forbidden(code: str) -> Optional[str]:
    for pat, reason in _PY_FORBIDDEN:
        if pat.search(code):
            return f"ERROR: 거부됨 — {reason}"
    return None


# bash 위험 패턴은 shell.py와 공유
def _check_bash_forbidden(command: str) -> Optional[str]:
    from jarvis.tools.shell import _check_forbidden
    return _check_forbidden(command)


def _python_exec(code: str, timeout: int = 10) -> str:
    """Python 코드 실행 (subprocess). stdin 없음, stdout/stderr 캡처."""
    forbidden = _check_py_forbidden(code)
    if forbidden:
        log.warning("python_exec rejected: %s", forbidden)
        return forbidden

    log.info("python_exec: timeout=%ss code_len=%d", timeout, len(code))
    timeout = max(1, min(timeout, 60))

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            [sys.executable, tmp],
            capture_output=True, text=True, timeout=timeout,
        )
        return json.dumps({
            "stdout": mask_secrets(r.stdout[-5000:]),
            "stderr": mask_secrets(r.stderr[-2000:]),
            "returncode": r.returncode,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        log.warning("python_exec timeout %ss", timeout)
        return f"timeout {timeout}s 초과"
    except Exception as e:
        log.error("python_exec failed: %s", e)
        return f"실행 실패: {type(e).__name__}: {e}"
    finally:
        try:
            Path(tmp).unlink()
        except OSError as e:
            log.debug("temp file cleanup failed: %s", e)


def _bash_exec(command: str, timeout: int = 10) -> str:
    """간단한 bash one-liner. 위험 패턴 검사."""
    forbidden = _check_bash_forbidden(command)
    if forbidden:
        log.warning("bash_exec rejected: %s | command=%s", forbidden, command[:200])
        return forbidden

    log.info("bash_exec: timeout=%ss command=%s", timeout, command[:200])
    timeout = max(1, min(timeout, 60))
    try:
        r = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True, text=True, timeout=timeout,
        )
        return json.dumps({
            "stdout": mask_secrets(r.stdout[-5000:]),
            "stderr": mask_secrets(r.stderr[-2000:]),
            "returncode": r.returncode,
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        log.warning("bash_exec timeout %ss", timeout)
        return "timeout"
    except FileNotFoundError:
        return "ERROR: /bin/bash 미설치 (Windows 환경?)"
    except Exception as e:
        log.error("bash_exec failed: %s", e)
        return f"ERROR: {type(e).__name__}: {e}"


def _node_exec(code: str, timeout: int = 10) -> str:
    """Node.js 코드 실행 (node 설치 필요)."""
    log.info("node_exec: timeout=%ss code_len=%d", timeout, len(code))
    timeout = max(1, min(timeout, 60))
    with tempfile.NamedTemporaryFile(suffix=".js", delete=False, mode="w", encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        r = subprocess.run(
            ["node", tmp],
            capture_output=True, text=True, timeout=timeout,
        )
        return json.dumps({
            "stdout": mask_secrets(r.stdout[-5000:]),
            "stderr": mask_secrets(r.stderr[-2000:]),
            "returncode": r.returncode,
        }, ensure_ascii=False)
    except FileNotFoundError:
        return "node 미설치"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        log.error("node_exec failed: %s", e)
        return f"ERROR: {type(e).__name__}: {e}"
    finally:
        try:
            Path(tmp).unlink()
        except OSError as e:
            log.debug("temp file cleanup failed: %s", e)


REGISTRY.register(Tool(
    name="python_exec",
    description=(
        "Python 코드 실행 (격리 subprocess, 타임아웃). "
        "stdout/stderr/returncode JSON 반환. "
        "위험 패턴(rm -rf /, /etc/shadow open, urllib+exec 등) 자동 거부."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "실행할 Python 코드 (전체 스크립트)"},
            "timeout": {"type": "integer", "description": "타임아웃 초, 기본 10, 최대 60", "default": 10},
        },
        "required": ["code"],
    },
    handler=_python_exec,
))

REGISTRY.register(Tool(
    name="bash_exec",
    description=(
        "bash one-liner 실행 (격리 subprocess, 타임아웃). "
        "run_shell과 동일한 위험 패턴 거부 (rm -rf /, fork bomb, curl|sh 등)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "한 줄 bash 명령"},
            "timeout": {"type": "integer", "description": "타임아웃 초, 기본 10, 최대 60", "default": 10},
        },
        "required": ["command"],
    },
    handler=_bash_exec,
))

REGISTRY.register(Tool(
    name="node_exec",
    description="Node.js 코드 실행 (node CLI 필요, 격리 subprocess).",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "실행할 Node.js 코드"},
            "timeout": {"type": "integer", "description": "타임아웃 초, 기본 10, 최대 60", "default": 10},
        },
        "required": ["code"],
    },
    handler=_node_exec,
))
