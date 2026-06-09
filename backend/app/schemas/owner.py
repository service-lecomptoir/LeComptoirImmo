import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, model_validator
from app.models.tenant import Civility


class OwnerCreate(BaseModel):
    civility: Optional[Civility] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    national_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None  # rue (n° + voie)
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None  # Compte de connexion (optionnel)

    @model_validator(mode="after")
    def check_identity(self):
        # Une fiche est valide si elle identifie soit une PERSONNE (prénom + nom),
        # soit une PERSONNE MORALE (société + SIREN/SIRET). `last_name` est NOT NULL
        # en base : à défaut de nom de personne, on y recopie la société (le
        # full_name affiche déjà la société en priorité → aucun impact d'affichage).
        first = (self.first_name or "").strip()
        last = (self.last_name or "").strip()
        company = (self.company_name or "").strip()
        siren = (self.national_id or "").strip()
        person_ok = bool(first and last)
        company_ok = bool(company and siren)
        if not person_ok and not company_ok:
            raise ValueError(
                "Renseignez soit le prénom ET le nom, soit la société ET le SIREN/SIRET."
            )
        if not last and company:
            self.last_name = company
        return self


class OwnerUpdate(BaseModel):
    civility: Optional[Civility] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    national_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None  # rue (n° + voie)
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_holder: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[uuid.UUID] = None


class OwnerResponse(BaseModel):
    id: uuid.UUID
    civility: Optional[Civility]
    first_name: Optional[str]
    last_name: str
    company_name: Optional[str]
    full_name: str
    national_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    zip_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    iban: Optional[str]
    bic: Optional[str]
    bank_holder: Optional[str]
    notes: Optional[str]
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OwnerListItem(BaseModel):
    """Version allégée pour les listes."""
    id: uuid.UUID
    full_name: str
    civility: Optional[Civility]
    first_name: Optional[str]
    last_name: str
    company_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
