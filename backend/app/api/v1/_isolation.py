"""
Helpers d'isolation des données par rôle.

Un gestionnaire mandataire (Role.GESTIONNAIRE) ne doit jamais voir les données
appartenant à un gestionnaire_proprio (Role.GESTIONNAIRE_PROPRIO).

Règle d'identification : on utilise TOUJOURS `created_by` pour identifier
à qui appartient une ressource. C'est le seul champ fiable car il est
automatiquement rempli avec l'ID de l'utilisateur connecté au moment de
la création (voir PropertyService.create, TenantService.create).

  - Propriétés dont created_by est un gestionnaire_proprio
  - Locataires (Tenant) dont created_by est un gestionnaire_proprio
  - Baux portant sur ces propriétés ou liés à ces locataires
  - Paiements, tickets, avis, entretiens qui en dépendent
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.owner import Owner
from app.models.lease import Lease
from app.core.permissions import Role


async def _gp_user_ids(db: AsyncSession) -> list[uuid.UUID]:
    """IDs de tous les utilisateurs avec le rôle gestionnaire_proprio."""
    result = await db.execute(
        select(User.id).where(User.role == Role.GESTIONNAIRE_PROPRIO.value)
    )
    return list(result.scalars().all())


async def gp_user_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs (set) de tous les gestionnaire_proprio — utile pour filtrer created_by."""
    return set(await _gp_user_ids(db))


async def gp_property_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des propriétés créées par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Property.id).where(Property.created_by.in_(gp_ids))
    )
    return set(result.scalars().all())


async def gp_tenant_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des Tenant créés par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Tenant.id).where(Tenant.created_by.in_(gp_ids))
    )
    return set(result.scalars().all())


async def gp_owner_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des fiches propriétaire créées par des gestionnaire_proprio (via created_by)."""
    gp_ids = await _gp_user_ids(db)
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Owner.id).where(Owner.created_by.in_(gp_ids))
    )
    return set(result.scalars().all())


async def gp_lease_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des baux liés aux propriétés OU aux locataires de gestionnaire_proprio."""
    prop_ids = await gp_property_ids(db)
    tenant_ids = await gp_tenant_ids(db)
    if not prop_ids and not tenant_ids:
        return set()
    conditions = []
    if prop_ids:
        conditions.append(Lease.property_id.in_(prop_ids))
    if tenant_ids:
        conditions.append(Lease.tenant_id.in_(tenant_ids))
    from sqlalchemy import or_
    result = await db.execute(
        select(Lease.id).where(or_(*conditions))
    )
    return set(result.scalars().all())


async def assert_manager_scope(db: AsyncSession, user: User, created_by, label: str = "cette ressource") -> None:
    """Garde-fou d'isolation pour les endpoints de gestion identifiés par `created_by`.

    - admin : accès total ;
    - gestionnaire_proprio (GP) : uniquement SES ressources (created_by == lui) ;
    - gestionnaire mandataire : tout SAUF les ressources appartenant à un GP ;
    - autres rôles (propriétaire/locataire) : pas d'accès à ces ressources de gestion
      (ils disposent d'endpoints dédiés et filtrés).

    Lève ForbiddenException si l'accès n'est pas autorisé.
    """
    from app.core.exceptions import ForbiddenException

    role = Role(user.role)
    if role == Role.ADMIN:
        return
    if role == Role.GESTIONNAIRE_PROPRIO:
        if created_by is None or str(created_by) != str(user.id):
            raise ForbiddenException(f"Accès refusé à {label}.")
        return
    if role == Role.GESTIONNAIRE:
        gp_ids = await gp_user_ids(db)
        if created_by in gp_ids:
            raise ForbiddenException(f"Accès refusé à {label}.")
        return
    raise ForbiddenException(f"Accès refusé à {label}.")
