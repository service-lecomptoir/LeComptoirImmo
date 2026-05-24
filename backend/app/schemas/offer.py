"""Schémas Pydantic pour les offres et services."""
import uuid
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

CATEGORIES = ["article", "service", "promotion", "autre"]


class OfferBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: str = "service"
    contact_info: Optional[str] = None
    is_active: bool = True


class OfferCreate(OfferBase):
    pass


class OfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    contact_info: Optional[str] = None
    is_active: Optional[bool] = None


class OfferResponse(OfferBase):
    id: uuid.UUID
    gestionnaire_id: Optional[uuid.UUID]
    image_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
