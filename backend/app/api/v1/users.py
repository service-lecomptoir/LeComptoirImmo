import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_active_admin, get_current_gestionnaire
from app.core.permissions import Role
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserRoleUpdate,
    UserPasswordUpdate, UserResponse
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

# Rôles que le gestionnaire peut créer / voir
_GESTIONNAIRE_ALLOWED_ROLES = {Role.PROPRIETAIRE, Role.LOCATAIRE}


@router.get("", response_model=List[UserResponse], summary="Liste des utilisateurs")
async def list_users(
    role: Optional[str] = Query(None, description="Filtrer par rôle (ex: proprietaire, locataire)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """
    Retourne la liste des utilisateurs.
    - Admin : tous les utilisateurs
    - Gestionnaire : seulement les propriétaires et locataires
    """
    users = await UserService.list_all(db)

    # Gestionnaire : restreindre aux rôles qu'il gère
    if Role(current_user.role) == Role.GESTIONNAIRE:
        users = [u for u in users if Role(u.role) in _GESTIONNAIRE_ALLOWED_ROLES]

    # Filtre optionnel par rôle
    if role:
        users = [u for u in users if u.role == role]

    return users


@router.post("", response_model=UserResponse, status_code=201, summary="Créer un utilisateur")
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_gestionnaire),
):
    """
    Crée un nouvel utilisateur.
    - Admin : peut créer n'importe quel rôle
    - Gestionnaire : peut créer uniquement propriétaire ou locataire
    """
    if Role(current_user.role) == Role.GESTIONNAIRE:
        if Role(data.role) not in _GESTIONNAIRE_ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire ne peut créer que des comptes propriétaire ou locataire.",
            )
    return await UserService.create(db, data)


@router.get("/me", response_model=UserResponse, summary="Mon profil")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Retourne le profil de l'utilisateur connecté."""
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Mettre à jour mon profil")
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permet à l'utilisateur connecté de mettre à jour son propre profil (nom, email)."""
    return await UserService.update(db, current_user.id, data)


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
