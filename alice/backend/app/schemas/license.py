import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LicenseBase(BaseModel):
    plan_id: Optional[uuid.UUID] = None
    property_limit_override: Optional[int] = Field(None, ge=1)
    monthly_price_override: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class LicenseUpdate(LicenseBase):
    pass


class LicenseOut(LicenseBase):
    id: uuid.UUID
    gestionnaire_user_id: uuid.UUID
    is_blocked: bool
    access_until: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # ── Stripe (abonnement) ──
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    stripe_status: Optional[str] = None
    stripe_payment_method_type: Optional[str] = None
    stripe_current_period_end: Optional[datetime] = None

    model_config = {"from_attributes": True}
