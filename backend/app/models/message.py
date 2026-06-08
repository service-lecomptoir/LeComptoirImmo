import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class ProprietaireMessage(Base, TimestampMixin):
    """Messages entre un propriétaire et le gestionnaire."""
    __tablename__ = "proprietaire_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    proprietaire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_from_gestionnaire: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    proprietaire: Mapped["User"] = relationship("User", foreign_keys=[proprietaire_id], lazy="select")
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id], lazy="select")

    def __repr__(self) -> str:
        return f"<ProprietaireMessage from={'gestionnaire' if self.is_from_gestionnaire else 'proprietaire'}>"
