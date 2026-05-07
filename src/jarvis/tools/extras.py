"""번역, 재미 도구, Apple Shortcuts, Spotify, 추가 macOS 통합."""
from __future__ import annotations

import json
import os
import random
import subprocess
from datetime import datetime

from jarvis.tools.registry import REGISTRY, Tool


# ─── Translation (LLM 기반) ─────────────────────────────────────────

def _translate(text: str, target_lang: str = "en", source_lang: str = "auto") -> str:
    """Anthropic Claude로 번역. fast model 사용."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return "anthropic SDK 미설치"
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return "ANTHROPIC_API_KEY 미설정"
    client = Anthropic(api_key=key)
    src = "" if source_lang == "auto" else f"({source_lang}에서) "
    msg = client.messages.create(
        model=os.environ.get("JARVIS_FAST_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                f"다음 텍스트를 {src}{target_lang}로 번역. 번역만 출력, 설명·인용 금지:\n\n{text}"
            ),
        }],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


# ─── Fun ────────────────────────────────────────────────────────────

def _dice_roll(sides: int = 6, count: int = 1) -> str:
    """주사위. 예: dice_roll(20, 3) → 3개의 D20 굴림."""
    sides = max(2, min(sides, 1000))
    count = max(1, min(count, 100))
    rolls = [random.randint(1, sides) for _ in range(count)]
    return json.dumps({"rolls": rolls, "sum": sum(rolls), "sides": sides, "count": count}, ensure_ascii=False)


def _coin_flip(count: int = 1) -> str:
    count = max(1, min(count, 100))
    flips = [random.choice(["앞", "뒤"]) for _ in range(count)]
    return json.dumps({"flips": flips, "heads": flips.count("앞"), "tails": flips.count("뒤")}, ensure_ascii=False)


def _random_choice(options: str) -> str:
    """쉼표 구분 옵션 중 random 선택. 예: '피자,햄버거,파스타'."""
    items = [x.strip() for x in options.split(",") if x.strip()]
    if not items:
        return "(빈 옵션)"
    return random.choice(items)


def _magic_8ball(question: str = "") -> str:
    """매직 8볼 — 질문에 random 답."""
    answers = [
        "예 — 확실합니다", "예 — 그럴 거예요", "긍정적으로 보입니다", "전망이 좋아요",
        "확실하지 않아요", "다시 물어보세요", "지금 답변하기 어려워요",
        "그렇게 보이지 않아요", "아니오", "전망이 나쁩니다", "매우 의심스럽네요",
    ]
    return random.choice(answers)


def _quote_of_day() -> str:
    """무료 quotes API."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.quotable.io/random", timeout=5) as r:
            return r.read().decode()
    except Exception:
        # Fallback 명언
        quotes = [
            ("Steve Jobs", "Stay hungry. Stay foolish."),
            ("Marcus Aurelius", "You have power over your mind — not outside events."),
            ("Lao Tzu", "A journey of a thousand miles begins with a single step."),
            ("Einstein", "Imagination is more important than knowledge."),
        ]
        a, c = random.choice(quotes)
        return json.dumps({"author": a, "content": c}, ensure_ascii=False)


# ─── Apple Shortcuts ─────────────────────────────────────────────────

def _shortcuts_list() -> str:
    """등록된 macOS Shortcuts 목록."""
    try:
        r = subprocess.run(["shortcuts", "list"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except FileNotFoundError:
        return "shortcuts CLI 없음 (macOS 12+ 필요)"


def _shortcuts_run(name: str, input_text: str = "") -> str:
    """Shortcut 실행."""
    try:
        args = ["shortcuts", "run", name]
        if input_text:
            args += ["--input-path", "-"]
            r = subprocess.run(args, input=input_text, capture_output=True, text=True, timeout=60)
        else:
            r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            return r.stdout.strip() or "(완료)"
        return f"실패: {r.stderr.strip()[:200]}"
    except FileNotFoundError:
        return "shortcuts CLI 없음"


# ─── Spotify ─────────────────────────────────────────────────────────

def _spotify_playpause() -> str:
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Spotify" to playpause'],
            capture_output=True, timeout=5,
        )
        return "OK"
    except Exception as e:
        return f"실패: {e}"


def _spotify_next() -> str:
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "Spotify" to next track'],
            capture_output=True, timeout=5,
        )
        return "OK"
    except Exception as e:
        return f"실패: {e}"


def _spotify_current() -> str:
    """현재 재생 중인 트랙."""
    script = '''
tell application "Spotify"
    if it is running then
        if player state is playing then
            return (artist of current track) & " — " & (name of current track) & " (" & (album of current track) & ")"
        else
            return "(일시정지)"
        end if
    else
        return "(Spotify 미실행)"
    end if
end tell
'''
    try:
        r = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception as e:
        return f"실패: {e}"


def _spotify_search_play(query: str) -> str:
    """검색 후 첫 결과 재생 (Spotify URI 직접 사용은 Premium 필요. 여기선 search URL 열기)."""
    import urllib.parse
    url = f"spotify:search:{urllib.parse.quote(query)}"
    try:
        subprocess.run(["open", url], capture_output=True, timeout=5)
        return f"OK: Spotify에서 '{query}' 검색"
    except Exception as e:
        return f"실패: {e}"


# ─── macOS 추가 ─────────────────────────────────────────────────────

