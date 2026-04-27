from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict

# 프로젝트 루트의 .env를 os.environ에 적재 (어디서 import하든 작동).
# 단, 기존 환경변수가 비어있을 때만 채움 (load_dotenv는 빈 값을 set으로 간주해 안 덮어씀 → 우회).
# 비-빈 shell env는 우선 — 사용자 명시 override 의도 보존.
_PROJECT_ENV = Path(__file__).resolve().parents[2] / ".env"
if _PROJECT_ENV.exists():
    for _k, _v in dotenv_values(_PROJECT_ENV).items():
        if _v and not os.environ.get(_k):
            os.environ[_k] = _v

# ~/.jarvis/config.toml 로드 → JARVIS_* env vars로 export
try:
    from jarvis import user_config as _user_config

    _user_config.apply_to_env()
except Exception:
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JARVIS_",
        extra="ignore",
    )

    anthropic_api_key: str = ""
    model: str = "claude-opus-4-7"
    fast_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 2048
    log_level: str = "INFO"

    def model_post_init(self, __context) -> None:
        import os

        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")


settings = Settings()
