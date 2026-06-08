import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.contact import ContactCategory


class ContactCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: str
    company_name: Optional[str] = None
    category: ContactCategory = ContactCategory.AUTRE
    email: Optional[str] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    siret: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: bool = False


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    category: Optional[ContactCategory] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    siret: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None


class ContactResponse(BaseModel):
    id: uuid.UUID
    first_name: Optional[str] = None
    last_name: str
    company_name: Optional[str] = None
    display_name: str
    full_name: str
    category: ContactCategory
    email: Optional[str] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    siret: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
