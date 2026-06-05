# -*- coding: utf-8 -*-
"""Intégration Stripe — abonnements récurrents des gestionnaires (carte / SEPA).

Centralisé dans Alice (propriétaire des plans/licences/factures). Conception
défensive : si `STRIPE_SECRET_KEY` est vide, l'intégration est désactivée et les
fonctions lèvent une erreur explicite (les endpoints renvoient alors 503/400).

Modèle : 1 Product + 1 Price (mensuel récurrent) par plan ; 1 Customer par
gestionnaire ; abonnement via Stripe Checkout (mode subscription) acceptant
carte ET prélèvement SEPA. Les webhooks synchronisent licence + factures.
"""
import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return get_settings().stripe_enabled


def _stripe():
    """Retourne le module stripe configuré, ou lève si désactivé/non installé."""
    s = get_settings()
    if not s.stripe_enabled:
        raise RuntimeError("Stripe non configuré (STRIPE_SECRET_KEY vide).")
    import stripe  # import paresseux (dépendance optionnelle au démarrage)
    stripe.api_key = s.STRIPE_SECRET_KEY
    return stripe


# ── Produits / prix par plan ─────────────────────────────────────────────────
async def ensure_plan_price(db, plan, *, force: bool = False) -> str:
    """Crée (si besoin) le Product + Price mensuel Stripe du plan ; renvoie price_id.

    Idempotent : ne recrée pas si `plan.stripe_price_id` existe déjà — SAUF si
    `force=True` (resynchro après changement de tarif : un Price Stripe est
    immuable, on en crée donc un nouveau pour les futurs abonnements)."""
    stripe = _stripe()
    s = get_settings()
    # Auto-cicatrisation : un price enregistré mais invalide dans le mode courant
    # (bascule test→live, ou supprimé) est ignoré et recréé.
    if plan.stripe_price_id and not force:
        try:
            pr = stripe.Price.retrieve(plan.stripe_price_id)
            if getattr(pr, "active", True):
                return plan.stripe_price_id
        except Exception:  # noqa: BLE001 — price invalide → on recrée
            pass
    # Product : valider l'existant, sinon (re)créer.
    product_id = plan.stripe_product_id
    if product_id:
        try:
            pr = stripe.Product.retrieve(product_id)
            if getattr(pr, "deleted", False):
                product_id = None
        except Exception:  # noqa: BLE001
            product_id = None
    if not product_id:
        product = stripe.Product.create(
            name=f"Abonnement {plan.name}",
            metadata={"alice_plan_id": str(plan.id)},
        )
        product_id = product.id
        plan.stripe_product_id = product_id
    amount_cents = int(round(float(plan.monthly_price or 0) * 100))
    price = stripe.Price.create(
        product=product_id,
        unit_amount=amount_cents,
        currency=s.STRIPE_CURRENCY,
        recurring={"interval": "month"},
        metadata={"alice_plan_id": str(plan.id)},
    )
    plan.stripe_price_id = price.id
    await db.flush()
    return price.id


# ── Client (customer) par gestionnaire ───────────────────────────────────────
async def ensure_customer(db, license, *, email: Optional[str] = None,
                          name: Optional[str] = None) -> str:
    """Crée (si besoin) le Customer Stripe du gestionnaire ; renvoie customer_id.

    Auto-cicatrisation : un customer enregistré mais invalide dans le mode courant
    (bascule test→live, ou supprimé) est recréé."""
    stripe = _stripe()
    if license.stripe_customer_id:
        try:
            c = stripe.Customer.retrieve(license.stripe_customer_id)
            if not getattr(c, "deleted", False):
                return license.stripe_customer_id
        except Exception:  # noqa: BLE001 — customer invalide → on recrée
            pass
    customer = stripe.Customer.create(
        email=email or None,
        name=name or None,
        metadata={"gestionnaire_user_id": str(license.gestionnaire_user_id)},
    )
    license.stripe_customer_id = customer.id
    await db.flush()
    return customer.id


