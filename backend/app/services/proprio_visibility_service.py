"""Calcul de la visibilité effective de l'espace propriétaire (lecture seule).

Effective = surcharge réglée sur la fiche du propriétaire, sinon toutes les
rubriques ; le tout ∩ plan du gestionnaire racine. (La visibilité se gère
uniquement par propriétaire, sur sa fiche : pas de défaut d'agence global.)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.features import get_plan_features
from app.core.proprio_sections import effective_keys
from app.models.user import User


async def agency_root_user(db: AsyncSession, user: User):
    """Compte gestionnaire racine de l'agence d'un propriétaire (porte le défaut + le plan)."""
    root_id = getattr(user, "agency_id", None) or getattr(user, "created_by", None)
    if not root_id or root_id == user.id:
        return None
    return await db.get(User, root_id)


async def effective_sections_for(db: AsyncSession, proprio_user: User) -> list:
    root = await agency_root_user(db, proprio_user)
    feats = await get_plan_features(db, root.id) if root else None
    # Pas de défaut d'agence : surcharge de la fiche, sinon toutes les rubriques du plan.
    return effective_keys(getattr(proprio_user, "proprio_visibility", None), None, feats)
