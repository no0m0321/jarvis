"""범용 유틸 확장 — emoji, unicode, hex, mermaid, encrypt, ssh, dictionary, text stats, etc."""
from __future__ import annotations

import binascii
import os
import secrets
import subprocess
import unicodedata
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


# ── Emoji search ──────────────────────────────────────────────────────────
_EMOJI_DB = [
    ("😀", "grinning face smile happy"),
    ("😂", "laugh tears joy"),
    ("🥲", "smiling tear"),
    ("🥰", "love hearts smile"),
    ("😊", "blush smile happy"),
    ("😎", "cool sunglasses"),
    ("🤔", "thinking think"),
    ("😴", "sleep tired"),
    ("🤯", "mind blown shock"),
    ("🥳", "party celebrate"),
    ("😭", "cry sad tears"),
    ("😡", "angry mad rage"),
    ("👍", "thumbs up like ok"),
    ("👎", "thumbs down dislike"),
    ("🙏", "pray thanks please"),
    ("💪", "muscle strong"),
    ("🤝", "handshake deal"),
    ("👋", "wave hello hi bye"),
    ("✊", "fist solidarity"),
    ("🫶", "heart hands love"),
    ("❤️", "heart love red"),
    ("💔", "broken heart sad"),
    ("💯", "100 perfect"),
    ("🔥", "fire hot lit"),
    ("✨", "sparkle magic shine"),
    ("⭐", "star"),
    ("🌟", "glowing star"),
    ("💎", "diamond gem"),
    ("🎉", "party celebration"),
    ("🎁", "gift present"),
    ("🚀", "rocket launch fast"),
    ("✅", "check ok done yes"),
    ("❌", "x cross no fail"),
    ("⚠️", "warning caution"),
    ("🔔", "bell notification"),
    ("📌", "pin save"),
    ("📝", "note memo write"),
    ("📚", "books reading study"),
    ("💡", "idea bulb"),
    ("🧠", "brain think smart"),
    ("☕", "coffee cafe"),
    ("🍕", "pizza food"),
    ("🍣", "sushi food"),
    ("🍺", "beer drink"),
    ("🎵", "music note"),
    ("🎶", "music notes"),
    ("📷", "camera photo"),
    ("📸", "camera flash"),
    ("📱", "phone mobile"),
    ("💻", "laptop computer"),
    ("⌨️", "keyboard typing"),
    ("🖱️", "mouse"),
    ("🖥️", "desktop monitor"),
    ("🌍", "earth world"),
    ("🌙", "moon night"),
    ("☀️", "sun day weather"),
    ("☁️", "cloud weather"),
    ("🌧️", "rain weather"),
    ("⛅", "partly cloudy"),
    ("❄️", "snow cold winter"),
    ("🐶", "dog puppy"),
    ("🐱", "cat kitten"),
    ("🦊", "fox"),
    ("🐻", "bear"),
    ("🐼", "panda"),
    ("🌸", "cherry blossom flower"),
    ("🌹", "rose flower"),
    ("🌻", "sunflower"),
    ("🍀", "clover lucky"),
    ("🌳", "tree nature"),
    ("🏃", "run running"),
    ("🚶", "walk walking"),
    ("🧘", "meditation yoga zen"),
    ("🏋️", "lift workout gym"),
    ("⚡", "lightning fast power"),
    ("🎯", "target goal aim"),
    ("🎨", "art paint creative"),
    ("📊", "chart graph data"),
    ("🔒", "lock secure"),
    ("🔑", "key"),
    ("🛠️", "tools fix"),
    ("⏰", "alarm clock"),
    ("⏳", "hourglass wait"),
    ("📍", "pin location"),
    ("🏠", "home house"),
]


def _emoji_search(query: str, max_results: int = 20) -> str:
    """간단 keyword search."""
    q = query.lower()
    matches = []
    for emo, kws in _EMOJI_DB:
        if q in kws.lower() or q == emo:
            matches.append(f"{emo}  {kws}")
            if len(matches) >= max_results:
                break
    return "\n".join(matches) or f"(no match for '{query}')"


REGISTRY.register(Tool(
    name="emoji_search",
    description="키워드로 이모지 찾기 (한글/영어 키워드).",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "description": "기본 20"},
        },
        "required": ["query"],
    },
    handler=_emoji_search,
))


