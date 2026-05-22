"""Modèle DocumentTemplate — templates personnalisables pour documents générés."""
import uuid
from typing import Optional
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin


class TemplateType(str, Enum):
    AVIS_ECHEANCE = "avis_echeance"
    QUITTANCE = "quittance"
    LETTRE_RELANCE = "lettre_relance"
    LETTRE_RESILIATION = "lettre_resiliation"
    CONTRAT_BAIL = "contrat_bail"
    ETAT_DES_LIEUX = "etat_des_lieux"


class DocumentTemplate(Base, TimestampMixin):
    __tablename__ = "document_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    template_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Personnalisation visuelle
    logo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    header_color: Mapped[Optional[str]] = mapped_column(String(20), default="#1E3A5F", nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company_address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    company_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    company_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_siret: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Contenu HTML du template
    content_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    footer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statut
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<DocumentTemplate {self.name} ({self.template_type})>"