def _dnd_toggle() -> str:
    """Do Not Disturb 토글 (Shortcuts 'Toggle DND' 등록 필요)."""
    try:
        r = subprocess.run(
            ["shortcuts", "run", "Toggle Do Not Disturb"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return "OK"
    except FileNotFoundError:
        pass
    return "Shortcuts에 'Toggle Do Not Disturb' 등록 필요"


def _dock_hide_show(hide: bool = True) -> str:
    """Dock 숨김/표시."""
    val = "true" if hide else "false"
    try:
        subprocess.run(
            ["defaults", "write", "com.apple.dock", "autohide", "-bool", val],
            check=True, timeout=5,
        )
        subprocess.run(["killall", "Dock"], timeout=5)
        return f"Dock autohide={val}"
    except Exception as e:
        return f"실패: {e}"


def _menubar_clock() -> str:
    """메뉴바 시계 포맷 가져오기."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")


def _trash_count() -> str:
    """휴지통 항목 수."""
    try:
        r = subprocess.run(
            ["osascript", "-e", 'tell application "Finder" to count items of trash'],
            capture_output=True, text=True, timeout=5,
        )
        return f"{r.stdout.strip()} 항목"
    except Exception as e:
        return f"실패: {e}"


def _disk_usage() -> str:
    """디스크 용량."""
    try:
        r = subprocess.run(["df", "-H", "/"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception as e:
        return f"실패: {e}"


def _public_ip() -> str:
    """공인 IP."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as r:
            return r.read().decode()
    except Exception as e:
        return f"실패: {e}"


# ─── REGISTER ────────────────────────────────────────────────────────

REGISTRY.register(Tool(
    name="translate",
    description="텍스트 번역 (Claude Haiku). target_lang: 'en','ko','ja','zh' 등. source 'auto' 가능.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "target_lang": {"type": "string", "default": "en"},
            "source_lang": {"type": "string", "default": "auto"},
        },
        "required": ["text"],
    },
    handler=_translate,
))

REGISTRY.register(Tool(
    name="dice_roll",
    description="주사위 굴림. sides: 면 수, count: 개수.",
    input_schema={
        "type": "object",
        "properties": {"sides": {"type": "integer", "default": 6}, "count": {"type": "integer", "default": 1}},
    },
    handler=_dice_roll,
))
REGISTRY.register(Tool(
    name="coin_flip",
    description="동전 던지기. count: 개수.",
    input_schema={"type": "object", "properties": {"count": {"type": "integer", "default": 1}}},
    handler=_coin_flip,
))
REGISTRY.register(Tool(
    name="random_choice",
    description="쉼표 구분 옵션 중 random 선택. 예: '피자,햄버거,파스타'.",
    input_schema={"type": "object", "properties": {"options": {"type": "string"}}, "required": ["options"]},
    handler=_random_choice,
))
REGISTRY.register(Tool(
    name="magic_8ball",
    description="매직 8볼 — 의사결정 보조.",
    input_schema={"type": "object", "properties": {"question": {"type": "string", "default": ""}}},
    handler=_magic_8ball,
))
REGISTRY.register(Tool(
    name="quote_of_day",
    description="명언/quote of the day.",
    input_schema={"type": "object", "properties": {}},
    handler=_quote_of_day,
))

REGISTRY.register(Tool(
    name="shortcuts_list",
    description="등록된 macOS Shortcuts 목록.",
    input_schema={"type": "object", "properties": {}},
    handler=_shortcuts_list,
))
REGISTRY.register(Tool(
    name="shortcuts_run",
    description="macOS Shortcut 이름으로 실행. 선택적 input_text.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "input_text": {"type": "string", "default": ""},
        },
        "required": ["name"],
    },
    handler=_shortcuts_run,
))

REGISTRY.register(Tool(
    name="spotify_playpause",
    description="Spotify 재생/일시정지 토글.",
    input_schema={"type": "object", "properties": {}},
    handler=_spotify_playpause,
))
REGISTRY.register(Tool(
    name="spotify_next",
    description="Spotify 다음 곡.",
    input_schema={"type": "object", "properties": {}},
    handler=_spotify_next,
))
REGISTRY.register(Tool(
    name="spotify_current",
    description="Spotify 현재 재생 중 트랙.",
    input_schema={"type": "object", "properties": {}},
    handler=_spotify_current,
))
REGISTRY.register(Tool(
    name="spotify_search_play",
    description="Spotify 검색 후 재생 시작 (URL 호출).",
    input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    handler=_spotify_search_play,
))

REGISTRY.register(Tool(
    name="dnd_toggle",
    description="Do Not Disturb 토글 (Shortcuts 등록 필요).",
    input_schema={"type": "object", "properties": {}},
    handler=_dnd_toggle,
))
REGISTRY.register(Tool(
    name="dock_hide_show",
    description="macOS Dock 자동 숨김 토글.",
    input_schema={"type": "object", "properties": {"hide": {"type": "boolean", "default": True}}},
    handler=_dock_hide_show,
))
REGISTRY.register(Tool(
    name="trash_count",
    description="휴지통 항목 수.",
    input_schema={"type": "object", "properties": {}},
    handler=_trash_count,
))
REGISTRY.register(Tool(
    name="disk_usage",
    description="디스크 용량 (df -H /).",
    input_schema={"type": "object", "properties": {}},
    handler=_disk_usage,
))
REGISTRY.register(Tool(
    name="public_ip",
    description="공인 IP 주소 (ipify.org).",
    input_schema={"type": "object", "properties": {}},
    handler=_public_ip,
))
REGISTRY.register(Tool(
    name="now_full",
    description="현재 시각 — 날짜/시간/요일 포함 full timestamp.",
    input_schema={"type": "object", "properties": {}},
    handler=_menubar_clock,
))
