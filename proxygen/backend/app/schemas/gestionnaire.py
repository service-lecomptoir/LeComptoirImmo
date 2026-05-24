import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.schemas.license import LicenseOut
from app.schemas.plan import PlanOut


class GestionnaireCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., max_length=150)
    password: str = Field(..., min_length=8)
    plan_id: Optional[uuid.UUID] = None
    property_limit_override: Optional[int] = Field(None, ge=1)
    monthly_price_override: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class GestionnaireUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=150)
    plan_id: Optional[uuid.UUID] = None
    property_limit_override: Optional[int] = Field(None, ge=1)
    monthly_price_override: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class GestionnaireOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    license: Optional[LicenseOut] = None
    plan: Optional[PlanOut] = None
    # Limite effective : override > plan > null
    effective_property_limit: Optional[int] = None
    # Nombre de biens actuellement créés par ce gestionnaire
    property_count: int = 0

    model_config = {"from_attributes": True}


class GestionnairePropertyOut(BaseModel):
    id: uuid.UUID
    name: str
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None

    model_config = {"from_attributes": True}
