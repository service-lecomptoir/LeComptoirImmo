from fastapi import APIRouter
from app.api.v1 import (
    auth, dashboard, gestionnaires, plans, internal, subscriptions, invoices,
    stripe_webhook, sejour,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(gestionnaires.router)
api_router.include_router(plans.router)
api_router.include_router(internal.router)
api_router.include_router(subscriptions.router)
api_router.include_router(invoices.router)
api_router.include_router(stripe_webhook.router)
api_router.include_router(sejour.router)