# ── Unicode info ──────────────────────────────────────────────────────────
def _unicode_info(text: str) -> str:
    """각 문자의 codepoint + 이름 + 카테고리."""
    out = []
    for ch in text[:50]:
        try:
            name = unicodedata.name(ch)
        except ValueError:
            name = "(no name)"
        cat = unicodedata.category(ch)
        out.append(f"{ch}  U+{ord(ch):04X}  {cat}  {name}")
    return "\n".join(out)


REGISTRY.register(Tool(
    name="unicode_info",
    description="문자열 각 문자의 codepoint + Unicode 이름.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    handler=_unicode_info,
))


# ── Hex view ──────────────────────────────────────────────────────────────
def _hex_view(path: str, offset: int = 0, length: int = 256) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        with p.open("rb") as f:
            f.seek(offset)
            data = f.read(min(length, 4096))
    except Exception as e:
        return f"ERROR: {e}"
    out = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{offset+i:08x}  {hex_part:<48}  |{ascii_part}|")
    return "\n".join(out) or "(empty)"


REGISTRY.register(Tool(
    name="hex_view",
    description="파일을 hex+ASCII로 덤프 (xxd 형식).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer"},
            "length": {"type": "integer", "description": "기본 256, 최대 4096"},
        },
        "required": ["path"],
    },
    handler=_hex_view,
))


# ── File encrypt/decrypt (openssl AES-256-CBC) ───────────────────────────
def _encrypt_file(path: str, password: str, out_path: str = "") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    out = Path(out_path).expanduser() if out_path else p.with_suffix(p.suffix + ".enc")
    try:
        subprocess.run(
            ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt",
             "-in", str(p), "-out", str(out), "-pass", f"pass:{password}"],
            capture_output=True, timeout=30, check=True,
        )
        return f"OK: encrypted → {out} ({out.stat().st_size} bytes)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or b'').decode().strip()}"
    except Exception as e:
        return f"ERROR: {e}"


def _decrypt_file(path: str, password: str, out_path: str = "") -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    if out_path:
        out = Path(out_path).expanduser()
    elif p.suffix == ".enc":
        out = p.with_suffix("")
    else:
        out = p.with_suffix(p.suffix + ".dec")
    try:
        subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-salt",
             "-in", str(p), "-out", str(out), "-pass", f"pass:{password}"],
            capture_output=True, timeout=30, check=True,
        )
        return f"OK: decrypted → {out} ({out.stat().st_size} bytes)"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or b'').decode().strip()} (wrong password?)"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="encrypt_file",
    description="파일 AES-256-CBC 암호화 (openssl). out_path 미지정 시 .enc 추가.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "password": {"type": "string"},
            "out_path": {"type": "string"},
        },
        "required": ["path", "password"],
    },
    handler=_encrypt_file,
))
REGISTRY.register(Tool(
    name="decrypt_file",
    description="파일 AES-256-CBC 복호화 (openssl).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "password": {"type": "string"},
            "out_path": {"type": "string"},
        },
        "required": ["path", "password"],
    },
    handler=_decrypt_file,
))


# ── SSH keygen ────────────────────────────────────────────────────────────
def _ssh_keygen(name: str = "id_jarvis", comment: str = "jarvis") -> str:
    """~/.ssh/<name> 생성 (ed25519). 이미 존재 시 거부."""
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    key_path = ssh_dir / name
    if key_path.exists():
        return f"ERROR: already exists: {key_path}"
    try:
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(key_path),
             "-N", "", "-C", comment],
            capture_output=True, timeout=10, check=True,
        )
        pub = (key_path.with_suffix(".pub")).read_text(encoding="utf-8")
        return f"OK: keypair generated → {key_path}\nPUBLIC KEY:\n{pub.strip()}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or b'').decode().strip()}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="ssh_keygen",
    description="ed25519 SSH 키페어 생성 (~/.ssh/<name>).",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "기본 id_jarvis"},
            "comment": {"type": "string"},
        },
        "required": [],
    },
    handler=_ssh_keygen,
))


# ── Dictionary (macOS Dictionary.app via DCS) ────────────────────────────
def _dictionary_define(word: str) -> str:
    """macOS open dict:// — Dictionary.app으로 단어 lookup."""
    try:
        subprocess.run(["open", f"dict://{word}"], timeout=5, check=True)
        return f"OK: opened Dictionary for '{word}'"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="dictionary_define",
    description="macOS Dictionary.app으로 단어 정의 열기 (dict:// URL).",
    input_schema={
        "type": "object",
        "properties": {"word": {"type": "string"}},
        "required": ["word"],
    },
    handler=_dictionary_define,
))


