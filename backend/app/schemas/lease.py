import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.lease import LeaseType, PaymentMethod

RentCallRuleT = Literal["contractuelle", "calendrier"]
PaymentFrequencyT = Literal[
    "mensuelle", "bimestrielle", "trimestrielle", "semestrielle", "annuelle"
]


# ── Sous-schémas pour les relations chargées ───────────────────────────────────


class TenantInLease(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    national_id: str | None = None

    model_config = {"from_attributes": True}


class PropertyInLease(BaseModel):
    id: uuid.UUID
    name: str
    full_address: str

    model_config = {"from_attributes": True}


# ── CRUD schemas ───────────────────────────────────────────────────────────────


class LeaseCreate(BaseModel):
    property_id: uuid.UUID
    tenant_id: uuid.UUID
    # Co-titulaires secondaires (le principal est tenant_id)
    secondary_tenant_ids: list[uuid.UUID] = Field(default_factory=list)
    lease_type: LeaseType = LeaseType.VIDE
    start_date: date
    end_date: date | None = None
    notice_date: date | None = None
    rent_amount: float = Field(..., gt=0)
    charges_amount: float = Field(0.0, ge=0)
    deposit_amount: float = Field(0.0, ge=0)
    payment_day: int = Field(1, ge=1, le=28)
    payment_method: PaymentMethod = PaymentMethod.VIREMENT
    rent_call_rule: RentCallRuleT = "calendrier"
    payment_frequency: PaymentFrequencyT = "mensuelle"
    apl_amount: float | None = Field(None, ge=0)
    apl_tiers_payant: bool = False
    has_guarantor: bool = False
    guarantor_name: str | None = None
    guarantor_email: str | None = None
    guarantor_phone: str | None = None
    notes: str | None = None


class LeaseUpdate(BaseModel):
    # Le locataire principal peut être réassigné en modification (pas le bien).
    tenant_id: uuid.UUID | None = None
    lease_type: LeaseType | None = None
    # Si fourni, remplace la liste des co-titulaires secondaires
    secondary_tenant_ids: list[uuid.UUID] | None = None
    # Date d'entrée modifiable (correction de saisie / bail à venir).
    start_date: date | None = None
    end_date: date | None = None
    notice_date: date | None = None
    rent_amount: float | None = Field(None, gt=0)
    charges_amount: float | None = Field(None, ge=0)
    # Date d'effet d'une modification du loyer/charges (défaut : 1er du mois suivant).
    # Le mois en cours n'est pas impacté ; l'ancien montant est conservé en historique.
    rent_effective_date: date | None = None
    deposit_amount: float | None = Field(None, ge=0)
    payment_day: int | None = Field(None, ge=1, le=28)
    payment_method: PaymentMethod | None = None
    rent_call_rule: RentCallRuleT | None = None
    payment_frequency: PaymentFrequencyT | None = None
    apl_amount: float | None = Field(None, ge=0)
    apl_tiers_payant: bool | None = None
    has_guarantor: bool | None = None
    guarantor_name: str | None = None
    guarantor_email: str | None = None
    guarantor_phone: str | None = None
    notes: str | None = None


class LeaseTerminate(BaseModel):
    end_date: date
    notice_date: date | None = None


class LeaseResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    tenant_id: uuid.UUID
    lease_type: LeaseType
    start_date: date
    end_date: date | None = None
    notice_date: date | None = None
    rent_amount: float
    charges_amount: float
    deposit_amount: float
    payment_day: int
    payment_method: PaymentMethod
    rent_call_rule: str = "calendrier"
    payment_frequency: str = "mensuelle"
    apl_amount: float | None = None
    apl_tiers_payant: bool
    has_guarantor: bool
    guarantor_name: str | None = None
    guarantor_email: str | None = None
    guarantor_phone: str | None = None
    is_active: bool
    notes: str | None = None
    total_monthly: float
    net_rent: float
    # Relations
    tenant: TenantInLease | None = None
    co_tenants: list[TenantInLease] = Field(default_factory=list)
    all_tenant_names: str | None = None
    parent_property: PropertyInLease | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaseListItem(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_full_name: str
    property_name: str
    owner_name: str | None = None
    lease_type: str
    start_date: date
    end_date: date | None = None
    rent_amount: float
    charges_amount: float
    is_active: bool
    apl_tiers_payant: bool


class LeaseListResponse(BaseModel):
    items: list[LeaseListItem]
    total: int
    skip: int
    limit: int
