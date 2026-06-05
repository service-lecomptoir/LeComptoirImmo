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
async def ensure_plan_price(db, plan) -> str:
    """Crée (si besoin) le Product + Price mensuel Stripe du plan ; renvoie price_id.

    Idempotent : ne recrée pas si `plan.stripe_price_id` existe déjà."""
    if plan.stripe_price_id:
        return plan.stripe_price_id
    stripe = _stripe()
    s = get_settings()
    product_id = plan.stripe_product_id
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
    """Crée (si besoin) le Customer Stripe du gestionnaire ; renvoie customer_id."""
    if license.stripe_customer_id:
        return license.stripe_customer_id
    stripe = _stripe()
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
