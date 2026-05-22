"""Modèle Contact — carnet d'adresses prestataires et autres."""
import uuid
from typing import Optional
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Identité
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Catégorie (stored as string)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="autre")

    # Contact
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    phone2: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Adresse
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Professionnel
    siret: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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
