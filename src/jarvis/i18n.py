"""국제화 (i18n) — 자비스 다국어 지원.

지원 언어 (v0.6.0):
- ko (한국어)        — 기본, native system prompt
- en (English)       — native system prompt
- ja (日本語)        — English base + 일본어 응답 지시
- zh (中文 简体)     — English base + 중국어 응답 지시
- es (Español)       — English base + 스페인어 응답 지시
- fr (Français)      — English base + 프랑스어 응답 지시
- de (Deutsch)       — English base + 독일어 응답 지시
- pt (Português)     — English base + 포르투갈어 응답 지시

언어 결정 우선순위:
1. JARVIS_LANG 환경변수 (e.g., JARVIS_LANG=en)
2. ~/.jarvis/config.toml의 language 키
3. 시스템 locale (locale.getlocale()) — ko_KR → ko, en_US → en
4. fallback: en

확장 패턴:
- 새 언어 추가 시 LANGUAGES dict에 항목 추가 + (선택) PERSONAS_NATIVE에 native prompt
- agent의 호출 응답 언어는 system prompt에 명시되어 LLM이 따름 (강제)
"""
from __future__ import annotations

import locale as _locale
import os
from typing import Optional


# ──────────────── 언어 메타데이터 ────────────────
LANGUAGES: dict[str, dict[str, str]] = {
    "ko": {
        "name": "한국어",
        "english_name": "Korean",
        "native": "한국어",
        "flag": "🇰🇷",
        "default_title": "주인님",
        "tts_voice_macos": "Yuna",
        "tts_voice_windows": "Heami",
    },
    "en": {
        "name": "English",
        "english_name": "English",
        "native": "English",
        "flag": "🇺🇸",
        "default_title": "Sir",
        "tts_voice_macos": "Reed",
        "tts_voice_windows": "David",
    },
    "ja": {
        "name": "日本語",
        "english_name": "Japanese",
        "native": "日本語",
        "flag": "🇯🇵",
        "default_title": "ご主人様",
        "tts_voice_macos": "Kyoko",
        "tts_voice_windows": "Haruka",
    },
    "zh": {
        "name": "中文",
        "english_name": "Chinese (Simplified)",
        "native": "中文",
        "flag": "🇨🇳",
        "default_title": "主人",
        "tts_voice_macos": "Tingting",
        "tts_voice_windows": "Huihui",
    },
    "es": {
        "name": "Español",
        "english_name": "Spanish",
        "native": "Español",
        "flag": "🇪🇸",
        "default_title": "Señor",
        "tts_voice_macos": "Mónica",
        "tts_voice_windows": "Helena",
    },
    "fr": {
        "name": "Français",
        "english_name": "French",
        "native": "Français",
        "flag": "🇫🇷",
        "default_title": "Monsieur",
        "tts_voice_macos": "Thomas",
        "tts_voice_windows": "Hortense",
    },
    "de": {
        "name": "Deutsch",
        "english_name": "German",
        "native": "Deutsch",
        "flag": "🇩🇪",
        "default_title": "Herr",
        "tts_voice_macos": "Anna",
        "tts_voice_windows": "Hedda",
    },
    "pt": {
        "name": "Português",
        "english_name": "Portuguese",
        "native": "Português",
        "flag": "🇵🇹",
        "default_title": "Senhor",
        "tts_voice_macos": "Joana",
        "tts_voice_windows": "Helia",
    },
}

DEFAULT_LANG = "en"
SUPPORTED_LANGS = list(LANGUAGES.keys())


# ──────────────── 언어 결정 ────────────────
def detect_lang() -> str:
    """현재 활성 언어를 결정. env > config > locale > fallback."""
    # 1) JARVIS_LANG env (가장 우선)
    env_lang = (os.environ.get("JARVIS_LANG") or "").strip().lower()
    if env_lang:
        # ko_KR / ko-KR / ko 모두 ko로 정규화
        norm = env_lang.split(".")[0].split("_")[0].split("-")[0].lower()
        if norm in LANGUAGES:
            return norm

    # 2) ~/.jarvis/config.toml의 language
    try:
        from jarvis import user_config
        cfg = user_config.load()
        cfg_lang = (cfg.get("language") or "").strip().lower()
        if cfg_lang in LANGUAGES:
            return cfg_lang
    except Exception:
        pass

    # 3) 시스템 locale
    try:
        loc = _locale.getlocale()[0] or ""
        if loc:
            norm = loc.split(".")[0].split("_")[0].split("-")[0].lower()
            if norm in LANGUAGES:
                return norm
    except Exception:
        pass

    return DEFAULT_LANG