# ── Session Checkout (abonnement : carte + SEPA) ─────────────────────────────
def create_checkout_session(*, customer_id: str, price_id: str,
                            success_url: str, cancel_url: str,
                            metadata: Optional[dict] = None) -> str:
    """Crée une session Checkout (mode subscription) et renvoie son URL."""
    stripe = _stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        payment_method_types=["card", "sepa_debit"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata or {},
        subscription_data={"metadata": metadata or {}},
        locale="fr",
    )
    return session.url


def change_subscription_plan(*, subscription_id: str, new_price_id: str) -> None:
    """Bascule l'abonnement sur un nouveau prix avec PRORATION automatique."""
    stripe = _stripe()
    sub = stripe.Subscription.retrieve(subscription_id)
    items = (sub.get("items") or {}).get("data") or []
    if not items:
        raise RuntimeError("Abonnement sans ligne de facturation.")
    stripe.Subscription.modify(
        subscription_id,
        items=[{"id": items[0]["id"], "price": new_price_id}],
        proration_behavior="create_prorations",
    )


def list_payments(*, customer_id: str, limit: int = 12) -> list[dict]:
    """Historique des factures/paiements Stripe d'un client (récent → ancien)."""
    stripe = _stripe()
    invs = stripe.Invoice.list(customer=customer_id, limit=limit)
    out = []
    for inv in (invs.get("data") or []):
        cents = inv.get("amount_paid") or inv.get("amount_due") or 0
        out.append({
            "id": inv.get("id"),
            "number": inv.get("number"),
            "created": inv.get("created"),  # unix
            "amount": float(cents) / 100.0,
            "currency": inv.get("currency"),
            "status": inv.get("status"),  # paid / open / void / uncollectible
            "hosted_invoice_url": inv.get("hosted_invoice_url"),
            "invoice_pdf": inv.get("invoice_pdf"),
        })
    return out


def create_billing_portal_session(*, customer_id: str, return_url: str) -> str:
    """Crée une session du portail de facturation Stripe (gérer carte/abonnement)."""
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=return_url,
    )
    return session.url


# ── Webhooks ─────────────────────────────────────────────────────────────────
def construct_event(payload: bytes, sig_header: str):
    """Vérifie la signature du webhook et renvoie l'événement Stripe."""
    stripe = _stripe()
    s = get_settings()
    if not s.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET non configuré.")
    return stripe.Webhook.construct_event(payload, sig_header, s.STRIPE_WEBHOOK_SECRET)


def _dt(ts):
    from datetime import datetime
    return datetime.utcfromtimestamp(ts) if ts else None


async def _license_by(db, *, customer_id=None, gestionnaire_user_id=None):
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.license import AliceLicense
    lic = None
    if customer_id:
        lic = (await db.execute(
            select(AliceLicense).where(AliceLicense.stripe_customer_id == customer_id)
        )).scalar_one_or_none()
    if lic is None and gestionnaire_user_id:
        try:
            gid = _uuid.UUID(str(gestionnaire_user_id))
        except Exception:  # noqa: BLE001
            gid = None
        if gid is not None:
            lic = (await db.execute(
                select(AliceLicense).where(AliceLicense.gestionnaire_user_id == gid)
            )).scalar_one_or_none()
    return lic


# Statuts Stripe qui donnent accès / qui suspendent.
_ACTIVE = {"active", "trialing"}
_SUSPEND = {"unpaid", "canceled", "incomplete_expired"}


async def _apply_subscription_status(db, lic, status: str):
    """Active/suspend la licence selon le statut d'abonnement Stripe."""
    from app.services.block_service import block_gestionnaire, unblock_gestionnaire
    lic.stripe_status = status
    if status in _ACTIVE:
        lic.access_until = None
        if lic.is_blocked:
            await unblock_gestionnaire(db, lic, lic.gestionnaire_user_id)
    elif status in _SUSPEND:
        if not lic.is_blocked:
            await block_gestionnaire(db, lic, lic.gestionnaire_user_id)


