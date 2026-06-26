import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.lease import Lease


class Civility(str, Enum):
    M = "M"
    MME = "Mme"
    AUTRE = "Autre"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Identifiant lisible unique de la fiche locataire (ex. « LO-00001 »).
    ref_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Identité ──────────────────────────────────────────────────────────────
    civility: Mapped[str | None] = mapped_column(
        SAEnum(
            Civility,
            name="civility_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Personne morale (locataire « entreprise ») : raison sociale + SIREN/SIRET.
    # `national_id` reste réservé au NIR (n° de sécurité sociale) d'une personne.
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    siret: Mapped[str | None] = mapped_column(String(50), nullable=True)  # SIREN / SIRET (société)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(150), nullable=True)
    national_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # NIR (n° sécu, personne)

    # ── Contact ───────────────────────────────────────────────────────────────
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone2: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Langue préférée pour les courriers automatiques (fr/en/pt-BR/ht/srn). Repli fr.
    language: Mapped[str] = mapped_column(String(8), default="fr", nullable=False)

    # ── Situation professionnelle ─────────────────────────────────────────────
    employer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    monthly_income: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    income_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ── Commerces partenaires ─────────────────────────────────────────────────
    # Autorise (défaut) le locataire à figurer dans la liste des clients des
    # commerces partenaires (boutiques Le Comptoir Market du gestionnaire) et à y
    # accéder via SSO. Décochable (par le gestionnaire ou le locataire) pour l'en
    # exclure : plus de provisionnement, et retrait des rattachements existants.
    partage_partenaires: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # ── Compte locataire ──────────────────────────────────────────────────────
    # Lien vers le compte utilisateur du locataire (rôle "locataire")
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── RGPD ──────────────────────────────────────────────────────────────────
    # Horodatage d'anonymisation (droit à l'effacement). Non NULL = identité
    # effacée ; l'historique comptable est conservé (obligation légale) mais
    # pseudonymisé. Empêche la réutilisation/réidentification.
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relations ─────────────────────────────────────────────────────────────
    leases: Mapped[list["Lease"]] = relationship("Lease", back_populates="tenant", lazy="select")
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        primaryjoin="and_(Document.entity_type=='tenant', foreign(Document.entity_id)==Tenant.id)",
        viewonly=True,
        lazy="select",
    )

    @property
    def full_name(self) -> str:
        # Société : la raison sociale prime. Sinon « Prénom Nom » (sans la civilité).
        if self.company_name:
            return self.company_name.strip()
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p).strip()

    def __repr__(self) -> str:
        return f"<Tenant {self.full_name}>"
