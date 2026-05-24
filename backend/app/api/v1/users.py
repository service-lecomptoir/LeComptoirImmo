import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, get_current_active_admin, get_current_gestionnaire
from app.core.permissions import Role
from app.api.v1._isolation import gp_tenant_ids as _isolation_gp_tenant_ids
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserRoleUpdate,
    UserPasswordUpdate, UserResponse
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Utilisateurs"])

# Rôles que le gestionnaire mandataire peut créer / voir
_GESTIONNAIRE_ALLOWED_ROLES = {Role.PROPRIETAIRE, Role.LOCATAIRE}


async def _gp_tenant_ids(db: AsyncSession, owner_id: uuid.UUID) -> set[str]:
    """Retourne les user_ids des locataires liés aux biens du gestionnaire-propriétaire."""
    from app.models.property import Property
    from app.models.lease import Lease
    from app.models.tenant import Tenant

    prop_ids = list((await db.execute(
        select(Property.id).where(Property.owner_user_id == owner_id)
    )).scalars().all())
    if not prop_ids:
        return set()

    tenant_table_ids = list((await db.execute(
        select(Lease.tenant_id).where(
            Lease.property_id.in_(prop_ids),
            Lease.tenant_id.isnot(None),
        )
    )).scalars().all())
    if not tenant_table_ids:
        return set()

    user_ids = list((await db.execute(
        select(Tenant.user_id).where(
            Tenant.id.in_(tenant_table_ids),
            Tenant.user_id.isnot(None),
        )
    )).scalars().all())
    return {str(uid) for uid in user_ids}


async def _require_gp_scope(db: AsyncSession, current_user: User, target_id: uuid.UUID):
    """Pour gestionnaire_proprio : vérifie que la cible est un de ses locataires (ou lui-même)."""
    if str(target_id) == str(current_user.id):
        return
    tenant_ids = await _gp_tenant_ids(db, current_user.id)
    if str(target_id) not in tenant_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


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

    current_role = Role(current_user.role)

    if current_role == Role.GESTIONNAIRE:
        # Gestionnaire mandataire : proprio/locataires, hors ceux créés par un gestionnaire_proprio
        # Approche directe : User.created_by → GP user ids
        from app.api.v1._isolation import _gp_user_ids
        gp_ids = await _gp_user_ids(db)
        gp_created_user_ids: set[str] = set()
        if gp_ids:
            rows = (await db.execute(
                select(User.id).where(User.created_by.in_(gp_ids))
            )).scalars().all()
            gp_created_user_ids = {str(uid) for uid in rows}
        users = [
            u for u in users
            if Role(u.role) in _GESTIONNAIRE_ALLOWED_ROLES
            and str(u.id) not in gp_created_user_ids
        ]
    elif current_role == Role.GESTIONNAIRE_PROPRIO:
        # Gestionnaire-propriétaire : lui-même + ses propres locataires uniquement
        tenant_ids = await _gp_tenant_ids(db, current_user.id)
        users = [u for u in users if str(u.id) == str(current_user.id) or str(u.id) in tenant_ids]

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
    current_role = Role(current_user.role)
    if current_role == Role.GESTIONNAIRE:
        if Role(data.role) not in _GESTIONNAIRE_ALLOWED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire ne peut créer que des comptes propriétaire ou locataire.",
            )
    elif current_role == Role.GESTIONNAIRE_PROPRIO:
        if Role(data.role) != Role.LOCATAIRE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Un gestionnaire-propriétaire ne peut créer que des comptes locataire.",
            )
    # Passer current_user.id pour tracer le créateur (isolation GP)
    return await UserService.create(db, data, created_by=current_user.id)


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
    current_user: User = Depends(get_current_active_admin),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    return await UserService.get_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Modifier un utilisateur")
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    return await UserService.update(db, user_id, data)


@router.patch("/{user_id}/role", response_model=UserResponse, summary="Changer le rôle")
async def update_role(
    user_id: uuid.UUID,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Modifie le rôle d'un utilisateur (admin et gestionnaire mandataire uniquement)."""
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Modification de rôle réservée aux administrateurs")
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
    current_user: User = Depends(get_current_active_admin),
):
    if Role(current_user.role) == Role.GESTIONNAIRE_PROPRIO:
        await _require_gp_scope(db, current_user, user_id)
    await UserService.delete(db, user_id)
