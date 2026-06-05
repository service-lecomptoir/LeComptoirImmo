"""API Abonnement — informations de licence Alice pour le gestionnaire connecté."""
import logging
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from pydantic import BaseModel, Field

from app.database import get_db
from app.api.deps import get_current_user
from app.core.permissions import Role
from app.models.user import User
from app.models.property import Property

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["Abonnement"])


class SubscriptionInfo(BaseModel):
    plan_name: Optional[str]
    is_blocked: bool
    property_limit: Optional[int]
    property_count: int
    can_create_property: bool
    access_until: Optional[str] = None
    resiliation_days_remaining: Optional[int] = None
    # Fonctionnalités incluses (null = toutes autorisées).
    features: Optional[List[str]] = None


@router.get("", response_model=SubscriptionInfo, summary="Mon abonnement Alice")
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne les informations d'abonnement Alice du gestionnaire connecté."""
    role = Role(current_user.role)
    if role not in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")

    # Nombre de biens actuels
    property_count = (await db.execute(
        select(func.count(Property.id)).where(Property.created_by == current_user.id)
    )).scalar_one_or_none() or 0

    # Infos licence depuis Alice
    plan_name: Optional[str] = None
    is_blocked = False
    property_limit: Optional[int] = None
    access_until: Optional[str] = None
    features: Optional[List[str]] = None

    try:
        import httpx
        from app.config import get_settings
        cfg = get_settings()
        async with httpx.AsyncClient(timeout=5.0) as hc:
            resp = await hc.get(
                f"{cfg.ALICE_URL}/api/v1/internal/license/{current_user.id}",
                headers={"X-Internal-Key": cfg.ALICE_INTERNAL_KEY},
            )
        if resp.status_code == 200:
            data = resp.json()
            plan_name = data.get("plan_name")
            is_blocked = data.get("is_blocked", False)
            property_limit = data.get("property_limit")
            access_until = data.get("access_until")
            features = data.get("features")
        elif resp.status_code == 404:
            # Pas de licence → considéré comme bloqué
            is_blocked = True
    except Exception as exc:
        logger.warning(f"Alice subscription check failed for {current_user.id}: {exc}")
        # Alice indisponible — on retourne ce qu'on sait de la DB locale
        from sqlalchemy import text as sa_text
        try:
            row = (await db.execute(
                sa_text("SELECT is_blocked FROM alice_licenses WHERE gestionnaire_user_id = :uid")
                .bindparams(uid=current_user.id)
            )).fetchone()
            if row:
                is_blocked = row[0]
        except Exception:
            pass

    can_create = not is_blocked and (property_limit is None or property_count < property_limit)

    # Décompte jours restants si une résiliation est programmée
    days_remaining: Optional[int] = None
    if access_until:
        try:
            from datetime import datetime as _dt
            end = _dt.fromisoformat(access_until)
            days_remaining = max(0, (end.date() - _dt.utcnow().date()).days)
        except Exception:
            days_remaining = None

    return SubscriptionInfo(
        plan_name=plan_name,
        is_blocked=is_blocked,
        property_limit=property_limit,
        property_count=property_count,
        can_create_property=can_create,
        access_until=access_until,
        resiliation_days_remaining=days_remaining,
        features=features,
    )


class ResiliationRequestIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


async def _notify_resiliation(full_name: str, email: str, reason: str) -> None:
    """Best-effort : prévient l'équipe Alice d'une demande de résiliation."""
    try:
        from app.config import get_settings
        from app.services.email_service import send_email
        cfg = get_settings()
        recipient = cfg.LEADS_NOTIFY_EMAIL or cfg.FIRST_ADMIN_EMAIL
        html = (
            "<h2>Demande de résiliation d'abonnement</h2>"
            f"<p><strong>{full_name}</strong> &lt;{email}&gt;</p>"
            f"<p><strong>Motif&nbsp;:</strong><br>{reason}</p>"
            "<p style='margin-top:16px'>À traiter dans Alice → <strong>Demandes</strong>.</p>"
        )
        await send_email(to=recipient, subject="Demande de résiliation — Le Comptoir Immo", html_body=html)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification de résiliation non envoyée : %s", exc)


