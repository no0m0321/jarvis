from jarvis.voice.wake import DEFAULT_WAKE_WORDS, strip_wake


def test_strip_wake_korean_command() -> None:
    assert strip_wake("자비스 시계 알려줘") == "시계 알려줘"


def test_strip_wake_english_command() -> None:
    assert strip_wake("Jarvis what's the weather") == "what's the weather"


def test_strip_wake_korean_only() -> None:
    assert strip_wake("자비스") == ""
    assert strip_wake("자비스.") == ""
    assert strip_wake("자비스!") == ""


def test_strip_wake_no_wake_word() -> None:
    assert strip_wake("hello world") == "hello world"


def test_strip_wake_variant() -> None:
    # small/base 모델이 "자비스"를 "지비스"로 전사하는 경우
    assert strip_wake("지비스 메모 적어줘") == "메모 적어줘"


def test_strip_wake_with_punctuation() -> None:
    assert strip_wake("자비스, 음악 틀어줘") == "음악 틀어줘"


def test_default_wake_words() -> None:
    assert "자비스" in DEFAULT_WAKE_WORDS
    assert "jarvis" in DEFAULT_WAKE_WORDS
    assert len(DEFAULT_WAKE_WORDS) >= 5
