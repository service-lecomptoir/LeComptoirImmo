import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.models.tenant import Civility


class OwnerCreate(BaseModel):
    civility: Optional[Civility] = None
    first_name: Optional[str] = None
    last_name: str
    company_name: Optional[str] = None
    national_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None  # Compte de connexion (optionnel)

    @field_validator("last_name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Le nom ne peut pas être vide")
        return v.strip()


class OwnerUpdate(BaseModel):
    civility: Optional[Civility] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    national_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None


class OwnerResponse(BaseModel):
    id: uuid.UUID
    civility: Optional[Civility]
    first_name: Optional[str]
    last_name: str
    company_name: Optional[str]
    full_name: str
    national_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    iban: Optional[str]
    bic: Optional[str]
    bank_holder: Optional[str]
    notes: Optional[str]
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OwnerListItem(BaseModel):
    """Version allégée pour les listes."""
    id: uuid.UUID
    full_name: str
    civility: Optional[Civility]
    first_name: Optional[str]
    last_name: str
    company_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