@router.post("/resiliation", status_code=201, summary="Demande de résiliation d'abonnement")
async def request_resiliation(
    data: ResiliationRequestIn,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enregistre une demande de résiliation (vue par Alice dans « Demandes »)
    et notifie l'équipe — même mécanisme que la demande de souscription."""
    role = Role(current_user.role)
    if role not in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")

    await db.execute(
        text(
            "INSERT INTO alice_subscription_requests "
            "(id, full_name, email, phone, company, message, source, status, created_at) "
            "VALUES (:id, :full_name, :email, :phone, :company, :message, "
            "'resiliation', 'nouveau', now())"
        ),
        {
            "id": uuid.uuid4(),
            "full_name": current_user.full_name,
            "email": current_user.email,
            "phone": getattr(current_user, "phone", None),
            "company": None,
            "message": data.reason.strip(),
        },
    )
    await db.commit()
    background.add_task(_notify_resiliation, current_user.full_name, current_user.email, data.reason.strip())
    return {"status": "received"}


@router.get("/invoices", summary="Mes factures d'abonnement")
async def get_my_invoices(current_user: User = Depends(get_current_user)):
    """Liste les factures d'abonnement du gestionnaire (proxy vers Alice)."""
    role = Role(current_user.role)
    if role not in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")
    try:
        import httpx
        from app.config import get_settings
        cfg = get_settings()
        async with httpx.AsyncClient(timeout=8.0) as hc:
            resp = await hc.get(
                f"{cfg.ALICE_URL}/api/v1/internal/invoices/{current_user.id}",
                headers={"X-Internal-Key": cfg.ALICE_INTERNAL_KEY},
            )
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Alice invoices fetch failed for {current_user.id}: {exc}")
    return []


@router.get("/invoices/{invoice_id}/pdf", summary="PDF d'une facture d'abonnement")
async def get_my_invoice_pdf(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
):
    """Renvoie le PDF d'une facture du gestionnaire (proxy vers Alice)."""
    role = Role(current_user.role)
    if role not in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")
    import httpx
    from app.config import get_settings
    cfg = get_settings()
    try:
        async with httpx.AsyncClient(timeout=15.0) as hc:
            resp = await hc.get(
                f"{cfg.ALICE_URL}/api/v1/internal/invoices/{current_user.id}/{invoice_id}/pdf",
                headers={"X-Internal-Key": cfg.ALICE_INTERNAL_KEY},
            )
    except Exception:
        raise HTTPException(status_code=502, detail="Service de facturation indisponible")
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return Response(
        content=resp.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": resp.headers.get(
                "content-disposition", 'attachment; filename="facture.pdf"'
            )
        },
    )


# ── Paiement Stripe (proxy vers Alice) ───────────────────────────────────────
def _require_manager(current_user: User) -> None:
    if Role(current_user.role) not in (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(status_code=403, detail="Réservé aux gestionnaires")


async def _alice_billing(method: str, path: str, user_id, json: dict | None = None):
    import httpx
    from app.config import get_settings
    cfg = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as hc:
        resp = await hc.request(
            method, f"{cfg.ALICE_URL}/api/v1/internal/billing/{path}/{user_id}",
            headers={"X-Internal-Key": cfg.ALICE_INTERNAL_KEY},
            json=json,
        )
    if resp.status_code >= 400:
        detail = "Service de facturation indisponible"
        try:
            detail = resp.json().get("detail", detail)
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(status_code=resp.status_code if resp.status_code < 500 else 502,
                            detail=detail)
    return resp.json()


@router.get("/billing", summary="État de l'abonnement Stripe")
async def billing_status(current_user: User = Depends(get_current_user)):
    """Statut d'abonnement Stripe du gestionnaire (proxy Alice). Fail-soft."""
    _require_manager(current_user)
    try:
        return await _alice_billing("GET", "status", current_user.id)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        return {"stripe_enabled": False, "has_subscription": False}


@router.post("/checkout", summary="Démarrer le paiement de l'abonnement (Stripe Checkout)")
async def billing_checkout(current_user: User = Depends(get_current_user)):
    """Crée une session Stripe Checkout et renvoie l'URL de paiement (carte/SEPA)."""
    _require_manager(current_user)
    return await _alice_billing("POST", "checkout", current_user.id)


@router.post("/portal", summary="Ouvrir le portail de gestion de l'abonnement Stripe")
async def billing_portal(current_user: User = Depends(get_current_user)):
    """Crée une session du portail de facturation Stripe (gérer carte/abonnement)."""
    _require_manager(current_user)
    return await _alice_billing("POST", "portal", current_user.id)


@router.get("/plans", summary="Plans proposables pour un changement d'abonnement")
async def billing_available_plans(current_user: User = Depends(get_current_user)):
    _require_manager(current_user)
    try:
        return await _alice_billing("GET", "available-plans", current_user.id)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        return []


class _ChangePlanIn(BaseModel):
    plan_id: str


@router.post("/change-plan", summary="Changer de plan (proration Stripe)")
async def billing_change_plan(body: _ChangePlanIn, current_user: User = Depends(get_current_user)):
    """Change le plan de l'abonnement avec proration automatique (via Alice/Stripe)."""
    _require_manager(current_user)
    return await _alice_billing("POST", "change-plan", current_user.id, json={"plan_id": body.plan_id})


@router.get("/payments", summary="Historique des paiements Stripe")
async def billing_payments(current_user: User = Depends(get_current_user)):
    _require_manager(current_user)
    try:
        return await _alice_billing("GET", "payments", current_user.id)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        return []
