import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Boolean, Text, Numeric, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base, TimestampMixin


class AliceLicense(Base, TimestampMixin):
    """Licence associée à chaque gestionnaire LeComptoirImmo."""
    __tablename__ = "alice_licenses"

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
        ForeignKey("alice_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Surcharges par compte
    property_limit_override: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    monthly_price_override: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Résiliation différée : accès maintenu jusqu'à cette date (fin du mois de
    # facturation), puis blocage appliqué paresseusement au prochain contrôle de licence.
    access_until: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=False), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Coordonnées du gestionnaire
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # IDs des users bloqués en cascade (pour pouvoir unblock proprement)
    blocked_user_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False, server_default="[]")

    # ── Stripe (abonnement récurrent : carte / prélèvement SEPA) ─────────────
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    # active / trialing / past_due / canceled / unpaid / incomplete… (statut Stripe).
    stripe_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # 'card' ou 'sepa_debit'.
    stripe_payment_method_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Fin de la période payée en cours (= prochaine échéance de prélèvement).
    stripe_current_period_end: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=False), nullable=True)

    def __repr__(self) -> str:
        return f"<AliceLicense gestionnaire={self.gestionnaire_user_id} blocked={self.is_blocked}>"
