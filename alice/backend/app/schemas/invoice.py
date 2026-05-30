import uuid
from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel


class InvoiceOut(BaseModel):
    id: uuid.UUID
    gestionnaire_user_id: uuid.UUID
    gestionnaire_name: Optional[str] = None
    gestionnaire_email: Optional[str] = None
    period_year: int
    period_month: int
    amount: float
    plan_name: Optional[str] = None
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceUpdate(BaseModel):
    """Tous les champs sont optionnels : sert au toggle de statut comme à
    l'édition complète (crayon)."""
    status: Optional[Literal["paid", "unpaid"]] = None
    amount: Optional[float] = None
    plan_name: Optional[str] = None
    period_year: Optional[int] = None
    period_month: Optional[int] = None


class GeneratePeriod(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None
