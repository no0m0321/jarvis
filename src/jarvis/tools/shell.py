"""bash 셸 명령 도구 — 위험 패턴 거부 + 감사 로깅.

보안 정책 (v0.7.0):
- 명백히 파괴적인 패턴은 거부 (`rm -rf /`, fork bomb, mkfs, dd of=/dev/sda 등)
- 모든 호출은 logger.info로 기록 (audit trail, ~/.jarvis/jarvis.log)
- stdout/stderr는 secret 마스킹 후 반환 (logger의 secret_filter는 log에만 적용)
- timeout / cwd 검증

거부된 패턴은 항상 명확한 ERROR string 반환 (raise X — agent loop 안전).
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from jarvis.logger import get_logger, mask_secrets
from jarvis.tools.registry import REGISTRY, Tool

log = get_logger(__name__)


# 명백히 파괴적인 명령 패턴 — 정상적으로 호출될 일이 거의 없음.
# 매우 좁게 정의해서 false positive 최소화.
_FORBIDDEN_PATTERNS = [
    # rm -rf 루트 또는 홈 전체 (whitespace tolerant)
    (re.compile(r"\brm\s+(-[a-zA-Z]*[rRfF][a-zA-Z]*\s+)+(/|/\*|~|\$HOME|\$\{HOME\})\s*($|;|&|\|)"),
     "rm -rf / 또는 ~ 전체 삭제 거부"),
    # Fork bomb (bash)
    (re.compile(r":\s*\(\s*\)\s*\{[^}]*:\s*\|\s*:[^}]*\}\s*;\s*:"),
     "fork bomb 패턴 거부"),
    # mkfs (파일시스템 포맷)
    (re.compile(r"\bmkfs(\.\w+)?\s+/dev/"), "mkfs 디스크 포맷 거부"),
    # dd to block device (디스크 덮어쓰기)
    (re.compile(r"\bdd\s+.*\bof\s*=\s*/dev/(sd[a-z]|nvme|disk\d)"),
     "dd 디스크 직접 쓰기 거부"),
    # /etc/shadow 같은 민감 파일 직접 수정
    (re.compile(r">\s*/etc/(shadow|sudoers|passwd)\b"),
     "민감 시스템 파일 직접 쓰기 거부"),
    # curl|sh 패턴 (네트워크에서 임의 코드 다운로드 후 실행)
    (re.compile(r"\b(curl|wget|fetch)\s+[^|;&]+\|\s*(sh|bash|zsh|fish)\b"),
     "curl|sh (네트워크에서 임의 스크립트 실행) 거부 — 별도 다운로드 후 검토 권장"),
]


def _check_forbidden(command: str) -> Optional[str]:
    """위험 패턴 감지. 매치되면 한국어 ERROR string 반환, 안전하면 None."""
    if not command or not command.strip():
        return "ERROR: 빈 명령"
    for pattern, reason in _FORBIDDEN_PATTERNS:
        if pattern.search(command):
            return f"ERROR: 거부됨 — {reason}"
    return None


def _run_shell(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    forbidden = _check_forbidden(command)
    if forbidden:
        log.warning("run_shell rejected: %s | command=%s", forbidden, command[:200])
        return forbidden

    log.info("run_shell: cwd=%s timeout=%ss command=%s", cwd, timeout, command[:200])
    try:
        result = subprocess.run(
            ["bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=max(1, min(timeout, 600)),
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        log.warning("run_shell timeout: %ss for %s", timeout, command[:100])
        return f"TIMEOUT (>{timeout}s)"
    except FileNotFoundError:
        return "ERROR: bash 미설치 (Windows 환경에서는 windows_run_powershell 사용)"
    except Exception as e:
        log.error("run_shell unexpected error: %s", e)
        return f"ERROR: {type(e).__name__}: {e}"

    parts = [f"exit_code={result.returncode}"]
    if result.stdout:
        parts.append(f"--- stdout ---\n{mask_secrets(result.stdout.rstrip())}")
    if result.stderr:
        parts.append(f"--- stderr ---\n{mask_secrets(result.stderr.rstrip())}")
    return "\n".join(parts) if len(parts) > 1 else parts[0]


REGISTRY.register(Tool(
    name="run_shell",
    description=(
        "bash 셸 명령 실행 (macOS/Linux). exit_code + stdout + stderr 반환. "
        "위험 패턴(rm -rf /, fork bomb, mkfs, dd of=/dev/sda, curl|sh 등)은 자동 거부. "
        "Windows에서는 windows_run_powershell 사용."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "실행할 bash 명령 (한 줄)"},
            "timeout": {"type": "integer", "description": "타임아웃 초, 기본 30, 최대 600"},
            "cwd": {"type": "string", "description": "작업 디렉토리 (절대경로, 옵션)"},
        },
        "required": ["command"],
    },
    handler=_run_shell,
))
