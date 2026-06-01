"""Entitlements par plan tarifaire.

Le plan Alice porte une liste de fonctionnalités autorisées (`alice_plans.features`).
Comme Alice partage la MÊME base Postgres, LeComptoir Immo lit ces données
directement (pas d'appel HTTP) pour appliquer le blocage côté serveur.

Convention : `features = NULL` (ou plan/licence absent) ⇒ AUCUNE restriction
(toutes les fonctionnalités). Une liste explicite restreint aux clés présentes.
Les rôles non-gestionnaire (admin, propriétaire, locataire) ne sont jamais
restreints — l'abonnement concerne le compte gestionnaire.
"""
import logging
from typing import Optional, List
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.core.permissions import Role
from app.models.user import User

logger = logging.getLogger(__name__)

# Clés canoniques (miroir de alice/frontend/src/constants/features.ts).
FEATURE_KEYS = {
    "dashboard", "properties", "tenants", "leases", "avis_echeances", "payments",
    "quittances", "actualisation", "automatisation", "templates", "incidents",
    "entretiens", "contacts", "offres", "documents_caf", "admin", "finances",
    "performance_biens", "liasse_fiscale",
}

_MANAGER_ROLES = (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO)


async def get_plan_features(db: AsyncSession, user_id: UUID) -> Optional[List[str]]:
    """Fonctionnalités du plan du gestionnaire (lecture directe des tables Alice).

    Retourne None s'il n'y a pas de plan, pas de licence, ou si `features` n'est
    pas défini → interprété comme « toutes les fonctionnalités ». Fail-open en cas
    d'erreur (on ne casse pas l'app si les tables Alice sont indisponibles)."""
    try:
        row = (await db.execute(
            text(
                "SELECT p.features FROM alice_licenses l "
                "JOIN alice_plans p ON p.id = l.plan_id "
                "WHERE l.gestionnaire_user_id = :uid"
            ).bindparams(uid=user_id)
        )).fetchone()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lecture des features du plan échouée pour %s : %s", user_id, exc)
        return None
    if not row or row[0] is None:
        return None
    feats = row[0]
    return feats if isinstance(feats, list) else None


async def get_plan_name(db: AsyncSession, user_id: UUID) -> Optional[str]:
    """Nom du plan tarifaire du gestionnaire (lecture directe des tables Alice)."""
    try:
        row = (await db.execute(
            text(
                "SELECT p.name FROM alice_licenses l "
                "JOIN alice_plans p ON p.id = l.plan_id "
                "WHERE l.gestionnaire_user_id = :uid"
            ).bindparams(uid=user_id)
        )).fetchone()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Lecture du nom de plan échouée pour %s : %s", user_id, exc)
        return None
    return row[0] if row else None


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
