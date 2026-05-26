import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease
    from app.models.property import Property


class InspectionType(str, Enum):
    ENTREE = "entree"
    SORTIE = "sortie"
    CONTRADICTOIRE = "contradictoire"
    PERIODIQUE = "periodique"


class OverallCondition(str, Enum):
    TRES_BON = "tres_bon"
    BON = "bon"
    MOYEN = "moyen"
    MAUVAIS = "mauvais"


class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Liens ─────────────────────────────────────────────────────────────────
    lease_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Type & date ───────────────────────────────────────────────────────────
    inspection_type: Mapped[str] = mapped_column(
        SAEnum(InspectionType, name="inspection_type_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    inspector_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tenant_present: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Résultat ──────────────────────────────────────────────────────────────
    overall_condition: Mapped[Optional[str]] = mapped_column(
        SAEnum(OverallCondition, name="overall_condition_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(3000), nullable=True)
    rooms_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    lease: Mapped[Optional["Lease"]] = relationship("Lease", back_populates="inspections")
    parent_property: Mapped[Optional["Property"]] = relationship("Property", lazy="select")

    def __repr__(self) -> str:
        return f"<Inspection {self.inspection_type} — {self.inspection_date}>"
