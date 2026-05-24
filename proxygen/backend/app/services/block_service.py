"""
Service de blocage/déblocage en cascade.
Quand un gestionnaire est bloqué, tous ses propriétaires et locataires
sont désactivés (is_active = False) dans la table users de LeCI.
"""
import logging
import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.license import ProxygenLicense
from app.models.leci import LeciUser, LeciProperty, LeciUnit, LeciTenant, LeciLease

logger = logging.getLogger(__name__)


async def _get_gestionnaire_property_ids(db: AsyncSession, gestionnaire_id: uuid.UUID) -> List[uuid.UUID]:
    """Retourne la liste des IDs de biens créés par ce gestionnaire."""
    result = await db.execute(
        select(LeciProperty.id).where(LeciProperty.created_by == gestionnaire_id)
    )
    return [row[0] for row in result.fetchall()]


async def _get_owner_user_ids(db: AsyncSession, property_ids: List[uuid.UUID]) -> List[uuid.UUID]:
    """Retourne les IDs des propriétaires associés à ces biens."""
    if not property_ids:
        return []
    result = await db.execute(
        select(LeciProperty.owner_user_id).where(
            LeciProperty.id.in_(property_ids),
            LeciProperty.owner_user_id.isnot(None),
        )
    )
    return [row[0] for row in result.fetchall()]


async def _get_tenant_user_ids(db: AsyncSession, property_ids: List[uuid.UUID]) -> List[uuid.UUID]:
    """
    Retourne les IDs des locataires (via users) liés aux baux actifs
    des logements appartenant à ces biens.
    """
    if not property_ids:
        return []

    # units du bien
    units_result = await db.execute(
        select(LeciUnit.id).where(LeciUnit.property_id.in_(property_ids))
    )
    unit_ids = [row[0] for row in units_result.fetchall()]
    if not unit_ids:
        return []

    # baux actifs sur ces unités
    leases_result = await db.execute(
        select(LeciLease.tenant_id).where(
            LeciLease.unit_id.in_(unit_ids),
            LeciLease.is_active == True,
            LeciLease.tenant_id.isnot(None),
        )
    )
    tenant_ids = [row[0] for row in leases_result.fetchall()]
    if not tenant_ids:
        return []

    # user_id des tenants
    users_result = await db.execute(
        select(LeciTenant.user_id).where(
            LeciTenant.id.in_(tenant_ids),
            LeciTenant.user_id.isnot(None),
        )
    )
    return [row[0] for row in users_result.fetchall()]


async def block_gestionnaire(
    db: AsyncSession,
    license: ProxygenLicense,
    gestionnaire_id: uuid.UUID,
) -> None:
    """
    Bloque le gestionnaire et désactive en cascade tous ses propriétaires
    et locataires dans la table users de LeCI.
    """
    logger.info(f"Blocage du gestionnaire {gestionnaire_id}")

    # 1. Trouver les biens de ce gestionnaire
    property_ids = await _get_gestionnaire_property_ids(db, gestionnaire_id)
    logger.info(f"  {len(property_ids)} bien(s) trouvé(s)")

    # 2. Trouver les propriétaires
    owner_user_ids = await _get_owner_user_ids(db, property_ids)

    # 3. Trouver les locataires
    tenant_user_ids = await _get_tenant_user_ids(db, property_ids)

    # 4. Collecter tous les IDs à bloquer (sauf le gestionnaire lui-même)
    all_cascade_ids = list(set(owner_user_ids + tenant_user_ids))
    logger.info(f"  {len(all_cascade_ids)} user(s) à bloquer en cascade")

    # 5. Désactiver le gestionnaire
    await db.execute(
        update(LeciUser)
        .where(LeciUser.id == gestionnaire_id)
        .values(is_active=False)
    )

    # 6. Désactiver les propriétaires et locataires
    if all_cascade_ids:
        await db.execute(
            update(LeciUser)
            .where(LeciUser.id.in_(all_cascade_ids))
            .values(is_active=False)
        )

    # 7. Stocker les IDs bloqués dans la licence pour l'unblock
    license.is_blocked = True
    license.blocked_user_ids = [str(uid) for uid in all_cascade_ids]

    logger.info(f"Gestionnaire {gestionnaire_id} bloqué avec succès")


async def unblock_gestionnaire(
    db: AsyncSession,
    license: ProxygenLicense,
    gestionnaire_id: uuid.UUID,
) -> None:
    """
    Réactive le gestionnaire et uniquement les users qui avaient été
    bloqués en cascade (listés dans license.blocked_user_ids).
    """
    logger.info(f"Déblocage du gestionnaire {gestionnaire_id}")

    # 1. Réactiver le gestionnaire
    await db.execute(
        update(LeciUser)
        .where(LeciUser.id == gestionnaire_id)
        .values(is_active=True)
    )

    # 2. Réactiver uniquement les users bloqués en cascade
    cascade_ids = license.blocked_user_ids or []
    if cascade_ids:
        cascade_uuids = [uuid.UUID(uid) for uid in cascade_ids if uid]
        logger.info(f"  {len(cascade_uuids)} user(s) à réactiver")
        await db.execute(
            update(LeciUser)
            .where(LeciUser.id.in_(cascade_uuids))
            .values(is_active=True)
        )

    # 3. Mettre à jour la licence
    license.is_blocked = False
    license.blocked_user_ids = []

    logger.info(f"Gestionnaire {gestionnaire_id} débloqué avec succès")