async def handle_event(db, event) -> None:
    """Traite un événement Stripe (idempotent côté effets : statuts/UPSERT)."""
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        if obj.get("mode") != "subscription":
            return
        lic = await _license_by(
            db, customer_id=obj.get("customer"),
            gestionnaire_user_id=(obj.get("metadata") or {}).get("gestionnaire_user_id"),
        )
        if not lic:
            return
        if obj.get("customer"):
            lic.stripe_customer_id = obj["customer"]
        if obj.get("subscription"):
            lic.stripe_subscription_id = obj["subscription"]
        await _apply_subscription_status(db, lic, "active")
        await db.flush()
        return

    if etype in ("customer.subscription.created", "customer.subscription.updated",
                 "customer.subscription.deleted"):
        lic = await _license_by(db, customer_id=obj.get("customer"),
                                gestionnaire_user_id=(obj.get("metadata") or {}).get("gestionnaire_user_id"))
        if not lic:
            return
        lic.stripe_subscription_id = obj.get("id") or lic.stripe_subscription_id
        lic.stripe_current_period_end = _dt(obj.get("current_period_end"))
        # Synchro du plan : si l'abonnement pointe vers un autre prix (changement de
        # plan via l'app OU le portail), on aligne license.plan_id.
        await _sync_plan_from_price(db, lic, obj)
        status = "canceled" if etype.endswith("deleted") else obj.get("status", "")
        await _apply_subscription_status(db, lic, status)
        await db.flush()
        return

    if etype == "invoice.paid":
        await _upsert_invoice_paid(db, obj)
        return

    # invoice.payment_failed : la suspension est pilotée par le statut de
    # l'abonnement (past_due → unpaid), géré ci-dessus. Rien à faire ici.


async def _sync_plan_from_price(db, lic, sub_obj) -> None:
    """Aligne license.plan_id sur le prix courant de l'abonnement Stripe."""
    from sqlalchemy import select
    from app.models.plan import AlicePlan
    items = (sub_obj.get("items") or {}).get("data") or []
    if not items:
        return
    price = items[0].get("price") or {}
    price_id = price.get("id")
    if not price_id:
        return
    plan = (await db.execute(
        select(AlicePlan).where(AlicePlan.stripe_price_id == price_id)
    )).scalar_one_or_none()
    if plan and lic.plan_id != plan.id:
        lic.plan_id = plan.id


async def _upsert_invoice_paid(db, inv_obj) -> None:
    """Marque/î crée la facture Alice correspondante comme payée (lien Stripe)."""
    from datetime import datetime
    from sqlalchemy import select
    from app.models.invoice import AliceInvoice
    lic = await _license_by(db, customer_id=inv_obj.get("customer"))
    if not lic:
        return
    # Période : on rattache au mois de la date de création de la facture Stripe.
    created = _dt(inv_obj.get("created")) or datetime.utcnow()
    year, month = created.year, created.month
    amount = float(inv_obj.get("amount_paid", 0) or 0) / 100.0
    pm = None
    # Type de moyen de paiement si présent.
    try:
        pm = (inv_obj.get("payment_settings") or {}).get("payment_method_types", [None])[0]
    except Exception:  # noqa: BLE001
        pm = None

    existing = (await db.execute(
        select(AliceInvoice).where(
            AliceInvoice.gestionnaire_user_id == lic.gestionnaire_user_id,
            AliceInvoice.period_year == year,
            AliceInvoice.period_month == month,
        )
    )).scalar_one_or_none()
    if existing:
        existing.status = "paid"
        existing.paid_at = datetime.utcnow()
        existing.stripe_invoice_id = inv_obj.get("id")
        existing.payment_method = pm or existing.payment_method
    else:
        db.add(AliceInvoice(
            gestionnaire_user_id=lic.gestionnaire_user_id,
            period_year=year, period_month=month, amount=amount,
            plan_name=None, status="paid",
            paid_at=datetime.utcnow(), stripe_invoice_id=inv_obj.get("id"),
            payment_method=pm, created_at=datetime.utcnow(),
        ))
    await db.flush()
