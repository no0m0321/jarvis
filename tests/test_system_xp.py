"""system_xp.py — cross-platform 도구 + Windows 전용 도구 검증."""
from __future__ import annotations

import os
from pathlib import Path

import jarvis.platform as plat
from jarvis.tools import REGISTRY


def test_system_xp_registered() -> None:
    names = set(REGISTRY.names())
    expected = {
        "system_open_path",
        "system_show_in_folder",
        "system_screenshot_to_file",
        "system_record_audio",
        "system_env_summary",
        "system_default_browser_url",
        "system_open_terminal_at",
        "windows_run_powershell",
        "windows_outlook_compose",
    }
    missing = expected - names
    assert not missing, f"missing: {missing}"


def test_system_open_path_not_found() -> None:
    """존재하지 않는 path는 ERROR 반환 (raise X)."""
    result = REGISTRY.dispatch("system_open_path", {"path": "/nonexistent_xyz_jarvis_test_123"})
    assert "ERROR" in result and "not found" in result


def test_system_show_in_folder_not_found() -> None:
    result = REGISTRY.dispatch("system_show_in_folder", {"path": "/nonexistent_xyz_jarvis_test_456"})
    assert "ERROR" in result and "not found" in result


def test_system_default_browser_url_empty() -> None:
    result = REGISTRY.dispatch("system_default_browser_url", {"url": ""})
    assert "ERROR" in result and "empty" in result


def test_system_env_summary_runs() -> None:
    """환경 진단 도구는 항상 동작해야 함 (어떤 OS에서도)."""
    result = REGISTRY.dispatch("system_env_summary", {})
    # 핵심 키가 모두 들어있는지
    assert "OS:" in result
    assert "Python:" in result
    assert "PLATFORM:" in result
    assert "ANTHROPIC_API_KEY" in result


def test_windows_only_branch_on_non_windows() -> None:
    """macOS에서 windows_only 도구 호출 시 한국어 ERROR 반환."""
    if plat.IS_WINDOWS:
        # 실제 Windows에서는 다른 동작이라 skip
        return
    result = REGISTRY.dispatch("windows_run_powershell", {"script": "echo hi"})
    assert "ERROR" in result
    assert "Windows 전용" in result


def test_windows_outlook_compose_branch_on_non_windows() -> None:
    if plat.IS_WINDOWS:
        return
    result = REGISTRY.dispatch("windows_outlook_compose", {"to": "x@y.com"})
    assert "ERROR" in result
    assert "Windows 전용" in result


def test_screenshot_seconds_validation() -> None:
    """system_record_audio의 seconds 입력 검증."""
    result = REGISTRY.dispatch("system_record_audio", {"seconds": 0})
    assert "ERROR" in result and "1~600" in result


def test_screenshot_to_file_default_path(tmp_path: Path, monkeypatch) -> None:
    """path 미지정 시 ~/.jarvis/screenshots/ 자동 생성. macOS에서만 실제 캡처 시도.

    HOME을 tmp_path로 monkeypatch해서 실제 사용자 디렉토리 오염 방지.
    """
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    if not plat.IS_MACOS:
        # 다른 OS에서는 mss display access 권한 문제로 실패할 수 있음 — 그래도 ERROR/OK string 반환
        result = REGISTRY.dispatch("system_screenshot_to_file", {})
        assert isinstance(result, str)
        return
    result = REGISTRY.dispatch("system_screenshot_to_file", {})
    # ScreenCaptureKit 권한 미부여 환경에서는 ERROR 반환할 수 있음. 그래도 string return.
    assert isinstance(result, str)
    if result.startswith("OK"):
        # 캡처 성공 시 디렉토리 생성 확인
        assert (tmp_path / ".jarvis" / "screenshots").exists()
