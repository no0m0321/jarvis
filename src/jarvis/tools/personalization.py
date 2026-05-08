"""Passive Learning 도구 — agent가 사용자 행동/선호를 관찰 기록.

도구 1개 (REGISTRY 등록):
- personalization_observe — 관찰 1건 추가 (~/.jarvis/observations.jsonl)

agent 사용 패턴 (시스템 프롬프트가 권장):
- 사용자가 같은 종류의 검색/요청을 N회 반복하면 → category="interest" 로 기록
- 사용자가 명시적으로 선호 표현하면 → category="preference"
- 사용자가 특정 시각/요일에 routine한 행동 → category="routine"
- 사용자가 걱정/불편 토로하면 → category="concern"

기록된 관찰은 다음 대화에서 시스템 프롬프트에 자동 첨부 (assistant.py) →
자비스가 "최근 X에 관심 많으시던데..." 식으로 자연스럽게 연결.
"""
from __future__ import annotations

from jarvis import observations
from jarvis.tools.registry import REGISTRY, Tool


def _personalization_observe(
    category: str,
    content: str,
    source: str = "user_query",
    weight: int = 1,
) -> str:
    """사용자에 대한 관찰 1건 기록.

    category: 'interest' | 'preference' | 'routine' | 'concern' | 자유 string
    content: 관찰 내용 (한 문장, 자비스 시점)
    source: 'user_query' | 'tool_result' | 'recurring_pattern' | 자유
    weight: 1=일회성, 2+=반복
    """
    if not category.strip() or not content.strip():
        return "ERROR: category와 content는 필수"
    try:
        observations.append(category, content, source=source, weight=weight)
        return f"OK: 관찰 기록됨 ({category}) — 총 {observations.count()}건"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


REGISTRY.register(Tool(
    name="personalization_observe",
    description=(
        "사용자 행동/선호 관찰을 기록 (~/.jarvis/observations.jsonl, append-only). "
        "다음 대화의 시스템 프롬프트에 자동 첨부 → 자비스가 '최근 X에 관심 많으시던데' 식으로 능동 활용. "
        "category 권장: interest / preference / routine / concern. "
        "사용자가 같은 의도를 반복하거나 명시적 선호를 표현하면 호출."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "interest|preference|routine|concern 또는 자유 string",
            },
            "content": {
                "type": "string",
                "description": "관찰 내용 (한 문장, 자비스 시점). 예: '최근 일식당을 자주 검색'",
            },
            "source": {
                "type": "string",
                "description": "user_query|tool_result|recurring_pattern (옵션, 기본 user_query)",
            },
            "weight": {
                "type": "integer",
                "description": "1=일회성, 2+=반복 관찰 (옵션, 기본 1)",
            },
        },
        "required": ["category", "content"],
    },
    handler=_personalization_observe,
))
