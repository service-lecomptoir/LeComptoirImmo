"""Mise en copie (CC) des e-mails locataires : pilotée par les Règles d'automatisation.

Le CC est désormais configuré PAR RÈGLE (`AutomationRule.cc_emails`), pas par un
réglage global. Ces helpers servent aux envois MANUELS (boutons relance / quittance
/ avis / communication groupée) pour réutiliser le CC de la règle du même type, afin
que manuel et automatique soient cohérents. Les envois automatiques, eux, lisent
directement `rule.cc_emails` dans automation_engine.
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _clean(raw: Optional[str]) -> Optional[str]:
    raw = (raw or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return ", ".join(parts) or None


async def rule_cc(db: AsyncSession, manager_id, *rule_types: str) -> Optional[str]:
    """CC de la 1re règle active (parmi `rule_types`) du gestionnaire, ou None."""
    if not manager_id or not rule_types:
        return None
    try:
        from app.models.automation import AutomationRule
        row = (await db.execute(
            select(AutomationRule.cc_emails).where(
                AutomationRule.created_by == manager_id,
                AutomationRule.rule_type.in_(list(rule_types)),
                AutomationRule.is_active.is_(True),
            ).limit(1)
        )).first()
        return _clean(row[0]) if row else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("rule_cc(%s, %s) failed: %s", manager_id, rule_types, exc)
        return None


async def rule_cc_for_lease(db: AsyncSession, lease_id, *rule_types: str) -> Optional[str]:
    """CC (selon la règle du type voulu) résolu via le gestionnaire créateur du bail."""
    if not lease_id:
        return None
    try:
        from app.models.lease import Lease
        lease = await db.get(Lease, lease_id)
        return await rule_cc(db, getattr(lease, "created_by", None), *rule_types) if lease else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("rule_cc_for_lease(%s) failed: %s", lease_id, exc)
        return None
