from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.avis_echeance import AvisEcheanceStatus


class AvisEcheanceBase(BaseModel):
    period_year: int
    period_month: int
    period_start: date | None = None
    period_end: date | None = None
    due_date: date
    amount_rent: float
    amount_charges: float
    amount_apl: float | None = None
    amount_total: float
    status: AvisEcheanceStatus = AvisEcheanceStatus.BROUILLON
    notes: str | None = None


class AvisEcheanceGenerateIn(BaseModel):
    """Corps de la requête pour générer un avis manuellement."""

    lease_id: uuid.UUID
    period_year: int
    period_month: int
    # Montant APL spécifique à ce mois (remplace celui du bail si fourni)
    apl_amount_override: float | None = None


class AvisEcheancePatchApl(BaseModel):
    """Modification du montant APL d'un avis existant."""

    apl_amount: float | None = None  # None = supprimer l'APL


class AvisEcheancePatch(BaseModel):
    """Modification complète d'un avis d'échéance."""

    amount_rent: float | None = None
    amount_charges: float | None = None
    amount_apl: float | None = None
    due_date: date | None = None
    notes: str | None = None


class AvisEcheaneBulkGenerateIn(BaseModel):
    """Génération en masse pour un mois donné."""

    period_year: int
    period_month: int


class AvisEcheanceOut(AvisEcheanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lease_id: uuid.UUID
    tenant_id: uuid.UUID
    sent_at: datetime | None = None
    pdf_path: str | None = None
    generated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    # Champs calculés depuis les relations
    tenant_full_name: str | None = None
    property_name: str | None = None
    period_label: str | None = None
    period_range_label: str | None = None
    is_auto_generated: bool | None = None


class AvisEcheanceSummary(BaseModel):
    """Résumé pour les listes."""

    id: uuid.UUID
    period_year: int
    period_month: int
    period_label: str
    due_date: date
    amount_total: float
    status: AvisEcheanceStatus
    tenant_full_name: str
    property_name: str
    sent_at: datetime | None = None
    is_auto_generated: bool


class GenerateMonthlyResult(BaseModel):
    generated: int
    period_year: int
    period_month: int
    message: str
