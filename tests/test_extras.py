"""새로 추가된 모듈/도구 스모크 테스트 (실제 시스템 호출 X — handler 등록만 검증)."""
from jarvis.tools import REGISTRY


def test_new_tools_registered() -> None:
    expected = {
        "calendar_add", "calendar_list_today", "screen_capture",
        "clipboard_read", "clipboard_write",
        "mail_compose", "spotlight_search", "activate_app", "play_sound",
        "music_control", "set_volume", "get_volume", "set_brightness",
        "reminder_add", "note_search", "note_list",
        "battery_info", "wifi_info", "bookmark_add",
        "top_processes", "system_action",
    }
    actual = set(REGISTRY.names())
    missing = expected - actual
    assert not missing, f"missing tools: {missing}"


def test_total_tool_count() -> None:
    assert len(REGISTRY.names()) >= 30


def test_persona_module() -> None:
    from jarvis import persona

    assert "jarvis" in persona.PERSONAS
    assert "casual" in persona.PERSONAS
    prompt = persona.get_active()
    assert "자비스" in prompt or "JARVIS" in prompt


def test_history_module() -> None:
    from jarvis import history

    history.append("user", "테스트 메시지")
    history.append("assistant", "테스트 응답")
    last = history.tail(2)
    assert len(last) >= 2
    assert any(e["content"] == "테스트 메시지" for e in last)


def test_hud_voice_history() -> None:
    from jarvis import hud

    hud.set_voice_level(0.05)
    hud.set_voice_level(0.08)
    # voice file should exist after writes
    from pathlib import Path

    p = Path.home() / "Library" / "Caches" / "jarvis-voice.json"
    assert p.exists()


def test_hud_state_writer() -> None:
    from jarvis import hud
    import json
    from pathlib import Path

    hud.set_state("listening", "test")
    p = Path.home() / "Library" / "Caches" / "jarvis-hud.json"
    assert p.exists()
    data = json.loads(p.read_text())
    assert data["state"] == "listening"
    hud.set_state("idle")  # cleanup


def test_hud_data_script_executes() -> None:
    """hud-data.sh가 valid JSON 출력하는지."""
    import json
    import subprocess

    result = subprocess.run(
        ["bash", "/Users/swxvno/jarvis/scripts/hud-data.sh"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    for key in ("cpu", "mem", "net_in", "net_out", "disk", "jarvis", "voice"):
        assert key in data
