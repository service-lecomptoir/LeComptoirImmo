import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.models.tenant import Civility


class TenantCreate(BaseModel):
    civility: Optional[Civility] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    national_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    employer: Optional[str] = None
    employer_phone: Optional[str] = None
    monthly_income: Optional[float] = None
    income_source: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None  # Lien vers le compte utilisateur locataire

    @model_validator(mode="after")
    def check_identity(self):
        # Locataire valide = PERSONNE (prénom + nom) OU PERSONNE MORALE (société).
        # `first_name`/`last_name` sont NOT NULL en base : pour une société on recopie
        # la raison sociale dans last_name (first_name = "") sans incidence d'affichage.
        first = (self.first_name or "").strip()
        last = (self.last_name or "").strip()
        company = (self.company_name or "").strip()
        if company:
            self.first_name = first
            self.last_name = last or company
        elif first and last:
            self.first_name = first
            self.last_name = last
        else:
            raise ValueError("Renseignez soit le prénom et le nom, soit la société.")
        return self


class TenantUpdate(BaseModel):
    civility: Optional[Civility] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    national_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    phone2: Optional[str] = None
    employer: Optional[str] = None
    employer_phone: Optional[str] = None
    monthly_income: Optional[float] = None
    income_source: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None  # Lien vers le compte utilisateur locataire


class TenantResponse(BaseModel):
    id: uuid.UUID
    civility: Optional[Civility]
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    full_name: str
    birth_date: Optional[date]
    birth_place: Optional[str]
    national_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    phone2: Optional[str]
    employer: Optional[str]
    employer_phone: Optional[str]
    monthly_income: Optional[float]
    income_source: Optional[str]
    notes: Optional[str]
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListItem(BaseModel):
    """Version allégée pour les listes."""
    id: uuid.UUID
    full_name: str
    civility: Optional[Civility]
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    email: Optional[str]
    phone: Optional[str]
    user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
