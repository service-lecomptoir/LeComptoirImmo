import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.entretien import EntretienFrequency, EntretienStatus, EntretienType


class PrestataireCreate(BaseModel):
    name: str
    specialty: str | None = None
    phone: str | None = None
    email: str | None = None
    siret: str | None = None
    notes: str | None = None


class PrestataireUpdate(BaseModel):
    name: str | None = None
    specialty: str | None = None
    phone: str | None = None
    email: str | None = None
    siret: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class PrestataireResponse(BaseModel):
    id: uuid.UUID
    name: str
    specialty: str | None = None
    phone: str | None = None
    email: str | None = None
    siret: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EntretienCreate(BaseModel):
    title: str
    description: str | None = None
    type: EntretienType = EntretienType.PREVENTIF
    status: EntretienStatus = EntretienStatus.PLANIFIE
    frequency: EntretienFrequency = EntretienFrequency.UNIQUE
    scheduled_date: date
    completed_date: date | None = None
    next_date: date | None = None
    cost: float | None = None
    property_id: uuid.UUID | None = None
    prestataire_id: uuid.UUID | None = None
    notes: str | None = None


class EntretienUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    type: EntretienType | None = None
    status: EntretienStatus | None = None
    frequency: EntretienFrequency | None = None
    scheduled_date: date | None = None
    completed_date: date | None = None
    next_date: date | None = None
    cost: float | None = None
    property_id: uuid.UUID | None = None
    prestataire_id: uuid.UUID | None = None
    notes: str | None = None


class EntretienResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    type: str
    status: str
    frequency: str
    scheduled_date: date
    completed_date: date | None = None
    next_date: date | None = None
    cost: float | None = None
    property_id: uuid.UUID | None = None
    property_label: str | None = None
    prestataire_id: uuid.UUID | None = None
    prestataire_name: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
