"""파일 확장 — exif, ffprobe, find duplicates / large / old, symlink, chmod."""
from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from collections import defaultdict
from pathlib import Path

from jarvis.tools.registry import REGISTRY, Tool


def _run(cmd: list, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except Exception as e:
        return f"ERROR: {e}"


# ── EXIF (사진 메타) ──────────────────────────────────────────────────────
def _file_exif(path: str) -> str:
    """exiftool 우선, 없으면 mdls 폴백."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    if subprocess.run(["which", "exiftool"], capture_output=True).returncode == 0:
        return _run(["exiftool", str(p)])[:3000]
    out = _run(["mdls", str(p)])
    return "\n".join(l for l in out.splitlines()
                     if any(k in l for k in ("kMDItem", "Pixel", "Image", "GPS")))[:3000]


REGISTRY.register(Tool(
    name="file_exif",
    description="이미지/문서 EXIF 메타데이터 (exiftool 우선, mdls 폴백).",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_file_exif,
))


# ── ffprobe (audio/video 메타) ───────────────────────────────────────────
def _media_info(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    if subprocess.run(["which", "ffprobe"], capture_output=True).returncode != 0:
        return "WARN: ffprobe 미설치. `brew install ffmpeg` 필요."
    return _run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "default=noprint_wrappers=0", str(p),
    ], timeout=20)[:3000]


REGISTRY.register(Tool(
    name="media_info",
    description="오디오/비디오 메타 (ffprobe). codec, duration, bitrate.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_media_info,
))


# ── Find duplicates (by hash) ────────────────────────────────────────────
def _find_duplicates(path: str, min_size_kb: int = 100) -> str:
    """크기가 같은 파일들끼리만 hash 비교. 결과 상위 30."""
    p = Path(path).expanduser()
    if not p.is_dir():
        return f"ERROR: not a directory: {p}"
    by_size: dict = defaultdict(list)
    skip = {".git", "node_modules", ".venv", "__pycache__", ".cache"}
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            fp = Path(root) / f
            try:
                size = fp.stat().st_size
            except Exception:
                continue
            if size < min_size_kb * 1024:
                continue
            by_size[size].append(fp)

    candidates = [v for v in by_size.values() if len(v) > 1]
    if not candidates:
        return "(no duplicate candidates)"

    by_hash: dict = defaultdict(list)
    for group in candidates:
        for fp in group:
            try:
                with open(fp, "rb") as fh:
                    h = hashlib.md5(fh.read(1024 * 1024)).hexdigest()  # first 1MB hash
                by_hash[(fp.stat().st_size, h)].append(fp)
            except Exception:
                continue

    dups = [(k, v) for k, v in by_hash.items() if len(v) > 1]
    dups.sort(key=lambda x: -x[0][0])
    if not dups:
        return "(no duplicates after hash check)"
    out = []
    for (size, h), files in dups[:30]:
        out.append(f"\n[{size:,} bytes  md5(1MB)={h[:8]}]")
        for fp in files:
            out.append(f"  {fp}")
    return "\n".join(out)


REGISTRY.register(Tool(
    name="find_duplicates",
    description="크기+hash로 중복 파일 탐지 (min_size_kb 이상만).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "min_size_kb": {"type": "integer", "description": "기본 100"},
        },
        "required": ["path"],
    },
    handler=_find_duplicates,
))


# ── Find large / old files ───────────────────────────────────────────────
def _find_large(path: str, top: int = 20, min_mb: int = 10) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    skip = {".git", "node_modules", ".venv", "__pycache__"}
    rows = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            fp = Path(root) / f
            try:
                size = fp.stat().st_size
            except Exception:
                continue
            if size >= min_mb * 1024 * 1024:
                rows.append((size, fp))
    rows.sort(reverse=True)
    rows = rows[:top]
    if not rows:
        return f"(no files >= {min_mb}MB)"
    return "\n".join(f"{size/1024/1024:>8.1f} MB  {fp}" for size, fp in rows)


def _find_old(path: str, days: int = 365, top: int = 20) -> str:
    """N일 이상 access되지 않은 파일."""
    import time as _time
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    skip = {".git", "node_modules", ".venv", "__pycache__"}
    cutoff = _time.time() - days * 86400
    rows = []
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            fp = Path(root) / f
            try:
                st = fp.stat()
            except Exception:
                continue
            if st.st_atime < cutoff:
                rows.append((st.st_atime, fp))
    rows.sort()
    rows = rows[:top]
    if not rows:
        return f"(no files older than {days}d)"
    import datetime as _dt
    return "\n".join(f"{_dt.datetime.fromtimestamp(t).date()}  {fp}" for t, fp in rows)


REGISTRY.register(Tool(
    name="find_large_files",
    description="N MB 이상 파일 상위 N개 (재귀).",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "top": {"type": "integer", "description": "기본 20"},
            "min_mb": {"type": "integer", "description": "기본 10"},
        },
        "required": ["path"],
    },
    handler=_find_large,
))
REGISTRY.register(Tool(
    name="find_old_files",
    description="N일 이상 access되지 않은 파일 list.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "days": {"type": "integer", "description": "기본 365"},
            "top": {"type": "integer", "description": "기본 20"},
        },
        "required": ["path"],
    },
    handler=_find_old,
))


# ── Symlink ──────────────────────────────────────────────────────────────
def _symlink_create(target: str, link: str) -> str:
    t = Path(target).expanduser()
    l = Path(link).expanduser()
    if not t.exists():
        return f"ERROR: target not found: {t}"
    if l.exists() or l.is_symlink():
        return f"ERROR: link path exists: {l}"
    try:
        l.parent.mkdir(parents=True, exist_ok=True)
        l.symlink_to(t)
        return f"OK: {l} → {t}"
    except Exception as e:
        return f"ERROR: {e}"


def _symlink_resolve(path: str) -> str:
    p = Path(path).expanduser()
    if not p.is_symlink():
        return f"(not a symlink: {p})"
    return f"{p} → {os.readlink(p)} (resolved: {p.resolve()})"


REGISTRY.register(Tool(
    name="symlink_create",
    description="심볼릭 링크 생성 (link → target).",
    input_schema={
        "type": "object",
        "properties": {
            "target": {"type": "string"},
            "link": {"type": "string"},
        },
        "required": ["target", "link"],
    },
    handler=_symlink_create,
))
REGISTRY.register(Tool(
    name="symlink_resolve",
    description="심볼릭 링크 target 조회.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    handler=_symlink_resolve,
))


# ── chmod ────────────────────────────────────────────────────────────────
def _chmod_set(path: str, mode: str) -> str:
    """mode: 8진수 string, 예: '755'."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    try:
        m = int(mode, 8)
        os.chmod(p, m)
        st = p.stat()
        return f"OK: {p} → {stat.filemode(st.st_mode)} ({oct(st.st_mode)[-3:]})"
    except Exception as e:
        return f"ERROR: {e}"


REGISTRY.register(Tool(
    name="chmod_set",
    description="파일/폴더 권한 변경 (8진수 mode, 예: '755').",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "mode": {"type": "string", "description": "예: 755, 644"},
        },
        "required": ["path", "mode"],
    },
    handler=_chmod_set,
))


