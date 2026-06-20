import uuid
from datetime import date

from pydantic import BaseModel


class ApurementPlanCreate(BaseModel):
    payment_id: uuid.UUID
    installments: int = 3
    first_date: date
    # Montant total à étaler. Absent ou >= solde -> mois totalement soldé (reporté).
    # Inférieur au solde -> apurement PARTIEL : seul ce montant sort du solde.
    total_amount: float | None = None


class InstallmentMark(BaseModel):
    paid: bool
    paid_date: date | None = None
