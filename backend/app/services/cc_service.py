"""Mise en copie (CC) des e-mails locataires : pilotée par les Règles d'automatisation.

Le CC est désormais configuré PAR RÈGLE (`AutomationRule.cc_emails`), pas par un
réglage global. Ces helpers servent aux envois MANUELS (boutons relance / quittance
/ avis / communication groupée) pour réutiliser le CC de la règle du même type, afin
que manuel et automatique soient cohérents. Les envois automatiques, eux, lisent
directement `rule.cc_emails` dans automation_engine.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _clean(raw: str | None) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return ", ".join(parts) or None


async def rule_cc(db: AsyncSession, manager_id, *rule_types: str) -> str | None:
    """CC de la 1re règle active (parmi `rule_types`) du gestionnaire, ou None."""
    if not manager_id or not rule_types:
        return None
    try:
        from app.models.automation import AutomationRule

        row = (
            await db.execute(
                select(AutomationRule.cc_emails)
                .where(
                    AutomationRule.created_by == manager_id,
                    AutomationRule.rule_type.in_(list(rule_types)),
                    AutomationRule.is_active.is_(True),
                )
                .limit(1)
            )
        ).first()
        return _clean(row[0]) if row else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("rule_cc(%s, %s) failed: %s", manager_id, rule_types, exc)
        return None


async def rule_message_for_lease(db: AsyncSession, lease_id, *rule_types: str):
    """(subject, body_template) de la 1re règle active (parmi `rule_types`) du
    gestionnaire du bail. Sert aux envois MANUELS pour réutiliser le contenu
    éditable de la règle (cohérence avec l'automatique)."""
    if not lease_id or not rule_types:
        return None, None
    try:
        from app.models.automation import AutomationRule
        from app.models.lease import Lease

        lease = await db.get(Lease, lease_id)
        mid = getattr(lease, "created_by", None) if lease else None
        if not mid:
            return None, None
        row = (
            await db.execute(
                select(AutomationRule.subject, AutomationRule.body_template)
                .where(
                    AutomationRule.created_by == mid,
                    AutomationRule.rule_type.in_(list(rule_types)),
                    AutomationRule.is_active.is_(True),
                )
                .limit(1)
            )
        ).first()
        return (row[0], row[1]) if row else (None, None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rule_message_for_lease(%s) failed: %s", lease_id, exc)
        return None, None


async def rule_cc_for_lease(db: AsyncSession, lease_id, *rule_types: str) -> str | None:
    """CC (selon la règle du type voulu) résolu via le gestionnaire créateur du bail."""
    if not lease_id:
        return None
    try:
        from app.models.lease import Lease
        from app.models.user import User

        lease = await db.get(Lease, lease_id)
        mid = getattr(lease, "created_by", None) if lease else None
        base = await rule_cc(db, mid, *rule_types)
        # Le gestionnaire est TOUJOURS en copie (exigence : tous les envois).
        parts = [p.strip() for p in (base or "").split(",") if p.strip()]
        if mid:
            u = await db.get(User, mid)
            if getattr(u, "email", None):
                parts.append(u.email.strip())
        seen, out = set(), []
        for p in parts:
            k = p.lower()
            if p and k not in seen:
                seen.add(k)
                out.append(p)
        return ", ".join(out) or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("rule_cc_for_lease(%s) failed: %s", lease_id, exc)
        return None
