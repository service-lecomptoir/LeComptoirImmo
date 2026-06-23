import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class CoproWorksFundEntry(Base, TimestampMixin):
    """Mouvement du fonds de travaux (loi ALUR) : cotisation (alimentation) ou
    dépense (travaux financés). Le solde = cumul des cotisations − dépenses."""

    __tablename__ = "copro_works_fund"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    # contribution (alimentation) | depense (travaux)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CoproMaintenance(Base, TimestampMixin):
    """Entrée du carnet d'entretien de la copropriété (intervention/contrat)."""

    __tablename__ = "copro_maintenance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    copropriete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coproprietes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)  # ascenseur, chauffage…
    description: Mapped[str] = mapped_column(Text, nullable=False)
    supplier: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
