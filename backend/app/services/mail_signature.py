"""Signature des e-mails d'automatisation : logo du gestionnaire (image inline
CID), nom du service (signature de la règle) et mention d'envoi automatique.

Le logo est lu depuis le fichier (`User.logo_path`) et embarqué en pièce inline,
ce qui le rend fiable dans tous les clients mail (pas de dépendance à une URL
publique ni au déblocage des images distantes)."""
import logging
import os
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Extensions image embarquables en e-mail (le SVG n'est pas rendu → ignoré).
_IMG_SUBTYPE = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "gif": "gif"}


def read_logo(logo_path: Optional[str]) -> Tuple[Optional[bytes], str]:
    """(octets, sous-type MIME) du logo, ou (None, 'png') si absent/non géré."""
    if not logo_path:
        return None, "png"
    try:
        ext = logo_path.rsplit(".", 1)[-1].lower()
        sub = _IMG_SUBTYPE.get(ext)
        if not sub or not os.path.exists(logo_path):
            return None, "png"
        with open(logo_path, "rb") as f:
            return f.read(), sub
    except Exception as exc:  # noqa: BLE001
        logger.warning("read_logo(%s) échec: %s", logo_path, exc)
        return None, "png"


async def build_for_manager(db: AsyncSession, manager_id, service_name: Optional[str]):
    """Renvoie (signature_html, logo_bytes, logo_subtype) pour un gestionnaire et
    un nom de service donné."""
    from app.models.user import User
    from app.services.email_service import build_signature_html, set_branding
    logo, sub = None, "png"
    theme = None
    if manager_id:
        u = await db.get(User, manager_id)
        logo, sub = read_logo(getattr(u, "logo_path", None))
        theme = getattr(u, "email_theme", None)
    # Apparence des e-mails du gestionnaire (thème choisi + logo si présent).
    set_branding(theme, logo=logo, logo_subtype=sub)
    return build_signature_html(service_name, has_logo=bool(logo)), logo, sub


async def build_for_lease(db: AsyncSession, lease_id, *rule_types: str):
    """Résout la règle active (parmi `rule_types`) du gestionnaire du bail pour en
    tirer la signature (service), puis renvoie (signature_html, logo_bytes, subtype)."""
    from app.models.lease import Lease
    from app.models.automation import AutomationRule
    manager_id = None
    service = None
    try:
        lease = await db.get(Lease, lease_id) if lease_id else None
        manager_id = getattr(lease, "created_by", None) if lease else None
        if manager_id and rule_types:
            row = (await db.execute(
                select(AutomationRule.signature).where(
                    AutomationRule.created_by == manager_id,
                    AutomationRule.rule_type.in_(list(rule_types)),
                    AutomationRule.is_active.is_(True),
                ).limit(1)
            )).first()
            service = row[0] if row else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("build_for_lease(%s) échec: %s", lease_id, exc)
    return await build_for_manager(db, manager_id, service)
