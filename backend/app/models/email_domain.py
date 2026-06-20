import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailDomain(Base):
    """Domaine e-mail autorisé pour l'envoi des communications d'un gestionnaire."""

    __tablename__ = "user_email_domains"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    # Défaut Python (pas server_default) pour éviter tout lazy-load post-flush en async.
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
