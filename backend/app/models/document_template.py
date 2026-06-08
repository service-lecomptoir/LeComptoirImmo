"""Modèle DocumentTemplate — templates personnalisables pour documents générés."""
import uuid
from typing import Optional, Any
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from enum import Enum

from app.database import Base, TimestampMixin


class TemplateType(str, Enum):
    AVIS_ECHEANCE = "avis_echeance"
    QUITTANCE = "quittance"
    REGULARISATION_CHARGES = "regularisation_charges"
    REVISION_LOYER = "revision_loyer"
    TAXES_FONCIERES = "taxes_foncieres"
    # Types historiques (plus proposés dans la papeterie, conservés pour compat).
    LETTRE_RELANCE = "lettre_relance"
    LETTRE_RESILIATION = "lettre_resiliation"
    CONTRAT_BAIL = "contrat_bail"
    ETAT_DES_LIEUX = "etat_des_lieux"


# Ordre d'affichage dans « Ma papeterie » + liste des types proposés.
PAPETERIE_ORDER = [
    TemplateType.AVIS_ECHEANCE.value,
    TemplateType.QUITTANCE.value,
    TemplateType.REGULARISATION_CHARGES.value,
    TemplateType.REVISION_LOYER.value,
    TemplateType.TAXES_FONCIERES.value,
]


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

    # Éditeur par blocs (avis d'échéance et autres documents de la papeterie) :
    # liste ordonnée de blocs réordonnables + thème (palette/police). NULL = pas
    # encore migré → on retombe sur le rendu HTML classique (content_html).
    blocks: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    theme: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # Isolation par gestionnaire (NULL = ancien template global, visible admin seulement)
    gestionnaire_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Statut
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<DocumentTemplate {self.name} ({self.template_type})>"
