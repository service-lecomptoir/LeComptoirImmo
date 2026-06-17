import uuid
from typing import Optional, Any
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


# Langues proposées pour le contenu des courriers (onglet Communication).
TEMPLATE_LANGS = ["fr", "en", "pt-BR", "ht", "srn"]
TEMPLATE_LANG_LABELS = {
    "fr": "Français",
    "en": "Anglais",
    "pt-BR": "Portugais (Brésil)",
    "ht": "Créole haïtien",
    "srn": "Sranan Tongo",
}


class MessageTemplate(Base, TimestampMixin):
    """Modèle de courrier (e-mail + SMS) multilingue de l'onglet Communication.

    Plusieurs modèles par type (rule_type) sont possibles ; un seul est marqué
    « utilisé » (is_selected) et sera celui repris par l'automatisation. Le contenu
    est porté par langue dans `content` : { lang: {subject, body, sms} }.
    """

    __tablename__ = "message_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gestionnaire_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Type de document/communication concerné (avis_echeance, quittance, …).
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Contenu par langue : { "fr": {"subject": str, "body": str, "sms": str}, ... }
    content: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)

    # Modèle retenu pour ce type (un seul actif par gestionnaire + type).
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<MessageTemplate {self.rule_type} : {self.name}>"
