import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, model_validator

from app.models.tenant import Civility


class TenantCreate(BaseModel):
    civility: Civility | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    siret: str | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    national_id: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    phone2: str | None = None
    language: str | None = "fr"  # langue des courriers (fr/en/pt-BR/ht/srn)
    employer: str | None = None
    employer_phone: str | None = None
    monthly_income: float | None = None
    income_source: str | None = None
    notes: str | None = None
    user_id: uuid.UUID | None = None  # Lien vers le compte utilisateur locataire

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
    civility: Civility | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    siret: str | None = None
    birth_date: date | None = None
    birth_place: str | None = None
    national_id: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    phone2: str | None = None
    language: str | None = None
    employer: str | None = None
    employer_phone: str | None = None
    monthly_income: float | None = None
    income_source: str | None = None
    notes: str | None = None
    user_id: uuid.UUID | None = None  # Lien vers le compte utilisateur locataire


class TenantResponse(BaseModel):
    id: uuid.UUID
    ref_code: str | None = None
    civility: Civility | None
    first_name: str
    last_name: str
    company_name: str | None = None
    siret: str | None = None
    full_name: str
    birth_date: date | None
    birth_place: str | None
    national_id: str | None
    email: str | None
    phone: str | None
    phone2: str | None
    language: str | None = "fr"
    employer: str | None
    employer_phone: str | None
    monthly_income: float | None
    income_source: str | None
    notes: str | None
    user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListItem(BaseModel):
    """Version allégée pour les listes."""

    id: uuid.UUID
    ref_code: str | None = None
    full_name: str
    civility: Civility | None
    first_name: str
    last_name: str
    company_name: str | None = None
    email: str | None
    phone: str | None
    user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
