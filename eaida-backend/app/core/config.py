"""Central application settings, loaded from environment / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Enterprise AI Data Analyst"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./storage/app.db"

    # Storage
    STORAGE_DIR: str = "./storage"
    UPLOAD_DIR: str = "./storage/uploads"
    MODEL_DIR: str = "./storage/models"
    REPORT_DIR: str = "./storage/reports"
    CHROMA_DIR: str = "./storage/chroma"

    # LLM
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    LLM_BASE_URL: str = ""          # <-- ADD THIS LINE
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Bootstrap admin
    FIRST_ADMIN_EMAIL: str = "admin@eaida.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@12345"

    def ensure_dirs(self) -> None:
        for d in (self.STORAGE_DIR, self.UPLOAD_DIR, self.MODEL_DIR,
                  self.REPORT_DIR, self.CHROMA_DIR):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


settings = get_settings()