from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

from anthropic import Anthropic

from jarvis import hud, persona
from jarvis.config import settings


def _build_system_prompt() -> str:
    """persona + cross-session memory 합쳐 시스템 프롬프트 생성."""
    base = persona.get_active()
    # ~/.jarvis/memory.md 가 있으면 시스템 프롬프트에 자동 첨부 (cross-session 기억)
    try:
        from pathlib import Path

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
    """Claude 기반 비서. 시스템 프롬프트는 ephemeral 캐시로 재사용."""

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않음. .env에 키를 채우거나 환경변수로 지정하시오."
            )
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.model
        self.max_tokens = max_tokens or settings.max_tokens

    def reply(self, messages: Iterable[dict]) -> str:
        """단발 응답. messages는 [{role, content}, ...] 형식."""
        hud.set_state("analyzing", "LLM reply")
        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=list(messages),
            )
            return "".join(block.text for block in msg.content if block.type == "text")
        finally:
            hud.set_state("idle")

    def stream(self, messages: Iterable[dict]):
        """스트리밍 응답. 토큰 단위 yield."""
        hud.set_state("analyzing", "LLM stream")
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=list(messages),
            ) as stream:
                yield from stream.text_stream
        finally:
            hud.set_state("idle")
