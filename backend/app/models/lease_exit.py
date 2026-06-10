import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Text, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin


class LeaseExit(Base, TimestampMixin):
    """Dossier de sortie du locataire (un par bail).

    Suit le préavis et la date de départ, relie les états des lieux d'entrée et de
    sortie (comparaison des dégradations), porte le décompte du dépôt de garantie
    (retenues → restitution), puis clôture administrativement le dossier
    (résiliation du bail + libération du bien)."""
    __tablename__ = "lease_exits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    # preavis | etat_des_lieux | decompte | cloture
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="preavis", index=True)

    # ── Préavis & départ ──────────────────────────────────────────────────────
    notice_received_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    departure_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # ── États des lieux (comparaison entrée / sortie) ─────────────────────────
    entry_inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True,
    )
    exit_inspection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True,
    )

    # ── Dépôt de garantie ─────────────────────────────────────────────────────
    # Montant du dépôt (copié du bail à l'ouverture du dossier).
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Retenues : [{label, amount}] (dégradations, loyers dus, etc.).
    deductions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<LeaseExit lease={self.lease_id} [{self.status}]>"
