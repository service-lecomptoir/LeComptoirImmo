import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator

from app.models.signalement import (
    SignalementCategory, SignalementUrgency, SignalementStatus,
)


class SignalementCreate(BaseModel):
    category: SignalementCategory
    description: str
    urgency: SignalementUrgency = SignalementUrgency.MOYEN
    title: Optional[str] = None
    # Date/heure de survenue ; par défaut « maintenant » côté service si absent.
    occurred_at: Optional[datetime] = None
    # Optionnels : un gestionnaire peut cibler un bien/locataire ; pour un locataire
    # ils sont résolus automatiquement depuis son bail actif.
    property_id: Optional[uuid.UUID] = None
    tenant_id: Optional[uuid.UUID] = None
    lease_id: Optional[uuid.UUID] = None

    @field_validator("description")
    @classmethod
    def _desc_not_empty(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("La description ne peut pas être vide")
        return v.strip()


class SignalementUpdate(BaseModel):
    status: Optional[SignalementStatus] = None
    urgency: Optional[SignalementUrgency] = None
    resolution_note: Optional[str] = None
