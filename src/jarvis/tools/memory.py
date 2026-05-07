"""Vector memory 도구 — LLM이 cross-session 사실을 저장/회상.

chromadb 미설치 시 graceful fail — 사용자에게 설치 안내.
"""
from __future__ import annotations

import json

from jarvis.tools.registry import REGISTRY, Tool


def _memory_save(text: str, source: str = "agent") -> str:
    from jarvis.memory_store import get_store
    store = get_store()
    if store is None:
        return "memory store 비활성 — pip install 'jarvis[memory]' 후 사용 가능"
    doc_id = store.add(text, source=source)
    return json.dumps({"saved": True, "id": doc_id, "total": store.count()}, ensure_ascii=False)


def _memory_recall(query: str, limit: int = 3) -> str:
    from jarvis.memory_store import get_store
    store = get_store()
    if store is None:
        return "memory store 비활성 — pip install 'jarvis[memory]' 후 사용 가능"
    results = store.search(query, limit=limit)
    return json.dumps(results, ensure_ascii=False, default=str)


def _memory_count() -> str:
    from jarvis.memory_store import get_store
    store = get_store()
    if store is None:
        return "0 (memory store 비활성)"
    return str(store.count())


REGISTRY.register(Tool(
    name="memory_save",
    description="사용자에 대한 사실/선호/약속을 vector memory에 영구 저장. cross-session 회상 가능. "
                "예: '주인님은 9시에 자고 6시에 일어남', '다음 주 화요일 미팅 예정'.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "저장할 사실/선호/이벤트"},
            "source": {"type": "string", "description": "출처 태그", "default": "agent"},
        },
        "required": ["text"],
    },
    handler=_memory_save,
))

REGISTRY.register(Tool(
    name="memory_recall",
    description="vector memory에서 query 기반 유사도 검색. score 높을수록 관련성 ↑. "
                "사용자에 대한 정보 필요 시 우선 호출.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "검색 query (자연어)"},
            "limit": {"type": "integer", "description": "최대 결과 수", "default": 3},
        },
        "required": ["query"],
    },
    handler=_memory_recall,
))

REGISTRY.register(Tool(
    name="memory_count",
    description="vector memory에 저장된 총 문서 수.",
    input_schema={"type": "object", "properties": {}},
    handler=_memory_count,
))
