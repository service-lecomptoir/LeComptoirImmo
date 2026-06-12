import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.tenant import Tenant


# Valeurs stockées en TEXTE (pas d'enum Postgres) : on pourra ajouter des
# catégories / sources (ex. capteurs télématiques) sans migration ALTER TYPE.

class SignalementCategory(str, Enum):
    BRUIT = "bruit"
    SECURITE = "securite"
    PROPRETE = "proprete"            # propreté des parties communes
    LOGEMENT = "logement"            # problème dans mon logement
    DEGRADATION = "degradation"      # dégradation / vandalisme
    AUTRE = "autre"


class SignalementUrgency(str, Enum):
    FAIBLE = "faible"
    MOYEN = "moyen"
    URGENT = "urgent"


class SignalementStatus(str, Enum):
    NOUVEAU = "nouveau"
    EN_COURS = "en_cours"
    RESOLU = "resolu"
    CLOS = "clos"


class SignalementSource(str, Enum):
    LOCATAIRE = "locataire"
    GESTIONNAIRE = "gestionnaire"
    TELEMATIQUE = "telematique"      # à terme : remontée automatique par capteurs


class Signalement(Base, TimestampMixin):
    """Signalement d'un problème (bruit, sécurité, propreté, logement…).

    Aujourd'hui saisi par un locataire (ou un gestionnaire) ; conçu pour qu'à terme
    la source puisse être « télématique » (capteurs). La localisation est le bien
    (`property_id`) ; `occurred_at` = date/heure de survenue (distincte de la
    création). Le moteur d'alertes bruit (étape 2) s'appuiera sur category=bruit +
    occurred_at + property_id.
    """
    __tablename__ = "signalements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    urgency: Mapped[str] = mapped_column(String(10), nullable=False, default=SignalementUrgency.MOYEN.value)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default=SignalementStatus.NOUVEAU.value, index=True)
    source: Mapped[str] = mapped_column(String(12), nullable=False, default=SignalementSource.LOCATAIRE.value)

    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Date/heure de survenue de l'incident (peut différer de la création).
    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Photo optionnelle (chemin relatif sous uploads/, servie via /uploads).
    photo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Localisation = le bien concerné. Locataire/contrat éventuels.
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lease_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leases.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Traitement par le gestionnaire.
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    parent_property: Mapped[Optional["Property"]] = relationship("Property", lazy="select")
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", lazy="select")

    def __repr__(self) -> str:
        return f"<Signalement {self.category} {self.status}>"
