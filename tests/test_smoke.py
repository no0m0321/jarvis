from jarvis import __version__
from jarvis.assistant import SYSTEM_PROMPT


def test_version() -> None:
    assert __version__ == "0.2.0"


def test_system_prompt_korean() -> None:
    assert "자비스" in SYSTEM_PROMPT
    assert "승우" in SYSTEM_PROMPT


def test_cli_imports() -> None:
    from jarvis.cli import app

    assert app is not None
