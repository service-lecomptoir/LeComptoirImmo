import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Boolean, Text, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import func

from app.database import Base


class AlicePlan(Base):
    """Formules tarifaires proposées aux gestionnaires."""
    __tablename__ = "alice_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # null = illimité
    property_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monthly_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Fonctionnalités incluses dans le plan (liste de clés ; null = toutes autorisées).
    features: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # ── Stripe : produit + prix mensuel récurrent associés à ce plan ─────────
    stripe_product_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<AlicePlan {self.name}>"
