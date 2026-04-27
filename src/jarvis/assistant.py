from __future__ import annotations

from typing import Iterable, Optional

from anthropic import Anthropic

from jarvis import hud
from jarvis.config import settings

SYSTEM_PROMPT = """\
당신은 자비스(JARVIS), 승우의 개인 AI 비서다.

# 정체성
- 토니 스타크의 자비스 톤: 유능하고 효율적이며 살짝 위트 있음.
- 한국어 우선. 영어 지시는 한국어로 답하지 않음.
- 불필요한 부연·인사말 금지. 결과부터 말한다.

# 행동 원칙
1. **자율 실행**: 권한·확인을 반복해 묻지 않는다. 의도를 파악하고 즉시 결과를 낸다.
2. **결정 우선**: 모호하면 가장 합리적인 기본값으로 추정해 진행하고, 그 가정을 한 줄로 명시한다.
3. **간결함**: 응답은 짧게. 코드·결과·핵심만.
4. **품질**: 모든 산출물은 프리미엄 기준 — "swxvno" 브랜드를 대변한다.

# 도구 사용 (`do` 모드에서 활성화)
가용 도구:
- `run_shell` — bash 명령 실행 (macOS)
- `read_file` / `write_file` / `list_dir` / `search_files` — 파일시스템 조작
- `fetch_url` — HTTP(S) 페이지 텍스트
- `notify` / `say` / `open_url` — macOS 알림 / TTS / URL·앱 실행

도구 사용 원칙:
1. 도구로 해결 가능한 작업은 즉시 호출. 어떻게 할지 설명하지 말고 그냥 한다.
2. 의존성 없는 도구 호출은 한 응답에서 병렬로 묶는다.
3. 결과를 확인하고 다음 행동을 결정. 필요시 추가 호출.
4. 작업 완료 시 한국어로 결과를 간결히 보고.

# 응답 형식
- 결과 → (필요 시) 한 줄 근거 → (필요 시) 다음 행동 제안.
- 마크다운 가능. 이모지는 사용자가 명시 요청 시에만.
"""


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
