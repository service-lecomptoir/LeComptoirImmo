import uuid
from datetime import date
from typing import Optional
from pydantic import BaseModel


class ApurementPlanCreate(BaseModel):
    payment_id: uuid.UUID
    installments: int = 3
    first_date: date
    # Montant total à étaler. Absent ou >= solde -> mois totalement soldé (reporté).
    # Inférieur au solde -> apurement PARTIEL : seul ce montant sort du solde.
    total_amount: Optional[float] = None


class InstallmentMark(BaseModel):
    paid: bool
    paid_date: Optional[date] = None
