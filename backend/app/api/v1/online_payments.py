"""Paiement en ligne du loyer par carte (Stripe / SumUp).

- Gestionnaire : configure ses clés (Mes informations) → /config.
- Locataire : disponibilité (gating) + création du checkout + confirmation SumUp.
- Public : webhook Stripe (par gestionnaire) — non authentifié, vérifié par signature.
"""
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import BadRequestException, ForbiddenException
from app.core.permissions import Role
from app.database import get_db
from app.models.user import User
from app.services import online_payment_service as ops

router = APIRouter(prefix="/online-payments", tags=["Paiement en ligne"])

_MANAGER_ROLES = {Role.GESTIONNAIRE.value, Role.GESTIONNAIRE_PROPRIO.value}


def _require_manager(user: User) -> None:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if role not in _MANAGER_ROLES:
        raise ForbiddenException("Réservé aux gestionnaires.")


# ── Gestionnaire : configuration ───────────────────────────────────────────────
@router.get("/config", summary="Lire ma configuration de paiement en ligne")
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    return ops.config_out(current_user)


@router.put("/config", summary="Enregistrer ma configuration de paiement en ligne")
async def put_config(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    ops.apply_config(current_user, data)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return ops.config_out(current_user)


@router.post("/config/test", summary="Tester mes clés de paiement (sans paiement réel)")
async def test_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_manager(current_user)
    return await ops.test_connection(current_user)


# ── Locataire : disponibilité + checkout ───────────────────────────────────────
@router.get("/locataire/availability", summary="Le paiement par carte est-il proposé ?")
async def availability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ops.card_availability(db, current_user)


@router.post("/locataire/checkout", summary="Démarrer un paiement par carte")
async def checkout(
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment_id = (data or {}).get("payment_id")
    return await ops.create_checkout(db, current_user, payment_id)


@router.post("/locataire/sumup/confirm", summary="Confirmer un paiement SumUp")
async def sumup_confirm(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkout_id = (data or {}).get("checkout_id")
    if not checkout_id:
        raise BadRequestException("Checkout SumUp non précisé.")
    return await ops.confirm_sumup(db, current_user, checkout_id)


# ── Public : webhook Stripe (par gestionnaire, vérifié par signature) ───────────
@router.post("/webhook/stripe/{gestionnaire_id}", summary="Webhook Stripe (public)")
async def stripe_webhook(
    gestionnaire_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    payload = await request.body()
    return await ops.handle_stripe_webhook(db, gestionnaire_id, payload, stripe_signature)
