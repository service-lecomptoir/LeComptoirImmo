import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.payment_adjustment import PaymentAdjustment
    from app.models.tenant import Tenant


class PaymentStatus(str, Enum):
    PENDING = "pending"  # En attente
    PAID = "paid"  # Payé intégralement
    PARTIAL = "partial"  # Paiement partiel
    LATE = "late"  # En retard
    CANCELLED = "cancelled"  # Annulé


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("lease_id", "period_year", "period_month", name="uq_payment_lease_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

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
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Montants ──────────────────────────────────────────────────────────────
    amount_rent: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_charges: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    amount_apl: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # ── Paiement ──────────────────────────────────────────────────────────────
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str | None] = mapped_column(
        SAEnum(
            "virement",
            "cheque",
            "prelevement",
            "especes",
            "carte",
            name="payment_method_enum",
            create_type=False,
        ),
        nullable=True,
    )

    # ── Statut ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # ── Déclaration de paiement par le locataire (à valider par le gestionnaire) ─
    declared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declared_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    declared_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Crédit (trop-perçu d'échéances précédentes) déjà consommé par CE paiement.
    credit_applied: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0"
    )

    # Mois reporté sur un plan d'apurement : le statut passe à « cancelled » (sort des
    # impayés et des revenus), la dette vit désormais dans le plan. Le drapeau permet
    # d'afficher « Reporté » (et non « Annulé ») et de restaurer la dette si le plan
    # est supprimé.
    settled_by_plan: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    # Part du solde de CE loyer reportée sur un plan d'apurement sans solder tout le
    # mois (apurement PARTIEL) : déduite du solde restant dû. L'apurement TOTAL passe
    # plutôt par `settled_by_plan` (+ statut cancelled). Remis à 0 si le plan est supprimé.
    amount_on_plan: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
    )

    # ── Ajustements ad hoc (suppléments / restitutions) ────────────────────────
    # Surplus de restitution (au-delà du loyer/charges du mois) reporté en crédit
    # du bail → déduit automatiquement de la prochaine échéance. Alimenté par le
    # service d'ajustements ; consommé via `credit_applied` comme une avance.
    restitution_credit: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0"
    )
    # Surplus de restitution à REMBOURSER au locataire (cas d'un congé : pas de
    # mois suivant sur lequel reporter le crédit). Montant informatif, affiché sur
    # l'avis / la quittance.
    restitution_refund: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0, server_default="0"
    )

    # ── Quittance ─────────────────────────────────────────────────────────────
    quittance_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quittance_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    lease: Mapped["Lease"] = relationship("Lease", lazy="select")
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="select")
    adjustments: Mapped[list["PaymentAdjustment"]] = relationship(
        "PaymentAdjustment",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentAdjustment.created_at",
        lazy="select",
    )

    @property
    def balance(self) -> float:
        """Solde restant dû (déduction faite de la part reportée sur un plan d'apurement partiel)."""
        return max(
            0.0, float(self.amount_due) - float(self.amount_paid) - float(self.amount_on_plan or 0)
        )

    @property
    def period_label(self) -> str:
        months = [
            "",
            "Janvier",
            "Février",
            "Mars",
            "Avril",
            "Mai",
            "Juin",
            "Juillet",
            "Août",
            "Septembre",
            "Octobre",
            "Novembre",
            "Décembre",
        ]
        return f"{months[self.period_month]} {self.period_year}"

    @property
    def period_range_label(self) -> str:
        """Période réellement couverte, ex. « du 01/02/2026 au 30/04/2026 »
        (ou le mois si les dates ne sont pas renseignées : anciens paiements)."""
        if self.period_start and self.period_end:
            return (
                f"du {self.period_start.strftime('%d/%m/%Y')} "
                f"au {self.period_end.strftime('%d/%m/%Y')}"
            )
        return self.period_label

    def __repr__(self) -> str:
        return f"<Payment {self.period_label} : {self.status}>"
