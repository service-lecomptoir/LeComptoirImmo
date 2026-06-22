import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, model_validator

from app.models.tenant import Civility


class OwnerCreate(BaseModel):
    civility: Civility | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    national_id: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None  # rue (n° + voie)
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    iban: str | None = None
    bic: str | None = None
    bank_holder: str | None = None
    # Surcharge du taux d'honoraires pour ce mandat (% ; null = défaut mandataire).
    mgmt_fee_rate: float | None = None
    notes: str | None = None
    user_id: uuid.UUID | None = None  # Compte de connexion (optionnel)

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
    civility: Civility | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    national_id: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None  # rue (n° + voie)
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    iban: str | None = None
    bic: str | None = None
    bank_holder: str | None = None
    mgmt_fee_rate: float | None = None
    notes: str | None = None
    user_id: uuid.UUID | None = None


class OwnerResponse(BaseModel):
    id: uuid.UUID
    ref_code: str | None = None
    civility: Civility | None
    first_name: str | None
    last_name: str
    company_name: str | None
    full_name: str
    national_id: str | None
    email: str | None
    phone: str | None
    address: str | None
    zip_code: str | None = None
    city: str | None = None
    country: str | None = None
    iban: str | None
    bic: str | None
    bank_holder: str | None
    mgmt_fee_rate: float | None = None
    notes: str | None
    user_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OwnerListItem(BaseModel):
    """Version allégée pour les listes."""

    id: uuid.UUID
    ref_code: str | None = None
    full_name: str
    civility: Civility | None
    first_name: str | None
    last_name: str
    company_name: str | None
    email: str | None
    phone: str | None
    user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
