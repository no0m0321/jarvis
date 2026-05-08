"""사용자 프로필 — 호칭, 첫 만남 여부, 영구 선호도.

저장: ~/.jarvis/profile.json
스키마:
{
  "title": "주인님",          # 자비스가 사용자를 부를 호칭
  "owner_name": "혁수",       # 사용자 이름 (선택)
  "first_met_at": "2026-05-08T10:00:00",  # 첫 만남 ISO 타임스탬프
  "interactions": 1,          # 총 대화 횟수 (첫 만남 시 1)
  "preferences": {            # 자유 형식 key-value
    "tone": "formal",
    "language": "ko"
  }
}

사용:
- assistant.py가 `is_first_meeting()` 으로 첫 만남 분기 → 시스템 프롬프트에 인사 + 호칭 묻기 지시
- agent가 사용자 호칭을 알아내면 `set_title("주인님")` 호출
- 모든 응답에서 시스템 프롬프트에 `read().get("title")` 자동 첨부
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

PROFILE_PATH = Path.home() / ".jarvis" / "profile.json"


def _default() -> dict[str, Any]:
    return {
        "title": "",                # 미정. 첫 만남 후 agent가 채움
        "owner_name": "",
        "first_met_at": "",
        "interactions": 0,
        "preferences": {},
    }


def read() -> dict[str, Any]:
    """프로필 읽기. 파일 없으면 default. 파일 손상 시 default."""
    if not PROFILE_PATH.exists():
        return _default()
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        # default와 merge — 누락 키 채우기
        merged = _default()
        merged.update(data)
        return merged
    except Exception:
        return _default()


def write(profile: dict[str, Any]) -> None:
    """프로필 저장 (atomic — 임시 파일 후 rename)."""
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PROFILE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(PROFILE_PATH)


def is_first_meeting() -> bool:
    """프로필 파일이 없거나 first_met_at이 비어있으면 첫 만남."""
    p = read()
    return not p.get("first_met_at")


def mark_first_meeting() -> None:
    """첫 만남 마킹 — first_met_at + interactions=1."""
    p = read()
    if p.get("first_met_at"):
        return  # 이미 첫 만남 끝남
    p["first_met_at"] = datetime.now().isoformat(timespec="seconds")
    p["interactions"] = 1
    write(p)


def increment_interactions() -> None:
    """대화 카운터 증가. 첫 만남 자동 마킹."""
    p = read()
    if not p.get("first_met_at"):
        p["first_met_at"] = datetime.now().isoformat(timespec="seconds")
    p["interactions"] = int(p.get("interactions", 0)) + 1
    write(p)


def set_title(title: str) -> None:
    """호칭 설정 — agent가 첫 만남 후 사용자에게 물어 알아낸 호칭."""
    title = title.strip()
    if not title:
        return
    p = read()
    p["title"] = title
    if not p.get("first_met_at"):
        p["first_met_at"] = datetime.now().isoformat(timespec="seconds")
    write(p)


def get_title() -> str:
    return read().get("title", "")


def set_preference(key: str, value: Any) -> None:
    p = read()
    p.setdefault("preferences", {})[key] = value
    write(p)


def get_preference(key: str, default: Any = None) -> Any:
    return read().get("preferences", {}).get(key, default)


def reset() -> None:
    """프로필 완전 초기화. 다음 호출에서 다시 첫 만남."""
    if PROFILE_PATH.exists():
        PROFILE_PATH.unlink()
