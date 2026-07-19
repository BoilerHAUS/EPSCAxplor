from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Pydantic raises a ValidationError at startup if any required field is
    missing, preventing silent misconfiguration in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env.local",
        case_sensitive=False,
    )

    database_url: str
    qdrant_url: str
    ollama_url: str
    ollama_embed_model: str = "nomic-embed-text"
    anthropic_api_key: str
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    claude_sonnet_model: str = "claude-sonnet-4-6"
    jwt_secret: str
    jwt_access_expiry_seconds: int = 900
    jwt_refresh_expiry_days: int = 7
    environment: str = "development"
    # Password + refresh-cookie policy (#23).
    bcrypt_rounds: int = 12
    refresh_cookie_name: str = "epsca_refresh"
    refresh_cookie_secure: bool = True  # set False only for local http development
    # "strict" — the SPA only ever sends the cookie via same-site XHR to /auth;
    # it is never needed on top-level cross-site navigations (#104).
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    refresh_cookie_domain: str | None = None
    # Per-client burst cap on /query (#85); per-tenant tier quota is enforce_tier_limit (#25).
    query_rate_limit_per_minute: int = 30
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