# ── tar / gz extract ─────────────────────────────────────────────────────
def _tar_extract(archive: str, dest: str = "") -> str:
    p = Path(archive).expanduser()
    if not p.exists():
        return f"ERROR: not found: {p}"
    d = Path(dest).expanduser() if dest else p.parent
    d.mkdir(parents=True, exist_ok=True)
    return _run(["tar", "-xvf", str(p), "-C", str(d)], timeout=60)[-1500:]


REGISTRY.register(Tool(
    name="tar_extract",
    description="tar/tgz/tbz 압축 해제.",
    input_schema={
        "type": "object",
        "properties": {
            "archive": {"type": "string"},
            "dest": {"type": "string"},
        },
        "required": ["archive"],
    },
    handler=_tar_extract,
))


# ── Empty trash count + size ─────────────────────────────────────────────
def _trash_size() -> str:
    trash = Path.home() / ".Trash"
    if not trash.exists():
        return "(no Trash)"
    total = 0
    n = 0
    for root, _, files in os.walk(trash):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
                n += 1
            except Exception:
                continue
    return f"trash: {n} files, {total/1024/1024:.1f} MB"


REGISTRY.register(Tool(
    name="trash_size",
    description="휴지통 항목 수 + 총 크기.",
    input_schema={"type": "object", "properties": {}, "required": []},
    handler=_trash_size,
))