def lang_meta(code: Optional[str] = None) -> dict[str, str]:
    """언어 메타데이터 dict 반환. code 미지정 시 활성 언어."""
    code = (code or detect_lang()).lower()
    return LANGUAGES.get(code, LANGUAGES[DEFAULT_LANG])


def is_supported(code: str) -> bool:
    return (code or "").lower() in LANGUAGES


# ──────────────── 다국어 string (CLI 메시지 + 핵심 문구) ────────────────
# 첫 만남 인사 — agent가 시스템 프롬프트로 받는 4단계 영구 지시 (각 언어로 직접 출력)
FIRST_MEETING_GREETING: dict[str, str] = {
    "ko": (
        "사용자가 자비스를 처음 부르는 상황입니다. 첫 응답에서 반드시 다음 4가지를 모두 포함:\n"
        "  1) '주인님 반갑습니다.' (정중한 첫 인사)\n"
        "  2) '저는 당신의 일상을 보조할 자비스입니다.' (자기소개)\n"
        "  3) '제가 당신을 어떻게 호칭하면 좋을까요?' (호칭 묻기)\n"
        "  4) 호칭 듣고 나면 personalization_observe 도구로 "
        "category='preference', content='호칭은 ___' 기록 + memory_save로 영구 저장."
    ),
    "en": (
        "The user is calling Jarvis for the first time. The first response MUST include all 4:\n"
        "  1) 'Greetings, Sir.' (polite first greeting)\n"
        "  2) 'I am Jarvis, your personal AI assistant.' (introduce yourself)\n"
        "  3) 'How would you like me to address you?' (ask for preferred title)\n"
        "  4) Once they tell you their preferred title, call personalization_observe "
        "with category='preference', content='Title is ___' AND memory_save to persist."
    ),
    "ja": (
        "ユーザーが初めて自비스を呼んでいます。最初の応答は必ず4つすべてを含むこと:\n"
        "  1) 'ご主人様、はじめまして。' (丁寧な最初の挨拶)\n"
        "  2) '私はあなたの日常をサポートする자비스です。' (自己紹介)\n"
        "  3) 'あなたを何とお呼びすればよろしいでしょうか?' (呼び方を尋ねる)\n"
        "  4) 呼び方を教えてもらったら personalization_observe ツールで "
        "category='preference', content='呼称は ___' 記録 + memory_save で永続化。"
    ),
    "zh": (
        "用户首次呼叫自비스。第一个回复必须包含以下4项:\n"
        "  1) '主人, 您好.' (礼貌的第一次问候)\n"
        "  2) '我是자비스, 您的个人AI助手.' (自我介绍)\n"
        "  3) '请问您希望我如何称呼您?' (询问称呼)\n"
        "  4) 得知称呼后, 使用 personalization_observe 工具记录 "
        "category='preference', content='称呼为 ___' + memory_save 永久保存。"
    ),
    "es": (
        "El usuario llama a Jarvis por primera vez. La primera respuesta DEBE incluir los 4:\n"
        "  1) 'Bienvenido, Señor.' (saludo formal inicial)\n"
        "  2) 'Soy Jarvis, su asistente personal de IA.' (presentación)\n"
        "  3) '¿Cómo le gustaría que me dirija a usted?' (preguntar el título)\n"
        "  4) Cuando le diga el título, use personalization_observe "
        "con category='preference', content='Título es ___' Y memory_save para persistir."
    ),
    "fr": (
        "L'utilisateur appelle Jarvis pour la première fois. La première réponse DOIT inclure les 4 :\n"
        "  1) 'Bonjour, Monsieur.' (salutation polie)\n"
        "  2) 'Je suis Jarvis, votre assistant IA personnel.' (présentation)\n"
        "  3) 'Comment souhaiteriez-vous que je m'adresse à vous ?' (demander le titre)\n"
        "  4) Une fois le titre donné, utiliser personalization_observe "
        "avec category='preference', content='Titre est ___' ET memory_save pour persister."
    ),
    "de": (
        "Der Benutzer ruft Jarvis zum ersten Mal an. Die erste Antwort MUSS alle 4 enthalten:\n"
        "  1) 'Guten Tag, Herr.' (höfliche Begrüßung)\n"
        "  2) 'Ich bin Jarvis, Ihr persönlicher KI-Assistent.' (Vorstellung)\n"
        "  3) 'Wie möchten Sie, dass ich Sie anspreche?' (nach Anrede fragen)\n"
        "  4) Sobald Anrede bekannt, personalization_observe verwenden "
        "mit category='preference', content='Anrede ist ___' UND memory_save zur Speicherung."
    ),
    "pt": (
        "O usuário está chamando Jarvis pela primeira vez. A primeira resposta DEVE incluir os 4:\n"
        "  1) 'Bem-vindo, Senhor.' (saudação formal inicial)\n"
        "  2) 'Sou Jarvis, seu assistente pessoal de IA.' (apresentação)\n"
        "  3) 'Como gostaria que eu me dirigisse ao senhor?' (perguntar o título)\n"
        "  4) Ao saber o título, use personalization_observe "
        "com category='preference', content='Título é ___' E memory_save para persistir."
    ),
}


