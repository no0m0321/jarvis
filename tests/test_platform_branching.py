"""Platform 분기 데코레이터 동작 검증.

mac_only / windows_only 데코레이터가:
1) 해당 OS에서는 정상 통과
2) 다른 OS에서는 한국어 ERROR string 반환 (raise 없음)
3) macOS 전용 모듈 99개 핸들러가 모두 graceful 분기되는지 sample 검증
"""
from __future__ import annotations

import jarvis.platform as plat
from jarvis.tools import REGISTRY


def test_mac_only_decorator_macos_passthrough() -> None:
    """macOS에서 @mac_only는 함수를 그대로 호출."""
    if not plat.IS_MACOS:
        return
    # apple_script는 macOS native — return string만 검증 (실제 osascript 동작은 별도)
    result = REGISTRY.dispatch("apple_script", {"script": "return 1"})
    # macOS에선 정상 결과 ("1") 또는 권한 ERROR이지만 "macOS 전용 도구" 문자열은 안 나옴
    assert "macOS 전용 도구" not in result


def test_mac_only_decorator_blocks_on_non_macos() -> None:
    """Windows/Linux mock에서 @mac_only는 한국어 ERROR 반환."""
    # 임시로 IS_MACOS=False로 set 후 호출 → 복원
    orig_mac = plat.IS_MACOS
    orig_win = plat.IS_WINDOWS
    orig_plat = plat.PLATFORM
    try:
        plat.IS_MACOS = False
        plat.IS_WINDOWS = True
        plat.PLATFORM = "win32"
        # mac_only 데코레이터는 closure로 plat 모듈 변수 참조 → 동적 확인
        from jarvis.platform import mac_only

        @mac_only
        def _dummy() -> str:
            return "should not run"

        result = _dummy()
        assert "ERROR: macOS 전용 도구" in result
        assert "win32" in result
    finally:
        plat.IS_MACOS = orig_mac
        plat.IS_WINDOWS = orig_win
        plat.PLATFORM = orig_plat


def test_windows_only_decorator_blocks_on_non_windows() -> None:
    """macOS/Linux에서 @windows_only는 한국어 ERROR 반환."""
    if plat.IS_WINDOWS:
        return
    from jarvis.platform import windows_only

    @windows_only
    def _dummy() -> str:
        return "should not run"

    result = _dummy()
    assert "ERROR: Windows 전용 도구" in result


def test_macos_tools_registered_on_all_platforms() -> None:
    """macOS 전용 도구는 모든 OS에서 REGISTRY에 등록되어 있어야 (graceful 분기 정책)."""
    names = set(REGISTRY.names())
    mac_tools = {
        "apple_script", "shortcuts_run", "frontmost_app", "running_apps",
        "imessage_send", "mail_compose", "spotlight_search", "activate_app",
        "music_control", "set_volume", "reminder_add", "battery_info", "wifi_info",
        "safari_new_tab", "chrome_new_tab",
        "bluetooth_status", "dark_mode_toggle", "audio_device_list", "mic_mute",
        "caffeinate_start", "listening_ports", "defaults_read",
        "pomodoro_start", "focus_mode", "calendar_today",
        "alarm_set", "eye_break_start", "breathing_478", "meditation",
        "window_list", "window_focus", "mission_control",
    }
    missing = mac_tools - names
    assert not missing, f"macOS 도구가 등록 안 됨 (Windows 시뮬에서 graceful 분기 안 됨): {missing}"


def test_macos_tools_return_korean_error_on_non_macos() -> None:
    """macOS 전용 도구 sample을 mock Windows에서 호출 → 한국어 ERROR."""
    orig_mac = plat.IS_MACOS
    orig_win = plat.IS_WINDOWS
    orig_plat = plat.PLATFORM
    try:
        plat.IS_MACOS = False
        plat.IS_WINDOWS = True
        plat.PLATFORM = "win32"
        # sample 5개 macOS 도구 호출 → 모두 한국어 ERROR
        # 직접 핸들러 호출 (REGISTRY.dispatch는 plat 변수와 연동)
        from jarvis.tools.applescript import _apple_script
        from jarvis.tools.macos_more import _mail_compose
        from jarvis.tools.macos_extras2 import _battery_info
        from jarvis.tools.macos_system import _bluetooth_status
        from jarvis.tools.window_mgmt import _window_focus

        for handler, args, name in [
            (_apple_script, ("return 1",), "apple_script"),
            (_mail_compose, ("x@y.com",), "mail_compose"),
            (_battery_info, (), "battery_info"),
            (_bluetooth_status, (), "bluetooth_status"),
            (_window_focus, ("Safari",), "window_focus"),
        ]:
            result = handler(*args)
            assert "ERROR: macOS 전용 도구" in result, f"{name} did not return Korean ERROR: {result}"
            assert "win32" in result, f"{name} did not include platform: {result}"
    finally:
        plat.IS_MACOS = orig_mac
        plat.IS_WINDOWS = orig_win
        plat.PLATFORM = orig_plat


def test_total_tool_count_lower_bound() -> None:
    """v0.5.0에서 도구 카운트는 최소 340 이상이어야 함 (regression 방지)."""
    count = len(REGISTRY.specs())
    assert count >= 340, f"tool count regressed: {count}"


def test_no_duplicate_tool_names() -> None:
    """이름 중복 등록은 마지막 것이 이긴다 — 그래도 sanity check."""
    names = REGISTRY.names()
    # REGISTRY는 dict 기반이라 중복 자체는 없지만, names list와 specs list 길이 비교
    specs = REGISTRY.specs()
    assert len(names) == len(specs)