# ── Text stats (chars/words/lines/sentences/avg) ─────────────────────────
def _text_stats(text: str) -> str:
    chars = len(text)
    chars_no_ws = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    words = len(text.split())
    lines = len(text.splitlines()) or 1
    sentences = sum(1 for c in text if c in ".!?。！？")
    sentences = max(sentences, 1)
    return (f"chars: {chars} (no ws: {chars_no_ws})\n"
            f"words: {words}\n"
            f"lines: {lines}\n"
            f"sentences: ~{sentences}\n"
            f"avg word len: {chars_no_ws/max(words,1):.2f}\n"
            f"avg words/sentence: {words/sentences:.2f}")


REGISTRY.register(Tool(
    name="text_stats",
    description="텍스트 통계 — chars/words/lines/sentences/avg.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    handler=_text_stats,
))


# ── Reverse text ─────────────────────────────────────────────────────────
def _reverse_text(text: str) -> str:
    return text[::-1]


REGISTRY.register(Tool(
    name="reverse_text",
    description="문자열 뒤집기.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    handler=_reverse_text,
))


# ── Mermaid render (CLI mmdc 필요) ───────────────────────────────────────
def _mermaid_render(source: str, out_path: str = "") -> str:
    if subprocess.run(["which", "mmdc"], capture_output=True).returncode != 0:
        return "WARN: mmdc 미설치. `npm i -g @mermaid-js/mermaid-cli` 필요."
    out = Path(out_path).expanduser() if out_path else Path.home() / ".jarvis" / "mermaid.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    src_file = Path.home() / ".jarvis" / "_mermaid.mmd"
    src_file.write_text(source, encoding="utf-8")
    try:
        subprocess.run(
            ["mmdc", "-i", str(src_file), "-o", str(out)],
            capture_output=True, timeout=20, check=True,
        )
        return f"OK: rendered → {out}"
    except subprocess.CalledProcessError as e:
        return f"ERROR: {(e.stderr or b'').decode().strip()}"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="mermaid_render",
    description="Mermaid 다이어그램 → SVG (mmdc CLI 필요).",
    input_schema={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Mermaid 코드"},
            "out_path": {"type": "string"},
        },
        "required": ["source"],
    },
    handler=_mermaid_render,
))


# ── Random secret token ──────────────────────────────────────────────────
def _secret_token(length: int = 32, kind: str = "hex") -> str:
    """kind: hex|urlsafe|bytes."""
    if kind == "hex":
        return secrets.token_hex(length)
    if kind == "urlsafe":
        return secrets.token_urlsafe(length)
    if kind == "bytes":
        return binascii.hexlify(secrets.token_bytes(length)).decode()
    return f"ERROR: kind must be hex|urlsafe|bytes"


REGISTRY.register(Tool(
    name="secret_token",
    description="암호학적 random token 생성. kind=hex|urlsafe|bytes.",
    input_schema={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "description": "기본 32"},
            "kind": {"type": "string"},
        },
        "required": [],
    },
    handler=_secret_token,
))


# ── Path expand / normalize ──────────────────────────────────────────────
def _path_info(path: str) -> str:
    p = Path(path).expanduser()
    abs_p = p.resolve() if p.exists() else p.absolute()
    info = {
        "input": path,
        "expanded": str(p),
        "absolute": str(abs_p),
        "exists": p.exists(),
        "is_file": p.is_file() if p.exists() else None,
        "is_dir": p.is_dir() if p.exists() else None,
        "parent": str(p.parent),
        "name": p.name,
        "stem": p.stem,
        "suffix": p.suffix,
    }
    return "\n".join(f"{k}: {v}" for k, v in info.items())


REGISTRY.register(Tool(
    name="path_info",
    description="경로 분석 — expand/abs/exists/parent/name/suffix.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_path_info,
))


# ── ANSI strip ───────────────────────────────────────────────────────────
def _ansi_strip(text: str) -> str:
    import re as _re
    return _re.sub(r"\x1b\[[0-9;]*[mK]", "", text)


REGISTRY.register(Tool(
    name="ansi_strip",
    description="ANSI 컬러 코드 제거.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    handler=_ansi_strip,
))
