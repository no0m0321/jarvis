from pathlib import Path

from jarvis.daemon import (
    LABEL,
    LOG_DIR,
    LOG_ERR,
    LOG_OUT,
    PLIST_PATH,
    project_root,
    render_plist,
    venv_jarvis,
)


def test_label() -> None:
    assert LABEL == "com.swxvno.jarvis.wake"
    assert PLIST_PATH.name == f"{LABEL}.plist"
    assert "LaunchAgents" in str(PLIST_PATH)


def test_paths_resolved() -> None:
    root = project_root()
    assert (root / "src" / "jarvis").exists()
    assert (root / "pyproject.toml").exists()
    assert venv_jarvis() == root / ".venv" / "bin" / "jarvis"


def test_log_paths() -> None:
    assert LOG_OUT.parent == LOG_DIR
    assert LOG_OUT.suffix == ".log"
    assert LOG_ERR.suffix == ".log"


def test_render_plist_default() -> None:
    plist = render_plist()
    assert "<key>Label</key>" in plist
    assert LABEL in plist
    assert "<key>RunAtLoad</key>" in plist
    assert "<true/>" in plist
    assert "<key>KeepAlive</key>" in plist
    assert "<key>WorkingDirectory</key>" in plist
    assert str(project_root()) in plist
    assert str(venv_jarvis()) in plist
    assert "<string>wake</string>" in plist


def test_render_plist_with_extra_args() -> None:
    plist = render_plist(["wake", "--no-chime", "--detect-model", "tiny"])
    assert "--no-chime" in plist
    assert "--detect-model" in plist
    assert "tiny" in plist


def test_render_plist_environment() -> None:
    plist = render_plist()
    assert "<key>PATH</key>" in plist
    assert "/opt/homebrew/bin" in plist


def test_render_plist_log_paths_present() -> None:
    plist = render_plist()
    assert str(LOG_OUT) in plist
    assert str(LOG_ERR) in plist
