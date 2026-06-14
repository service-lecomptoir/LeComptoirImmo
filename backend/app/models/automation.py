"""Modèles Automatisation — règles d'envoi et logs de communication."""
import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum


from app.database import Base, TimestampMixin


class RuleType(str, Enum):
    AVIS_ECHEANCE = "avis_echeance"
    QUITTANCE = "quittance"
    RAPPEL_IMPAYE = "rappel_impaye"
    RELANCE_1 = "relance_1"
    RELANCE_2 = "relance_2"
    COMMUNICATION_GROUPEE = "communication_groupee"


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    EMAIL_SMS = "email_sms"


class AutomationRule(Base, TimestampMixin):
    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Déclenchement : X jours avant/après
    trigger_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Canal d'envoi
    channel: Mapped[str] = mapped_column(String(20), default="email", nullable=False)

    # Contenu personnalisé
    subject: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    body_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Adresse(s) en copie (CC) des e-mails de cette règle, séparées par des
    # virgules (ex. l'e-mail du gestionnaire). NULL/"" = aucune copie.
    cc_emails: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Signature (nom du service) affichée en bas des e-mails de cette règle,
    # ex. « Service contentieux » ou « Service Gestion Locative ».
    signature: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # Actif/inactif
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Filtre optionnel
    filter_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Propriétaire de la règle (gestionnaire ou admin)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<AutomationRule {self.name}>"


class CommunicationLog(Base, TimestampMixin):
    __tablename__ = "communication_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automation_rules.id", ondelete="SET NULL"),
        nullable=True
    )

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True
    )

    lease_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"),
        nullable=True
    )

    # Clé d'idempotence : une cible + une règle = un seul envoi (anti-doublon).
    dedup_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<CommLog {self.channel} → {self.recipient}>"
