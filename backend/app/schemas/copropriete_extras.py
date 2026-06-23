import uuid
from datetime import date

from pydantic import BaseModel, field_validator

WORKS_KINDS = ("contribution", "depense")


# ── Fonds travaux (ALUR) ─────────────────────────────────────────────────────
class WorksFundEntryCreate(BaseModel):
    entry_date: date
    kind: str
    label: str
    amount: float

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, v: str) -> str:
        if v not in WORKS_KINDS:
            raise ValueError("Type invalide (contribution / depense).")
        return v

    @field_validator("amount")
    @classmethod
    def positive(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("Le montant doit être supérieur à 0.")
        return v

    @field_validator("label")
    @classmethod
    def label_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Le libellé est requis.")
        return v


class WorksFundEntryResponse(BaseModel):
    id: uuid.UUID
    entry_date: date
    kind: str
    label: str
    amount: float


class WorksFundSummary(BaseModel):
    total_contributions: float = 0
    total_depenses: float = 0
    balance: float = 0
    entries: list[WorksFundEntryResponse] = []


# ── Carnet d'entretien ───────────────────────────────────────────────────────
class MaintenanceCreate(BaseModel):
    entry_date: date | None = None
    category: str | None = None
    description: str
    supplier: str | None = None
    cost: float | None = None

    @field_validator("description")
    @classmethod
    def desc_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("La description est requise.")
        return v


class MaintenanceUpdate(BaseModel):
    entry_date: date | None = None
    category: str | None = None
    description: str | None = None
    supplier: str | None = None
    cost: float | None = None


class MaintenanceResponse(BaseModel):
    id: uuid.UUID
    entry_date: date | None = None
    category: str | None = None
    description: str
    supplier: str | None = None
    cost: float | None = None
