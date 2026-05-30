import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import func

from app.database import Base


class AliceSubscriptionRequest(Base):
    """Demande de souscription / démo envoyée depuis la page d'accueil
    Le Comptoir Immo, à traiter par l'équipe Alice."""
    __tablename__ = "alice_subscription_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="site_lecomptoir")
    # nouveau | en_cours | traite | rejete
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="nouveau")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<AliceSubscriptionRequest {self.email} [{self.status}]>"
