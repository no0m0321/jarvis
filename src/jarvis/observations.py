"""Passive Learning — 사용자 행동/선호 관찰 기록.

저장: ~/.jarvis/observations.jsonl (append-only, JSONL)

각 observation:
{
  "ts": "2026-05-08T11:30:00",
  "category": "interest",          # 자유 string. interest/routine/preference/concern/etc.
  "content": "일식당을 자주 검색",  # 핵심 관찰 내용 (자비스가 직접 작성)
  "source": "user_query",          # 어디서 관찰됐는지 (user_query/tool_result/recurring_pattern)
  "weight": 1                      # 1=일회성, 2+=반복 관찰
}

사용:
- agent가 도구 `personalization_observe` 호출 → append(category, content, ...)
- assistant.py가 시스템 프롬프트 빌드 시 `recent(50)` 자동 첨부 → 자비스가 관찰을 인지하고 능동 제안

설계 원칙:
- append-only (수정/삭제 X — 정직한 기록)
- 자유 형식 (스키마 강제 X) — agent가 자비스답게 자유롭게 기록
- 사용자가 '/observations clear' 같은 명령으로만 삭제 가능
- 최대 10000줄 도달 시 가장 오래된 것부터 5000줄 자동 archive (~/.jarvis/observations.archive.jsonl)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

OBSERVATIONS_PATH = Path.home() / ".jarvis" / "observations.jsonl"
ARCHIVE_PATH = Path.home() / ".jarvis" / "observations.archive.jsonl"
_MAX_LINES = 10000
_ARCHIVE_KEEP = 5000  # 보관 후 최근 5000줄만 남김


def append(
    category: str,
    content: str,
    *,
    source: str = "user_query",
    weight: int = 1,
    extra: dict[str, Any] | None = None,
) -> None:
    """관찰 1개 append. 호출자는 agent (도구) 또는 internal jarvis 컴포넌트."""
    OBSERVATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "category": str(category).strip()[:40] or "uncategorized",
        "content": str(content).strip()[:500],
        "source": str(source).strip()[:40] or "user_query",
        "weight": max(1, int(weight)),
    }
    if extra:
        record["extra"] = {k: str(v)[:200] for k, v in extra.items()}
    with OBSERVATIONS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    _maybe_rotate()


def recent(n: int = 50) -> list[dict[str, Any]]:
    """최근 n개 observation 반환 (최신 마지막)."""
    if not OBSERVATIONS_PATH.exists():
        return []
    try:
        with OBSERVATIONS_PATH.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def by_category(category: str, limit: int = 100) -> list[dict[str, Any]]:
    """특정 category 필터. 최근부터 limit개."""
    cat = category.strip().lower()
    matches = []
    for rec in reversed(recent(_MAX_LINES)):
        if rec.get("category", "").lower() == cat:
            matches.append(rec)
            if len(matches) >= limit:
                break
    return list(reversed(matches))  # 시간순 정렬


def count() -> int:
    """전체 observation 개수."""
    if not OBSERVATIONS_PATH.exists():
        return 0
    try:
        with OBSERVATIONS_PATH.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def clear() -> int:
    """모든 observations 삭제 + 삭제된 줄 수 반환. 사용자 명시 요청 시만."""
    if not OBSERVATIONS_PATH.exists():
        return 0
    n = count()
    OBSERVATIONS_PATH.unlink()
    return n


def _maybe_rotate() -> None:
    """파일 크기가 _MAX_LINES 초과 시 오래된 절반을 archive로 이동."""
    try:
        with OBSERVATIONS_PATH.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return
    if len(lines) <= _MAX_LINES:
        return
    # 오래된 (len - _ARCHIVE_KEEP) 줄을 archive로
    cutoff = len(lines) - _ARCHIVE_KEEP
    archived = lines[:cutoff]
    keep = lines[cutoff:]
    # archive append
    with ARCHIVE_PATH.open("a", encoding="utf-8") as f:
        f.writelines(archived)
    # 새 파일로 keep 만 남기기
    with OBSERVATIONS_PATH.open("w", encoding="utf-8") as f:
        f.writelines(keep)


def format_for_system_prompt(n: int = 50) -> str:
    """시스템 프롬프트에 첨부할 형태로 포맷."""
    obs = recent(n)
    if not obs:
        return ""
    lines = ["# 사용자 관찰 (~/.jarvis/observations.jsonl)"]
    lines.append(
        "당신이 이전에 관찰한 사용자의 패턴/관심사. 해당 맥락에서 능동적으로 활용 가능 "
        "(예: '최근 X에 자주 관심 보이셨는데' 식으로 자연스럽게 연결). 너무 자주 언급하면 부담스러우니 적절히."
    )
    for rec in obs[-30:]:
        ts = rec.get("ts", "")[:10]  # 날짜만
        lines.append(f"- [{ts}] [{rec.get('category')}] {rec.get('content')}")
    return "\n".join(lines)
