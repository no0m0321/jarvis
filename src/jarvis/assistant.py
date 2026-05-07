from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Optional

from jarvis import hud, persona
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
    """persona + cross-session memory + owner_name 합쳐 시스템 프롬프트 생성."""
    base = persona.get_active()
    # owner_name override — settings.owner_name 또는 JARVIS_OWNER_NAME 환경변수
    owner = settings.owner_name.strip() if settings.owner_name else ""
    if owner:
        base += f"\n\n# 호칭 override\n사용자를 '{owner}'(으)로 호칭. 'memory.md' 또는 persona의 다른 호칭은 무시."
    # ~/.jarvis/memory.md 가 있으면 시스템 프롬프트에 자동 첨부 (cross-session 기억)
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
    return base


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
            return self.provider.reply(
                list(messages), SYSTEM_PROMPT, self.model, self.max_tokens
            )
        finally:
            hud.set_state("idle")

    def stream(self, messages: Iterable[dict]):
        """스트리밍 응답. 토큰 단위 yield."""
        hud.set_state("analyzing", "LLM stream")
        try:
            yield from self.provider.stream(
                list(messages), SYSTEM_PROMPT, self.model, self.max_tokens
            )
        finally:
            hud.set_state("idle")
