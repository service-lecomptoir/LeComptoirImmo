from fastapi import APIRouter
from app.api.v1 import auth, dashboard, gestionnaires, plans

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(gestionnaires.router)
api_router.include_router(plans.router)
