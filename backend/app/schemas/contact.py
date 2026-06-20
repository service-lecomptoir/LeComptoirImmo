import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.contact import ContactCategory


class ContactCreate(BaseModel):
    first_name: str | None = None
    last_name: str
    company_name: str | None = None
    category: ContactCategory = ContactCategory.AUTRE
    email: str | None = None
    phone: str | None = None
    phone2: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    siret: str | None = None
    website: str | None = None
    notes: str | None = None
    is_favorite: bool = False


class ContactUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    category: ContactCategory | None = None
    email: str | None = None
    phone: str | None = None
    phone2: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    siret: str | None = None
    website: str | None = None
    notes: str | None = None
    is_favorite: bool | None = None


class ContactResponse(BaseModel):
    id: uuid.UUID
    first_name: str | None = None
    last_name: str
    company_name: str | None = None
    display_name: str
    full_name: str
    category: ContactCategory
    email: str | None = None
    phone: str | None = None
    phone2: str | None = None
    address: str | None = None
    zip_code: str | None = None
    city: str | None = None
    siret: str | None = None
    website: str | None = None
    notes: str | None = None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
