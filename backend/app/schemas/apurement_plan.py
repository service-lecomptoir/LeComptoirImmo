import uuid
from datetime import date
from typing import Optional
from pydantic import BaseModel


class ApurementPlanCreate(BaseModel):
    payment_id: uuid.UUID
    installments: int = 3
    first_date: date


class InstallmentMark(BaseModel):
    paid: bool
    paid_date: Optional[date] = None
