"""profile.py + observations.py + personalization_observe 도구 검증.

각 컴포넌트가 독립적으로 동작하고, 시스템 프롬프트에 자동 첨부되는지까지 확인.
사용자 홈 디렉토리 오염 방지를 위해 monkeypatch로 Path.home() 격리.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from jarvis import observations, profile
from jarvis.tools import REGISTRY


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """모든 테스트에서 ~/.jarvis 격리."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # 모듈 module-level 경로도 동기화
    monkeypatch.setattr(profile, "PROFILE_PATH", tmp_path / ".jarvis" / "profile.json")
    monkeypatch.setattr(observations, "OBSERVATIONS_PATH", tmp_path / ".jarvis" / "observations.jsonl")
    monkeypatch.setattr(observations, "ARCHIVE_PATH", tmp_path / ".jarvis" / "observations.archive.jsonl")
    yield


# ─── profile ────────────────────────────────────────────────
class TestProfile:
    def test_read_default_when_missing(self) -> None:
        p = profile.read()
        assert p["title"] == ""
        assert p["interactions"] == 0
        assert p["first_met_at"] == ""

    def test_is_first_meeting_initially(self) -> None:
        assert profile.is_first_meeting() is True

    def test_mark_first_meeting(self) -> None:
        profile.mark_first_meeting()
        assert not profile.is_first_meeting()
        p = profile.read()
        assert p["interactions"] == 1
        assert p["first_met_at"]

    def test_mark_first_meeting_idempotent(self) -> None:
        profile.mark_first_meeting()
        first_ts = profile.read()["first_met_at"]
        profile.mark_first_meeting()  # 두 번째 호출 무시
        assert profile.read()["first_met_at"] == first_ts

    def test_increment_interactions(self) -> None:
        profile.increment_interactions()
        profile.increment_interactions()
        profile.increment_interactions()
        assert profile.read()["interactions"] == 3

    def test_set_title(self) -> None:
        profile.set_title("주인님")
        assert profile.get_title() == "주인님"

    def test_set_title_marks_first_meeting(self) -> None:
        assert profile.is_first_meeting() is True
        profile.set_title("보스")
        assert profile.is_first_meeting() is False
        assert profile.get_title() == "보스"

    def test_set_title_empty_ignored(self) -> None:
        profile.set_title("주인님")
        profile.set_title("   ")  # 무시
        assert profile.get_title() == "주인님"

    def test_set_get_preference(self) -> None:
        profile.set_preference("tone", "formal")
        profile.set_preference("language", "ko")
        assert profile.get_preference("tone") == "formal"
        assert profile.get_preference("language") == "ko"
        assert profile.get_preference("missing", "default") == "default"

    def test_reset(self) -> None:
        profile.set_title("X")
        profile.reset()
        assert profile.is_first_meeting() is True
        assert profile.get_title() == ""

    def test_corrupt_file_falls_back_to_default(self) -> None:
        profile.PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        profile.PROFILE_PATH.write_text("not json", encoding="utf-8")
        p = profile.read()
        assert p["title"] == ""  # default 반환
        assert p["interactions"] == 0


# ─── observations ────────────────────────────────────────────
class TestObservations:
    def test_count_zero_initially(self) -> None:
        assert observations.count() == 0

    def test_append_and_recent(self) -> None:
        observations.append("interest", "일식당 검색")
        observations.append("preference", "다크모드 선호")
        recent = observations.recent(10)
        assert len(recent) == 2
        assert recent[0]["category"] == "interest"
        assert recent[1]["content"] == "다크모드 선호"

    def test_recent_limit(self) -> None:
        for i in range(20):
            observations.append("test", f"obs {i}")
        recent = observations.recent(5)
        assert len(recent) == 5
        # 마지막 5개 (최신)
        assert recent[-1]["content"] == "obs 19"
        assert recent[0]["content"] == "obs 15"

    def test_by_category(self) -> None:
        observations.append("interest", "A")
        observations.append("preference", "B")
        observations.append("interest", "C")
        observations.append("concern", "D")
        observations.append("interest", "E")
        results = observations.by_category("interest")
        assert len(results) == 3
        contents = [r["content"] for r in results]
        assert contents == ["A", "C", "E"]  # 시간순

    def test_count_after_appends(self) -> None:
        for i in range(7):
            observations.append("x", f"item {i}")
        assert observations.count() == 7

    def test_clear(self) -> None:
        observations.append("x", "y")
        observations.append("x", "z")
        n = observations.clear()
        assert n == 2
        assert observations.count() == 0

    def test_clear_empty(self) -> None:
        assert observations.clear() == 0

    def test_format_for_system_prompt_empty(self) -> None:
        assert observations.format_for_system_prompt() == ""

    def test_format_for_system_prompt_with_data(self) -> None:
        observations.append("interest", "일식당 검색")
        observations.append("preference", "다크모드")
        text = observations.format_for_system_prompt()
        assert "사용자 관찰" in text
        assert "interest" in text
        assert "일식당" in text

    def test_truncates_long_content(self) -> None:
        big = "x" * 1000
        observations.append("test", big)
        rec = observations.recent(1)[0]
        assert len(rec["content"]) <= 500

    def test_extra_field(self) -> None:
        observations.append("test", "hi", extra={"location": "Seoul", "time": "morning"})
        rec = observations.recent(1)[0]
        assert rec.get("extra", {}).get("location") == "Seoul"

    def test_append_minimum_weight(self) -> None:
        observations.append("test", "a", weight=0)  # 0은 1로 강제
        rec = observations.recent(1)[0]
        assert rec["weight"] == 1

    def test_jsonl_format_valid(self) -> None:
        """파일이 유효한 JSONL인지 (한 줄에 한 JSON object)."""
        observations.append("a", "1")
        observations.append("b", "2")
        with observations.OBSERVATIONS_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    assert "ts" in obj
                    assert "category" in obj
                    assert "content" in obj


