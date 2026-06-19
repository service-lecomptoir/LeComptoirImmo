"""Entitlements par plan tarifaire.

Le plan Alice porte une liste de fonctionnalités autorisées (`features`).
Alice ayant sa propre base, LeComptoir Immo interroge son API /internal
(via app.services.alice_client) : plus aucune lecture directe des tables alice_*.

Convention : `features = NULL` (ou plan/licence absent) ⇒ AUCUNE restriction
(toutes les fonctionnalités). Une liste explicite restreint aux clés présentes.
Les rôles non-gestionnaire (admin, propriétaire, locataire) ne sont jamais
restreints : l'abonnement concerne le compte gestionnaire.
"""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.core.permissions import Role
from app.models.user import User
from app.services import alice_client

logger = logging.getLogger(__name__)

# Clés canoniques : dérivées du catalogue unique (app/core/feature_catalog.py).
from app.core.feature_catalog import FEATURE_KEYS  # noqa: F401  (réexport)

_MANAGER_ROLES = (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO)


async def get_plan_features(db: AsyncSession, user_id: UUID) -> Optional[List[str]]:
    """Fonctionnalités du plan du gestionnaire (via l'API Alice).

    Retourne None s'il n'y a pas de plan/licence ou si `features` n'est pas défini
    → interprété comme « toutes les fonctionnalités ». Fail-open si Alice est
    indisponible (le client renvoie None). `db` conservé pour compat. de signature."""
    lic = await alice_client.get_license(user_id)
    if not lic:
        return None
    feats = lic.get("features")
    return feats if isinstance(feats, list) else None


async def get_plan_name(db: AsyncSession, user_id: UUID) -> Optional[str]:
    """Nom du plan tarifaire du gestionnaire (via l'API Alice)."""
    lic = await alice_client.get_license(user_id)
    return lic.get("plan_name") if lic else None


def require_feature(feature: str):
    """Dépendance FastAPI : 403 si le plan du gestionnaire n'inclut pas `feature`."""
    async def _dep(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        try:
            role = Role(current_user.role)
        except ValueError:
            return current_user
        if role not in _MANAGER_ROLES:
            return current_user
        feats = await get_plan_features(db, current_user.id)
        if feats is None or feature in feats:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fonctionnalité non incluse dans votre abonnement",
        )
    return _dep


def require_any_feature(*features: str):
    """Dépendance FastAPI : autorise si AU MOINS UNE des fonctionnalités est incluse.

    Utile quand plusieurs fonctionnalités partagent le même endpoint (ex. la donnée
    finances/performance/liasse provient d'un seul endpoint propriétaire)."""
    async def _dep(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        try:
            role = Role(current_user.role)
        except ValueError:
            return current_user
        if role not in _MANAGER_ROLES:
            return current_user
        feats = await get_plan_features(db, current_user.id)
        if feats is None or any(f in feats for f in features):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fonctionnalité non incluse dans votre abonnement",
        )
    return _dep
