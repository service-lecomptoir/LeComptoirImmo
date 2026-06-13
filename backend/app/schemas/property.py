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
    property_type: PropertyType = PropertyType.APPARTEMENT
    owner_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    year_built: Optional[int] = None
    # ── Caractéristiques du logement ──────────────────────────────────────────
    typology: Optional[str] = None          # T1 … T10
    floor: Optional[int] = None
    area_sqm: Optional[float] = None
    bathrooms: Optional[int] = None         # salles d'eau / de bain
    heating_type: Optional[str] = None
    energy_class: Optional[str] = None
    # ── Équipements & extérieurs ──────────────────────────────────────────────
    furnished: bool = False
    kitchen_equipped: bool = False
    has_elevator: bool = False
    has_balcony: bool = False
    has_terrace: bool = False
    has_garden: bool = False
    has_parking: bool = False
    has_cellar: bool = False
    has_fiber: bool = False
    has_air_conditioning: bool = False


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    reference: Optional[str] = None
    address: Optional[str] = None
    address2: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    property_type: Optional[PropertyType] = None
    owner_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    owner_phone: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    year_built: Optional[int] = None
    typology: Optional[str] = None
    floor: Optional[int] = None
    area_sqm: Optional[float] = None
    bathrooms: Optional[int] = None
    heating_type: Optional[str] = None
    energy_class: Optional[str] = None
    furnished: Optional[bool] = None
    kitchen_equipped: Optional[bool] = None
    has_elevator: Optional[bool] = None
    has_balcony: Optional[bool] = None
    has_terrace: Optional[bool] = None
    has_garden: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_cellar: Optional[bool] = None
    has_fiber: Optional[bool] = None
    has_air_conditioning: Optional[bool] = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    ref_code: Optional[str] = None
    name: str
    reference: Optional[str]
    address: str
    address2: Optional[str]
    zip_code: str
    city: str
    country: str
    property_type: PropertyType
    full_address: str
    owner_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str]
    owner_email: Optional[str]
    owner_phone: Optional[str]
    description: Optional[str]
    notes: Optional[str]
    year_built: Optional[int]
    typology: Optional[str] = None
    floor: Optional[int] = None
    area_sqm: Optional[float] = None
    bathrooms: Optional[int] = None
    heating_type: Optional[str] = None
    energy_class: Optional[str] = None
    furnished: bool = False
    kitchen_equipped: bool = False
    has_elevator: bool = False
    has_balcony: bool = False
    has_terrace: bool = False
    has_garden: bool = False
    has_parking: bool = False
    has_cellar: bool = False
    has_fiber: bool = False
    has_air_conditioning: bool = False
    is_occupied: bool = False
    is_available: bool = True
    unit_count: int = 0
    occupied_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyListItem(BaseModel):
    id: uuid.UUID
    ref_code: Optional[str] = None
    name: str
    city: str
    property_type: PropertyType
    full_address: str
    owner_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    owner_name: Optional[str]
    typology: Optional[str] = None
    area_sqm: Optional[float] = None
    is_occupied: bool = False
    unit_count: int = 0
    occupied_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
