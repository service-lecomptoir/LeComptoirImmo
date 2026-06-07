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
    APP_NAME: str = "Alice"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8001  # Port d'écoute uvicorn (distinct du port 8000 de LeCI)

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "alice-dev-secret-key-change-in-production"
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
    # Le Comptoir Séjour (produit autonome, base séparée) — piloté via son API interne.
    SEJOUR_URL: str = "http://sejour_backend:8000"
    SEJOUR_INTERNAL_KEY: str = ""

    # ── First Admin ──────────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@alice.fr"
    FIRST_ADMIN_PASSWORD: str = "Alice1!"
    FIRST_ADMIN_NAME: str = "Admin Alice"

    # ── SMTP (désactivé si SMTP_HOST est vide) ───────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@lecomptoirimmo.fr"
    SMTP_FROM_NAME: str = "Le Comptoir Immo"
    SMTP_TLS: bool = True

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_HOST)

    # ── Stripe (paiement des abonnements gestionnaires) ──────────────────────
    # Vide → intégration désactivée (no-op). Mode test : clés sk_test_… / whsec_…
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_CURRENCY: str = "eur"
    # URLs de retour après Checkout (page « Mon abonnement » côté LeCI).
    STRIPE_SUCCESS_URL: str = "http://localhost:5173/abonnement?paiement=succes"
    STRIPE_CANCEL_URL: str = "http://localhost:5173/abonnement?paiement=annule"

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
