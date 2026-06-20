from fastapi import APIRouter, Depends

from app.api.v1 import (
    actualisation,
    apurement_plans,
    audit,
    auth,
    automation,
    avis_echeances,
    caf,
    candidatures,
    contacts,
    dashboard,
    documents,
    entretiens,
    inspections,
    lease_exits,
    leases,
    letters,
    message_templates,
    messages,
    notifications,
    offers,
    online_payments,
    owners,
    payments,
    properties,
    proprietaire_perf,
    public,
    publishing,
    rgpd,
    scoring,
    settings,
    signalements,
    subscription,
    telegram,
    templates,
    tenants,
    tickets,
    users,
    webhook,
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
api_router.include_router(apurement_plans.router, dependencies=_feat("payments"))
api_router.include_router(notifications.router)
api_router.include_router(avis_echeances.router, dependencies=_feat("avis_echeances"))
api_router.include_router(contacts.router, dependencies=_feat("contacts"))
api_router.include_router(automation.router, dependencies=_feat("automatisation"))
api_router.include_router(message_templates.router, dependencies=_feat("automatisation"))
api_router.include_router(templates.router, dependencies=_feat("templates"))
api_router.include_router(dashboard.router)
api_router.include_router(proprietaire_perf.router)
api_router.include_router(tickets.router, dependencies=_feat("incidents"))
api_router.include_router(signalements.router, dependencies=_feat("incidents"))
api_router.include_router(entretiens.router, dependencies=_feat("entretiens"))
api_router.include_router(scoring.router)
api_router.include_router(telegram.router)
api_router.include_router(messages.router)
api_router.include_router(offers.router, dependencies=_feat("offres"))
api_router.include_router(subscription.router)
api_router.include_router(webhook.router)
api_router.include_router(audit.router)
api_router.include_router(rgpd.router)
api_router.include_router(settings.router)
api_router.include_router(public.router)
api_router.include_router(publishing.router, dependencies=_feat("diffusion"))
api_router.include_router(candidatures.router, dependencies=_feat("candidatures"))
api_router.include_router(lease_exits.router, dependencies=_feat("sortie_locataire"))
api_router.include_router(caf.router, dependencies=_feat("documents_caf"))
api_router.include_router(actualisation.router, dependencies=_feat("actualisation"))
# Paiement en ligne du loyer par carte (config GM + checkout locataire + webhooks).
# Pas de _feat : la config est transverse au profil et les webhooks sont publics.
api_router.include_router(online_payments.router)
