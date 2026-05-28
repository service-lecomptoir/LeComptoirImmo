import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    lease_id: uuid.UUID
    period_year: int = Field(..., ge=2000, le=2100)
    period_month: int = Field(..., ge=1, le=12)
    notes: Optional[str] = None


class PaymentRecordIn(BaseModel):
    """Payload pour saisir un paiement."""
    amount_paid: float = Field(..., gt=0)
    payment_date: date
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[PaymentStatus] = None


class TenantInPayment(BaseModel):
    id: uuid.UUID
    full_name: str
    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id: uuid.UUID
    lease_id: uuid.UUID
    tenant_id: uuid.UUID
    period_year: int
    period_month: int
    period_label: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_range_label: Optional[str] = None
    due_date: date
    amount_rent: float
    amount_charges: float
    amount_apl: Optional[float] = None
    amount_due: float
    amount_paid: float
    balance: float
    credit_applied: float = 0.0
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    status: PaymentStatus
    notes: Optional[str] = None
    quittance_generated_at: Optional[datetime] = None
    quittance_sent_at: Optional[datetime] = None
    tenant: Optional[TenantInPayment] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListItem(BaseModel):
    id: uuid.UUID
    tenant_full_name: str
    property_name: str
    period_label: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    period_range_label: Optional[str] = None
    period_year: int
    period_month: int
    due_date: date
    amount_rent: float = 0.0
    amount_charges: float = 0.0
    amount_apl: Optional[float] = None
    amount_due: float
    amount_paid: float
    balance: float
    credit_applied: float = 0.0
    status: PaymentStatus
    quittance_generated_at: Optional[datetime] = None
    quittance_sent_at: Optional[datetime] = None
    declared_at: Optional[datetime] = None
    declared_method: Optional[str] = None
    declared_amount: Optional[float] = None


class PaymentListResponse(BaseModel):
    items: list[PaymentListItem]
    total: int
    skip: int
    limit: int


class MonthlyStats(BaseModel):
    period_label: str
    total_due: float
    total_paid: float
    total_balance: float
    paid_count: int
    pending_count: int
    partial_count: int
    late_count: int


class DashboardStats(BaseModel):
    monthly: MonthlyStats
    active_leases: int
    occupied_units: int
    total_units: int
    occupancy_rate: float
    total_tenants: int


class GenerateMonthlyIn(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
