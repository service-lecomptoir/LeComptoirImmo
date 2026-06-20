import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease


class RentRevision(Base, TimestampMixin):
    """Révision d'UN champ (loyer HC OU charges) avec date d'effet.

    Modèle « par champ » : chaque ligne ne concerne que le loyer (kind='rent')
    OU les charges (kind='charges'), avec son nouveau montant (`amount`) et le
    montant précédent (`prev_amount`, pour l'affichage « en rappel »).

    On ne conserve qu'UNE révision « en cours » par champ : une nouvelle
    réévaluation du même champ encore non appliquée remplace la précédente
    (pas de doublon). Le mois déjà appelé n'est jamais modifié : la génération
    applique, pour une période, la dernière révision du champ dont la date
    d'effet précède le début de la période.
    """

    __tablename__ = "lease_rent_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Champ concerné : 'rent' (loyer HC) ou 'charges' (provisions).
    kind: Mapped[str] = mapped_column(String(10), nullable=False, default="rent", index=True)

    # Date à partir de laquelle le nouveau montant s'applique (1er du mois en général).
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Nouveau montant du champ, et montant précédent (rappel).
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    prev_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Origine : 'manuel' | 'irl' | 'charges' | 'amiable'
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manuel")
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # True quand la date d'effet est atteinte (sinon : révision programmée à venir).
    applied: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    lease: Mapped["Lease"] = relationship("Lease", lazy="select")

    def __repr__(self) -> str:
        return f"<RentRevision {self.lease_id} {self.kind} eff={self.effective_date} amount={self.amount}>"
