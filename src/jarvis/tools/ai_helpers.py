"""AI 헬퍼 도구 — Claude API 기반 cross-platform.

모든 도구는 ANTHROPIC_API_KEY 환경변수를 사용하며, 빠른 응답을 위해 Haiku 모델 기본.
JARVIS_FAST_MODEL 환경변수로 override 가능.

도구:
- text_summarize       텍스트 요약 (긴 문서 → 핵심)
- text_proofread       한국어/영어 교정 + 자연스러운 표현 제안
- text_explain         어려운 개념을 쉽게 풀이 (파인만 기법)
- text_korean_polish   한국어 어색한 표현 다듬기
- email_draft          이메일 초안 (격식/캐주얼/한국어/영어)
- code_explain         코드 한 토막 설명
- code_review_quick    빠른 코드 리뷰 (보안/성능/스타일)
- decision_helper      의사결정 보조 (장단점 정리)
- task_decompose       작업을 단계별로 분해
- meeting_notes_format 자유 메모 → 구조화된 회의록
"""
from __future__ import annotations

import os

from jarvis.tools.registry import REGISTRY, Tool


def _claude_call(
    user_prompt: str,
    *,
    system: str = "",
    max_tokens: int = 1024,
    model: str = "",
) -> str:
    """Claude Haiku 호출 헬퍼. 모든 ai_helpers가 공유."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return "ERROR: anthropic SDK 미설치 — pip install anthropic"
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return "ERROR: ANTHROPIC_API_KEY 미설정"
    model = model or os.environ.get("JARVIS_FAST_MODEL", "claude-haiku-4-5-20251001")
    try:
        client = Anthropic(api_key=key)
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = client.messages.create(**kwargs)
        return "".join(b.text for b in msg.content if b.type == "text").strip()
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ──────────────── text_summarize ────────────────
def _text_summarize(text: str, max_lines: int = 5, lang: str = "ko") -> str:
    """긴 텍스트를 N줄 이내로 요약."""
    if not text.strip():
        return "ERROR: empty text"
    sys_p = (
        "당신은 정확하고 간결한 요약 도우미입니다. "
        "핵심만 담고, 추측·과장·인용 금지. 결론과 근거를 분리해서 제시."
    )
    instr = (
        f"다음 텍스트를 {lang} 언어로 최대 {max_lines}줄(번호 매겨)로 요약해줘. "
        "원문 그대로 인용하지 말고 자기 말로 다시 표현:\n\n"
    )
    return _claude_call(instr + text, system=sys_p, max_tokens=1024)


REGISTRY.register(Tool(
    name="text_summarize",
    description="긴 텍스트를 N줄 이내로 요약 (Claude Haiku). lang: ko/en.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "max_lines": {"type": "integer", "description": "기본 5"},
            "lang": {"type": "string", "description": "ko/en, 기본 ko"},
        },
        "required": ["text"],
    },
    handler=_text_summarize,
))


# ──────────────── text_proofread ────────────────
def _text_proofread(text: str, lang: str = "ko") -> str:
    """맞춤법/문법/자연스러운 표현 교정. 변경 사항만 explanation 없이 출력."""
    if not text.strip():
        return "ERROR: empty text"
    sys_p = (
        "당신은 엄격하지만 자연스러움을 살리는 교정자입니다. "
        "오자, 문법 오류, 어색한 표현만 고칩니다. 의미는 절대 바꾸지 않습니다."
    )
    instr = (
        f"다음 {lang} 텍스트를 교정. 출력 형식:\n"
        "1) 교정본 — 자연스럽게 다듬은 전체 텍스트\n"
        "2) 변경점 — 항목별 (원본 → 교정, 이유 한 줄)\n"
        "변경할 게 없으면 '변경 없음'.\n\n"
        "원문:\n"
    )
    return _claude_call(instr + text, system=sys_p, max_tokens=1500)


REGISTRY.register(Tool(
    name="text_proofread",
    description="맞춤법/문법/표현 교정 + 변경점 설명 (Claude). lang: ko/en.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "lang": {"type": "string", "description": "ko/en, 기본 ko"},
        },
        "required": ["text"],
    },
    handler=_text_proofread,
))


# ──────────────── text_explain (Feynman) ────────────────
def _text_explain(concept: str, audience: str = "초등학생") -> str:
    """어려운 개념을 audience 수준으로 쉽게 설명 (파인만 기법)."""
    if not concept.strip():
        return "ERROR: empty concept"
    sys_p = (
        "당신은 어려운 개념을 누구나 이해할 수 있게 풀이하는 선생님입니다. "
        "전문 용어는 풀어쓰고, 비유와 일상 예시를 활용합니다."
    )
    instr = (
        f"'{concept}' 을 {audience} 수준으로 한국어로 풀이해줘.\n"
        "출력: (1) 한 문장 요약 (2) 일상 비유 1개 (3) 단계별 설명 3-5개 (4) 만약 잘못 이해하기 쉬운 부분 1줄.\n"
    )
    return _claude_call(instr, system=sys_p, max_tokens=1024)


REGISTRY.register(Tool(
    name="text_explain",
    description="어려운 개념을 쉽게 풀이 (파인만 기법). audience: '초등학생'/'고등학생'/'개발자' 등.",
    input_schema={
        "type": "object",
        "properties": {
            "concept": {"type": "string"},
            "audience": {"type": "string", "description": "기본 '초등학생'"},
        },
        "required": ["concept"],
    },
    handler=_text_explain,
))


# ──────────────── text_korean_polish ────────────────
def _text_korean_polish(text: str, tone: str = "neutral") -> str:
    """한국어 텍스트의 어색한/번역체 표현 다듬기.

    tone: neutral(일반), formal(존댓말 격식), casual(반말 친근), professional(공적 보고).
    """
    if not text.strip():
        return "ERROR: empty text"
    tone_map = {
        "neutral": "중립적이고 자연스러운 한국어",
        "formal": "정중한 존댓말, 격식 있는 한국어",
        "casual": "친근하고 부드러운 반말 또는 해체",
        "professional": "공적이고 명확한 보고체 한국어",
    }
    style = tone_map.get(tone, tone_map["neutral"])
    sys_p = (
        "당신은 어색한 번역체나 영어 직역체 한국어를 자연스럽게 다듬는 한국어 작가입니다. "
        "원래 의미는 보존하되, 문장 길이/어순/조사를 한국어 흐름에 맞게 재구성합니다."
    )
    instr = f"{style}로 다듬어줘. 결과만 출력 (설명 X):\n\n{text}"
    return _claude_call(instr, system=sys_p, max_tokens=1500)


REGISTRY.register(Tool(
    name="text_korean_polish",
    description=(
        "한국어 어색한 표현/번역체를 자연스럽게 다듬기 (Claude). "
        "neutral=중립적, formal=정중한 존댓말, casual=친근한 반말/해체, professional=공적 보고체."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "다듬을 한국어 텍스트"},
            "tone": {
                "type": "string",
                "description": "원하는 어조",
                "enum": ["neutral", "formal", "casual", "professional"],
                "default": "neutral",
            },
        },
        "required": ["text"],
    },
    handler=_text_korean_polish,
))


# ──────────────── email_draft ────────────────
def _email_draft(
    purpose: str,
    recipient: str = "",
    tone: str = "formal",
    lang: str = "ko",
) -> str:
    """이메일 초안. tone: formal/casual."""
    if not purpose.strip():
        return "ERROR: empty purpose"
    tone_desc = "정중하고 격식 있는" if tone == "formal" else "자연스럽고 친근한"
    sys_p = (
        f"당신은 {tone_desc} 이메일을 잘 쓰는 비서입니다. "
        "용건이 명확하고, 받는 사람의 시간을 존중하는 짧은 분량으로 작성합니다."
    )
    rec_part = f"받는 사람: {recipient}\n" if recipient else ""
    instr = (
        f"{rec_part}용건: {purpose}\n\n"
        f"{lang} 언어, {tone_desc} 톤으로 이메일 초안 작성. "
        "출력 형식:\n제목: ...\n본문:\n안녕하세요...\n"
    )
    return _claude_call(instr, system=sys_p, max_tokens=1024)


REGISTRY.register(Tool(
    name="email_draft",
    description="이메일 초안 작성 (Claude). tone: formal/casual, lang: ko/en.",
    input_schema={
        "type": "object",
        "properties": {
            "purpose": {"type": "string", "description": "이메일 용건/목적"},
            "recipient": {"type": "string", "description": "받는 사람 호칭 (옵션)"},
            "tone": {"type": "string", "description": "formal/casual"},
            "lang": {"type": "string", "description": "ko/en"},
        },
        "required": ["purpose"],
    },
    handler=_email_draft,
))


# ──────────────── code_explain ────────────────
def _code_explain(code: str, lang_hint: str = "") -> str:
    """코드 한 토막의 동작을 한국어로 설명."""
    if not code.strip():
        return "ERROR: empty code"
    sys_p = (
        "당신은 코드 동작을 정확히 분석하고 한국어로 설명하는 시니어 엔지니어입니다. "
        "추측 없이 보이는 사실만 설명하고, 부작용/성능 위험이 있으면 마지막에 별도로 명시합니다."
    )
    hint = f"언어 힌트: {lang_hint}\n\n" if lang_hint else ""
    instr = (
        f"{hint}다음 코드의 동작을 설명해줘. 출력:\n"
        "1) 한 문장 요약\n"
        "2) 단계별 흐름 (3-7개 bullet)\n"
        "3) 주의사항/부작용 (해당 시)\n\n"
        f"```\n{code}\n```"
    )
    return _claude_call(instr, system=sys_p, max_tokens=1500)


REGISTRY.register(Tool(
    name="code_explain",
    description="코드 한 토막 동작 설명 (Claude). lang_hint: 'python'/'js'/'rust' 등.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "lang_hint": {"type": "string", "description": "옵션"},
        },
        "required": ["code"],
    },
    handler=_code_explain,
))


# ──────────────── code_review_quick ────────────────
def _code_review_quick(code: str, focus: str = "all") -> str:
    """빠른 코드 리뷰. focus: all/security/performance/style."""
    if not code.strip():
        return "ERROR: empty code"
    focus_map = {
        "all": "보안, 성능, 스타일, 버그 가능성을 모두",
        "security": "보안 위험(injection, secrets 노출, 권한)을",
        "performance": "성능 (N+1, 불필요 alloc, 동기 I/O)을",
        "style": "스타일/가독성/네이밍을",
    }
    aspect = focus_map.get(focus, focus_map["all"])
    sys_p = (
        "당신은 시니어 코드 리뷰어입니다. 추측 없이 보이는 위험만 지적하고, "
        "각 지적은 (위험 수준 / 위치 / 권장 조치) 형식으로 출력합니다. "
        "지적할 게 없으면 '문제 없음'."
    )
    instr = f"{aspect} 검토. 한국어 답변. 출력 형식:\n[심각도] 위치 — 문제 — 권장 조치\n\n```\n{code}\n```"
    return _claude_call(instr, system=sys_p, max_tokens=1500)


REGISTRY.register(Tool(
    name="code_review_quick",
    description=(
        "빠른 코드 리뷰 (Claude). 보안/성능/스타일/버그 가능성을 (심각도/위치/조치) 형식으로. "
        "focus로 검토 영역을 좁혀서 더 깊이 파게 할 수 있음."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "리뷰할 코드 (전체 또는 일부)"},
            "focus": {
                "type": "string",
                "description": "검토 영역",
                "enum": ["all", "security", "performance", "style"],
                "default": "all",
            },
        },
        "required": ["code"],
    },
    handler=_code_review_quick,
))


# ──────────────── decision_helper ────────────────
def _decision_helper(question: str, options: str = "") -> str:
    """의사결정 보조. options 미지정 시 Claude가 후보 생성."""
    if not question.strip():
        return "ERROR: empty question"
    sys_p = (
        "당신은 균형 잡힌 의사결정 코치입니다. 한 쪽으로 기울어진 판단을 하지 않고, "
        "장단점을 객관적으로 정리하고 마지막에 (사용자가 X를 더 중시한다면) 식의 조건부 추천만 합니다."
    )
    opt_part = f"\n선택지: {options}" if options else "\n(선택지가 명시 안 됐으니 합리적 후보 2~3개 제안 후 비교)"
    instr = (
        f"질문: {question}{opt_part}\n\n"
        "한국어 출력:\n"
        "1) 핵심 트레이드오프 한 문장\n"
        "2) 옵션별 장점/단점 (각 3개)\n"
        "3) 조건부 추천 (어떤 가치를 우선할 때 어느 쪽)"
    )
    return _claude_call(instr, system=sys_p, max_tokens=1500)


REGISTRY.register(Tool(
    name="decision_helper",
    description="의사결정 보조 — 장단점 + 조건부 추천 (Claude). options: 쉼표 구분 후보 (옵션).",
    input_schema={
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "options": {"type": "string", "description": "쉼표 구분 후보 (옵션)"},
        },
        "required": ["question"],
    },
    handler=_decision_helper,
))


# ──────────────── task_decompose ────────────────
def _task_decompose(task: str, depth: int = 2) -> str:
    """큰 작업을 단계별로 분해. depth: 1=한 단계, 2=상위+하위, 3=상위+중간+하위."""
    if not task.strip():
        return "ERROR: empty task"
    depth = max(1, min(3, int(depth)))
    sys_p = (
        "당신은 큰 작업을 실행 가능한 단위로 쪼개는 프로젝트 매니저입니다. "
        "각 단계는 동사로 시작하고, 명확한 완료 조건이 있어야 합니다."
    )
    instr = (
        f"작업: {task}\n\n"
        f"한국어로 {depth}단계 깊이로 분해. 출력 형식 (Markdown 순서 list):\n"
        "1. 상위 단계 — 완료조건\n"
        "   1.1. 하위 단계 — 완료조건\n"
        "...\n"
        "예상 소요시간(상위 단계별) 마지막에 추가."
    )
    return _claude_call(instr, system=sys_p, max_tokens=1500)


REGISTRY.register(Tool(
    name="task_decompose",
    description="큰 작업을 단계별 실행 단위로 분해 (Claude). depth: 1/2/3.",
    input_schema={
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "depth": {"type": "integer", "description": "1/2/3, 기본 2"},
        },
        "required": ["task"],
    },
    handler=_task_decompose,
))


# ──────────────── meeting_notes_format ────────────────
def _meeting_notes_format(notes: str, attendees: str = "") -> str:
    """자유 형식 메모를 구조화된 회의록으로."""
    if not notes.strip():
        return "ERROR: empty notes"
    sys_p = (
        "당신은 자유 메모를 구조화된 회의록으로 정리하는 회의 비서입니다. "
        "메모에 없는 사실은 추가하지 않고, 말한 사람과 결정 사항을 분리합니다."
    )
    att_part = f"참석자: {attendees}\n\n" if attendees else ""
    instr = (
        f"{att_part}자유 메모를 한국어 회의록으로 정리. 출력 형식 (Markdown):\n"
        "## 안건\n- ...\n## 논의\n- ...\n## 결정 사항\n- ...\n## 액션 아이템 (담당자/기한)\n- [ ] ...\n## 다음 회의\n- ...\n\n"
        f"메모:\n{notes}"
    )
    return _claude_call(instr, system=sys_p, max_tokens=2000)


REGISTRY.register(Tool(
    name="meeting_notes_format",
    description="자유 메모를 구조화된 회의록으로 (Claude). attendees: 쉼표 구분 (옵션).",
    input_schema={
        "type": "object",
        "properties": {
            "notes": {"type": "string"},
            "attendees": {"type": "string", "description": "쉼표 구분 (옵션)"},
        },
        "required": ["notes"],
    },
    handler=_meeting_notes_format,
))
