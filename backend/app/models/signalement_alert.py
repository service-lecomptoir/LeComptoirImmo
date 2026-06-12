import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin


class AlertType(str, Enum):
    NOCTURNE = "nocturne"      # bruit signalé entre 22h et 7h
    ESCALADE = "escalade"      # récurrence de bruit sur un bien → gestionnaire
    PREVENTIF = "preventif"    # rappel préventif périodique


class SignalementAlert(Base, TimestampMixin):
    """Historique des alertes du moteur bruit (traçabilité + anti-spam).

    Toute alerte émise (message nocturne à l'appartement, escalade au gestionnaire,
    rappel préventif) y est journalisée. Sert aussi de garde-fou : on ne ré-escalade
    pas / ne re-relance pas un même bien tant qu'une alerte récente existe.
    """
    __tablename__ = "signalement_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    signalement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signalements.id", ondelete="SET NULL"), nullable=True
    )
    recipient_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SignalementAlert {self.alert_type}>"
