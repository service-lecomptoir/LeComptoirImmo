"""Modèle Contact — carnet d'adresses prestataires et autres."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class ContactCategory(str, Enum):
    PLOMBIER = "plombier"
    ELECTRICIEN = "electricien"
    MENUISIER = "menuisier"
    PEINTRE = "peintre"
    SERRURIER = "serrurier"
    CHAUFFAGISTE = "chauffagiste"
    JARDINIER = "jardinier"
    NETTOYAGE = "nettoyage"
    ARCHITECTE = "architecte"
    NOTAIRE = "notaire"
    AVOCAT = "avocat"
    ASSURANCE = "assurance"
    BANQUE = "banque"
    AUTRE = "autre"


class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identité
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Catégorie (stored as string)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="autre")

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone2: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Adresse
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Professionnel
    siret: Mapped[str | None] = mapped_column(String(20), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Propriétaire de la fiche (gestionnaire ou admin)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name or "", self.last_name]
        return " ".join(p for p in parts if p).strip()

    @property
    def display_name(self) -> str:
        if self.company_name:
            return self.company_name
        return self.full_name

    def __repr__(self) -> str:
        return f"<Contact {self.display_name}>"
