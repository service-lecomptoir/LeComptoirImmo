"""Contrat interne unifié `/internal` (Alice → LeCI).

Même structure que l'API interne de Le Comptoir Séjour, pour qu'Alice pilote les
deux produits de façon identique. Router monté À LA RACINE (hors `/api`) : il
n'est donc PAS proxifié publiquement par nginx (location `/api/` seulement) →
joignable uniquement par Alice sur le réseau Docker interne.

Protégé par l'en-tête `X-Internal-Key` == `ALICE_INTERNAL_KEY` (clé partagée).
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.permissions import Role
from app.database import get_db
from app.models.property import Property
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/internal", tags=["internal-admin"])

_MANAGER_ROLES = [Role.GESTIONNAIRE.value, Role.GESTIONNAIRE_PROPRIO.value]


def require_internal_key(x_internal_key: Optional[str] = Header(default=None)) -> None:
    cfg = get_settings()
    if not x_internal_key or x_internal_key != cfg.ALICE_INTERNAL_KEY:
        raise HTTPException(status_code=401, detail="Clé interne invalide.")


# ── Schémas du contrat (identiques côté Séjour) ───────────────────────────────
class ManagerOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    owner_full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    property_count: int = 0

    model_config = {"from_attributes": True}


class PropertyOut(BaseModel):
    id: uuid.UUID
    name: str
    address: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None

    model_config = {"from_attributes": True}


class ManagerCreate(BaseModel):
    email: EmailStr
    full_name: str = Field("", max_length=255)
    phone: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=128)


class ManagerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)


class Stats(BaseModel):
    managers: int
    active_managers: int
    users: int


# ── Endpoints ─────────────────────────────────────────────────────────────────
async def _property_counts(db: AsyncSession) -> dict[uuid.UUID, int]:
    """Nb de biens par créateur (gestionnaire), en une requête."""
    rows = await db.execute(
        select(Property.created_by, func.count(Property.id)).group_by(Property.created_by)
    )
    return {cb: n for cb, n in rows.all() if cb is not None}


def _manager_out(user: User, property_count: int = 0) -> ManagerOut:
    return ManagerOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        owner_full_name=getattr(user, "owner_full_name", None),
        phone=getattr(user, "phone", None),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        created_at=getattr(user, "created_at", None),
        property_count=property_count,
    )


@router.get("/managers", response_model=list[ManagerOut])
async def list_managers(_: None = Depends(require_internal_key), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(User).where(User.role.in_(_MANAGER_ROLES)).order_by(User.full_name)
        )
    ).scalars().all()
    counts = await _property_counts(db)
    return [_manager_out(u, counts.get(u.id, 0)) for u in rows]


@router.get("/managers/{manager_id}", response_model=ManagerOut)
async def get_manager(
    manager_id: uuid.UUID,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, manager_id)
    if user is None or user.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    count = await db.scalar(
        select(func.count(Property.id)).where(Property.created_by == manager_id)
    ) or 0
    return _manager_out(user, count)


@router.get("/managers/{manager_id}/properties", response_model=list[PropertyOut])
async def manager_properties(
    manager_id: uuid.UUID,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(Property).where(Property.created_by == manager_id).order_by(Property.name)
        )
    ).scalars().all()
    return list(rows)


@router.post("/managers", response_model=ManagerOut, status_code=201)
async def create_manager(
    data: ManagerCreate,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.create(
        db,
        UserCreate(email=data.email, password=data.password, full_name=data.full_name, role=Role.GESTIONNAIRE),
        created_by=None,  # compte principal (agence), créé par la plateforme
    )
    if data.phone:
        user.phone = data.phone
        await db.flush()
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/managers/{manager_id}", response_model=ManagerOut)
async def update_manager(
    manager_id: uuid.UUID,
    data: ManagerUpdate,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    await UserService.update(
        db,
        manager_id,
        UserUpdate(full_name=data.full_name, is_active=data.is_active, phone=data.phone),
    )
    await db.commit()
    refreshed = await db.get(User, manager_id)
    return refreshed


@router.post("/managers/{manager_id}/reset-password", status_code=204)
async def reset_manager_password(
    manager_id: uuid.UUID,
    data: ResetPassword,
    _: None = Depends(require_internal_key),
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(User, manager_id)
    if target is None or target.role not in _MANAGER_ROLES:
        raise HTTPException(status_code=404, detail="Gestionnaire introuvable.")
    await UserService.admin_set_password(db, manager_id, data.new_password)
    await db.commit()


@router.get("/stats", response_model=Stats)
async def stats(_: None = Depends(require_internal_key), db: AsyncSession = Depends(get_db)):
    managers = await db.scalar(select(func.count()).select_from(User).where(User.role.in_(_MANAGER_ROLES))) or 0
    active = await db.scalar(
        select(func.count()).select_from(User).where(User.role.in_(_MANAGER_ROLES), User.is_active.is_(True))
    ) or 0
    total = await db.scalar(select(func.count()).select_from(User)) or 0
    return Stats(managers=managers, active_managers=active, users=total)
