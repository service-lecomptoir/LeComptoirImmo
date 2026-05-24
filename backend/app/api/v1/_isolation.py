"""
Helpers d'isolation des données par rôle.

Un gestionnaire mandataire (Role.GESTIONNAIRE) ne doit jamais voir les données
appartenant à un gestionnaire_proprio (Role.GESTIONNAIRE_PROPRIO) :
  - Propriétés dont owner_user_id est un gestionnaire_proprio
  - Locataires (Tenant) dont created_by est un gestionnaire_proprio
  - Baux, paiements, tickets qui en dépendent
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.lease import Lease
from app.core.permissions import Role


async def gp_property_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des propriétés appartenant à des gestionnaire_proprio."""
    result = await db.execute(
        select(Property.id)
        .join(User, Property.owner_user_id == User.id)
        .where(User.role == Role.GESTIONNAIRE_PROPRIO.value)
    )
    return set(result.scalars().all())


async def gp_tenant_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des Tenant créés par des gestionnaire_proprio."""
    gp_ids = (await db.execute(
        select(User.id).where(User.role == Role.GESTIONNAIRE_PROPRIO.value)
    )).scalars().all()
    if not gp_ids:
        return set()
    result = await db.execute(
        select(Tenant.id).where(Tenant.created_by.in_(gp_ids))
    )
    return set(result.scalars().all())


async def gp_lease_ids(db: AsyncSession) -> set[uuid.UUID]:
    """IDs des baux sur des propriétés de gestionnaire_proprio."""
    prop_ids = await gp_property_ids(db)
    if not prop_ids:
        return set()
    result = await db.execute(
        select(Lease.id).where(Lease.property_id.in_(prop_ids))
    )
    return set(result.scalars().all())
