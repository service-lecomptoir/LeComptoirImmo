import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.property import PropertyType


class PropertyCreate(BaseModel):
    name: str
    reference: Optional[str] = None
    address: str
    address2: Optional[str] = None
    zip_code: str
    city: str
    country: str = "France"
    property_type: PropertyType = PropertyType.IMMEUBLE
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    year_built: Optional[int] = None


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    reference: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    property_type: Optional[PropertyType] = None
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    year_built: Optional[int] = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    name: str
    reference: Optional[str]
    address: str
    address2: Optional[str]
    zip_code: str
    city: str
    country: str
    property_type: PropertyType
    full_address: str
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str]
    owner_email: Optional[str]
    owner_phone: Optional[str]
    description: Optional[str]
    notes: Optional[str]
    year_built: Optional[int]
    unit_count: int = 0
    occupied_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyListItem(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    property_type: PropertyType
    full_address: str
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str]
    unit_count: int = 0
    occupied_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
