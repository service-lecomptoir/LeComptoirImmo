import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_active_admin
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserRoleUpdate,
    UserPasswordUpdate, UserResponse
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Utilisateurs"])


@router.get("", response_model=List[UserResponse], summary="Liste des utilisateurs")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    """Retourne la liste de tous les utilisateurs (admin uniquement)."""
    return await UserService.list_all(db)


@router.post("", response_model=UserResponse, status_code=201, summary="Créer un utilisateur")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    """Crée un nouvel utilisateur (admin uniquement)."""
    return await UserService.create(db, data)


@router.get("/me", response_model=UserResponse, summary="Mon profil")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Retourne le profil de l'utilisateur connecté."""
    return current_user


@router.get("/{user_id}", response_model=UserResponse, summary="Détail d'un utilisateur")
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    return await UserService.get_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Modifier un utilisateur")
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    return await UserService.update(db, user_id, data)


@router.patch("/{user_id}/role", response_model=UserResponse, summary="Changer le rôle")
async def update_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    """Modifie le rôle d'un utilisateur (admin uniquement)."""
    return await UserService.update_role(db, user_id, data)


@router.patch("/me/password", status_code=204, summary="Changer mon mot de passe")
async def change_my_password(
    data: UserPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permet à l'utilisateur connecté de changer son propre mot de passe."""
    await UserService.update_password(db, current_user, data)


@router.delete("/{user_id}", status_code=204, summary="Supprimer un utilisateur")
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_admin),
):
    await UserService.delete(db, user_id)
