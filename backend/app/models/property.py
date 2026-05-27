import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Numeric, Boolean, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease


class PropertyType(str, Enum):
    APPARTEMENT = "appartement"
    MAISON = "maison"
    LOCAL_COMMERCIAL = "local_commercial"
    AUTRE = "autre"


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Identification ────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    reference: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ── Adresse ───────────────────────────────────────────────────────────────
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    address2: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="France")

    # ── Type & propriétaire ───────────────────────────────────────────────────
    property_type: Mapped[str] = mapped_column(
        SAEnum(PropertyType, name="property_type_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=PropertyType.APPARTEMENT,
    )
    owner_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # ── Infos complémentaires ─────────────────────────────────────────────────
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(nullable=True)

    # ── Caractéristiques du logement ──────────────────────────────────────────
    typology: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)   # T1 … T10
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)    # salles d'eau / de bain
    heating_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    energy_class: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)  # DPE A..G

    # ── Équipements & extérieurs ──────────────────────────────────────────────
    furnished: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kitchen_equipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_elevator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_balcony: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_terrace: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_garden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_parking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_cellar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_fiber: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # fibre internet

    # ── État d'occupation ──────────────────────────────────────────────────────
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Propriétaire connecté ─────────────────────────────────────────────────
    # Lien vers le compte utilisateur du propriétaire (rôle "proprietaire")
    owner_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    leases: Mapped[list["Lease"]] = relationship(
        "Lease", back_populates="parent_property", lazy="select"
    )

    @property
    def full_address(self) -> str:
        parts = [self.address, self.zip_code, self.city]
        return ", ".join(p for p in parts if p)

    def __repr__(self) -> str:
        return f"<Property {self.name} — {self.city}>"
