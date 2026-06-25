import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class BoutiqueSsoToken(Base, TimestampMixin):
    """Jeton opaque à usage unique pour le SSO « boutique de résidence ».

    Émis pour un locataire afin qu'il accède à la boutique Market de sa résidence
    sans recréer de compte. Résolu une seule fois par Market via l'API interne.
    """

    __tablename__ = "boutique_sso_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    tenant_email: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Nom du compte gestionnaire d'origine (transmis à Market pour la colonne
    # « Gestionnaire » dans les fichiers clients du gérant).
    gestionnaire_nom: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Coordonnées du locataire transmises à Market (préremplissage du compte client).
    tenant_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tenant_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tenant_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tenant_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tenant_country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # PK de la boutique côté Market.
    boutique_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
