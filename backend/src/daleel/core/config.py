"""Application settings.

All settings come from environment variables (or a `.env` file in the backend
folder). Nothing secret is written in code. In production the app refuses to
start with a weak signing secret (closes BUG-038).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = BACKEND_DIR.parent

_DEV_SECRET = "dev-only-secret-change-me-dev-only-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    environment: str = "development"  # development | production | test
    app_name: str = "Daleel"

    # Database. The default points at a local PostgreSQL listening on a Unix socket.
    database_url: str = "postgresql://postgres@/daleel?host=/tmp"

    # Where uploaded files and generated Parquet and reports are kept (local storage).
    data_dir: Path = BACKEND_DIR / "var"

    # Paths to versioned configuration kept in git.
    rulebook_dir: Path = REPO_DIR / "rulebook"
    mappings_dir: Path = REPO_DIR / "mappings"
    sources_dir: Path = REPO_DIR / "docs" / "sources" / "sbp"

    # Session tokens for the demo workspaces.
    jwt_secret: str = _DEV_SECRET
    session_hours: int = 12

    # Upload limits.
    max_upload_mb: int = 50

    # Browser origins allowed to call the API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # AI gateway. "openrouter" for the demo, "ollama" for on premises, "off" for templates only.
    ai_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Tried in order. Free models first, because the demo must cost nothing to run.
    ai_models: str = "nvidia/nemotron-3.5-super-vl:free,openrouter/free"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen3.6:27b"
    ai_timeout_seconds: int = 90

    # Run the pipeline worker inside the API process (simplest for the demo).
    embedded_worker: bool = True

    @model_validator(mode="after")
    def _refuse_weak_secret_in_production(self) -> "Settings":
        if self.environment == "production" and (
            self.jwt_secret == _DEV_SECRET or len(self.jwt_secret) < 32
        ):
            raise ValueError(
                "JWT_SECRET must be set to a random value of at least 32 characters in production."
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_model_list(self) -> list[str]:
        return [m.strip() for m in self.ai_models.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
