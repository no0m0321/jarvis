"""중앙 로깅 — 모든 모듈이 통일된 logger 사용.

사용:
    from jarvis.logger import get_logger
    log = get_logger(__name__)
    log.warning("msg")
    log.error("msg %s", e)

환경변수:
- JARVIS_LOG_LEVEL: DEBUG/INFO/WARNING/ERROR (기본 INFO)
- JARVIS_LOG_FILE: stderr 외에 추가 file (기본 ~/.jarvis/jarvis.log)
- JARVIS_LOG_FORMAT: "console" (인간 읽기) 또는 "json" (JSON Lines, 기본 console)

설계:
- 단일 root logger 'jarvis' — 모든 sub-logger가 propagate
- StreamHandler (stderr) + RotatingFileHandler (~/.jarvis/jarvis.log, 5MB × 3)
- secret 마스킹: ANTHROPIC_API_KEY 등 알려진 secret 환경변수 값을 자동으로 '***' 처리
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import sys
from pathlib import Path
from typing import Optional

_INITIALIZED = False
_LOG_DIR = Path.home() / ".jarvis"

# 알려진 secret 환경변수 — 이 값들은 로그에서 자동 마스킹
_SECRET_ENV_KEYS = (
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "STRIPE_SECRET_KEY",
    "GITHUB_TOKEN", "TELEGRAM_BOT_TOKEN", "SLACK_WEBHOOK_URL",
    "DISCORD_WEBHOOK_URL", "SMTP_PASS", "DATABASE_URL",
)


class _SecretMaskingFilter(logging.Filter):
    """log record에서 secret 값을 마스킹.

    환경변수에 secret이 설정되어 있으면 그 값이 log 메시지/args에 들어왔을 때 '***'로 치환.
    """

    def __init__(self) -> None:
        super().__init__()
        self._secrets: list[str] = []
        self._refresh_secrets()

    def _refresh_secrets(self) -> None:
        self._secrets = []
        for k in _SECRET_ENV_KEYS:
            v = os.environ.get(k, "")
            if v and len(v) >= 12:  # 너무 짧으면 false positive 위험
                self._secrets.append(v)

    def filter(self, record: logging.LogRecord) -> bool:
        # 매 50번째 마다 secret list 갱신 (env 변경 감지)
        if record.relativeCreated and int(record.relativeCreated) % 50000 == 0:
            self._refresh_secrets()
        for secret in self._secrets:
            if isinstance(record.msg, str) and secret in record.msg:
                record.msg = record.msg.replace(secret, "***")
            # args도 검사
            if record.args:
                args = list(record.args) if isinstance(record.args, tuple) else [record.args]
                new_args = []
                for a in args:
                    if isinstance(a, str) and secret in a:
                        new_args.append(a.replace(secret, "***"))
                    else:
                        new_args.append(a)
                record.args = tuple(new_args) if isinstance(record.args, tuple) else new_args[0]
        return True


class _JsonFormatter(logging.Formatter):
    """JSON Lines 형식. 자동화 파이프라인 / observability 도구 친화."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _setup() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    level_name = os.environ.get("JARVIS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt_mode = os.environ.get("JARVIS_LOG_FORMAT", "console").lower()

    root = logging.getLogger("jarvis")
    root.setLevel(level)
    # 기존 handler 제거 (test reload 대응)
    for h in list(root.handlers):
        root.removeHandler(h)

    # secret 마스킹 필터
    secret_filter = _SecretMaskingFilter()

    # console handler (stderr)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    if fmt_mode == "json":
        console.setFormatter(_JsonFormatter())
    else:
        console.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        ))
    console.addFilter(secret_filter)
    root.addHandler(console)

    # file handler (rotating) — silent fallback
    log_file = os.environ.get("JARVIS_LOG_FILE", "")
    if not log_file:
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = str(_LOG_DIR / "jarvis.log")
        except Exception:
            log_file = ""
    if log_file:
        try:
            fh = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
            )
            fh.setLevel(level)
            fh.setFormatter(_JsonFormatter())
            fh.addFilter(secret_filter)
            root.addHandler(fh)
        except Exception:
            pass

    # propagate=False so other libraries' loggers don't double-emit ours
    root.propagate = False


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """모듈별 logger. name 미지정 시 'jarvis' root."""
    _setup()
    if not name:
        return logging.getLogger("jarvis")
    # 'jarvis.tools.shell' 같이 namespace
    if not name.startswith("jarvis"):
        name = f"jarvis.{name}"
    return logging.getLogger(name)


def mask_secrets(text: str) -> str:
    """수동 마스킹 — 외부에서 호출 가능 (e.g., user-facing 메시지)."""
    if not text:
        return text
    for k in _SECRET_ENV_KEYS:
        v = os.environ.get(k, "")
        if v and len(v) >= 12 and v in text:
            text = text.replace(v, "***")
    # bearer/token 패턴 (Anthropic, OpenAI sk-* / GitHub ghp_*)
    text = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "***", text)
    text = re.sub(r"ghp_[a-zA-Z0-9_]{20,}", "***", text)
    text = re.sub(r"github_pat_[a-zA-Z0-9_]{30,}", "***", text)
    return text
