"""_build_system_prompt 캐시 동작 검증.

- signature(lang/persona/owner + 3개 파일 mtime) 동일 시 cache hit
- env 변경 / 파일 변경 시 자동 invalidation
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """모든 테스트에서 ~/.jarvis 격리 + 캐시 clear."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from jarvis import assistant as ast
    from jarvis import observations as obs
    from jarvis import profile as prof
    monkeypatch.setattr(prof, "PROFILE_PATH", tmp_path / ".jarvis" / "profile.json")
    monkeypatch.setattr(obs, "OBSERVATIONS_PATH", tmp_path / ".jarvis" / "observations.jsonl")
    monkeypatch.setattr(obs, "ARCHIVE_PATH", tmp_path / ".jarvis" / "observations.archive.jsonl")
    ast.clear_prompt_cache()
    yield


def test_cache_hit_on_repeat(monkeypatch) -> None:
    """동일 condition에서 두 번 호출 → 두 번째는 cache hit."""
    from jarvis.assistant import (
        _build_system_prompt, clear_prompt_cache, prompt_cache_stats,
    )
    monkeypatch.setenv("JARVIS_LANG", "ko")
    clear_prompt_cache()

    p1 = _build_system_prompt()
    stats_after_1 = prompt_cache_stats()
    p2 = _build_system_prompt()
    stats_after_2 = prompt_cache_stats()

    assert p1 == p2
    assert stats_after_2["hits"] > stats_after_1["hits"]


def test_cache_invalidates_on_lang_change(monkeypatch) -> None:
    """언어 환경변수 변경 → 캐시 miss + 다른 결과."""
    from jarvis.assistant import _build_system_prompt, clear_prompt_cache
    clear_prompt_cache()

    monkeypatch.setenv("JARVIS_LANG", "ko")
    p_ko = _build_system_prompt()
    monkeypatch.setenv("JARVIS_LANG", "en")
    p_en = _build_system_prompt()
    assert p_ko != p_en
    assert "주인님" in p_ko or "자비스" in p_ko
    assert "Sir" in p_en or "Jarvis" in p_en


def test_cache_invalidates_on_profile_change(monkeypatch) -> None:
    """프로필 파일 변경 → 캐시 miss + 다른 prompt."""
    from jarvis import profile as prof
    from jarvis.assistant import _build_system_prompt, clear_prompt_cache
    monkeypatch.setenv("JARVIS_LANG", "en")
    clear_prompt_cache()

    p1 = _build_system_prompt()
    # 파일 수정으로 mtime 변경
    time.sleep(0.01)  # mtime 해상도 보장
    prof.set_title("Boss")
    p2 = _build_system_prompt()
    assert p1 != p2
    assert "Boss" in p2


def test_cache_invalidates_on_observations_change(monkeypatch) -> None:
    """observation append → 캐시 miss + 새 prompt에 관찰 첨부."""
    from jarvis import observations as obs
    from jarvis import profile as prof
    from jarvis.assistant import _build_system_prompt, clear_prompt_cache

    monkeypatch.setenv("JARVIS_LANG", "en")
    prof.mark_first_meeting()
    clear_prompt_cache()

    p1 = _build_system_prompt()
    time.sleep(0.01)
    obs.append("interest", "Italian food")
    p2 = _build_system_prompt()
    assert p1 != p2
    assert "Italian food" in p2


def test_clear_cache(monkeypatch) -> None:
    from jarvis.assistant import (
        _build_system_prompt, clear_prompt_cache, prompt_cache_stats,
    )
    monkeypatch.setenv("JARVIS_LANG", "en")
    clear_prompt_cache()

    _build_system_prompt()
    _build_system_prompt()
    stats = prompt_cache_stats()
    assert stats["hits"] >= 1
    clear_prompt_cache()
    # 캐시 비워졌으면 다음 호출은 miss
    misses_before = stats["misses"]
    _build_system_prompt()
    stats_after = prompt_cache_stats()
    assert stats_after["misses"] > misses_before


def test_cache_size_limit(monkeypatch) -> None:
    """5개 이상 신호 변경 시 오래된 것부터 제거."""
    from jarvis.assistant import _build_system_prompt, clear_prompt_cache, _PROMPT_CACHE
    clear_prompt_cache()

    for code in ["ko", "en", "ja", "zh", "es", "fr", "de"]:
        monkeypatch.setenv("JARVIS_LANG", code)
        _build_system_prompt()

    # 5개 이하로 유지 (LRU-like)
    assert len(_PROMPT_CACHE) <= 5
