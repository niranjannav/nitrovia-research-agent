"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str

    # Google Drive (base64 encoded service account JSON)
    google_service_account_json: str | None = None

    # LLM
    anthropic_api_key: str
    openai_api_key: str | None = None

    # Embedding model for pgvector
    embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "openai"

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Storage buckets
    upload_bucket: str = "uploads"
    output_bucket: str = "generated-reports"

    # Limits
    max_file_size_mb: int = 50
    max_files_per_report: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
