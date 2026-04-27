"""Voice I/O — 마이크 녹음(sounddevice) + Whisper 전사(faster-whisper) + wake word."""
from jarvis.voice.recorder import capture_phrase, record_until_silence
from jarvis.voice.transcribe import transcribe
from jarvis.voice.wake import (
    DEFAULT_WAKE_WORDS,
    detect_wake_word,
    listen_for_wake,
    strip_wake,
)

__all__ = [
    "capture_phrase",
    "record_until_silence",
    "transcribe",
    "detect_wake_word",
    "listen_for_wake",
    "strip_wake",
    "DEFAULT_WAKE_WORDS",
]
