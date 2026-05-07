"""재미 도구 — joke, riddle, fact, compliment, motivation, fortune, name generators."""
from __future__ import annotations

import random

from jarvis.tools.registry import REGISTRY, Tool


_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything.",
    "I told my computer I needed a break, and it said 'no problem — I'll go to sleep.'",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "There are 10 kinds of people: those who understand binary, and those who don't.",
    "전공 시험 망쳤더니 친구가 위로해줬다. '괜찮아, 나도 망쳤어.' 그 친구는 의대생이었다.",
    "왜 자비스는 잠을 안 자나? 백그라운드 스레드라서.",
    "프로그래머가 가장 무서워하는 건? null pointer.",
    "I would tell you a UDP joke, but you might not get it.",
    "How many programmers does it take to change a light bulb? None — it's a hardware issue.",
    "Why did the developer go broke? Because he used up all his cache.",
]

_RIDDLES = [
    ("나는 도시도 있고 산도 있고 강도 있지만, 사람은 한 명도 없다. 나는 무엇일까?", "지도"),
    ("아침에 네 발, 점심에 두 발, 저녁에 세 발인 것은?", "사람 (인생)"),
    ("What has keys but cannot open locks?", "A piano"),
    ("The more you take, the more you leave behind. What are they?", "Footsteps"),
    ("입은 있어도 말을 못 하는 것은?", "강 / 병"),
    ("What gets wetter the more it dries?", "A towel"),
    ("I speak without a mouth and hear without ears. What am I?", "An echo"),
]

_FACTS = [
    "꿀은 부패하지 않는다. 3000년 전 이집트 무덤에서 발견된 꿀도 먹을 수 있었다.",
    "Octopuses have three hearts and blue blood.",
    "The Eiffel Tower can grow up to 6 inches taller in summer due to thermal expansion.",
    "바나나는 베리(berry)이고, 딸기는 베리가 아니다.",
    "Bananas are radioactive (very mildly — due to potassium-40).",
    "There are more possible chess games than atoms in the observable universe.",
    "달팽이는 최대 3년까지 잘 수 있다.",
    "고대 로마인들은 보라색 염료가 너무 비싸서, 황제만 입을 수 있었다.",
    "A day on Venus is longer than a year on Venus.",
    "Hot water freezes faster than cold water under certain conditions (Mpemba effect).",
]

_COMPLIMENTS = [
    "오늘 한 결정 하나하나가 미래의 나에게 도움이 될 거예요.",
    "어려운 문제를 끝까지 붙잡고 있는 그 끈기가 진짜 무기예요.",
    "당신의 호기심은 이 방에서 가장 빛나는 자산입니다.",
    "남들이 보지 못하는 디테일을 발견하는 능력이 정말 인상적이에요.",
    "지금 모습 그대로 충분히 잘하고 있어요.",
    "Your instinct on this is sharper than you give yourself credit for.",
    "You have the rare ability to make complicated things feel simple.",
    "Your patience with this problem is paying off — keep going.",
]

_MOTIVATIONS = [
    "완벽한 시작은 없다. 일단 시작하면 길은 보인다.",
    "Discipline beats motivation. 규칙적인 작은 행동이 큰 결과를 만든다.",
    "지금 1%의 진전이 1년 뒤 37배의 차이가 된다.",
    "It's not about being the best. It's about being better than you were yesterday.",
    "Energy follows attention — focus on what you can control.",
    "Done is better than perfect.",
    "압박감은 특권이다 — 누구나 받는 게 아니다.",
    "The cave you fear to enter holds the treasure you seek. — Joseph Campbell",
]

_FORTUNES = [
    "다음 24시간 안에 좋은 소식이 옵니다.",
    "오랫동안 미뤄둔 일을 끝낼 절호의 기회입니다.",
    "오늘 만나는 사람과의 대화가 길게 도움이 될 것입니다.",
    "당신의 직감을 신뢰하세요. 이번 주에는 정확합니다.",
    "A pleasant surprise is waiting in the next 48 hours.",
    "Your patience this week will be rewarded next week.",
    "지금 망설이는 결정 — 첫 번째 직감이 맞습니다.",
    "곧 만날 누군가가 새로운 관점을 가져다 줄 것입니다.",
]


def _joke() -> str:
    return random.choice(_JOKES)


def _riddle(reveal: bool = False) -> str:
    q, a = random.choice(_RIDDLES)
    return f"{q}\n\n[정답] {a}" if reveal else q


def _fact() -> str:
    return random.choice(_FACTS)


