from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Optional

from jarvis import hud, observations, persona
from jarvis import profile as user_profile
from jarvis.config import settings

_MEMORY_TEMPLATE = """# 자비스 메모 (~/.jarvis/memory.md)

이 파일은 모든 자비스 세션에서 시스템 프롬프트에 자동 첨부됩니다.
사용자 정체성·선호·작업 기본값을 적어 두면 cross-session 기억으로 활용됩니다.

## 정체성
- 이름:
- 호칭: (예: "주인님", "보스", 영어 이름 등 — JARVIS_OWNER_NAME env 우선)

## 작업 기본값
- 응답 길이: 짧게 / 보통 / 자세히
- 코드 스타일: (예: Python 3.11, type hints, ruff)
- 사이트/디자인 톤: (예: 미니멀, sci-fi, 다크 테마)

## 환경
- OS: macOS / Linux / Windows
- 자주 쓰는 디렉토리: ~/Desktop, ~/Documents/work
"""


def _ensure_memory_template() -> None:
    """~/.jarvis/memory.md 가 없으면 안내 템플릿 생성."""
    try:
        from pathlib import Path

        memo = Path.home() / ".jarvis" / "memory.md"
        if not memo.exists():
            memo.parent.mkdir(parents=True, exist_ok=True)
            memo.write_text(_MEMORY_TEMPLATE, encoding="utf-8")
    except Exception:
        pass


def _build_system_prompt() -> str:
    """persona + 호칭 + cross-session memory + 사용자 관찰 합쳐 시스템 프롬프트 생성.

    빌드 순서 (우선순위 높은 것이 마지막에 첨부 → LLM이 더 강하게 인지):
    1. base persona (jarvis/casual/formal/creative)
    2. 첫 만남 분기 — first_met_at이 비어있으면 자기소개 + 호칭 묻기 지시
    3. 호칭 — settings.owner_name (env) > profile.title (저장된) > persona 기본
    4. ~/.jarvis/memory.md (사용자 명시 메모)
    5. ~/.jarvis/observations.jsonl 최근 관찰 (passive learning)
    """
    base = persona.get_active()

    # 1) 첫 만남 — profile.json이 없거나 first_met_at 비어있으면 자비스가 자기소개 + 호칭 질문
    if user_profile.is_first_meeting():
        base += (
            "\n\n# 첫 만남 (CRITICAL)\n"
            "사용자가 자비스를 처음 부르는 상황입니다. 첫 응답에서 반드시 다음 4가지를 모두 포함:\n"
            "  1) '주인님 반갑습니다.' (정중한 첫 인사)\n"
            "  2) '저는 당신의 일상을 보조할 자비스입니다.' (자기소개)\n"
            "  3) '제가 당신을 어떻게 호칭하면 좋을까요?' (호칭 묻기)\n"
            "  4) 호칭 듣고 나면 personalization_observe 도구로 "
            "category='preference', content='호칭은 ___' 기록 + memory_save로 영구 저장.\n"
            "  5) 사용자가 호칭 알려주면 다음 응답부터는 그 호칭으로 부른다.\n"
            "이후 대화에서는 이 첫 만남 안내가 자동으로 사라집니다."
        )
    else:
        p = user_profile.read()
        title = (p.get("title") or "").strip()
        interactions = int(p.get("interactions", 0))
        first_met = (p.get("first_met_at") or "")[:10]
        if title or interactions:
            ctx = f"# 사용자 정보\n- 호칭: '{title or '주인님'}'\n- 첫 만남: {first_met}\n- 누적 대화: {interactions}회"
            base += "\n\n" + ctx

    # 2) 호칭 override — JARVIS_OWNER_NAME env > profile.title > persona 기본 (주인님)
    owner = settings.owner_name.strip() if settings.owner_name else ""
    if not owner:
        owner = (user_profile.read().get("title") or "").strip()
    if owner:
        base += (
            f"\n\n# 호칭 override\n사용자를 '{owner}'(으)로 호칭. "
            "이전 메모리·persona 기본 호칭은 무시하고 이 호칭만 사용."
        )

    # 3) ~/.jarvis/memory.md (cross-session 기억)
    try:
        from pathlib import Path

        _ensure_memory_template()
        memo = Path.home() / ".jarvis" / "memory.md"
        if memo.exists():
            mem_text = memo.read_text(encoding="utf-8").strip()
            if mem_text:
                base += f"\n\n# 사용자 메모 (~/.jarvis/memory.md)\n{mem_text[:4000]}"
    except Exception:
        pass

    # 4) Passive learning observations (최근 30개) — 자비스가 능동 활용
    try:
        obs_block = observations.format_for_system_prompt(50)
        if obs_block:
            base += "\n\n" + obs_block
            base += (
                "\n\n# 능동 활용 가이드\n"
                "위 관찰 기록을 바탕으로 자연스럽게 능동 제안 가능:\n"
                "- 같은 카테고리가 3회 이상 반복 → '최근 X에 자주 관심 보이시던데...' 식 자연스러운 연결\n"
                "- 너무 자주 언급하면 부담스러우니 1-2회 대화에 1번 정도만\n"
                "- 사용자가 명시적으로 새 패턴 보이면 personalization_observe 도구로 기록 추가"
            )
    except Exception:
        pass

    return base


# 모듈 import 시점의 스냅샷 — 외부에서 `from jarvis.assistant import SYSTEM_PROMPT`
# 같은 패턴을 위해 유지. 단, 실제 LLM 호출은 reply/stream에서 _build_system_prompt()를
# 매번 재평가해서 첫 만남 → 이후 대화의 상태 변화를 즉시 반영한다.
SYSTEM_PROMPT = _build_system_prompt()


class JarvisAssistant:
    """LLM 기반 비서.

    JARVIS_PROVIDER 환경변수로 backend 전환 가능 (anthropic/openai/ollama).
    Anthropic은 ephemeral 캐시 + 도구 use 완전 지원 (기본).
    OpenAI/Ollama는 chat-only — 'jarvis ask/chat'에서만 작동.
    """

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> None:
        from jarvis.providers import get_provider
        self.provider = get_provider()
        self.model = model or settings.model
        self.max_tokens = max_tokens or settings.max_tokens
        # 모델 기본값 자동 변환 — provider에 맞게
        if self.provider.name == "openai" and self.model.startswith("claude-"):
            self.model = os.environ.get("JARVIS_MODEL_OPENAI", "gpt-4o-mini")
        elif self.provider.name == "ollama" and self.model.startswith("claude-"):
            self.model = os.environ.get("JARVIS_MODEL_OLLAMA", "llama3.2")

    def reply(self, messages: Iterable[dict]) -> str:
        """단발 응답. messages는 [{role, content}, ...] 형식."""
        hud.set_state("analyzing", "LLM reply")
        try:
            sp = _build_system_prompt()
            response = self.provider.reply(list(messages), sp, self.model, self.max_tokens)
            # 첫 만남이었다면 응답 직후 상태 마킹 (다음 호출부터 첫 만남 분기 OFF)
            user_profile.increment_interactions()
            return response
        finally:
            hud.set_state("idle")

    def stream(self, messages: Iterable[dict]):
        """스트리밍 응답. 토큰 단위 yield."""
        hud.set_state("analyzing", "LLM stream")
        try:
            sp = _build_system_prompt()
            yield from self.provider.stream(list(messages), sp, self.model, self.max_tokens)
            user_profile.increment_interactions()
        finally:
            hud.set_state("idle")
