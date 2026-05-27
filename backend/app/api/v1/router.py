from fastapi import APIRouter
from app.api.v1 import (
    auth, users, tenants, properties, documents,
    leases, inspections, payments, letters, notifications,
    avis_echeances, contacts, automation, templates, dashboard,
    tickets, entretiens, messages, proprietaire_perf, offers, subscription,
    webhook, audit, settings, public,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router)
api_router.include_router(properties.router)
api_router.include_router(documents.router)
api_router.include_router(leases.router)
api_router.include_router(inspections.router)
api_router.include_router(payments.router)
api_router.include_router(letters.router)
api_router.include_router(notifications.router)
api_router.include_router(avis_echeances.router)
api_router.include_router(contacts.router)
api_router.include_router(automation.router)
api_router.include_router(templates.router)
api_router.include_router(dashboard.router)
api_router.include_router(proprietaire_perf.router)
api_router.include_router(tickets.router)
api_router.include_router(entretiens.router)
api_router.include_router(messages.router)
api_router.include_router(offers.router)
api_router.include_router(subscription.router)
api_router.include_router(webhook.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)
api_router.include_router(public.router)
