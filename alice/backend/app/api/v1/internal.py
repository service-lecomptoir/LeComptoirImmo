"""API interne Alice — service-to-service, accès restreint par clé API."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.config import get_settings
from app.models.license import AliceLicense
from app.models.plan import AlicePlan
from app.models.invoice import AliceInvoice
from app.models.leci import LeciUser
from app.schemas.invoice import InvoiceOut
from app.services.invoice_pdf import build_invoice_pdf, invoice_number

router = APIRouter(prefix="/internal", tags=["Internal"])

settings = get_settings()


def _require_internal_key(x_internal_key: Optional[str] = Header(None)) -> None:
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API interne invalide")


class LicenseInfoResponse(BaseModel):
    gestionnaire_user_id: uuid.UUID
    is_blocked: bool
    property_limit: Optional[int]
    plan_name: Optional[str]
    access_until: Optional[datetime] = None


@router.get("/license/{user_id}", response_model=LicenseInfoResponse, dependencies=[Depends(_require_internal_key)])
async def get_license_info(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les informations de licence d'un gestionnaire.
    Endpoint service-to-service pour LeComptoirImmo.
    Requiert l'en-tête X-Internal-Key.
    """
    lic = (await db.execute(
        select(AliceLicense).where(AliceLicense.gestionnaire_user_id == user_id)
    )).scalar_one_or_none()

    if lic is None:
        raise HTTPException(status_code=404, detail="Licence introuvable pour cet utilisateur")

    # Résiliation différée : si la date d'accès est dépassée, on applique le
    # blocage maintenant (enforcement paresseux, sans tâche planifiée).
    if lic.access_until is not None and datetime.utcnow() >= lic.access_until:
        lic.is_blocked = True
        lic.access_until = None

    # Résoudre la limite effective
    effective_limit: Optional[int] = lic.property_limit_override
    plan_name: Optional[str] = None

    if lic.plan_id:
        plan = (await db.execute(
            select(AlicePlan).where(AlicePlan.id == lic.plan_id)
        )).scalar_one_or_none()
        if plan:
            plan_name = plan.name
            if effective_limit is None:
                effective_limit = plan.property_limit  # None = illimité

    return LicenseInfoResponse(
        gestionnaire_user_id=lic.gestionnaire_user_id,
        is_blocked=lic.is_blocked,
        property_limit=effective_limit,
        plan_name=plan_name,
        access_until=lic.access_until,
    )


@router.get("/invoices/{user_id}", response_model=List[InvoiceOut], dependencies=[Depends(_require_internal_key)])
async def get_user_invoices(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Factures d'abonnement d'un gestionnaire (service-to-service pour LeCI)."""
    invoices = list((await db.execute(
        select(AliceInvoice)
        .where(AliceInvoice.gestionnaire_user_id == user_id)
        .order_by(AliceInvoice.period_year.desc(), AliceInvoice.period_month.desc())
    )).scalars().all())
    if not invoices:
        return []
    urow = (await db.execute(
        select(LeciUser.full_name, LeciUser.email).where(LeciUser.id == user_id)
    )).fetchone()
    name = urow.full_name if urow else None
    email = urow.email if urow else None
    return [
        InvoiceOut(
            id=inv.id,
            gestionnaire_user_id=inv.gestionnaire_user_id,
            gestionnaire_name=name,
            gestionnaire_email=email,
            period_year=inv.period_year,
            period_month=inv.period_month,
            amount=float(inv.amount),
            plan_name=inv.plan_name,
            status=inv.status,
            paid_at=inv.paid_at,
            created_at=inv.created_at,
        )
        for inv in invoices
    ]


@router.get("/invoices/{user_id}/{invoice_id}/pdf", dependencies=[Depends(_require_internal_key)])
async def get_user_invoice_pdf(
    user_id: uuid.UUID,
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """PDF d'une facture — restreint au gestionnaire propriétaire de la facture."""
    inv = (await db.execute(
        select(AliceInvoice).where(
            AliceInvoice.id == invoice_id,
            AliceInvoice.gestionnaire_user_id == user_id,
        )
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    urow = (await db.execute(
        select(LeciUser.full_name, LeciUser.email).where(LeciUser.id == user_id)
    )).fetchone()
    name = urow.full_name if urow else None
    email = urow.email if urow else None
    pdf = build_invoice_pdf(inv, name, email)
    filename = f"facture-{invoice_number(inv)}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
