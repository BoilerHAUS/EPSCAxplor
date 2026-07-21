from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
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
    # Optional Qdrant API key (#144). Blank ⇒ None so an unset ${QDRANT_API_KEY}
    # (which a compose variable expands to "") never becomes an empty "api-key"
    # header on the wire; local/dev stays keyless. A real key is forwarded
    # byte-for-byte to stay matched with the Qdrant service, which reads the
    # same value from QDRANT__SERVICE__API_KEY.
    qdrant_api_key: str | None = None
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
    # 0 disables; a negative value is rejected at startup (ge=0).
    query_rate_limit_per_minute: int = Field(default=30, ge=0)
    # Stricter per-client cap on /auth/login + /auth/refresh (#140); 0 disables.
    # Auth is far lower-frequency than /query, so this can be tight without
    # affecting legitimate use while still throttling online brute-force.
    auth_rate_limit_per_minute: int = Field(default=10, ge=0)
    # Number of trusted reverse-proxy hops in front of the app (#140). The
    # limiter key is taken as the Nth-from-right X-Forwarded-For entry, because
    # Traefik appends the true socket peer as the right-most hop; a client-
    # supplied leading value is attacker-controlled and must not be trusted.
    # Set to 0 for direct-peer mode (no proxy, e.g. local dev).
    trusted_proxy_hops: int = Field(default=1, ge=0)
    # Hard cap on distinct limiter keys held in memory (#140); bounds the
    # in-process sliding-window state against unique-key flooding. Must be >= 1:
    # a smaller value would force an eviction sweep on every request.
    rate_limit_max_keys: int = Field(default=10_000, ge=1)
    cors_origins: str = "http://localhost:3000"
    # Commit SHA of the running build, baked into the image at build time
    # (Dockerfile ARG → ENV) and surfaced in /health so the deploy workflow
    # can confirm the freshly built image is actually serving (#75).
    git_sha: str = "unknown"

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def _blank_qdrant_key_to_none(cls, value: str | None) -> str | None:
        """Treat a blank ``QDRANT_API_KEY`` as unset (keyless), but never strip
        a real key — the Qdrant service reads the same raw value, so trimming
        here would desync the client from the server."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
