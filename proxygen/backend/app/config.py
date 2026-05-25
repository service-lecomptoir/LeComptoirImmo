from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "ProxyGen"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8001  # Port d'écoute uvicorn (distinct du port 8000 de LeCI)

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "proxygen-dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://lecomptoirimmo_user:devpassword123@localhost:5432/lecomptoirimmo"

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5174"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── Internal API (service-to-service) ────────────────────────────────────
    INTERNAL_API_KEY: str = "lecomptoir-internal-dev-key-change-in-production"
    LECI_URL: str = "http://localhost:8000"

    # ── First Admin ──────────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@proxygen.fr"
    FIRST_ADMIN_PASSWORD: str = "ProxyGen1!"
    FIRST_ADMIN_NAME: str = "Admin ProxyGen"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
