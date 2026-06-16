import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lease import Lease


class RentRevision(Base, TimestampMixin):
    """Révision de loyer / charges avec date d'effet.

    Toute évolution du loyer ou des charges d'un bail (édition manuelle, révision
    IRL, régularisation de charges, réévaluation amiable) est enregistrée ici avec
    une **date d'effet**. Le mois déjà appelé n'est jamais modifié : la génération
    des échéances applique, pour une période donnée, la dernière révision dont la
    date d'effet précède le début de la période. Les champs `prev_*` conservent le
    montant précédent pour l'affichage « en rappel » dans l'historique du bail.
    """
    __tablename__ = "lease_rent_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Date à partir de laquelle les nouveaux montants s'appliquent (1er du mois en général).
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Nouveaux montants applicables à compter de la date d'effet.
    rent_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    charges_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # Montants précédents (rappel).
    prev_rent_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    prev_charges_amount: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    # Origine : 'manuel' | 'irl' | 'charges' | 'amiable' | 'initial'
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manuel")
    reason: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # True tant que la date d'effet n'est pas atteinte (révision programmée à venir).
    applied: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    lease: Mapped["Lease"] = relationship("Lease", lazy="select")

    def __repr__(self) -> str:
        return f"<RentRevision {self.lease_id} eff={self.effective_date} rent={self.rent_amount}>"
