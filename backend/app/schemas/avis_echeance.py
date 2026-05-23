from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.avis_echeance import AvisEcheanceStatus


class AvisEcheanceBase(BaseModel):
    period_year: int
    period_month: int
    due_date: date
    amount_rent: float
    amount_charges: float
    amount_apl: Optional[float] = None
    amount_total: float
    status: AvisEcheanceStatus = AvisEcheanceStatus.BROUILLON
    notes: Optional[str] = None


class AvisEcheanceGenerateIn(BaseModel):
    """Corps de la requête pour générer un avis manuellement."""
    lease_id: uuid.UUID
    period_year: int
    period_month: int
    # Montant APL spécifique à ce mois (remplace celui du bail si fourni)
    apl_amount_override: Optional[float] = None


class AvisEcheancePatchApl(BaseModel):
    """Modification du montant APL d'un avis existant."""
    apl_amount: Optional[float] = None  # None = supprimer l'APL


class AvisEcheaneBulkGenerateIn(BaseModel):
    """Génération en masse pour un mois donné."""
    period_year: int
    period_month: int


class AvisEcheanceOut(AvisEcheanceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lease_id: uuid.UUID
    tenant_id: uuid.UUID
    unit_id: uuid.UUID
    sent_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    generated_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    # Champs calculés depuis les relations
    tenant_full_name: Optional[str] = None
    unit_ref: Optional[str] = None
    property_name: Optional[str] = None
    period_label: Optional[str] = None
    is_auto_generated: Optional[bool] = None


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
    unit_ref: str
    property_name: str
    sent_at: Optional[datetime] = None
    is_auto_generated: bool


class GenerateMonthlyResult(BaseModel):
    generated: int
    period_year: int
    period_month: int
    message: str
