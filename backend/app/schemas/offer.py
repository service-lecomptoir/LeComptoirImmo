"""Schémas Pydantic pour les offres et services."""

import uuid
from datetime import datetime

from pydantic import BaseModel

CATEGORIES = ["article", "service", "promotion", "autre"]


class OfferBase(BaseModel):
    title: str
    description: str | None = None
    price: float | None = None
    category: str = "service"
    contact_info: str | None = None
    is_active: bool = True


class OfferCreate(OfferBase):
    pass


class OfferUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    category: str | None = None
    contact_info: str | None = None
    is_active: bool | None = None


class OfferResponse(OfferBase):
    id: uuid.UUID
    gestionnaire_id: uuid.UUID | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
