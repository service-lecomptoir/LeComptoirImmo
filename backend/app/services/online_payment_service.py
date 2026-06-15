"""Paiement en ligne du loyer par carte (Stripe ou SumUp).

Chaque GESTIONNAIRE configure SES propres clés dans « Mes informations ». Le
locataire ne voit le paiement par carte que si son gestionnaire l'a activé. Les
clés secrètes sont stockées chiffrées (cf. core.crypto). Aucune donnée carte ne
transite par notre serveur : Stripe Checkout (page hébergée) et SumUp (widget)
gèrent la saisie. À la confirmation (webhook Stripe / vérification SumUp), le
loyer est enregistré comme payé (quittance automatique).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import date
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.exceptions import BadRequestException
from app.models.lease import Lease
from app.models.payment import Payment
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)

_STRIPE_API = "https://api.stripe.com/v1"
_SUMUP_API = "https://api.sumup.com/v0.1"
_DUE_STATUSES = ["pending", "partial", "late"]


# ── Configuration côté gestionnaire ───────────────────────────────────────────
def config_out(user: User) -> dict:
    """Config visible par le gestionnaire (jamais les secrets en clair : on
    indique seulement s'ils sont renseignés)."""
    return {
        "card_payments_enabled": bool(user.card_payments_enabled),
        "payment_provider": user.payment_provider,
        "stripe": {
            "publishable_key": user.stripe_publishable_key or "",
            "secret_key_set": bool(user.stripe_secret_key_enc),
            "webhook_secret_set": bool(user.stripe_webhook_secret_enc),
            "webhook_url": f"{get_settings().PUBLIC_APP_URL.rstrip('/')}/api/v1/online-payments/webhook/stripe/{user.id}",
        },
        "sumup": {
            "merchant_code": user.sumup_merchant_code or "",
            "api_key_set": bool(user.sumup_api_key_enc),
        },
    }


def apply_config(user: User, data: dict) -> None:
    """Applique la config envoyée par le gestionnaire. Les secrets ne sont mis à
    jour QUE si une valeur non vide est fournie (sinon on garde l'existant) ; pour
    effacer un secret, envoyer la valeur spéciale '__clear__'."""
    if "payment_provider" in data:
        prov = (data.get("payment_provider") or "").strip().lower() or None
        if prov not in (None, "stripe", "sumup"):
            raise BadRequestException("Prestataire inconnu (stripe ou sumup).")
        user.payment_provider = prov
    if "card_payments_enabled" in data:
        user.card_payments_enabled = bool(data.get("card_payments_enabled"))
    # Champs non secrets : toujours mis à jour s'ils sont présents.
    if "stripe_publishable_key" in data:
        user.stripe_publishable_key = (data.get("stripe_publishable_key") or "").strip() or None
    if "sumup_merchant_code" in data:
        user.sumup_merchant_code = (data.get("sumup_merchant_code") or "").strip() or None

    # Secrets : mise à jour seulement si fournis.
    def _secret(key: str):
        return data[key].strip() if isinstance(data.get(key), str) else None

    for field, attr in (
        ("stripe_secret_key", "stripe_secret_key_enc"),
        ("stripe_webhook_secret", "stripe_webhook_secret_enc"),
        ("sumup_api_key", "sumup_api_key_enc"),
    ):
        val = _secret(field)
        if val == "__clear__":
            setattr(user, attr, None)
        elif val:
            setattr(user, attr, encrypt_secret(val))

    # Garde-fou : si on active sans clés exploitables pour le prestataire choisi,
    # on refuse (évite un bouton « carte » qui plante côté locataire).
    if user.card_payments_enabled:
        if user.payment_provider == "stripe" and not user.stripe_secret_key_enc:
            raise BadRequestException("Renseignez la clé secrète Stripe avant d'activer.")
        if user.payment_provider == "sumup" and not (user.sumup_api_key_enc and user.sumup_merchant_code):
            raise BadRequestException("Renseignez la clé API et le merchant code SumUp avant d'activer.")
        if not user.payment_provider:
            raise BadRequestException("Choisissez un prestataire (Stripe ou SumUp) avant d'activer.")


# ── Résolution locataire → loyer dû → config du gestionnaire ───────────────────
async def _tenant_due_payment(
    db: AsyncSession, tenant_user: User, payment_id: Optional[str] = None
) -> Optional[tuple[Tenant, Optional[Payment]]]:
    tenant = (await db.execute(
        select(Tenant).where(Tenant.user_id == tenant_user.id)
    )).scalar_one_or_none()
    if not tenant:
        return None
    q = select(Payment).options(selectinload(Payment.lease)).where(Payment.tenant_id == tenant.id)
    if payment_id:
        q = q.where(Payment.id == uuid.UUID(str(payment_id)))
    else:
        q = (q.where(Payment.status.in_(_DUE_STATUSES))
             .order_by(Payment.period_year.desc(), Payment.period_month.desc()).limit(1))
    payment = (await db.execute(q)).scalar_one_or_none()
    return tenant, payment


async def _config_holder_for_payment(db: AsyncSession, payment: Payment) -> Optional[User]:
    """Compte gestionnaire (principal d'agence) qui porte la config de paiement."""
    mgr_id = getattr(payment.lease, "created_by", None) if payment.lease else None
    if not mgr_id:
        return None
    mgr = await db.get(User, mgr_id)
    if not mgr:
        return None
    principal_id = mgr.agency_id or mgr.id
    if principal_id and principal_id != mgr.id:
        return (await db.get(User, principal_id)) or mgr
    return mgr


def _period_label(payment: Payment) -> str:
    return getattr(payment, "period_label", None) or f"{payment.period_month:02d}/{payment.period_year}"


# ── Disponibilité (gating côté locataire) ──────────────────────────────────────
async def card_availability(db: AsyncSession, tenant_user: User) -> dict:
    res = await _tenant_due_payment(db, tenant_user)
    if not res or not res[1]:
        return {"available": False, "provider": None}
    holder = await _config_holder_for_payment(db, res[1])
    if not holder or not holder.card_payments_enabled or not holder.payment_provider:
        return {"available": False, "provider": None}
    prov = holder.payment_provider
    ok = (
        (prov == "stripe" and bool(decrypt_secret(holder.stripe_secret_key_enc)))
        or (prov == "sumup" and bool(decrypt_secret(holder.sumup_api_key_enc) and holder.sumup_merchant_code))
    )
    return {"available": ok, "provider": prov if ok else None}


# ── Création du paiement (checkout) ────────────────────────────────────────────
async def create_checkout(
    db: AsyncSession, tenant_user: User, payment_id: Optional[str] = None
) -> dict:
    res = await _tenant_due_payment(db, tenant_user, payment_id)
    if not res or not res[1]:
        raise BadRequestException("Aucun loyer à régler.")
    tenant, payment = res
    if payment.tenant_id != tenant.id:
        raise BadRequestException("Loyer non autorisé.")
    holder = await _config_holder_for_payment(db, payment)
    if not holder or not holder.card_payments_enabled or not holder.payment_provider:
        raise BadRequestException("Le paiement par carte n'est pas disponible pour ce loyer.")

    amount = round(float(payment.balance or 0), 2)
    if amount <= 0.005:
        raise BadRequestException("Aucun montant à régler.")
    cents = int(round(amount * 100))
    label = f"Loyer {_period_label(payment)}"
    base = get_settings().PUBLIC_APP_URL.rstrip("/")

    if holder.payment_provider == "stripe":
        secret = decrypt_secret(holder.stripe_secret_key_enc)
        if not secret:
            raise BadRequestException("Configuration Stripe incomplète.")
        form = {
            "mode": "payment",
            "success_url": f"{base}/locataire/payer?card=success",
            "cancel_url": f"{base}/locataire/payer?card=cancel",
            "client_reference_id": str(payment.id),
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": "eur",
            "line_items[0][price_data][unit_amount]": str(cents),
            "line_items[0][price_data][product_data][name]": label,
            "metadata[payment_id]": str(payment.id),
            "payment_intent_data[metadata][payment_id]": str(payment.id),
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                r = await c.post(f"{_STRIPE_API}/checkout/sessions", data=form, auth=(secret, ""))
        except httpx.RequestError as exc:
            raise BadRequestException(f"Stripe injoignable : {exc}")
        if r.status_code >= 400:
            logger.warning("Stripe checkout error %s: %s", r.status_code, r.text[:300])
            raise BadRequestException("Le paiement par carte a échoué (Stripe). Réessayez plus tard.")
        return {"provider": "stripe", "url": r.json().get("url")}

    # SumUp : crée un checkout ; le widget côté front collecte la carte.
    api = decrypt_secret(holder.sumup_api_key_enc)
    if not api or not holder.sumup_merchant_code:
        raise BadRequestException("Configuration SumUp incomplète.")
    payload = {
        "checkout_reference": str(payment.id),
        "amount": amount,
        "currency": "EUR",
        "merchant_code": holder.sumup_merchant_code,
        "description": label,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(f"{_SUMUP_API}/checkouts", json=payload,
                             headers={"Authorization": f"Bearer {api}"})
    except httpx.RequestError as exc:
        raise BadRequestException(f"SumUp injoignable : {exc}")
    if r.status_code >= 400:
        logger.warning("SumUp checkout error %s: %s", r.status_code, r.text[:300])
        raise BadRequestException("Le paiement par carte a échoué (SumUp). Réessayez plus tard.")
    co = r.json()
    return {"provider": "sumup", "checkout_id": co.get("id"), "amount": amount, "currency": "EUR"}


# ── Confirmation / enregistrement ──────────────────────────────────────────────
async def _record_card_payment(db: AsyncSession, payment_id, provider_label: str) -> bool:
    """Enregistre le loyer comme payé par carte (idempotent)."""
    from app.schemas.payment import PaymentRecordIn
    from app.services.payment_service import PaymentService

    pid = uuid.UUID(str(payment_id))
    payment = await PaymentService.get_by_id(db, pid)
    if str(payment.status) == "paid" or getattr(payment.status, "value", None) == "paid":
        return True  # déjà réglé : webhook rejoué, on ne double pas
    amount = round(float(payment.balance or payment.amount_due or 0), 2)
    if amount <= 0.005:
        return True
    await PaymentService.record_payment(
        db, pid,
        PaymentRecordIn(
            amount_paid=amount, payment_date=date.today(),
            payment_method="carte", notes=f"Paiement par carte ({provider_label})",
        ),
    )
    await db.commit()
    logger.info("Loyer %s réglé par carte (%s)", pid, provider_label)
    return True


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    try:
        parts = dict(p.split("=", 1) for p in sig_header.split(","))
        signed = parts["t"].encode() + b"." + payload
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, parts.get("v1", ""))
    except Exception:  # noqa: BLE001
        return False


async def handle_stripe_webhook(
    db: AsyncSession, gestionnaire_id: str, payload: bytes, sig_header: Optional[str]
) -> dict:
    holder = await db.get(User, uuid.UUID(str(gestionnaire_id)))
    if not holder:
        raise BadRequestException("Gestionnaire inconnu.")
    secret = decrypt_secret(holder.stripe_webhook_secret_enc)
    if secret:
        if not sig_header or not _verify_stripe_signature(payload, sig_header, secret):
            raise BadRequestException("Signature webhook invalide.")
    else:
        logger.warning("Webhook Stripe sans secret de signature (gestionnaire %s)", gestionnaire_id)
    try:
        event = json.loads(payload)
    except ValueError:
        raise BadRequestException("Charge utile invalide.")
    if event.get("type") == "checkout.session.completed":
        obj = (event.get("data") or {}).get("object") or {}
        if obj.get("payment_status") == "paid":
            pid = (obj.get("metadata") or {}).get("payment_id") or obj.get("client_reference_id")
            if pid:
                await _record_card_payment(db, pid, "Stripe")
    return {"received": True}


async def confirm_sumup(db: AsyncSession, tenant_user: User, checkout_id: str) -> dict:
    """Vérifie côté serveur l'état d'un checkout SumUp (après le widget) et
    enregistre le loyer si PAID. Sûr : on relit l'état chez SumUp, on ne fait pas
    confiance au client."""
    res = await _tenant_due_payment(db, tenant_user)
    holder = await _config_holder_for_payment(db, res[1]) if res and res[1] else None
    if not holder:
        raise BadRequestException("Paiement non disponible.")
    api = decrypt_secret(holder.sumup_api_key_enc)
    if not api:
        raise BadRequestException("Configuration SumUp incomplète.")
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.get(f"{_SUMUP_API}/checkouts/{checkout_id}",
                            headers={"Authorization": f"Bearer {api}"})
    except httpx.RequestError as exc:
        raise BadRequestException(f"SumUp injoignable : {exc}")
    if r.status_code >= 400:
        raise BadRequestException("Impossible de vérifier le paiement SumUp.")
    co = r.json()
    if co.get("status") == "PAID":
        pid = co.get("checkout_reference")
        if pid:
            await _record_card_payment(db, pid, "SumUp")
        return {"status": "paid"}
    return {"status": (co.get("status") or "pending").lower()}
