import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, Date, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.unit import Unit


class EntretienType(str, Enum):
    PREVENTIF = "preventif"
    CORRECTIF = "correctif"
    INSPECTION = "inspection"


class EntretienStatus(str, Enum):
    PLANIFIE = "planifie"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    ANNULE = "annule"


class EntretienFrequency(str, Enum):
    UNIQUE = "unique"
    MENSUEL = "mensuel"
    TRIMESTRIEL = "trimestriel"
    SEMESTRIEL = "semestriel"
    ANNUEL = "annuel"


class Prestataire(Base, TimestampMixin):
    __tablename__ = "prestataires"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    specialty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    siret: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    entretiens: Mapped[list["Entretien"]] = relationship("Entretien", back_populates="prestataire", lazy="select")

    def __repr__(self) -> str:
        return f"<Prestataire {self.name!r}>"


class Entretien(Base, TimestampMixin):
    __tablename__ = "entretiens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    type: Mapped[str] = mapped_column(
        SAEnum(EntretienType, name="entretien_type_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=EntretienType.PREVENTIF, index=True,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(EntretienStatus, name="entretien_status_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=EntretienStatus.PLANIFIE, index=True,
    )
    frequency: Mapped[str] = mapped_column(
        SAEnum(EntretienFrequency, name="entretien_frequency_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False, default=EntretienFrequency.UNIQUE,
    )

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id", ondelete="SET NULL"), nullable=True
    )
    prestataire_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prestataires.id", ondelete="SET NULL"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    property: Mapped[Optional["Property"]] = relationship("Property", lazy="select")
    unit: Mapped[Optional["Unit"]] = relationship("Unit", lazy="select")
    prestataire: Mapped[Optional["Prestataire"]] = relationship("Prestataire", back_populates="entretiens", lazy="select")

    def __repr__(self) -> str:
        return f"<Entretien {self.title!r} [{self.status}]>"
