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
    APP_NAME: str = "LeComptoirImmo"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "locataire_cloud"
    POSTGRES_USER: str = "locataire_user"
    POSTGRES_PASSWORD: str

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://localhost:5177,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── Alice internal API ─────────────────────────────────────────────────
    ALICE_URL: str = "http://localhost:8001"
    ALICE_INTERNAL_KEY: str = "lecomptoir-internal-dev-key-change-in-production"

    # ── SMTP (désactivé si SMTP_HOST est vide) ───────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@lecomptoirimmo.fr"
    SMTP_FROM_NAME: str = "Le Comptoir Immo"
    SMTP_TLS: bool = True

    # Destinataire des notifications de nouvelles demandes de souscription
    # (vide → repli sur FIRST_ADMIN_EMAIL).
    LEADS_NOTIFY_EMAIL: str = ""

    # Clé API INSEE (BDM) pour la récupération auto de l'IRL (vide → saisie manuelle).
    INSEE_API_KEY: str = ""

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_HOST)

    # ── First Admin ──────────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@locataire-cloud.fr"
    FIRST_ADMIN_PASSWORD: str = "Admin1234!"
    FIRST_ADMIN_NAME: str = "Administrateur"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
