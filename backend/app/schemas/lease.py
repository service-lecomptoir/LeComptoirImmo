import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.lease import LeaseType, PaymentMethod


# ── Sous-schémas pour les relations chargées ───────────────────────────────────

class TenantInLease(BaseModel):
    id: uuid.UUID
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class UnitInLease(BaseModel):
    id: uuid.UUID
    unit_ref: str
    unit_type: str
    area_sqm: Optional[float] = None
    floor: Optional[int] = None

    model_config = {"from_attributes": True}


class PropertyInLease(BaseModel):
    id: uuid.UUID
    name: str
    full_address: str

    model_config = {"from_attributes": True}


# ── CRUD schemas ───────────────────────────────────────────────────────────────

class LeaseCreate(BaseModel):
    property_id: uuid.UUID
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    # Co-titulaires secondaires (le principal est tenant_id)
    secondary_tenant_ids: list[uuid.UUID] = Field(default_factory=list)
    lease_type: LeaseType = LeaseType.VIDE
    start_date: date
    end_date: Optional[date] = None
    notice_date: Optional[date] = None
    rent_amount: float = Field(..., gt=0)
    charges_amount: float = Field(0.0, ge=0)
    deposit_amount: float = Field(0.0, ge=0)
    payment_day: int = Field(1, ge=1, le=28)
    payment_method: PaymentMethod = PaymentMethod.VIREMENT
    apl_amount: Optional[float] = Field(None, ge=0)
    apl_tiers_payant: bool = False
    has_guarantor: bool = False
    guarantor_name: Optional[str] = None
    guarantor_email: Optional[str] = None
    guarantor_phone: Optional[str] = None
    notes: Optional[str] = None


class LeaseUpdate(BaseModel):
    lease_type: Optional[LeaseType] = None
    # Si fourni, remplace la liste des co-titulaires secondaires
    secondary_tenant_ids: Optional[list[uuid.UUID]] = None
    end_date: Optional[date] = None
    notice_date: Optional[date] = None
    rent_amount: Optional[float] = Field(None, gt=0)
    charges_amount: Optional[float] = Field(None, ge=0)
    deposit_amount: Optional[float] = Field(None, ge=0)
    payment_day: Optional[int] = Field(None, ge=1, le=28)
    payment_method: Optional[PaymentMethod] = None
    apl_amount: Optional[float] = Field(None, ge=0)
    apl_tiers_payant: Optional[bool] = None
    has_guarantor: Optional[bool] = None
    guarantor_name: Optional[str] = None
    guarantor_email: Optional[str] = None
    guarantor_phone: Optional[str] = None
    notes: Optional[str] = None


class LeaseTerminate(BaseModel):
    end_date: date
    notice_date: Optional[date] = None


class LeaseResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    lease_type: LeaseType
    start_date: date
    end_date: Optional[date] = None
    notice_date: Optional[date] = None
    rent_amount: float
    charges_amount: float
    deposit_amount: float
    payment_day: int
    payment_method: PaymentMethod
    apl_amount: Optional[float] = None
    apl_tiers_payant: bool
    has_guarantor: bool
    guarantor_name: Optional[str] = None
    guarantor_email: Optional[str] = None
    guarantor_phone: Optional[str] = None
    is_active: bool
    notes: Optional[str] = None
    total_monthly: float
    net_rent: float
    # Relations
    tenant: Optional[TenantInLease] = None
    co_tenants: list[TenantInLease] = Field(default_factory=list)
    all_tenant_names: Optional[str] = None
    unit: Optional[UnitInLease] = None
    parent_property: Optional[PropertyInLease] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaseListItem(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_full_name: str
    unit_ref: str
    property_name: str
    lease_type: str
    start_date: date
    end_date: Optional[date] = None
    rent_amount: float
    charges_amount: float
    is_active: bool
    apl_tiers_payant: bool


class LeaseListResponse(BaseModel):
    items: list[LeaseListItem]
    total: int
    skip: int
    limit: int
