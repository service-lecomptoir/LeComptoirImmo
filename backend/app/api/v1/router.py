from fastapi import APIRouter, Depends
from app.api.v1 import (
    auth, users, tenants, owners, properties, documents,
    leases, inspections, payments, letters, notifications,
    avis_echeances, contacts, automation, templates, dashboard,
    tickets, entretiens, messages, proprietaire_perf, offers, subscription,
    webhook, audit, settings, public, actualisation, scoring, telegram,
    publishing,
)
from app.core.features import require_feature

api_router = APIRouter(prefix="/api/v1")

# Enforcement serveur des fonctionnalités de plan (entitlements).
# Appliqué aux routers qui correspondent proprement à UNE fonctionnalité.
# Routers laissés libres car partagés / transverses (profil, tableau de bord,
# abonnement, notifications, documents, messages, perf propriétaire, etc.) ou
# parce que la fonctionnalité n'a pas de router dédié (quittances, finances,
# performance_biens, liasse_fiscale → gérés côté front menu+URL).
def _feat(key: str):
    return [Depends(require_feature(key))]

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router, dependencies=_feat("tenants"))
api_router.include_router(owners.router)
api_router.include_router(properties.router, dependencies=_feat("properties"))
api_router.include_router(documents.router)
api_router.include_router(leases.router, dependencies=_feat("leases"))
api_router.include_router(inspections.router)
api_router.include_router(payments.router, dependencies=_feat("payments"))
api_router.include_router(letters.router)
api_router.include_router(notifications.router)
api_router.include_router(avis_echeances.router, dependencies=_feat("avis_echeances"))
api_router.include_router(contacts.router, dependencies=_feat("contacts"))
api_router.include_router(automation.router, dependencies=_feat("automatisation"))
api_router.include_router(templates.router, dependencies=_feat("templates"))
api_router.include_router(dashboard.router)
api_router.include_router(proprietaire_perf.router)
api_router.include_router(tickets.router, dependencies=_feat("incidents"))
api_router.include_router(entretiens.router, dependencies=_feat("entretiens"))
api_router.include_router(scoring.router)
api_router.include_router(telegram.router)
api_router.include_router(messages.router)
api_router.include_router(offers.router, dependencies=_feat("offres"))
api_router.include_router(subscription.router)
api_router.include_router(webhook.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(public.router)
api_router.include_router(publishing.router)
api_router.include_router(actualisation.router, dependencies=_feat("actualisation"))
