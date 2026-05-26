import uuid
from typing import Optional
from sqlalchemy import String, Boolean, Text, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin


class ProxygenLicense(Base, TimestampMixin):
    """Licence associée à chaque gestionnaire LeComptoirImmo."""
    __tablename__ = "proxygen_licenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Référence vers users.id (gestionnaire dans LeCI)
    gestionnaire_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    # Plan tarifaire (peut être null = pas de plan assigné)
    plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proxygen_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Surcharges par compte
    property_limit_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monthly_price_override: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Coordonnées du gestionnaire
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # IDs des users bloqués en cascade (pour pouvoir unblock proprement)
    blocked_user_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False, server_default="[]")

    def __repr__(self) -> str:
        return f"<ProxygenLicense gestionnaire={self.gestionnaire_user_id} blocked={self.is_blocked}>"
