import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Numeric, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin

# Checklist standard des pièces justificatives d'un dossier candidat.
# Chaque entrée du JSONB `docs` : {"key": ..., "provided": bool, "verified": bool}.
CANDIDATURE_DOC_KEYS: list[tuple[str, str]] = [
    ("identite", "Pièce d'identité"),
    ("justificatif_revenus", "Justificatifs de revenus (3 derniers bulletins)"),
    ("avis_imposition", "Avis d'imposition"),
    ("justificatif_domicile", "Justificatif de domicile"),
    ("contrat_travail", "Contrat de travail / attestation employeur"),
    ("dossier_garant", "Dossier du garant"),
    ("attestation_caf", "Attestation de paiement CAF"),
]


class Candidature(Base, TimestampMixin):
    """Dossier de candidature pour la location d'un bien.

    Centralise les candidatures (déposées depuis la page d'annonce publique ou
    saisies par le gestionnaire), la vérification des pièces (checklist), et les
    éléments d'analyse/comparaison (revenus, garant, complétude) pour aider à la
    sélection du locataire."""
    __tablename__ = "candidatures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Candidat ──────────────────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    employment: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)  # situation pro
    monthly_income: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    has_guarantor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Dossier ───────────────────────────────────────────────────────────────
    # nouvelle | documents_demandes | en_etude | retenue | refusee
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="nouvelle", index=True)
    # Checklist des pièces : [{key, required, provided, verified, file_path, filename,
    # uploaded_at}] (clés : CANDIDATURE_DOC_KEYS).
    docs: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # Jeton public pour le dépôt des pièces par le candidat (lien envoyé par e-mail).
    upload_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    # Visite : créneau réservé par le candidat + date d'invitation envoyée.
    visit_slot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("property_visit_slots.id", ondelete="SET NULL"), nullable=True,
    )
    visit_invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Relance avant visite déjà envoyée (anti-doublon de la relance automatique).
    visit_reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Relance « dossier incomplet » déjà envoyée (anti-doublon de la relance auto).
    docs_reminded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # annonce (page publique) | manuel (saisie gestionnaire)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="annonce")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Candidature {self.full_name} [{self.status}]>"
