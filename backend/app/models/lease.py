import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, Numeric, Boolean, Integer, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.unit import Unit
    from app.models.property import Property
    from app.models.inspection import Inspection


class LeaseType(str, Enum):
    VIDE = "vide"
    MEUBLE = "meuble"
    MOBILITE = "mobilite"
    COMMERCIAL = "commercial"


class PaymentMethod(str, Enum):
    VIREMENT = "virement"
    CHEQUE = "cheque"
    PRELEVEMENT = "prelevement"
    ESPECES = "especes"


class Lease(Base, TimestampMixin):
    __tablename__ = "leases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Liens ─────────────────────────────────────────────────────────────────
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Type de contrat ───────────────────────────────────────────────────────
    lease_type: Mapped[str] = mapped_column(
        SAEnum(LeaseType, name="lease_type_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=LeaseType.VIDE,
    )

    # ── Dates ─────────────────────────────────────────────────────────────────
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── Finances ──────────────────────────────────────────────────────────────
    rent_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    charges_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payment_method: Mapped[str] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=PaymentMethod.VIREMENT,
    )

    # ── APL ───────────────────────────────────────────────────────────────────
    apl_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    apl_tiers_payant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Garant ────────────────────────────────────────────────────────────────
    has_guarantor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guarantor_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    guarantor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    guarantor_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # ── État ──────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="leases")
    unit: Mapped["Unit"] = relationship("Unit", back_populates="leases")
    parent_property: Mapped["Property"] = relationship("Property", back_populates="leases")
    inspections: Mapped[list["Inspection"]] = relationship(
        "Inspection", back_populates="lease", lazy="select", cascade="all, delete-orphan"
    )

    @property
    def total_monthly(self) -> float:
        return float(self.rent_amount) + float(self.charges_amount)

    @property
    def net_rent(self) -> float:
        """Loyer net après déduction APL tiers-payant."""
        if self.apl_tiers_payant and self.apl_amount:
            return max(0.0, float(self.rent_amount) - float(self.apl_amount))
        return float(self.rent_amount)

    def __repr__(self) -> str:
        return f"<Lease {self.id} — actif={self.is_active}>"
