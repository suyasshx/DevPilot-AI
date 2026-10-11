"""
DevPilot AI - Backend Configuration Settings.
Loads application settings from environment variables or .env file.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    PROJECT_NAME: str = "DevPilot AI"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database configuration: defaults to SQLite for local development, can be set to PostgreSQL
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./devpilot.db",
        description="Async database connection string (SQLite or PostgreSQL with pgvector)",
    )

    # CORS configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    # Target API allowlist (Security & SSRF Guardrail)
    ALLOWED_TARGET_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
    ]

    # LLM configuration (Groq)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_RETRIES: int = 2

    # Upload constraints
    MAX_SPEC_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_postgres(self) -> bool:
        """Return True if configured database is PostgreSQL."""
        return "postgres" in self.DATABASE_URL.lower()


settings = Settings()
