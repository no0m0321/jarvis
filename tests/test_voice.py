import numpy as np


def test_voice_module_imports() -> None:
    from jarvis.voice import record_until_silence, transcribe

    assert callable(record_until_silence)
    assert callable(transcribe)


def test_transcribe_empty_audio_returns_empty_string() -> None:
    from jarvis.voice import transcribe

    empty = np.zeros(0, dtype=np.float32)
    assert transcribe(empty) == ""


def test_recorder_signature() -> None:
    """recorder가 numpy를 import하고 sounddevice가 로드되는지."""
    import sounddevice as sd

    from jarvis.voice.recorder import record_until_silence

    assert hasattr(sd, "InputStream")
    assert callable(record_until_silence)
