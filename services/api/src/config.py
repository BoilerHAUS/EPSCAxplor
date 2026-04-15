from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Pydantic raises a ValidationError at startup if any required field is
    missing, preventing silent misconfiguration in production.
    """

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
    cors_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env.local"
        case_sensitive = False


settings = Settings()
