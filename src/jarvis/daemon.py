from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

LABEL = "com.swxvno.jarvis.wake"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs"
LOG_OUT = LOG_DIR / "jarvis-wake.out.log"
LOG_ERR = LOG_DIR / "jarvis-wake.err.log"


def project_root() -> Path:
    """jarvis 프로젝트 루트 (.../src/jarvis/daemon.py → ../../..)."""
    return Path(__file__).resolve().parents[2]


def venv_jarvis() -> Path:
    """venv 안의 jarvis 진입점 절대경로."""
    return project_root() / ".venv" / "bin" / "jarvis"


def render_plist(
    args: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> str:
    """plist XML 생성. args는 jarvis 뒤에 붙는 인자 (기본: ['wake'])."""
    args = list(args or ["wake"])
    program_args = [str(venv_jarvis()), *args]
    args_xml = "\n".join(f"        <string>{a}</string>" for a in program_args)

    base_env: Dict[str, str] = {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
    if env_vars:
        base_env.update(env_vars)
    env_xml = "\n".join(
        f"        <key>{k}</key>\n        <string>{v}</string>"
        for k, v in base_env.items()
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>
    <key>WorkingDirectory</key>
    <string>{project_root()}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>30</integer>
    <key>StandardOutPath</key>
    <string>{LOG_OUT}</string>
    <key>StandardErrorPath</key>
    <string>{LOG_ERR}</string>
    <key>EnvironmentVariables</key>
    <dict>
{env_xml}
    </dict>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""


def _gui_target() -> str:
    return f"gui/{os.getuid()}"


def _bootout() -> None:
    """이미 로드돼 있으면 unload (실패 무시)."""
    subprocess.run(
        ["launchctl", "bootout", _gui_target(), str(PLIST_PATH)],
        capture_output=True,
    )


def install(
    args: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
) -> str:
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(render_plist(args, env_vars))
    _bootout()
    result = subprocess.run(
        ["launchctl", "bootstrap", _gui_target(), str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"FAILED: {result.stderr.strip() or result.stdout.strip()}"
    return f"OK: loaded {LABEL}\n  plist: {PLIST_PATH}\n  logs:  {LOG_OUT}"


def uninstall() -> str:
    if not PLIST_PATH.exists():
        return "NOT_INSTALLED"
    _bootout()
    PLIST_PATH.unlink()
    return f"OK: removed {LABEL} (logs preserved at {LOG_DIR})"


def restart() -> str:
    if not PLIST_PATH.exists():
        return "NOT_INSTALLED — run `jarvis daemon install` first"
    _bootout()
    result = subprocess.run(
        ["launchctl", "bootstrap", _gui_target(), str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"FAILED: {result.stderr.strip() or result.stdout.strip()}"
    return f"OK: restarted {LABEL}"


def status() -> str:
    if not PLIST_PATH.exists():
        return "NOT_INSTALLED"
    result = subprocess.run(
        ["launchctl", "print", f"{_gui_target()}/{LABEL}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "INSTALLED_BUT_NOT_LOADED"
    keep = ("state =", "pid =", "last exit", "program =", "run interval", "throttle")
    interesting = [
        line.strip() for line in result.stdout.splitlines()
        if any(kw in line for kw in keep)
    ]
    return "\n".join(interesting[:10]) if interesting else "LOADED"


def tail_log(stream: str = "out", lines: int = 50) -> str:
    log_path = LOG_OUT if stream == "out" else LOG_ERR
    if not log_path.exists():
        return f"NO_LOG: {log_path}"
    result = subprocess.run(
        ["tail", "-n", str(lines), str(log_path)],
        capture_output=True,
        text=True,
    )
    return result.stdout or "(empty)"
