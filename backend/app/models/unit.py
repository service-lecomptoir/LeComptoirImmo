import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.lease import Lease


class UnitType(str, Enum):
    STUDIO = "studio"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5_PLUS = "T5+"
    MAISON = "maison"
    LOCAL = "local"
    AUTRE = "autre"


class Unit(Base, TimestampMixin):
    __tablename__ = "units"

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

    # ── Identification ────────────────────────────────────────────────────────
    unit_ref: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_type: Mapped[str] = mapped_column(
        SAEnum(UnitType, name="unit_type_enum", create_type=True),
        nullable=False,
        default=UnitType.T2,
    )
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    building: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ── Surface & composition ─────────────────────────────────────────────────
    area_sqm: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Finances ──────────────────────────────────────────────────────────────
    base_rent: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    charges_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deposit_months: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── État ──────────────────────────────────────────────────────────────────
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # ── Relations ─────────────────────────────────────────────────────────────
    parent_property: Mapped["Property"] = relationship("Property", back_populates="units")
    leases: Mapped[list["Lease"]] = relationship(
        "Lease", back_populates="unit", lazy="select"
    )

    @property
    def deposit_amount(self) -> float:
        return float(self.base_rent) * self.deposit_months

    @property
    def total_monthly(self) -> float:
        return float(self.base_rent) + float(self.charges_amount)

    def __repr__(self) -> str:
        return f"<Unit {self.unit_ref} — {self.unit_type}>"
