import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PlanBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    property_limit: Optional[int] = Field(None, ge=1, description="null = illimité")
    monthly_price: float = Field(0.0, ge=0)
    # Liste de clés de fonctionnalités incluses ; null = toutes autorisées.
    features: Optional[List[str]] = None


class PlanCreate(PlanBase):
    pass


class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    property_limit: Optional[int] = Field(None, ge=1)
    monthly_price: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None
    features: Optional[List[str]] = None


class PlanOut(PlanBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    gestionnaire_count: int = 0
    stripe_product_id: Optional[str] = None
    stripe_price_id: Optional[str] = None

    model_config = {"from_attributes": True}
