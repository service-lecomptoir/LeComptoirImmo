import uuid
from datetime import date

from pydantic import BaseModel, field_validator

PERIODICITIES = ("mensuel", "trimestriel", "semestriel", "annuel")


# ── Budget ───────────────────────────────────────────────────────────────────
class BudgetLineIn(BaseModel):
    key_id: uuid.UUID
    label: str
    amount: float = 0

    @field_validator("label")
    @classmethod
    def label_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Le libellé du poste est requis.")
        return v


class BudgetLineOut(BaseModel):
    id: uuid.UUID
    key_id: uuid.UUID
    key_name: str | None = None
    label: str
    amount: float


class BudgetCreate(BaseModel):
    year: int
    periodicity: str = "trimestriel"
    label: str | None = None
    lines: list[BudgetLineIn] = []

    @field_validator("periodicity")
    @classmethod
    def valid_periodicity(cls, v: str) -> str:
        if v not in PERIODICITIES:
            raise ValueError("Périodicité invalide.")
        return v


class BudgetUpdate(BaseModel):
    periodicity: str | None = None
    label: str | None = None
    lines: list[BudgetLineIn] | None = None

    @field_validator("periodicity")
    @classmethod
    def valid_periodicity(cls, v: str | None) -> str | None:
        if v is not None and v not in PERIODICITIES:
            raise ValueError("Périodicité invalide.")
        return v


class BudgetResponse(BaseModel):
    id: uuid.UUID
    copropriete_id: uuid.UUID
    year: int
    periodicity: str
    label: str | None = None
    total: float = 0
    nb_periods: int = 1
    lines: list[BudgetLineOut] = []


# ── Appels de fonds ──────────────────────────────────────────────────────────
class FundCallGenerate(BaseModel):
    period_index: int = 1
    due_date: date | None = None


class CallItemOut(BaseModel):
    id: uuid.UUID
    lot_id: uuid.UUID | None = None
    lot_numero: str | None = None
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    amount_due: float
    amount_paid: float
    status: str


class FundCallResponse(BaseModel):
    id: uuid.UUID
    period_index: int
    period_label: str
    due_date: date | None = None
    total_due: float = 0
    total_paid: float = 0
    items: list[CallItemOut] = []


# ── Encaissements ────────────────────────────────────────────────────────────
class CoproPaymentIn(BaseModel):
    amount: float
    payment_date: date
    method: str | None = None
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("Le montant doit être supérieur à 0.")
        return v


# ── Comptes copropriétaires ──────────────────────────────────────────────────
class CoproAccountRow(BaseModel):
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    total_due: float = 0
    total_paid: float = 0
    balance: float = 0


# ── Dépenses réelles ─────────────────────────────────────────────────────────
class ExpenseCreate(BaseModel):
    year: int
    key_id: uuid.UUID
    label: str
    amount: float = 0
    expense_date: date | None = None
    supplier: str | None = None

    @field_validator("label")
    @classmethod
    def label_required(cls, v: str) -> str:
        if not (v or "").strip():
            raise ValueError("Le libellé de la dépense est requis.")
        return v


class ExpenseUpdate(BaseModel):
    key_id: uuid.UUID | None = None
    label: str | None = None
    amount: float | None = None
    expense_date: date | None = None
    supplier: str | None = None


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    year: int
    key_id: uuid.UUID
    key_name: str | None = None
    label: str
    amount: float
    expense_date: date | None = None
    supplier: str | None = None


# ── Régularisation annuelle (réel vs provisions appelées) ─────────────────────
class RegularizationRow(BaseModel):
    owner_id: uuid.UUID | None = None
    owner_name: str | None = None
    appele: float = 0  # provisions appelées sur l'année
    reel: float = 0  # quote-part des dépenses réelles
    solde: float = 0  # appelé - réel (>0 = à rembourser ; <0 = complément à appeler)


class RegularizationResult(BaseModel):
    year: int
    budget_total: float = 0
    expenses_total: float = 0
    appele_total: float = 0
    rows: list[RegularizationRow] = []
