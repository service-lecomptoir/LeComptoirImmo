"""Console Alice — gestion de Le Comptoir Séjour via son API interne.

Délègue au contrat /internal de Séjour (ProductClient). Réservé aux admins Alice.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.core.deps import get_current_alice_admin
from app.models.admin import AliceAdmin
from app.services.product_client import ProductClient

router = APIRouter(prefix="/sejour", tags=["Séjour"])


class SejourManagerCreate(BaseModel):
    email: EmailStr
    full_name: str = Field("", max_length=255)
    phone: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=128)


class SejourManagerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class SejourResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


def _client() -> ProductClient:
    return ProductClient("sejour")


@router.get("/stats")
async def sejour_stats(_: AliceAdmin = Depends(get_current_alice_admin)):
    return await _client().stats()


@router.get("/managers")
async def list_sejour_managers(_: AliceAdmin = Depends(get_current_alice_admin)):
    return await _client().list_managers()


@router.post("/managers", status_code=201)
async def create_sejour_manager(
    data: SejourManagerCreate, _: AliceAdmin = Depends(get_current_alice_admin)
):
    return await _client().create_manager(data.model_dump())


@router.patch("/managers/{manager_id}")
async def update_sejour_manager(
    manager_id: str,
    data: SejourManagerUpdate,
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    return await _client().update_manager(manager_id, data.model_dump(exclude_unset=True))


@router.post("/managers/{manager_id}/reset-password", status_code=204)
async def reset_sejour_manager_password(
    manager_id: str,
    data: SejourResetPassword,
    _: AliceAdmin = Depends(get_current_alice_admin),
):
    await _client().reset_password(manager_id, data.new_password)
