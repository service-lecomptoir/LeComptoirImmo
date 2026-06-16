import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.tenant import Tenant


class ChargeRegularization(Base, TimestampMixin):
    """Régularisation annuelle des charges (Actualisation — Étape 3).

    Sur une période (typiquement 1 an), on compare les provisions de charges
    versées par le locataire aux charges réelles saisies par le gestionnaire :
        balance = provisions_total − real_total
        balance > 0 → trop-perçu, remboursement au locataire (crédit déduit du
                       prochain loyer)
        balance < 0 → complément de charges dû par le locataire
    À l'application, la provision mensuelle du bail est réajustée
    (new_monthly_provision) et le solde ponctuel est traité.
    """
    __tablename__ = "charge_regularizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Période régularisée ──────────────────────────────────────────────────
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    months_count: Mapped[int] = mapped_column(Integer, nullable=False, default=12)

    # ── Montants ─────────────────────────────────────────────────────────────
    provisions_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    real_total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # balance = provisions_total − real_total (signé)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    old_monthly_provision: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    new_monthly_provision: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # ── État ─────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="applied")  # applied
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Révision de loyer/charges générée par cette régularisation (lien pour annulation).
    rent_revision_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    lease: Mapped["Lease"] = relationship("Lease", lazy="select")
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="select")

    def __repr__(self) -> str:
        return f"<ChargeRegularization {self.lease_id} {self.period_start}→{self.period_end} bal={self.balance}>"
