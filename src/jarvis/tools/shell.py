from __future__ import annotations

import subprocess
from typing import Optional

from jarvis.tools.registry import REGISTRY, Tool


def _run_shell(command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
    try:
        result = subprocess.run(
            ["bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return f"TIMEOUT (>{timeout}s)"

    parts = [f"exit_code={result.returncode}"]
    if result.stdout:
        parts.append(f"--- stdout ---\n{result.stdout.rstrip()}")
    if result.stderr:
        parts.append(f"--- stderr ---\n{result.stderr.rstrip()}")
    return "\n".join(parts) if len(parts) > 1 else parts[0]


REGISTRY.register(Tool(
    name="run_shell",
    description="bash 셸 명령을 macOS에서 실행. 결과는 exit_code + stdout + stderr.",
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "실행할 bash 명령"},
            "timeout": {"type": "integer", "description": "타임아웃 초, 기본 30"},
            "cwd": {"type": "string", "description": "작업 디렉토리 (절대경로)"},
        },
        "required": ["command"],
    },
    handler=_run_shell,
))
