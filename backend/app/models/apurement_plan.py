import uuid
from typing import Optional, Any
from sqlalchemy import String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin


class ApurementPlan(Base, TimestampMixin):
    """Plan d'apurement d'une dette locative : échéancier suivi (versements prévus
    vs réglés). Les échéances sont stockées en JSONB :
    [{seq, due_date 'YYYY-MM-DD', amount, paid bool, paid_date 'YYYY-MM-DD'|null}]."""
    __tablename__ = "apurement_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    origin_payment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    installments: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    # active (en cours) | completed (tout réglé) | cancelled (annulé)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    def __repr__(self) -> str:
        return f"<ApurementPlan {self.id} : {self.status}>"
