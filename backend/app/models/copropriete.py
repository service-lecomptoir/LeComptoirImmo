import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.owner import Owner


class Copropriete(Base, TimestampMixin):
    """Immeuble en copropriété géré par le syndic (mandataire). Le syndic est le
    gestionnaire courant ; les copropriétaires réutilisent l'entité Owner."""

    __tablename__ = "coproprietes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ref_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # N° d'immatriculation au registre national des copropriétés.
    immatriculation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Adresse postale structurée (même format que les biens).
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    construction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    keys: Mapped[list["CoproRepartitionKey"]] = relationship(
        "CoproRepartitionKey",
        back_populates="copropriete",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )
    lots: Mapped[list["CoproLot"]] = relationship(
        "CoproLot",
        back_populates="copropriete",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    @property
    def full_address(self) -> str | None:
        loc = " ".join(p for p in [(self.zip_code or "").strip(), (self.city or "").strip()] if p)
        country = (self.country or "").strip()
        parts = [
            (self.address or "").strip(),
            loc,
            country if country and country.lower() != "france" else "",
        ]
        joined = ", ".join(p for p in parts if p)
        return joined or None

    def __repr__(self) -> str:
        return f"<Copropriete {self.name}>"


class CoproRepartitionKey(Base, TimestampMixin):
    """Clé de répartition des charges (générale, ascenseur, chauffage, eau…).
    Chaque lot porte un nombre de tantièmes pour chaque clé."""

    __tablename__ = "copro_repartition_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Base totale de la clé (ex. 10000 millièmes). La somme des tantièmes des lots
    # doit l'égaler (contrôle d'intégrité côté service).
    total_tantiemes: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    # Clé générale (charges communes générales) : une par copropriété en principe.
    is_general: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    copropriete: Mapped["Copropriete"] = relationship("Copropriete", back_populates="keys")

    def __repr__(self) -> str:
        return f"<CoproRepartitionKey {self.name}>"


class CoproLot(Base, TimestampMixin):
    """Lot de copropriété (appartement, cave, parking, local…) appartenant à un
    copropriétaire (Owner). Peut être relié à un bien géré (property)."""

    __tablename__ = "copro_lots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    numero: Mapped[str] = mapped_column(String(30), nullable=False)  # « Lot 12 »
    lot_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # appartement/cave/parking
    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Copropriétaire : on réutilise l'entité Owner (un copropriétaire est un propriétaire).
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Lien optionnel vers un bien géré (location) correspondant à ce lot.
    property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True
    )

    copropriete: Mapped["Copropriete"] = relationship("Copropriete", back_populates="lots")
    owner: Mapped["Owner | None"] = relationship("Owner", lazy="select")
    tantiemes: Mapped[list["CoproLotTantieme"]] = relationship(
        "CoproLotTantieme",
        back_populates="lot",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<CoproLot {self.numero}>"


class CoproLotTantieme(Base, TimestampMixin):
    """Tantièmes d'un lot pour une clé de répartition donnée."""

    __tablename__ = "copro_lot_tantiemes"
    __table_args__ = (UniqueConstraint("lot_id", "key_id", name="uq_copro_lot_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_lots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("copro_repartition_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tantiemes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    lot: Mapped["CoproLot"] = relationship("CoproLot", back_populates="tantiemes")

    def __repr__(self) -> str:
        return f"<CoproLotTantieme lot={self.lot_id} key={self.key_id} {self.tantiemes}>"
