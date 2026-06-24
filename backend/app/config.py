from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valeurs par défaut « de développement » qui ne doivent JAMAIS rester en production.
_INSECURE_DEFAULTS = {
    "ALICE_INTERNAL_KEY": "lecomptoir-internal-dev-key-change-in-production",
    "FIRST_ADMIN_PASSWORD": "Admin1234!",
}


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
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── URL publique de l'app (liens de retour Stripe/SumUp, webhooks) ───────
    PUBLIC_APP_URL: str = "https://immo.lecomptoir.services"

    # ── Alice internal API ─────────────────────────────────────────────────
    ALICE_URL: str = "http://localhost:8001"
    ALICE_INTERNAL_KEY: str = "lecomptoir-internal-dev-key-change-in-production"

    # ── Pont Le Comptoir Market (boutique de résidence) ──────────────────────
    # URL publique de Market pour construire le lien vers une boutique de résidence.
    MARKET_PUBLIC_URL: str = "https://market.lecomptoir.services"

    # ── SMTP / e-mail (désactivé si SMTP_HOST est vide) ──────────────────────
    # Brevo (recommandé) : SMTP_HOST=smtp-relay.brevo.com, SMTP_PORT=587,
    # SMTP_USER=<login SMTP Brevo>, SMTP_PASSWORD=<clé SMTP Brevo>, SMTP_TLS=true.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@lecomptoirimmo.fr"
    SMTP_FROM_NAME: str = "Le Comptoir Immo"
    SMTP_TLS: bool = True

    # ── SMS via Brevo (désactivé si BREVO_API_KEY est vide) ──────────────────
    # Brevo (ex-Sendinblue), API transactionnelle SMS. Clé : app.brevo.com →
    # « SMTP & API » → API Keys. SMS_SENDER = expéditeur affiché (≤ 11 caractères
    # alphanumériques, pas d'espace). Fail-soft : si désactivé, les SMS sont simulés.
    BREVO_API_KEY: str = ""
    SMS_SENDER: str = "LeComptoir"

    # Destinataire des notifications de nouvelles demandes de souscription
    # (vide → repli sur FIRST_ADMIN_EMAIL).
    LEADS_NOTIFY_EMAIL: str = ""

    # Clé API INSEE (BDM) pour la récupération auto de l'IRL (vide → saisie manuelle).
    INSEE_API_KEY: str = ""

    # ── Agents IA via Telegram (canal gratuit) ───────────────────────────────
    # Bot créé via @BotFather. Vide → envoi désactivé (no-op), l'app reste OK.
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""  # ex. "LeComptoirImmoBot" (pour les instructions)
    TELEGRAM_WEBHOOK_SECRET: str = ""  # secret d'en-tête vérifié sur le webhook entrant

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN)

    # ── Cerveau LLM des agents IA (Phase 2) — compatible API OpenAI ──────────
    # Vide → repli automatique sur le routeur déterministe gratuit (Phase 1).
    # Par défaut : Google Gemini (offre gratuite, endpoint compatible OpenAI).
    AGENT_LLM_API_KEY: str = ""
    AGENT_LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    AGENT_LLM_MODEL: str = "gemini-2.5-flash"

    @property
    def agent_llm_enabled(self) -> bool:
        return bool(self.AGENT_LLM_API_KEY)

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_HOST)

    @property
    def sms_enabled(self) -> bool:
        return bool(self.BREVO_API_KEY)

    # ── First Admin ──────────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@locataire-cloud.fr"
    FIRST_ADMIN_PASSWORD: str = "Admin1234!"
    FIRST_ADMIN_NAME: str = "Administrateur"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @model_validator(mode="after")
    def _forbid_insecure_defaults_in_production(self) -> "Settings":
        """En production, refuse de démarrer si un secret est resté sur sa valeur
        de développement (clé interne, mot de passe admin par défaut)."""
        if self.is_production:
            leaked = [
                name
                for name, default in _INSECURE_DEFAULTS.items()
                if getattr(self, name, None) == default
            ]
            if leaked:
                raise ValueError(
                    "Secrets non configurés en production : "
                    + ", ".join(leaked)
                    + ". Définissez-les dans le fichier .env."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
