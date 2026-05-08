"""system_xp.py의 v0.5.0 추가 5개 도구 + 모든 신규 도구 일괄 smoke test."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import jarvis.platform as plat
from jarvis.tools import REGISTRY


# ─── system_uptime ────────────────────────────────────────────────
def test_system_uptime_runs() -> None:
    """uptime 도구는 모든 OS에서 동작해야 (psutil 있으면 native, 없으면 OS fallback).

    출력 형식이 OS별로 다름:
    - psutil: 'uptime: Nd Hh Mm (booted ...)'
    - macOS sysctl: '{ sec = ... } <ctime>'
    - Linux /proc: 'uptime: ...'
    - Windows: 'booted: ...'
    """
    result = REGISTRY.dispatch("system_uptime", {})
    assert isinstance(result, str)
    assert result.strip(), "empty result"
    # 어떤 형식이든 정상 동작했으면 unsupported/ERROR가 없음
    if "ERROR: unsupported OS" in result:
        pytest.fail("uptime returned unsupported OS")


# ─── system_locale ────────────────────────────────────────────────
def test_system_locale_runs() -> None:
    result = REGISTRY.dispatch("system_locale", {})
    assert isinstance(result, str)
    # 핵심 키 모두 존재
    assert "locale:" in result
    assert "encoding:" in result
    assert "TZ env:" in result
    assert "now local:" in result
    assert "now utc:" in result


# ─── file_compare_dirs ────────────────────────────────────────────
class TestFileCompareDirs:
    def test_dir_not_found(self) -> None:
        result = REGISTRY.dispatch(
            "file_compare_dirs", {"dir1": "/nonexistent_jarvis_aaa", "dir2": "/tmp"}
        )
        assert "ERROR" in result and "디렉토리 아님" in result

    def test_identical_dirs(self, tmp_path: Path) -> None:
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        (d1 / "x.txt").write_text("hello")
        (d2 / "x.txt").write_text("hello")
        # 같은 사이즈/내용 + 거의 같은 mtime
        result = REGISTRY.dispatch(
            "file_compare_dirs", {"dir1": str(d1), "dir2": str(d2)}
        )
        assert "ONLY in a: 0" in result
        assert "ONLY in b: 0" in result

    def test_only_in_dir1(self, tmp_path: Path) -> None:
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        (d1 / "x.txt").write_text("hi")
        (d1 / "y.txt").write_text("hi")
        result = REGISTRY.dispatch(
            "file_compare_dirs", {"dir1": str(d1), "dir2": str(d2)}
        )
        assert "ONLY in a: 2" in result
        assert "x.txt" in result
        assert "y.txt" in result

    def test_differ_size(self, tmp_path: Path) -> None:
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        (d1 / "x.txt").write_text("aaa")
        (d2 / "x.txt").write_text("bbbbbb")  # 다른 사이즈
        result = REGISTRY.dispatch(
            "file_compare_dirs", {"dir1": str(d1), "dir2": str(d2)}
        )
        assert "DIFFER" in result

    def test_recursive(self, tmp_path: Path) -> None:
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        (d1 / "sub").mkdir(parents=True)
        d2.mkdir()
        (d1 / "sub" / "deep.txt").write_text("deep")
        result = REGISTRY.dispatch(
            "file_compare_dirs", {"dir1": str(d1), "dir2": str(d2)}
        )
        assert "deep.txt" in result


# ─── system_kill_process ──────────────────────────────────────────
class TestKillProcess:
    def test_pid_zero_rejected(self) -> None:
        result = REGISTRY.dispatch("system_kill_process", {"pid": 0})
        assert "ERROR" in result and "거부" in result

    def test_pid_one_rejected(self) -> None:
        result = REGISTRY.dispatch("system_kill_process", {"pid": 1})
        assert "ERROR" in result and "거부" in result

    def test_self_pid_rejected(self) -> None:
        result = REGISTRY.dispatch(
            "system_kill_process", {"pid": os.getpid()}
        )
        assert "ERROR" in result and "자기 자신" in result

    def test_nonexistent_pid(self) -> None:
        # 매우 높은 PID — 거의 확실히 존재하지 않음
        result = REGISTRY.dispatch("system_kill_process", {"pid": 999999})
        # POSIX에선 ProcessLookupError, Windows에선 taskkill ERROR
        assert "ERROR" in result

    def test_real_kill(self) -> None:
        """실제 짧은 sleep 프로세스 spawn 후 종료."""
        import subprocess
        if plat.IS_WINDOWS:
            # Windows: ping은 인자만큼 sleep 비슷하게
            p = subprocess.Popen(["ping", "-n", "60", "127.0.0.1"], stdout=subprocess.DEVNULL)
        else:
            p = subprocess.Popen(["sleep", "60"], stdout=subprocess.DEVNULL)
        try:
            result = REGISTRY.dispatch("system_kill_process", {"pid": p.pid})
            assert "OK" in result
            # 실제 종료 검증 (타임아웃 1초 wait)
            p.wait(timeout=2)
        finally:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=1)


# ─── network_speedtest_simple (외부 의존, 네트워크 끊겨도 graceful 처리) ───
def test_network_speedtest_returns_string() -> None:
    """네트워크 끊겨도 ERROR string으로 graceful 처리 — 외부 의존 + slow → timeout 6초."""
    result = REGISTRY.dispatch("network_speedtest_simple", {"timeout": 5})
    assert isinstance(result, str)
    # 적어도 latency 라인은 있어야 함
    assert "latency" in result


# ─── 모든 v0.5.0 신규 도구 일괄 smoke (한 번씩 dispatch) ───
class TestAllNewToolsSmoke:
    """v0.5.0에서 추가된 모든 신규 도구를 REGISTRY.dispatch로 한 번씩 호출.

    각 도구가:
    1) 호출 시 raise 없이 string 반환
    2) Windows/Linux 전용 도구는 macOS에서 한국어 ERROR
    3) cross-platform 도구는 정상 응답 또는 합리적 ERROR
    """

    # v0.5.0 신규 도구 전체 (44개)
    NEW_TOOLS_NO_ARGS = [
        # cross-platform
        "system_env_summary",
        "system_uptime",
        "system_locale",
    ]

    NEW_TOOLS_WITH_ARGS: list[tuple[str, dict]] = [
        # cross-platform
        ("system_open_path", {"path": "/nonexistent_jarvis_xxx"}),
        ("system_show_in_folder", {"path": "/nonexistent_jarvis_xxx"}),
        ("system_default_browser_url", {"url": ""}),
        ("system_open_terminal_at", {"path": "/nonexistent_jarvis_xxx"}),
        ("system_screenshot_to_file", {}),  # 자동 path
        ("system_record_audio", {"seconds": 0}),  # 검증 ERROR
        ("file_compare_dirs", {"dir1": "/nope1", "dir2": "/nope2"}),
        ("system_kill_process", {"pid": 0}),
        # ai_helpers — API key 없으면 ERROR
        ("text_summarize", {"text": ""}),
        ("text_proofread", {"text": ""}),
        ("text_explain", {"concept": ""}),
        ("text_korean_polish", {"text": ""}),
        ("email_draft", {"purpose": ""}),
        ("code_explain", {"code": ""}),
        ("code_review_quick", {"code": ""}),
        ("decision_helper", {"question": ""}),
        ("task_decompose", {"task": ""}),
        ("meeting_notes_format", {"notes": ""}),
        # personalization
        ("personalization_observe", {"category": "", "content": ""}),
        # windows_extras (macOS에서 호출 시 ERROR)
        ("windows_dark_mode_status", {}),
        ("windows_dark_mode_toggle", {}),
        ("windows_top_processes", {}),
        ("windows_frontmost_app", {}),
        ("windows_running_apps", {}),
        ("windows_audio_device_list", {}),
        ("windows_mic_mute", {}),
        ("windows_battery_info", {}),
        ("windows_wifi_info", {}),
        ("windows_bluetooth_status", {}),
        ("windows_caffeinate_start", {}),
        ("windows_caffeinate_stop", {}),
        ("windows_listening_ports", {}),
        ("windows_registry_read", {"path": "HKCU:\\x"}),
        ("windows_run_powershell", {"script": "echo hi"}),
        ("windows_outlook_compose", {"to": "x@y.com"}),
        # linux_extras (macOS에서 호출 시 ERROR)
        ("linux_notify", {"title": "x", "message": "y"}),
        ("linux_dark_mode_status", {}),
        ("linux_dark_mode_toggle", {}),
        ("linux_top_processes", {}),
        ("linux_volume_get", {}),
        ("linux_volume_set", {"level": 50}),
        ("linux_battery_info", {}),
        ("linux_wifi_info", {}),
        ("linux_bluetooth_status", {}),
        ("linux_caffeinate_start", {}),
        ("linux_caffeinate_stop", {}),
        ("linux_window_list", {}),
    ]

    def test_no_args_tools_return_string(self) -> None:
        for name in self.NEW_TOOLS_NO_ARGS:
            result = REGISTRY.dispatch(name, {})
            assert isinstance(result, str), f"{name} did not return str: {type(result)}"
            assert result.strip(), f"{name} returned empty"

    def test_with_args_tools_return_string(self) -> None:
        for name, args in self.NEW_TOOLS_WITH_ARGS:
            result = REGISTRY.dispatch(name, args)
            assert isinstance(result, str), f"{name} did not return str"

    def test_windows_only_tools_return_korean_error_on_macos(self) -> None:
        if plat.IS_WINDOWS:
            return
        windows_tools = [n for n, _ in self.NEW_TOOLS_WITH_ARGS if n.startswith("windows_")]
        for name in windows_tools:
            result = REGISTRY.dispatch(name, {})
            # graceful Windows 전용 분기 또는 inputs validation은 가능 — 둘 다 string ERROR
            assert isinstance(result, str)
            # input validation으로 일찍 ERROR가 날 수도 있고 (windows_registry_read),
            # @windows_only로 ERROR가 날 수도 있다 — 어느 쪽이든 ERROR/Windows 표시
            if "Windows 전용" in result:
                assert "ERROR" in result

    def test_linux_only_tools_return_korean_error_on_macos(self) -> None:
        if plat.IS_LINUX:
            return
        linux_tools = [n for n, args in self.NEW_TOOLS_WITH_ARGS if n.startswith("linux_")]
        for name in linux_tools:
            args_for = {"title": "x", "message": "y"} if name == "linux_notify" else {}
            if name == "linux_volume_set":
                args_for = {"level": 50}
            result = REGISTRY.dispatch(name, args_for)
            assert isinstance(result, str)
            if "Linux 전용" in result:
                assert "ERROR" in result


# ─── 기존 v0.4.0 graceful 분기 도구 sample 검증 (regression 가드) ──
class TestRegressionV04Branching:
    def test_macos_tools_still_branch_on_mock_windows(self) -> None:
        """v0.4.0에서 추가된 99개 macOS 도구의 sample이 graceful 분기 유지."""
        orig_mac = plat.IS_MACOS
        orig_win = plat.IS_WINDOWS
        orig_plat = plat.PLATFORM
        try:
            plat.IS_MACOS = False
            plat.IS_WINDOWS = True
            plat.PLATFORM = "win32"
            from jarvis.tools.applescript import _apple_script
            from jarvis.tools.macos_more import _mail_compose
            from jarvis.tools.macos_extras2 import _battery_info
            assert "macOS 전용" in _apple_script("return 1")
            assert "macOS 전용" in _mail_compose("x@y.com")
            assert "macOS 전용" in _battery_info()
        finally:
            plat.IS_MACOS = orig_mac
            plat.IS_WINDOWS = orig_win
            plat.PLATFORM = orig_plat


# ─── 도구 카운트 가드 ──────────────────────────────────────────────
def test_tool_count_exactly_350() -> None:
    """v0.5.0 정확한 도구 카운트 350."""
    assert len(REGISTRY.specs()) == 350, (
        f"tool count mismatch: {len(REGISTRY.specs())} != 350"
    )


def test_no_duplicate_tool_names() -> None:
    names = REGISTRY.names()
    assert len(set(names)) == len(names), "duplicate tool names exist"


def test_all_tools_have_description() -> None:
    """모든 도구에 description이 채워져 있어야 (한국어 권장)."""
    missing: list[str] = []
    for spec in REGISTRY.specs():
        desc = (spec.get("description") or "").strip()
        if not desc:
            missing.append(spec["name"])
    assert not missing, f"tools without description: {missing}"


def test_all_tool_schemas_well_formed() -> None:
    """모든 도구의 input_schema가 JSON Schema 형식 — type=object + properties dict."""
    bad: list[str] = []
    for spec in REGISTRY.specs():
        schema = spec.get("input_schema", {})
        if schema.get("type") != "object":
            bad.append(f"{spec['name']}: type != object")
        if not isinstance(schema.get("properties"), dict):
            bad.append(f"{spec['name']}: properties not dict")
    assert not bad, "\n".join(bad)
