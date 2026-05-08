"""Windows wake daemon — Task Scheduler 백엔드.

macOS의 launchd 플러그인 daemon.py와 의미적으로 동일한 install/uninstall/restart/status/tail_log 제공.
사용자가 로그인할 때마다 자동 실행되는 schtasks 작업을 등록한다 (`/sc onlogon`).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

TASK_NAME = "JarvisWake"


def project_root() -> Path:
    """jarvis 프로젝트 루트 (.../src/jarvis/daemon_windows.py → ../../..)."""
    return Path(__file__).resolve().parents[2]


def venv_jarvis() -> Path:
    """venv 안의 jarvis.exe 절대경로 (Windows)."""
    return project_root() / ".venv" / "Scripts" / "jarvis.exe"


def log_dir() -> Path:
    """%APPDATA%\\jarvis\\logs (없으면 ~/.jarvis/logs)."""
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) / "jarvis" if appdata else Path.home() / ".jarvis"
    p = base / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _run_schtasks(args: List[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["schtasks", *args],
        capture_output=True, text=True, timeout=timeout,
    )


def install(
    args: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> str:
    """schtasks /create로 wake daemon 등록 (사용자 로그인 시 자동 실행).

    env_vars는 .bat 래퍼 안에서 set으로 적용된다.
    """
    cmd_args = list(args or ["wake"])
    jarvis_exe = venv_jarvis()
    if not jarvis_exe.exists():
        return f"FAILED: jarvis.exe 없음 — {jarvis_exe} (먼저 install.ps1 실행)"

    # .bat 래퍼: env vars + jarvis.exe wake
    bat_dir = log_dir().parent  # %APPDATA%\jarvis\
    bat_path = bat_dir / "wake.bat"
    out_log = log_dir() / "wake.out.log"
    err_log = log_dir() / "wake.err.log"

    env_lines = []
    if env_vars:
        for k, v in env_vars.items():
            # .bat escape: %는 %%로
            safe_v = v.replace("%", "%%").replace('"', '\\"')
            env_lines.append(f'set "{k}={safe_v}"')

    quoted_args = " ".join(f'"{a}"' for a in cmd_args)
    bat_content = (
        "@echo off\r\n"
        + "\r\n".join(env_lines) + ("\r\n" if env_lines else "")
        + f'cd /d "{project_root()}"\r\n'
        + f'"{jarvis_exe}" {quoted_args} 1>>"{out_log}" 2>>"{err_log}"\r\n'
    )
    bat_path.parent.mkdir(parents=True, exist_ok=True)
    bat_path.write_text(bat_content, encoding="ascii")

    # 기존 task 제거 (있으면)
    _run_schtasks(["/delete", "/tn", TASK_NAME, "/f"])

    # 새로 등록 — 사용자 로그인 시 자동 실행
    result = _run_schtasks([
        "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{bat_path}"',
        "/sc", "onlogon",
        "/rl", "limited",
        "/f",
    ])
    if result.returncode != 0:
        return f"FAILED: {(result.stderr or result.stdout).strip()}"
    return (
        f"OK: registered {TASK_NAME} (Task Scheduler)\n"
        f"  bat:  {bat_path}\n"
        f"  logs: {out_log}, {err_log}"
    )


def uninstall() -> str:
    result = _run_schtasks(["/delete", "/tn", TASK_NAME, "/f"])
    if result.returncode == 0:
        return f"OK: removed {TASK_NAME} (logs preserved at {log_dir()})"
    if "not exist" in (result.stderr + result.stdout).lower():
        return "NOT_INSTALLED"
    return f"FAILED: {(result.stderr or result.stdout).strip()}"


def restart() -> str:
    """schtasks /end + /run."""
    end_result = _run_schtasks(["/end", "/tn", TASK_NAME])
    if end_result.returncode != 0 and "not exist" in (end_result.stderr + end_result.stdout).lower():
        return "NOT_INSTALLED — run `jarvis daemon install` first"
    run_result = _run_schtasks(["/run", "/tn", TASK_NAME])
    if run_result.returncode != 0:
        return f"FAILED: {(run_result.stderr or run_result.stdout).strip()}"
    return f"OK: restarted {TASK_NAME}"


def status() -> str:
    result = _run_schtasks(["/query", "/tn", TASK_NAME, "/v", "/fo", "list"])
    if result.returncode != 0:
        if "not exist" in (result.stderr + result.stdout).lower():
            return "NOT_INSTALLED"
        return f"FAILED: {(result.stderr or result.stdout).strip()}"
    keep = ("Status:", "Last Run", "Last Result", "Next Run", "Schedule:", "Task To Run:")
    interesting = [
        line.strip() for line in result.stdout.splitlines()
        if any(line.lstrip().startswith(k) for k in keep)
    ]
    return "\n".join(interesting[:12]) if interesting else "INSTALLED"


def tail_log(stream: str = "out", lines: int = 50) -> str:
    log_path = log_dir() / ("wake.out.log" if stream == "out" else "wake.err.log")
    if not log_path.exists():
        return f"NO_LOG: {log_path}"
    try:
        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        tail = "".join(all_lines[-lines:])
        return tail or "(empty)"
    except Exception as e:
        return f"ERROR: {e}"
