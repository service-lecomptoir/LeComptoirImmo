import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Enum as SAEnum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.unit import Unit
    from app.models.lease import Lease


class PropertyType(str, Enum):
    IMMEUBLE = "immeuble"
    MAISON = "maison"
    APPARTEMENT = "appartement"
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
        default=PropertyType.IMMEUBLE,
    )
    owner_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # ── Infos complémentaires ─────────────────────────────────────────────────
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(nullable=True)

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
    units: Mapped[list["Unit"]] = relationship(
        "Unit", back_populates="parent_property", cascade="all, delete-orphan", lazy="select"
    )
    leases: Mapped[list["Lease"]] = relationship(
        "Lease", back_populates="parent_property", lazy="select"
    )

    @property
    def full_address(self) -> str:
        parts = [self.address, self.zip_code, self.city]
        return ", ".join(p for p in parts if p)

    def __repr__(self) -> str:
        return f"<Property {self.name} — {self.city}>"
