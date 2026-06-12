import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum

from app.database import Base, TimestampMixin


class NotificationType(str, Enum):
    LOYER_RETARD = "loyer_retard"
    BAIL_EXPIRE_SOON = "bail_expire_soon"
    BAIL_EXPIRE = "bail_expire"
    PAIEMENT_RECU = "paiement_recu"
    SYSTEME = "systeme"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Type & contenu ────────────────────────────────────────────────────────
    notification_type: Mapped[str] = mapped_column(
        SAEnum(NotificationType, name="notification_type_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        SAEnum(NotificationPriority, name="notification_priority_enum", create_type=False,
               values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=NotificationPriority.NORMAL,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Entité liée (polymorphique) ────────────────────────────────────────────
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # ── Lecture ───────────────────────────────────────────────────────────────
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # ── Destinataire (NULL = tous les utilisateurs) ────────────────────────────
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} : {self.title[:40]}>"
