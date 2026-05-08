"""windows_extras / linux_extras / ai_helpers 모듈 검증.

각 모듈의 도구가:
1) REGISTRY에 모두 등록되어 있는지
2) 다른 OS에서 graceful 분기 (한국어 ERROR string) 동작하는지
3) 입력 검증 (empty 등) 적절히 작동하는지
"""
from __future__ import annotations

import jarvis.platform as plat
from jarvis.tools import REGISTRY


# ─── windows_extras ─────────────────────────────────────────────────
def test_windows_extras_registered() -> None:
    names = set(REGISTRY.names())
    expected = {
        "windows_dark_mode_status", "windows_dark_mode_set", "windows_dark_mode_toggle",
        "windows_top_processes", "windows_frontmost_app", "windows_running_apps",
        "windows_audio_device_list", "windows_mic_mute",
        "windows_battery_info", "windows_wifi_info", "windows_bluetooth_status",
        "windows_caffeinate_start", "windows_caffeinate_stop",
        "windows_listening_ports", "windows_registry_read",
    }
    missing = expected - names
    assert not missing, f"missing: {missing}"


def test_windows_extras_branch_on_non_windows() -> None:
    """non-Windows에서 windows_* 도구 호출 → 한국어 ERROR."""
    if plat.IS_WINDOWS:
        return
    sample = ["windows_dark_mode_status", "windows_top_processes",
              "windows_battery_info", "windows_wifi_info", "windows_bluetooth_status"]
    for name in sample:
        result = REGISTRY.dispatch(name, {})
        assert "ERROR" in result and "Windows 전용" in result, f"{name}: {result}"


def test_windows_registry_read_path_validation() -> None:
    """non-Windows에서도 input validation은 동작 — but @windows_only가 먼저 잡음."""
    # mock Windows로 IS_WINDOWS=True 강제 후 input validation 확인
    orig = plat.IS_WINDOWS
    try:
        plat.IS_WINDOWS = True
        # 잘못된 path prefix → ERROR
        from jarvis.tools.windows_extras import _windows_registry_read
        result = _windows_registry_read("INVALID:\\x")
        assert "ERROR" in result and "HKCU" in result
    finally:
        plat.IS_WINDOWS = orig


# ─── linux_extras ─────────────────────────────────────────────────
def test_linux_extras_registered() -> None:
    names = set(REGISTRY.names())
    expected = {
        "linux_notify",
        "linux_dark_mode_status", "linux_dark_mode_set", "linux_dark_mode_toggle",
        "linux_top_processes", "linux_volume_set", "linux_volume_get",
        "linux_battery_info", "linux_wifi_info", "linux_bluetooth_status",
        "linux_caffeinate_start", "linux_caffeinate_stop", "linux_window_list",
    }
    missing = expected - names
    assert not missing, f"missing: {missing}"


def test_linux_extras_branch_on_non_linux() -> None:
    """non-Linux에서 linux_* 도구 호출 → 한국어 ERROR."""
    if plat.IS_LINUX:
        return
    sample = ["linux_notify", "linux_dark_mode_status", "linux_top_processes",
              "linux_battery_info", "linux_window_list"]
    for name in sample:
        # 인자가 필요한 것들도 빈 dict로 호출 가능 (handler 안에서 처리)
        result = REGISTRY.dispatch(name, {} if name != "linux_notify"
                                   else {"title": "x", "message": "y"})
        assert "ERROR" in result and "Linux 전용" in result, f"{name}: {result}"


# ─── ai_helpers ─────────────────────────────────────────────────
def test_ai_helpers_registered() -> None:
    names = set(REGISTRY.names())
    expected = {
        "text_summarize", "text_proofread", "text_explain", "text_korean_polish",
        "email_draft", "code_explain", "code_review_quick",
        "decision_helper", "task_decompose", "meeting_notes_format",
    }
    missing = expected - names
    assert not missing, f"missing: {missing}"


def test_ai_helpers_empty_input_validation() -> None:
    """ai_helpers 도구는 빈 입력에 대해 ERROR 반환."""
    # text_summarize empty
    result = REGISTRY.dispatch("text_summarize", {"text": ""})
    assert "ERROR" in result and "empty" in result
    # text_proofread empty
    result = REGISTRY.dispatch("text_proofread", {"text": "  "})
    assert "ERROR" in result and "empty" in result
    # email_draft empty
    result = REGISTRY.dispatch("email_draft", {"purpose": ""})
    assert "ERROR" in result and "empty" in result
    # code_explain empty
    result = REGISTRY.dispatch("code_explain", {"code": ""})
    assert "ERROR" in result
    # task_decompose empty
    result = REGISTRY.dispatch("task_decompose", {"task": ""})
    assert "ERROR" in result


def test_ai_helpers_no_api_key(monkeypatch) -> None:
    """ANTHROPIC_API_KEY 미설정 시 명확한 ERROR."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = REGISTRY.dispatch("text_summarize", {"text": "hello world", "max_lines": 1})
    # api key 미설정 ERROR이거나 anthropic SDK 미설치 ERROR
    assert "ERROR" in result
    assert "API_KEY" in result or "anthropic SDK" in result


def test_total_count_after_v05() -> None:
    """v0.5.0 도구 카운트: 최소 340 이상."""
    assert len(REGISTRY.specs()) >= 340