# 시스템 프롬프트 부가 — 비-네이티브 언어에서 base 영어 persona에 붙어 응답 언어 강제
RESPOND_IN_LANG_SUFFIX: dict[str, str] = {
    "ko": "ALWAYS respond in 한국어 (Korean). All replies, including tool outputs, in Korean only.",
    "en": "ALWAYS respond in English. All replies in English only.",
    "ja": "ALWAYS respond in 日本語 (Japanese). All replies in Japanese only. Use polite form (です/ます).",
    "zh": "ALWAYS respond in 中文 简体 (Simplified Chinese). All replies in Chinese only.",
    "es": "ALWAYS respond in Español (Spanish). All replies in Spanish only. Use formal 'usted' form.",
    "fr": "ALWAYS respond in Français (French). All replies in French only. Use formal 'vous' form.",
    "de": "ALWAYS respond in Deutsch (German). All replies in German only. Use formal 'Sie' form.",
    "pt": "ALWAYS respond in Português (Portuguese). All replies in Portuguese only. Use formal address.",
}


# CLI 메시지 (jarvis lang/profile 등 자체 출력) — 8개 언어
CLI_MESSAGES: dict[str, dict[str, str]] = {
    "lang_current": {
        "ko": "현재 언어",
        "en": "Current language",
        "ja": "現在の言語",
        "zh": "当前语言",
        "es": "Idioma actual",
        "fr": "Langue actuelle",
        "de": "Aktuelle Sprache",
        "pt": "Idioma atual",
    },
    "lang_set_ok": {
        "ko": "언어 설정 완료",
        "en": "Language set",
        "ja": "言語設定完了",
        "zh": "语言已设置",
        "es": "Idioma configurado",
        "fr": "Langue définie",
        "de": "Sprache eingestellt",
        "pt": "Idioma definido",
    },
    "lang_unsupported": {
        "ko": "지원 안 되는 언어",
        "en": "Unsupported language",
        "ja": "サポートされていない言語",
        "zh": "不支持的语言",
        "es": "Idioma no soportado",
        "fr": "Langue non prise en charge",
        "de": "Sprache nicht unterstützt",
        "pt": "Idioma não suportado",
    },
    "lang_supported_list": {
        "ko": "지원 언어 목록",
        "en": "Supported languages",
        "ja": "サポート言語一覧",
        "zh": "支持的语言列表",
        "es": "Idiomas soportados",
        "fr": "Langues prises en charge",
        "de": "Unterstützte Sprachen",
        "pt": "Idiomas suportados",
    },
}


def msg(key: str, lang: Optional[str] = None) -> str:
    """CLI 메시지 다국어 lookup. lang 미지정 시 활성 언어."""
    lang = (lang or detect_lang()).lower()
    bucket = CLI_MESSAGES.get(key, {})
    return bucket.get(lang) or bucket.get("en") or key


def first_meeting_greeting(lang: Optional[str] = None) -> str:
    """언어별 첫 만남 인사 시스템 프롬프트 지시."""
    lang = (lang or detect_lang()).lower()
    return FIRST_MEETING_GREETING.get(lang) or FIRST_MEETING_GREETING["en"]


def respond_in_lang_suffix(lang: Optional[str] = None) -> str:
    """언어별 응답 강제 지시 — 시스템 프롬프트에 첨부."""
    lang = (lang or detect_lang()).lower()
    return RESPOND_IN_LANG_SUFFIX.get(lang) or RESPOND_IN_LANG_SUFFIX["en"]


def default_title(lang: Optional[str] = None) -> str:
    """언어별 기본 호칭 (사용자가 호칭 알려주기 전까지 임시 사용)."""
    return lang_meta(lang)["default_title"]


def tts_voice(lang: Optional[str] = None, platform: str = "macos") -> str:
    """언어별 권장 TTS voice 이름 (macOS=`say`, Windows=pyttsx3 SAPI5)."""
    meta = lang_meta(lang)
    if platform == "windows":
        return meta["tts_voice_windows"]
    return meta["tts_voice_macos"]
