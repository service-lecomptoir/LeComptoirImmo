import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, Numeric, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.document import Document


class Civility(str, Enum):
    M = "M"
    MME = "Mme"
    AUTRE = "Autre"


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identité ──────────────────────────────────────────────────────────────
    civility: Mapped[Optional[str]] = mapped_column(
        SAEnum(Civility, name="civility_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]), nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Personne morale (locataire « entreprise ») : raison sociale + SIREN/SIRET.
    # `national_id` reste réservé au NIR (n° de sécurité sociale) d'une personne.
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    siret: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # SIREN / SIRET (société)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    birth_place: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    national_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # NIR (n° sécu, personne)

    # ── Contact ───────────────────────────────────────────────────────────────
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    phone2: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # ── Situation professionnelle ─────────────────────────────────────────────
    employer: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    employer_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    monthly_income: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    income_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # ── Compte locataire ──────────────────────────────────────────────────────
    # Lien vers le compte utilisateur du locataire (rôle "locataire")
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    leases: Mapped[list["Lease"]] = relationship(
        "Lease", back_populates="tenant", lazy="select"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        primaryjoin="and_(Document.entity_type=='tenant', "
                    "foreign(Document.entity_id)==Tenant.id)",
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
