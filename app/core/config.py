"""
Centralized application settings.

All environment-dependent values (API keys, model names, paths) are
read here once via pydantic-settings, instead of being scattered
across modules or hardcoded.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "DocMind API"
    environment: str = "development"
    cors_origins: list[str] = ["*"]

    # LLM / Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Embeddings
    # embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    google_api_key: str
    # Tools
    alpha_vantage_api_key: str

    # Storage
    database_dir: Path = Path("database")
    database_path: Path = database_dir / "chat_history.db"
    faiss_index_dir: Path = database_dir / "faiss_indexes"

    # Uploads
    max_upload_mb: int = 25


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance so .env is parsed only once."""
    return Settings()
