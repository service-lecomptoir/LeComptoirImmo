import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr

from app.models.property import PropertyType


class PropertyCreate(BaseModel):
    name: str
    reference: str | None = None
    address: str
    address2: str | None = None
    zip_code: str
    city: str
    country: str = "France"
    property_type: PropertyType = PropertyType.APPARTEMENT
    owner_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    owner_name: str | None = None
    owner_email: EmailStr | None = None
    owner_phone: str | None = None
    description: str | None = None
    notes: str | None = None
    year_built: int | None = None
    acquisition_date: date | None = None
    acquisition_value: float | None = None
    # ── Caractéristiques du logement ──────────────────────────────────────────
    typology: str | None = None  # T1 … T10
    floor: int | None = None
    area_sqm: float | None = None
    bathrooms: int | None = None  # salles d'eau / de bain
    heating_type: str | None = None
    energy_class: str | None = None
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
    name: str | None = None
    reference: str | None = None
    address: str | None = None
    address2: str | None = None
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    property_type: PropertyType | None = None
    owner_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    owner_name: str | None = None
    owner_email: EmailStr | None = None
    owner_phone: str | None = None
    description: str | None = None
    notes: str | None = None
    year_built: int | None = None
    acquisition_date: date | None = None
    acquisition_value: float | None = None
    typology: str | None = None
    floor: int | None = None
    area_sqm: float | None = None
    bathrooms: int | None = None
    heating_type: str | None = None
    energy_class: str | None = None
    furnished: bool | None = None
    kitchen_equipped: bool | None = None
    has_elevator: bool | None = None
    has_balcony: bool | None = None
    has_terrace: bool | None = None
    has_garden: bool | None = None
    has_parking: bool | None = None
    has_cellar: bool | None = None
    has_fiber: bool | None = None
    has_air_conditioning: bool | None = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    ref_code: str | None = None
    name: str
    reference: str | None
    address: str
    address2: str | None
    zip_code: str
    city: str
    country: str
    property_type: PropertyType
    full_address: str
    owner_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    owner_name: str | None
    owner_email: str | None
    owner_phone: str | None
    description: str | None
    notes: str | None
    year_built: int | None
    acquisition_date: date | None = None
    acquisition_value: float | None = None
    typology: str | None = None
    floor: int | None = None
    area_sqm: float | None = None
    bathrooms: int | None = None
    heating_type: str | None = None
    energy_class: str | None = None
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
    ref_code: str | None = None
    name: str
    city: str
    property_type: PropertyType
    full_address: str
    owner_id: uuid.UUID | None = None
    owner_user_id: uuid.UUID | None = None
    owner_name: str | None
    typology: str | None = None
    area_sqm: float | None = None
    is_occupied: bool = False
    unit_count: int = 0
    occupied_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
