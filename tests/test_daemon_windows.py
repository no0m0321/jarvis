"""daemon_windows.py — Task Scheduler 백엔드 mock 검증.

실제 schtasks를 호출하지 않고:
1) project_root / venv_jarvis / log_dir 경로 계산
2) install/uninstall이 schtasks 호출 형태가 올바른지 (subprocess 모킹)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from jarvis import daemon_windows


def test_project_root() -> None:
    root = daemon_windows.project_root()
    assert root.is_dir()
    assert (root / "src" / "jarvis" / "daemon_windows.py").exists()


def test_venv_jarvis_path() -> None:
    p = daemon_windows.venv_jarvis()
    # Windows venv 위치
    assert "Scripts" in str(p)
    assert p.name == "jarvis.exe"


def test_log_dir_creates(tmp_path: Path, monkeypatch) -> None:
    """log_dir()는 호출 시 디렉토리 자동 생성."""
    monkeypatch.setenv("APPDATA", str(tmp_path))
    p = daemon_windows.log_dir()
    assert p.exists()
    assert p.is_dir()
    assert "logs" in str(p)


def test_install_calls_schtasks_create(tmp_path: Path, monkeypatch) -> None:
    """install()은 schtasks /create 명령을 호출해야 한다."""
    monkeypatch.setenv("APPDATA", str(tmp_path))

    # venv_jarvis가 존재한다고 가정 (실제 파일 만들기)
    venv_dir = daemon_windows.project_root() / ".venv" / "Scripts"
    venv_dir.mkdir(parents=True, exist_ok=True)
    fake_exe = venv_dir / "jarvis.exe"
    if not fake_exe.exists():
        fake_exe.write_text("# fake")

    captured_calls = []

    def fake_run(cmd, **kwargs):
        captured_calls.append(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = "OK"
        result.stderr = ""
        return result

    with patch.object(daemon_windows.subprocess, "run", side_effect=fake_run):
        out = daemon_windows.install(["wake"], {"JARVIS_DEBUG": "1"})
        assert "OK" in out
        # /delete (cleanup) + /create 두 번 호출
        assert any("schtasks" in c[0] and "/create" in c for c in captured_calls)
        # /sc onlogon 옵션 사용 확인
        create_call = next(c for c in captured_calls if "/create" in c)
        assert "/sc" in create_call
        assert "onlogon" in create_call
        # task name JarvisWake
        assert "/tn" in create_call
        assert "JarvisWake" in create_call

    # 정리
    if fake_exe.exists():
        fake_exe.unlink()


def test_uninstall_calls_schtasks_delete() -> None:
    captured = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        result = MagicMock()
        result.returncode = 0
        result.stdout = "OK"
        result.stderr = ""
        return result

    with patch.object(daemon_windows.subprocess, "run", side_effect=fake_run):
        out = daemon_windows.uninstall()
        assert "OK" in out
        assert any("/delete" in c for c in captured)


def test_status_handles_not_installed() -> None:
    """task가 등록 안 되어 있으면 NOT_INSTALLED 반환."""
    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        result.stderr = "ERROR: The system cannot find the file specified. (does not exist)"
        return result

    with patch.object(daemon_windows.subprocess, "run", side_effect=fake_run):
        out = daemon_windows.status()
        assert out == "NOT_INSTALLED"


def test_tail_log_no_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    out = daemon_windows.tail_log("out", 10)
    assert "NO_LOG" in out


def test_tail_log_reads_recent_lines(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    log_path = daemon_windows.log_dir() / "wake.out.log"
    # 100줄 작성
    log_path.write_text("\n".join(f"line {i}" for i in range(100)) + "\n", encoding="utf-8")
    out = daemon_windows.tail_log("out", 10)
    # 마지막 10줄만
    lines = out.strip().splitlines()
    assert len(lines) == 10
    assert lines[-1] == "line 99"
    assert lines[0] == "line 90"
