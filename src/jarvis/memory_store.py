"""Vector store 기반 cross-session 회상 — chromadb optional.

설치:  pip install 'jarvis[memory]'

사용:
  from jarvis.memory_store import MemoryStore
  store = MemoryStore()
  store.add("주인님은 미니멀 디자인을 선호함", source="conversation")
  results = store.search("디자인 취향", limit=3)
  → [{"text": "주인님은 미니멀 디자인을 선호함", "score": 0.82, ...}, ...]

저장 경로: ~/.jarvis/vectorstore/
모델: chromadb 기본 (sentence-transformers all-MiniLM-L6-v2)

chromadb 미설치 시 graceful fallback — None 반환.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional


_STORE_DIR = Path.home() / ".jarvis" / "vectorstore"
_COLLECTION = "jarvis-memory"


class MemoryStore:
    """chromadb 기반 영구 vector memory."""

    def __init__(self) -> None:
        try:
            import chromadb  # type: ignore
        except ImportError:
            raise RuntimeError(
                "chromadb 미설치 — pip install 'jarvis[memory]' 또는 pip install chromadb"
            )
        _STORE_DIR.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(_STORE_DIR))
        self.coll = self.client.get_or_create_collection(_COLLECTION)

    def add(self, text: str, source: str = "manual", metadata: Optional[dict] = None) -> str:
        """문서 추가. 자동 ID 생성. 중복 없음 검사 — 동일 text면 skip."""
        import hashlib
        import time as _t
        text = text.strip()
        if not text:
            return ""
        doc_id = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        # 이미 있으면 skip
        existing = self.coll.get(ids=[doc_id])
        if existing.get("ids"):
            return doc_id
        meta = {"source": source, "ts": _t.time(), **(metadata or {})}
        self.coll.add(documents=[text], ids=[doc_id], metadatas=[meta])
        return doc_id

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """쿼리로 유사도 검색. 거리 → score 변환 (1 / (1 + dist))."""
        if not query.strip():
            return []
        r = self.coll.query(query_texts=[query], n_results=max(1, min(limit, 20)))
        out: List[dict] = []
        ids = (r.get("ids") or [[]])[0]
        docs = (r.get("documents") or [[]])[0]
        metas = (r.get("metadatas") or [[]])[0]
        dists = (r.get("distances") or [[]])[0]
        for i, doc_id in enumerate(ids):
            out.append({
                "id": doc_id,
                "text": docs[i] if i < len(docs) else "",
                "score": 1.0 / (1.0 + (dists[i] if i < len(dists) else 0)),
                "metadata": metas[i] if i < len(metas) else {},
            })
        return out

    def remove(self, doc_id: str) -> bool:
        if not doc_id:
            return False
        self.coll.delete(ids=[doc_id])
        return True

    def count(self) -> int:
        return self.coll.count()

    def clear(self) -> None:
        """전체 메모리 삭제 (위험)."""
        self.client.delete_collection(_COLLECTION)
        self.coll = self.client.get_or_create_collection(_COLLECTION)


_singleton: Optional[MemoryStore] = None


def get_store() -> Optional[MemoryStore]:
    """singleton 접근. chromadb 없으면 None."""
    global _singleton
    if _singleton is None:
        try:
            _singleton = MemoryStore()
        except Exception:
            return None
    return _singleton
