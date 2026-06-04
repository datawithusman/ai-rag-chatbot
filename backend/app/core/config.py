"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────
    app_name: str = "AI RAG Chatbot"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # ── API Configuration ──────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── LLM Configuration ─────────────────────────────────────────
    llm_provider: Literal["openai", "google"] = "openai"
    openai_api_key: str = ""
    google_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048

    # ── Vector Store ───────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "documents"
    embedding_model: str = "text-embedding-3-small"

    # ── Document Processing ────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_file_size_mb: int = 50
    allowed_file_types: list[str] = ["application/pdf"]

    # ── Redis (optional, for caching) ──────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600

    # ── Rate Limiting ──────────────────────────────────────────────
    rate_limit_per_minute: int = 30

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()