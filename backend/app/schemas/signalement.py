import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.signalement import (
    SignalementCategory,
    SignalementStatus,
    SignalementUrgency,
)


class SignalementCreate(BaseModel):
    category: SignalementCategory
    description: str
    urgency: SignalementUrgency = SignalementUrgency.MOYEN
    title: str | None = None
    # Date/heure de survenue ; par défaut « maintenant » côté service si absent.
    occurred_at: datetime | None = None
    # Optionnels : un gestionnaire peut cibler un bien/locataire ; pour un locataire
    # ils sont résolus automatiquement depuis son bail actif.
    property_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    lease_id: uuid.UUID | None = None

    @field_validator("description")
    @classmethod
    def _desc_not_empty(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("La description ne peut pas être vide")
        return v.strip()


class SignalementUpdate(BaseModel):
    status: SignalementStatus | None = None
    urgency: SignalementUrgency | None = None
    resolution_note: str | None = None
