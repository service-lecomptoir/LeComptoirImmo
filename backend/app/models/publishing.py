import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Numeric, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin


class PublishPlatform(Base, TimestampMixin):
    """Plateforme de diffusion définie au préalable par le gestionnaire.

    Le canal de publication est une page d'annonce hébergée par Le Comptoir ; chaque
    plateforme est une CIBLE DE PARTAGE libre (réseau social, site, e-mail de dépôt,
    lien) que le gestionnaire crée une fois et réutilise pour ses annonces."""
    __tablename__ = "publish_platforms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Canal : reseau | site | email | lien | autre
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="lien")
    # Cible : URL du site/réseau, ou e-mail de dépôt d'annonce (selon le canal).
    target: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<PublishPlatform {self.name} ({self.kind})>"


class Listing(Base, TimestampMixin):
    """Annonce d'un bien — contenu et photos pré-enregistrés (actualisables avant
    publication), statut de diffusion et programmation. Une annonce par bien."""
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # loyer hors charges
    charges: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # charges mensuelles
    # IDs (str) des documents-photos du bien retenus pour l'annonce — ordre conservé.
    photo_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # IDs (str) des plateformes de diffusion ciblées.
    platform_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # draft | scheduled | published | unpublished
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)
    # Jeton de la page d'annonce publique (URL non devinable).
    public_token: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, unique=True, index=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Suivi de performance : nombre de consultations de la page publique.
    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Alerte « vacance » (annonce publiée sans candidature) déjà poussée (anti-doublon).
    vacancy_alerted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Listing property={self.property_id} [{self.status}]>"
