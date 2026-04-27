from jarvis.voice.wake import DEFAULT_WAKE_WORDS, strip_wake


def test_strip_wake_korean_command() -> None:
    assert strip_wake("자비스 시계 알려줘") == "시계 알려줘"


def test_strip_wake_english_command() -> None:
    assert strip_wake("Jarvis what's the weather") == "what's the weather"


def test_strip_wake_korean_only() -> None:
    assert strip_wake("자비스") == ""
    assert strip_wake("자비스.") == ""
    assert strip_wake("자비스!") == ""


def test_strip_wake_repeated_calls() -> None:
    """반복 호출은 모두 제거 → 단독 호출 분기로."""
    assert strip_wake("자비스 자비스 자비스") == ""
    assert strip_wake("자비스. 자비스. 자비스. 자비스.") == ""


def test_strip_wake_interleaved() -> None:
    """명령 사이에 wake word 끼어있어도 모두 제거."""
    assert strip_wake("자비스 메모 자비스 적어줘") == "메모 적어줘"


def test_strip_wake_no_wake_word() -> None:
    assert strip_wake("hello world") == "hello world"


def test_strip_wake_variant() -> None:
    # 안전한 변종만 유지 (자비스/쟈비스/재비스/자뷔스/jarvis).
    # "지비스/서비스/자비슨"은 false positive 우려로 제거됨.
    assert strip_wake("쟈비스 메모 적어줘") == "메모 적어줘"
    assert strip_wake("재비스 메모 적어줘") == "메모 적어줘"


def test_strip_wake_with_punctuation() -> None:
    assert strip_wake("자비스, 음악 틀어줘") == "음악 틀어줘"


def test_default_wake_words() -> None:
    assert "자비스" in DEFAULT_WAKE_WORDS
    assert "jarvis" in DEFAULT_WAKE_WORDS
    assert len(DEFAULT_WAKE_WORDS) >= 5
