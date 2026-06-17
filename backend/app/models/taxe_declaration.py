import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    pass


class TaxeDeclaration(Base, TimestampMixin):
    """Déclaration de taxe d'enlèvement des ordures ménagères (TEOM) récupérée
    auprès du locataire, pour une année donnée. Conserve juste les données (pas de
    PDF) : le décompte est régénéré à la volée par TaxesFoncieresPDFService, et la
    déclaration est visible côté locataire (« Mes documents ») et gestionnaire."""

    __tablename__ = "taxe_declarations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    teom_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<TaxeDeclaration {self.year} : {self.teom_amount} €>"
