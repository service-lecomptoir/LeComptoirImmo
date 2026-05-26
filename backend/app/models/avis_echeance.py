import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, Numeric, Integer, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.tenant import Tenant


class AvisEcheanceStatus(str, Enum):
    BROUILLON = "brouillon"   # Généré, pas encore envoyé
    ENVOYE = "envoye"          # Marqué comme envoyé
    ACQUITTE = "acquitte"      # Loyer payé


class AvisEcheance(Base, TimestampMixin):
    __tablename__ = "avis_echeances"
    __table_args__ = (
        UniqueConstraint("lease_id", "period_year", "period_month",
                         name="uq_avis_lease_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Liens ─────────────────────────────────────────────────────────────────
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ── Période ───────────────────────────────────────────────────────────────
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Montants ──────────────────────────────────────────────────────────────
    amount_rent: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_charges: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    amount_apl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    amount_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # ── Statut & envoi ────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        SAEnum(AvisEcheanceStatus, name="avis_echeance_status_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=AvisEcheanceStatus.BROUILLON, index=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    # NULL = généré automatiquement par le scheduler
    generated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    lease: Mapped["Lease"] = relationship("Lease", lazy="select")
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="select")

    @property
    def period_label(self) -> str:
        months = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        return f"{months[self.period_month]} {self.period_year}"

    @property
    def is_auto_generated(self) -> bool:
        return self.generated_by is None

    def __repr__(self) -> str:
        return f"<AvisEcheance {self.period_label} — {self.status}>"
