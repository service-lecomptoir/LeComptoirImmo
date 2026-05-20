import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, model_validator
from app.models.unit import UnitType


class UnitCreate(BaseModel):
    property_id: uuid.UUID
    unit_ref: str
    unit_type: UnitType = UnitType.T2
    floor: Optional[int] = None
    building: Optional[str] = None
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    base_rent: float
    charges_amount: float = 0.0
    deposit_months: int = 1
    is_available: bool = True
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_rent(self) -> "UnitCreate":
        if self.base_rent <= 0:
            raise ValueError("Le loyer doit être supérieur à 0")
        if self.charges_amount < 0:
            raise ValueError("Les charges ne peuvent pas être négatives")
        return self


class UnitUpdate(BaseModel):
    unit_ref: Optional[str] = None
    unit_type: Optional[UnitType] = None
    floor: Optional[int] = None
    building: Optional[str] = None
    area_sqm: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    base_rent: Optional[float] = None
    charges_amount: Optional[float] = None
    deposit_months: Optional[int] = None
    is_available: Optional[bool] = None
    notes: Optional[str] = None


class UnitResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    unit_ref: str
    unit_type: UnitType
    floor: Optional[int]
    building: Optional[str]
    area_sqm: Optional[float]
    rooms: Optional[int]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    base_rent: float
    charges_amount: float
    deposit_months: int
    deposit_amount: float
    total_monthly: float
    is_occupied: bool
    is_available: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UnitListItem(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    unit_ref: str
    unit_type: UnitType
    floor: Optional[int]
    area_sqm: Optional[float]
    rooms: Optional[int]
    base_rent: float
    charges_amount: float
    total_monthly: float
    is_occupied: bool
    is_available: bool

    model_config = {"from_attributes": True}