def _compliment(name: str = "") -> str:
    msg = random.choice(_COMPLIMENTS)
    return f"{name}, {msg}" if name else msg


def _motivation() -> str:
    return random.choice(_MOTIVATIONS)


def _fortune() -> str:
    return random.choice(_FORTUNES)


def _name_generator(kind: str = "fantasy", n: int = 5) -> str:
    """이름 생성기. kind: fantasy|sci-fi|petname|domain."""
    fantasy_first = ["Aer", "Bel", "Cor", "Dae", "Eth", "Fae", "Gar", "Hael",
                     "Ire", "Jor", "Kael", "Lor", "Myr", "Nia", "Ori", "Pyr",
                     "Quel", "Ran", "Sera", "Thal", "Ulr", "Vael", "Wyn", "Xan",
                     "Yor", "Zal"]
    fantasy_last = ["adra", "ion", "wyn", "thar", "olin", "myra", "anor",
                    "ondel", "ithar", "hyl", "rin", "vael", "estra", "zephir"]
    scifi_prefix = ["Neo", "Nexa", "Quan", "Vex", "Zyx", "Kyro", "Velo", "Auro",
                    "Nyra", "Drex", "Qor", "Tyr"]
    scifi_suffix = ["7", "9", "X", "Prime", "-V", "ndix", "tron", "ius", "th"]
    petname_first = ["Sunny", "Mochi", "Peanut", "Biscuit", "Pixel", "Toffee",
                     "Mango", "Sushi", "Marble", "Pebble", "Ginger", "Honey"]
    petname_last = ["paws", "wiggles", "tail", "nose", "boots", "spots"]

    out = []
    for _ in range(max(1, min(20, n))):
        if kind == "fantasy":
            out.append(random.choice(fantasy_first) + random.choice(fantasy_last))
        elif kind in ("sci-fi", "scifi"):
            out.append(random.choice(scifi_prefix) + random.choice(scifi_suffix))
        elif kind == "petname":
            out.append(random.choice(petname_first) +
                       (random.choice(petname_last) if random.random() < 0.4 else ""))
        elif kind == "domain":
            out.append(random.choice(petname_first).lower() +
                       random.choice(["", "ly", "ify", "io", "labs", "hq", "co"]) +
                       "." + random.choice(["com", "io", "app", "dev", "ai", "co"]))
        else:
            return f"ERROR: invalid kind '{kind}'. valid: fantasy|sci-fi|petname|domain"
    return "\n".join(out)


def _eight_ball_extended() -> str:
    """기존 magic_8ball 확장 — 더 다양한 답변."""
    answers = [
        "확실히 그렇다 ✨", "예측은 좋다 🌟", "당장 해라 🚀",
        "조금 더 기다려라 ⏳", "다시 물어봐라 🔄", "지금은 모호하다 🌫",
        "절대 아니다 ❌", "전혀 ✗", "위험하다 ⚠️",
        "아주 가능성 높다 ✅", "신호가 약하다 📡", "직감을 믿어라 🧭",
    ]
    return random.choice(answers)


REGISTRY.register(Tool(
    name="joke",
    description="짧은 농담 (한/영 혼합).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_joke,
))
REGISTRY.register(Tool(
    name="riddle",
    description="수수께끼 (reveal=true 시 정답 동봉).",
    input_schema={
        "type": "object",
        "properties": {"reveal": {"type": "boolean"}},
        "required": [],
    },
    handler=_riddle,
))
REGISTRY.register(Tool(
    name="random_fact",
    description="흥미로운 잡학 (한/영).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_fact,
))
REGISTRY.register(Tool(
    name="compliment",
    description="긍정적 메시지/칭찬.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string", "description": "이름 prefix (옵션)"}},
        "required": [],
    },
    handler=_compliment,
))
REGISTRY.register(Tool(
    name="motivation",
    description="동기 부여 한 마디.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_motivation,
))
REGISTRY.register(Tool(
    name="fortune",
    description="포춘 쿠키 스타일 한 줄 점.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_fortune,
))
REGISTRY.register(Tool(
    name="name_generator",
    description="이름 생성. kind=fantasy|sci-fi|petname|domain.",
    input_schema={
        "type": "object",
        "properties": {
            "kind": {"type": "string"},
            "n": {"type": "integer", "description": "기본 5"},
        },
        "required": [],
    },
    handler=_name_generator,
))
REGISTRY.register(Tool(
    name="eight_ball_extended",
    description="확장된 magic 8-ball (12 답변).",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_eight_ball_extended,
))
