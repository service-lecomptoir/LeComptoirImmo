import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class OwnerReversement(Base, TimestampMixin):
    """Reversement effectif au propriétaire (mandant) par le gestionnaire mandataire.

    Trace ce qui a réellement été versé au bailleur (loyers encaissés nets des
    honoraires) afin de calculer le « solde à reverser » et d'alimenter le compte
    rendu de gestion (CRG). Distinct des paiements locataire (table payments)."""

    __tablename__ = "owner_reversements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Période couverte par le reversement. Le mois est optionnel : un reversement
    # peut couvrir plusieurs mois (NULL = reversement annuel / ad hoc).
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_month: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Montant net effectivement versé au propriétaire.
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Mode de versement (virement | cheque | especes | autre).
    method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reversement_date: Mapped[date] = mapped_column(Date, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit / isolation : qui a saisi le reversement (mandataire).
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<OwnerReversement {self.owner_id} {self.amount}>"
