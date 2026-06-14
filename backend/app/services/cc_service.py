"""Mise en copie (CC) du gestionnaire sur les e-mails envoyés aux locataires.

Réglage `cc_manager_emails` (app_settings, défaut « true ») : quand il est actif,
les e-mails locataire (avis d'échéance, quittance, relance, communication groupée)
mettent le gestionnaire concerné en copie. Le gestionnaire = le créateur du bail
(`Lease.created_by`) ou, à défaut, l'utilisateur fourni.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _enabled(db: AsyncSession) -> bool:
    from app.services import settings_service
    return (await settings_service.get(db, "cc_manager_emails") or "true").lower() == "true"


async def manager_cc_for_user(db: AsyncSession, manager_id) -> Optional[str]:
    """Adresse e-mail à mettre en copie pour un gestionnaire donné (ou None si
    le réglage est désactivé / pas d'e-mail). `manager_id` = id du gestionnaire."""
    if not manager_id:
        return None
    try:
        if not await _enabled(db):
            return None
        from app.models.user import User
        u = await db.get(User, manager_id if isinstance(manager_id, uuid.UUID) else uuid.UUID(str(manager_id)))
        email = (getattr(u, "email", None) or "").strip() if u else ""
        return email or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("manager_cc_for_user(%s) failed: %s", manager_id, exc)
        return None


async def manager_cc_for_lease(db: AsyncSession, lease_id) -> Optional[str]:
    """Adresse e-mail du gestionnaire (créateur du bail) à mettre en copie."""
    if not lease_id:
        return None
    try:
        if not await _enabled(db):
            return None
        from app.models.lease import Lease
        lease = await db.get(Lease, lease_id)
        return await manager_cc_for_user(db, getattr(lease, "created_by", None)) if lease else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("manager_cc_for_lease(%s) failed: %s", lease_id, exc)
        return None
