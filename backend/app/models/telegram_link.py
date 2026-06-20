import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class TelegramLink(Base, TimestampMixin):
    """Liaison entre un gestionnaire et son compte Telegram (équipe d'agents IA).

    Flux : le gestionnaire génère un `link_code` dans l'app, démarre le bot
    Telegram avec « /start <code> ». Le webhook relie alors le `chat_id` au
    compte. `link_code` est consommé (mis à None) une fois la liaison faite.
    """

    __tablename__ = "telegram_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Identifiant de conversation Telegram (rempli après /start).
    chat_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # Code de liaison à usage unique (le temps de relier le compte).
    link_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Action proposée en attente de confirmation (Phase 3 — actions des agents).
    pending_action: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pending_action_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<TelegramLink user={self.user_id} chat={self.chat_id}>"
