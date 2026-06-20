"""Modèles Automatisation — règles d'envoi et logs de communication."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class RuleType(str, Enum):
    AVIS_ECHEANCE = "avis_echeance"
    QUITTANCE = "quittance"
    RAPPEL_IMPAYE = "rappel_impaye"
    RELANCE_1 = "relance_1"
    RELANCE_2 = "relance_2"
    COMMUNICATION_GROUPEE = "communication_groupee"
    # Révision du loyer / des charges (déclenché à une revalorisation datée)
    REVISION_LOYER = "revision_loyer"
    REVISION_CHARGES = "revision_charges"
    # Taxe d'enlèvement des ordures ménagères (déclenché à une déclaration à payer)
    TAXE_OM = "taxe_om"
    # Rapport mensuel de gestion (envoi planifié, jour = trigger_days)
    RAPPORT_MENSUEL = "rapport_mensuel"
    # Communications de candidature (event-driven, e-mail au candidat)
    CANDIDATURE_ACCUSE = "candidature_accuse"
    CANDIDATURE_PIECES = "candidature_pieces"
    CANDIDATURE_VISITE = "candidature_visite"
    CANDIDATURE_RELANCE_VISITE = "candidature_relance_visite"
    CANDIDATURE_ACCEPTATION = "candidature_acceptation"
    CANDIDATURE_REFUS = "candidature_refus"


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    EMAIL_SMS = "email_sms"


class AutomationRule(Base, TimestampMixin):
    __tablename__ = "automation_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # Déclenchement : X jours avant/après
    trigger_days: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Heure:minute d'exécution quotidienne de cette automatisation (génération /
    # traitement), réglée dans l'onglet Auto Génération (format hh:mm).
    run_hour: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    run_minute: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Dernière exécution automatique ou manuelle (« Exécuter maintenant »).
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Canal d'envoi (hérité ; remplacé par les interrupteurs send_email/send_sms).
    channel: Mapped[str] = mapped_column(String(20), default="email", nullable=False)

    # Options d'automatisation (onglet Automatisation), activables/désactivables :
    # génération du document, dépôt sur le compte locataire, envoi e-mail, envoi SMS.
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_deposit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    send_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    send_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Contenu personnalisé
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True)
    body_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Adresse(s) en copie (CC) des e-mails de cette règle, séparées par des
    # virgules (ex. l'e-mail du gestionnaire). NULL/"" = aucune copie.
    cc_emails: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Signature (nom du service) affichée en bas des e-mails de cette règle,
    # ex. « Service contentieux » ou « Service Gestion Locative ».
    signature: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Actif/inactif
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Filtre optionnel
    filter_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Propriétaire de la règle (gestionnaire ou admin)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<AutomationRule {self.name}>"


class CommunicationLog(Base, TimestampMixin):
    __tablename__ = "communication_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automation_rules.id", ondelete="SET NULL"), nullable=True
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )

    lease_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="CASCADE"), nullable=True
    )

    # Clé d'idempotence : une cible + une règle = un seul envoi (anti-doublon).
    dedup_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<CommLog {self.channel} → {self.recipient}>"
