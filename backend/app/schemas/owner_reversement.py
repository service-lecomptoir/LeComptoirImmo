import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator


class ReversementCreate(BaseModel):
    period_year: int
    # Mois optionnel : null = reversement couvrant plusieurs mois / annuel.
    period_month: int | None = None
    amount: float
    method: str | None = None  # virement | cheque | especes | autre
    reversement_date: date
    label: str | None = None
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("Le montant du reversement doit être supérieur à 0.")
        return v

    @field_validator("period_month")
    @classmethod
    def month_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 12):
            raise ValueError("Le mois doit être compris entre 1 et 12.")
        return v


class ReversementResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    period_year: int
    period_month: int | None
    amount: float
    method: str | None
    reversement_date: date
    label: str | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
