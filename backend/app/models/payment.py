import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, Numeric, Integer, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.tenant import Tenant


class PaymentStatus(str, Enum):
    PENDING = "pending"       # En attente
    PAID = "paid"             # Payé intégralement
    PARTIAL = "partial"       # Paiement partiel
    LATE = "late"             # En retard
    CANCELLED = "cancelled"   # Annulé


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("lease_id", "period_year", "period_month", name="uq_payment_lease_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Liens ─────────────────────────────────────────────────────────────────
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Période ───────────────────────────────────────────────────────────────
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    # Étendue réellement couverte (multi-mois selon la fréquence + prorata).
    # Nullable pour compat avec les paiements générés avant cette fonctionnalité.
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Montants ──────────────────────────────────────────────────────────────
    amount_rent: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_charges: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    amount_apl: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # ── Paiement ──────────────────────────────────────────────────────────────
    payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(
        SAEnum(
            "virement", "cheque", "prelevement", "especes",
            name="payment_method_enum", create_type=False,
        ),
        nullable=True,
    )

    # ── Statut ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # ── Quittance ─────────────────────────────────────────────────────────────
    quittance_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quittance_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    lease: Mapped["Lease"] = relationship("Lease", lazy="select")
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="select")

    @property
    def balance(self) -> float:
        """Solde restant dû."""
        return max(0.0, float(self.amount_due) - float(self.amount_paid))

    @property
    def period_label(self) -> str:
        months = [
            "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ]
        return f"{months[self.period_month]} {self.period_year}"

    @property
    def period_range_label(self) -> str:
        """Période réellement couverte, ex. « du 01/02/2026 au 30/04/2026 »
        (ou le mois si les dates ne sont pas renseignées — anciens paiements)."""
        if self.period_start and self.period_end:
            return (f"du {self.period_start.strftime('%d/%m/%Y')} "
                    f"au {self.period_end.strftime('%d/%m/%Y')}")
        return self.period_label

    def __repr__(self) -> str:
        return f"<Payment {self.period_label} — {self.status}>"
