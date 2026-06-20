import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    PENDING_CLOSURE = "pending_closure"  # clôture proposée par le gestionnaire, en attente de validation du demandeur
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, Enum):
    INCIDENT = "incident"
    QUESTION = "question"
    DEMANDE = "demande"
    AUTRE = "autre"


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Sujet déclaré par le locataire — pilote l'agent IA notifié au gestionnaire
    # (voisinage → Sécurité, logement → Administratif…). Voir services/agent_events.py.
    topic: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    category: Mapped[str] = mapped_column(
        SAEnum(
            TicketCategory,
            name="ticket_category_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=TicketCategory.AUTRE,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(
            TicketStatus,
            name="ticket_status_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=TicketStatus.OPEN,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        SAEnum(
            TicketPriority,
            name="ticket_priority_enum",
            create_type=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=TicketPriority.MEDIUM,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lease_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Photo optionnelle jointe par le locataire à la création de la démarche.
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage",
        back_populates="ticket",
        lazy="select",
        order_by="TicketMessage.created_at",
    )
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="select")
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_to_id], lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.title!r} [{self.status}]>"


class TicketMessage(Base, TimestampMixin):
    __tablename__ = "ticket_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="messages")
    author: Mapped["User"] = relationship("User", lazy="select")

    def __repr__(self) -> str:
        return f"<TicketMessage ticket={self.ticket_id}>"
