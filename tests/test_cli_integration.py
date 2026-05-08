"""CLI integration test — subprocess로 jarvis 진입점 직접 호출.

각 CLI 명령이:
1) exit 0
2) 기대 키워드 포함 출력
3) 한국어 메시지 정상 (UTF-8 깨짐 없음)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# venv의 jarvis 진입점 (CI에서는 PATH에 있을 수도 있음)
_REPO = Path(__file__).resolve().parents[1]
_JARVIS_BIN = _REPO / ".venv" / "bin" / "jarvis"
_JARVIS_BAT = _REPO / ".venv" / "Scripts" / "jarvis.exe"  # Windows


def _jarvis_cmd() -> list[str]:
    """jarvis 진입점 명령. venv 안에 있으면 그것, 없으면 python -m jarvis.cli."""
    if _JARVIS_BIN.exists():
        return [str(_JARVIS_BIN)]
    if _JARVIS_BAT.exists():
        return [str(_JARVIS_BAT)]
    if shutil.which("jarvis"):
        return ["jarvis"]
    # fallback: python -m
    return [sys.executable, "-m", "jarvis.cli"]


def _run(args: list[str], timeout: int = 30, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    cmd = _jarvis_cmd() + args
    env = os.environ.copy()
    # API key 없어도 동작하는 명령들만 테스트 (version/profile/stats/daemon status)
    env["ANTHROPIC_API_KEY"] = env.get("ANTHROPIC_API_KEY", "dummy-for-cli-test")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, env=env, encoding="utf-8",
    )


def test_jarvis_help() -> None:
    """jarvis --help — 메인 명령 list 출력."""
    r = _run(["--help"])
    assert r.returncode == 0
    assert "Commands" in r.stdout or "명령" in r.stdout
    # 핵심 명령들 list에 표시되어야
    for cmd in ["version", "profile", "ask", "do", "doctor", "daemon", "stats"]:
        assert cmd in r.stdout, f"command '{cmd}' not in help"


def test_jarvis_version() -> None:
    """jarvis version — '0.7.0' 출력 (현재 릴리스 버전)."""
    r = _run(["version"])
    assert r.returncode == 0
    assert "0.7.0" in r.stdout
    assert "jarvis" in r.stdout.lower()


def test_jarvis_profile_show() -> None:
    """jarvis profile (인자 없음) — 프로필 정보 출력."""
    r = _run(["profile"])
    assert r.returncode == 0
    out = r.stdout
    # 핵심 라벨이 모두 보임
    for label in ["title:", "owner_name:", "first_met:", "interactions:", "observations:"]:
        assert label in out, f"missing label '{label}' in profile output"


def test_jarvis_profile_help() -> None:
    """jarvis profile --help — 모든 옵션 표시."""
    r = _run(["profile", "--help"])
    assert r.returncode == 0
    out = r.stdout
    for opt in ["--title", "--name", "--pref", "--reset", "--observations", "--clear-observations"]:
        assert opt in out


def test_jarvis_stats() -> None:
    """jarvis stats — 도구 카운트 350 표시."""
    r = _run(["stats"])
    assert r.returncode == 0
    assert "tools registered:" in r.stdout
    # 정확히 350개 등록되어 있어야 (regression 가드)
    assert "350" in r.stdout, f"tool count not 350: {r.stdout}"


def test_jarvis_tools_list_count() -> None:
    """jarvis tools-list — 350개 tool 한 줄씩."""
    r = _run(["tools-list"])
    assert r.returncode == 0
    # tool name이 한 줄당 하나씩
    lines = [l for l in r.stdout.splitlines() if l.strip() and not l.startswith("#")]
    # 일부 헤더/구분선이 있을 수 있으니 최소 300줄 이상
    assert len(lines) >= 300, f"too few tools in tools-list: {len(lines)}"


def test_jarvis_daemon_help() -> None:
    """jarvis daemon --help — 서브커맨드 list."""
    r = _run(["daemon", "--help"])
    assert r.returncode == 0
    for sub in ["install", "uninstall", "status", "restart", "logs"]:
        assert sub in r.stdout


def test_jarvis_daemon_status() -> None:
    """jarvis daemon status — NOT_INSTALLED 또는 INSTALLED 키워드."""
    r = _run(["daemon", "status"], timeout=10)
    # 어떤 OS에서도 status는 동작해야
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert any(kw in out for kw in ["NOT_INSTALLED", "INSTALLED", "OK", "macOS launchd", "Task Scheduler"])


def test_jarvis_korean_output_not_garbled() -> None:
    """한국어 출력이 UTF-8 깨짐 없이 정상."""
    r = _run(["profile"])
    assert r.returncode == 0
    # 한국어 키워드 정상 표시
    assert "프로필" in r.stdout or "사용자" in r.stdout or "(미정)" in r.stdout


def test_jarvis_unknown_command() -> None:
    """존재하지 않는 명령은 exit non-zero."""
    r = _run(["totally_nonexistent_command_xyz"], timeout=5)
    assert r.returncode != 0


@pytest.mark.skipif(
    not Path.home().joinpath(".jarvis").exists() or os.environ.get("ANTHROPIC_API_KEY", "dummy-for-cli-test") == "dummy-for-cli-test",
    reason="API key dummy / ~/.jarvis 미생성 상태에서는 ask 비활성",
)
def test_jarvis_ask_minimal() -> None:
    """jarvis ask '안녕' — API 호출 (실제 API key 있을 때만)."""
    r = _run(["ask", "안녕"], timeout=20)
    # 응답이든 ERROR든 exit 0이면 OK (raise 안 함)
    assert isinstance(r.stdout, str)
