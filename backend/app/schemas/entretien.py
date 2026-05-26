import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

from app.models.entretien import EntretienType, EntretienStatus, EntretienFrequency


class PrestataireCreate(BaseModel):
    name: str
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    notes: Optional[str] = None


class PrestataireUpdate(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class PrestataireResponse(BaseModel):
    id: uuid.UUID
    name: str
    specialty: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    siret: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EntretienCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: EntretienType = EntretienType.PREVENTIF
    status: EntretienStatus = EntretienStatus.PLANIFIE
    frequency: EntretienFrequency = EntretienFrequency.UNIQUE
    scheduled_date: date
    completed_date: Optional[date] = None
    next_date: Optional[date] = None
    cost: Optional[float] = None
    property_id: Optional[uuid.UUID] = None
    prestataire_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class EntretienUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[EntretienType] = None
    status: Optional[EntretienStatus] = None
    frequency: Optional[EntretienFrequency] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    next_date: Optional[date] = None
    cost: Optional[float] = None
    property_id: Optional[uuid.UUID] = None
    prestataire_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class EntretienResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    type: str
    status: str
    frequency: str
    scheduled_date: date
    completed_date: Optional[date] = None
    next_date: Optional[date] = None
    cost: Optional[float] = None
    property_id: Optional[uuid.UUID] = None
    property_label: Optional[str] = None
    prestataire_id: Optional[uuid.UUID] = None
    prestataire_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
