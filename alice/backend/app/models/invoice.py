import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Numeric, Integer, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AliceInvoice(Base):
    """Facture mensuelle émise à un gestionnaire (client) pour sa formule."""
    __tablename__ = "alice_invoices"
    __table_args__ = (
        UniqueConstraint(
            "gestionnaire_user_id", "period_year", "period_month",
            name="uq_invoice_gestionnaire_period",
        ),
        Index("ix_invoice_period", "period_year", "period_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Référence vers users.id (gestionnaire dans LeCI)
    gestionnaire_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Snapshot du nom de la formule au moment de la génération
    plan_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # paid | unpaid
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="unpaid")
    paid_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return f"<AliceInvoice {self.gestionnaire_user_id} {self.period_year}-{self.period_month:02d} [{self.status}]>"