# ─── personalization_observe 도구 ──────────────────────────────
class TestPersonalizationTool:
    def test_tool_registered(self) -> None:
        assert "personalization_observe" in REGISTRY.names()

    def test_observe_via_dispatch(self) -> None:
        result = REGISTRY.dispatch(
            "personalization_observe",
            {"category": "interest", "content": "초밥집 자주 검색"},
        )
        assert "OK" in result
        assert "interest" in result
        # 실제로 기록되었는지
        recent = observations.recent(1)
        assert recent[0]["content"] == "초밥집 자주 검색"

    def test_observe_with_full_args(self) -> None:
        result = REGISTRY.dispatch(
            "personalization_observe",
            {"category": "routine", "content": "오전 9시 메모", "source": "recurring_pattern", "weight": 3},
        )
        assert "OK" in result
        rec = observations.recent(1)[0]
        assert rec["weight"] == 3
        assert rec["source"] == "recurring_pattern"

    def test_observe_empty_validation(self) -> None:
        result = REGISTRY.dispatch(
            "personalization_observe",
            {"category": "", "content": "hi"},
        )
        assert "ERROR" in result and "필수" in result

    def test_observe_no_dummy(self) -> None:
        result = REGISTRY.dispatch(
            "personalization_observe",
            {"category": "x", "content": "  "},
        )
        assert "ERROR" in result


# ─── 시스템 프롬프트 통합 ──────────────────────────────────────
class TestSystemPromptIntegration:
    def test_first_meeting_prompt_contains_introduction(self, monkeypatch) -> None:
        """첫 만남이면 시스템 프롬프트에 인사 + 자기소개 + 호칭 묻기 4개 모두 포함."""
        # profile 비어있어야 함
        if profile.PROFILE_PATH.exists():
            profile.reset()

        # i18n: 한국어로 강제 (이 테스트는 한국어 인사 검증)
        monkeypatch.setenv("JARVIS_LANG", "ko")

        # SYSTEM_PROMPT는 매번 _build_system_prompt 재호출
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "주인님 반갑습니다" in sp
        assert "자비스입니다" in sp
        assert "어떻게 호칭" in sp

    def test_after_first_meeting_no_introduction_block(self, monkeypatch) -> None:
        """첫 만남 후에는 인사 블록 사라지고 사용자 정보 블록 표시."""
        monkeypatch.setenv("JARVIS_LANG", "ko")
        profile.set_title("보스")
        profile.increment_interactions()  # 누적 1회
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        # 첫 만남 블록은 없어야 함
        assert "첫 만남 (CRITICAL)" not in sp
        # 사용자 정보 블록은 있어야 함
        assert "사용자 정보" in sp
        assert "보스" in sp
        assert "호칭 override" in sp

    def test_observations_attached_to_prompt(self) -> None:
        profile.mark_first_meeting()  # 첫 만남 분기 OFF
        observations.append("interest", "초밥집")
        observations.append("interest", "라멘")
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        assert "사용자 관찰" in sp
        assert "초밥집" in sp
        assert "라멘" in sp
        assert "능동 활용 가이드" in sp

    def test_no_observations_no_block(self) -> None:
        profile.mark_first_meeting()
        from jarvis.assistant import _build_system_prompt
        sp = _build_system_prompt()
        # 관찰 0건이면 사용자 관찰 블록 없음
        assert "# 사용자 관찰" not in sp
