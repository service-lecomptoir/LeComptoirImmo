from fastapi import APIRouter
from app.api.v1 import (
    auth, users, tenants, properties, units, documents,
    leases, inspections, payments, letters, notifications,
    avis_echeances,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tenants.router)
api_router.include_router(properties.router)
api_router.include_router(units.router)
api_router.include_router(documents.router)
api_router.include_router(leases.router)
api_router.include_router(inspections.router)
api_router.include_router(payments.router)
api_router.include_router(letters.router)
api_router.include_router(notifications.router)
api_router.include_router(avis_echeances.router)
