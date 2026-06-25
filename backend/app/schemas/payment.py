import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    lease_id: uuid.UUID
    period_year: int = Field(..., ge=2000, le=2100)
    period_month: int = Field(..., ge=1, le=12)
    notes: str | None = None


class PaymentRecordIn(BaseModel):
    """Payload pour saisir un paiement."""

    amount_paid: float = Field(..., gt=0)
    payment_date: date
    payment_method: str | None = None
    notes: str | None = None


class PaymentUpdate(BaseModel):
    notes: str | None = None
    status: PaymentStatus | None = None


class TenantInPayment(BaseModel):
    id: uuid.UUID
    full_name: str
    model_config = {"from_attributes": True}


class PaymentAdjustmentIn(BaseModel):
    """Ajout d'une ligne ad hoc sur une échéance."""

    type: str = Field(..., pattern="^(supplement|restitution)$")
    libelle: str | None = Field(None, max_length=200)
    montant: float = Field(..., gt=0)


class PaymentAdjustmentOut(BaseModel):
    id: uuid.UUID
    type: str
    libelle: str
    montant: float
    created_at: datetime
    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    id: uuid.UUID
    lease_id: uuid.UUID
    tenant_id: uuid.UUID
    period_year: int
    period_month: int
    period_label: str
    period_start: date | None = None
    period_end: date | None = None
    period_range_label: str | None = None
    due_date: date
    amount_rent: float
    amount_charges: float
    amount_apl: float | None = None
    amount_due: float
    amount_paid: float
    balance: float
    credit_applied: float = 0.0
    restitution_credit: float = 0.0
    restitution_refund: float = 0.0
    payment_date: date | None = None
    payment_method: str | None = None
    status: PaymentStatus
    settled_by_plan: bool = False
    notes: str | None = None
    quittance_generated_at: datetime | None = None
    quittance_sent_at: datetime | None = None
    tenant: TenantInPayment | None = None
    adjustments: list[PaymentAdjustmentOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListItem(BaseModel):
    id: uuid.UUID
    tenant_full_name: str
    property_name: str
    period_label: str
    period_start: date | None = None
    period_end: date | None = None
    period_range_label: str | None = None
    period_year: int
    period_month: int
    due_date: date
    amount_rent: float = 0.0
    amount_charges: float = 0.0
    amount_apl: float | None = None
    amount_due: float
    amount_paid: float
    balance: float
    credit_applied: float = 0.0
    restitution_credit: float = 0.0
    restitution_refund: float = 0.0
    amount_on_plan: float = 0.0
    payment_method: str | None = None
    payment_date: date | None = None
    status: PaymentStatus
    settled_by_plan: bool = False
    quittance_generated_at: datetime | None = None
    quittance_sent_at: datetime | None = None
    declared_at: datetime | None = None
    declared_method: str | None = None
    declared_amount: float | None = None


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
