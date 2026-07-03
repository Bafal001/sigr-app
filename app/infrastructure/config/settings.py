"""
Configuration centralisée via Pydantic Settings.
Lit les variables d'environnement depuis le fichier .env.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application chargés depuis .env et l'environnement."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "SIGR"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_debug: bool = True

    # Serveur
    host: str = "0.0.0.0"
    port: int = 8000

    # Base de données
    database_url: str = "sqlite:///./data/sigr.db"

    # LLM — DeepSeek (compatible OpenAI SDK)
    llm_api_key: str = ""
    llm_api_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-pro"
    llm_max_tokens: int = 4096

    # Sécurité
    secret_key: str = "change-me-in-production"


@lru_cache()
def get_settings() -> Settings:
    """Retourne l'instance unique de Settings (cache)."""
    return Settings()
