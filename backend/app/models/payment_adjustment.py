import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.payment import Payment


# Types d'ajustement « à la volée » sur une échéance.
ADJUSTMENT_SUPPLEMENT = "supplement"  # montant à payer EN PLUS du loyer + charges
ADJUSTMENT_RESTITUTION = "restitution"  # montant à restituer (caution ou autre)


class PaymentAdjustment(Base, TimestampMixin):
    """Ligne d'ajustement ad hoc rattachée à l'échéance d'un mois.

    Permet d'ajouter, à la volée, un montant à payer en plus du loyer/charges
    (`supplement`) ou un montant à restituer au locataire (`restitution`, ex.
    remboursement de caution). Chaque ligne apparaît dans l'avis d'échéance et la
    quittance du mois. Le net à payer du mois = loyer + charges + Σ suppléments −
    Σ restitutions, plancher à 0. Le surplus de restitution (au-delà du mois) est
    soit reporté en crédit sur la prochaine échéance (bail actif), soit traité comme
    un remboursement (locataire ayant donné son congé).
    """

    __tablename__ = "payment_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # supplement | restitution
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    libelle: Mapped[str] = mapped_column(String(200), nullable=False)
    montant: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    payment: Mapped["Payment"] = relationship("Payment", back_populates="adjustments")

    def __repr__(self) -> str:
        return f"<PaymentAdjustment {self.type} {self.montant} '{self.libelle}'>"
