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
    # Fonctionnalités incluses dans le plan (null = toutes autorisées).
    features: Optional[List[str]] = None


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
    features: Optional[List[str]] = None

    if lic.plan_id:
        plan = (await db.execute(
            select(AlicePlan).where(AlicePlan.id == lic.plan_id)
        )).scalar_one_or_none()
        if plan:
            plan_name = plan.name
            features = plan.features  # None = toutes les fonctionnalités
            if effective_limit is None:
                effective_limit = plan.property_limit  # None = illimité

    return LicenseInfoResponse(
        gestionnaire_user_id=lic.gestionnaire_user_id,
        is_blocked=lic.is_blocked,
        property_limit=effective_limit,
        plan_name=plan_name,
        access_until=lic.access_until,
        features=features,
    )


# ── Stripe : abonnement (carte / SEPA) ───────────────────────────────────────
class BillingStatusResponse(BaseModel):
    stripe_enabled: bool
    has_subscription: bool
    status: Optional[str] = None
    current_period_end: Optional[datetime] = None
    payment_method_type: Optional[str] = None
    plan_name: Optional[str] = None
    monthly_price: Optional[float] = None


class BillingUrlResponse(BaseModel):
    url: str


@router.get("/billing/status/{user_id}", response_model=BillingStatusResponse,
            dependencies=[Depends(_require_internal_key)])
async def billing_status(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """État d'abonnement Stripe d'un gestionnaire (pour la page Mon abonnement)."""
    from app.services import stripe_service
    lic = (await db.execute(
        select(AliceLicense).where(AliceLicense.gestionnaire_user_id == user_id)
    )).scalar_one_or_none()
    plan_name = None
    monthly_price = None
    if lic and lic.plan_id:
        plan = (await db.execute(select(AlicePlan).where(AlicePlan.id == lic.plan_id))).scalar_one_or_none()
        if plan:
            plan_name = plan.name
            monthly_price = float(plan.monthly_price or 0)
    return BillingStatusResponse(
        stripe_enabled=stripe_service.enabled(),
        has_subscription=bool(lic and lic.stripe_subscription_id),
        status=getattr(lic, "stripe_status", None) if lic else None,
        current_period_end=getattr(lic, "stripe_current_period_end", None) if lic else None,
        payment_method_type=getattr(lic, "stripe_payment_method_type", None) if lic else None,
        plan_name=plan_name, monthly_price=monthly_price,
    )


@router.post("/billing/checkout/{user_id}", response_model=BillingUrlResponse,
             dependencies=[Depends(_require_internal_key)])
async def billing_checkout(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Crée une session Stripe Checkout (abonnement) et renvoie l'URL de paiement."""
    from app.services import stripe_service
    if not stripe_service.enabled():
        raise HTTPException(status_code=503, detail="Paiement en ligne non activé.")
    lic = (await db.execute(
        select(AliceLicense).where(AliceLicense.gestionnaire_user_id == user_id)
    )).scalar_one_or_none()
    if not lic:
        raise HTTPException(status_code=404, detail="Licence introuvable.")
    if not lic.plan_id:
        raise HTTPException(status_code=400, detail="Aucun plan tarifaire assigné à ce compte.")
    plan = (await db.execute(select(AlicePlan).where(AlicePlan.id == lic.plan_id))).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=400, detail="Plan tarifaire introuvable.")
    urow = (await db.execute(
        select(LeciUser.full_name, LeciUser.email).where(LeciUser.id == user_id)
    )).fetchone()
    price_id = await stripe_service.ensure_plan_price(db, plan)
    customer_id = await stripe_service.ensure_customer(
        db, lic, email=(urow.email if urow else None), name=(urow.full_name if urow else None),
    )
    await db.commit()
    url = stripe_service.create_checkout_session(
        customer_id=customer_id, price_id=price_id,
        success_url=settings.STRIPE_SUCCESS_URL, cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={"gestionnaire_user_id": str(user_id), "alice_plan_id": str(plan.id)},
    )
    return BillingUrlResponse(url=url)


@router.post("/billing/portal/{user_id}", response_model=BillingUrlResponse,
             dependencies=[Depends(_require_internal_key)])
async def billing_portal(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Crée une session du portail de facturation Stripe (gérer carte/abonnement)."""
    from app.services import stripe_service
    if not stripe_service.enabled():
        raise HTTPException(status_code=503, detail="Paiement en ligne non activé.")
    lic = (await db.execute(
        select(AliceLicense).where(AliceLicense.gestionnaire_user_id == user_id)
    )).scalar_one_or_none()
    if not lic or not lic.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Aucun abonnement Stripe pour ce compte.")
    url = stripe_service.create_billing_portal_session(
        customer_id=lic.stripe_customer_id, return_url=settings.STRIPE_SUCCESS_URL,
    )
    return BillingUrlResponse(url=url)


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
