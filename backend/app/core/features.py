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
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import Role
from app.database import get_db
from app.models.user import User
from app.services import alice_client

logger = logging.getLogger(__name__)

# Clés canoniques : dérivées du catalogue unique (app/core/feature_catalog.py).
from app.core.feature_catalog import FEATURE_KEYS  # noqa: F401  (réexport)

# Fonctionnalité « propriétaire » d'un type de règle d'automatisation. Sert à
# masquer/seeder les règles selon le plan : une règle n'est pertinente que si la
# fonctionnalité qu'elle sert est incluse. Les e-mails de candidature, eux,
# fonctionnent en repli sur leur modèle standard même sans le module Communication
# (cf. candidature_comm.resolve). rule_type absent ⇒ toujours autorisé.
RULE_TYPE_FEATURE = {
    "avis_echeance": "avis_echeances",
    "quittance": "quittances",
    "rappel_impaye": "payments",
    "relance_1": "payments",
    "relance_2": "payments",
    "revision_loyer": "actualisation",
    "revision_charges": "actualisation",
    "taxe_om": "actualisation",
    "rapport_mensuel": "finances",
    "candidature_accuse": "candidatures",
    "candidature_pieces": "candidatures",
    "candidature_visite": "candidatures",
    "candidature_relance_visite": "candidatures",
    "candidature_acceptation": "candidatures",
    "candidature_refus": "candidatures",
}


def rule_type_allowed(rule_type: str, feats) -> bool:
    """Vrai si le type de règle est pertinent pour le plan (feats=None ⇒ tout)."""
    if feats is None:
        return True
    feat = RULE_TYPE_FEATURE.get(rule_type)
    return feat is None or feat in feats


_MANAGER_ROLES = (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO)


def _profile_for_role(role: str | None) -> str | None:
    """Profil d'audience du rôle : "proprietaire", "mandataire", ou None (non géré)."""
    if role == Role.GESTIONNAIRE_PROPRIO.value:
        return "proprietaire"
    if role == Role.GESTIONNAIRE.value:
        return "mandataire"
    return None


def _features_for_role(lic: dict, role: str | None) -> list | None:
    """Liste EFFECTIVE de fonctionnalités du plan selon le profil du gestionnaire.

    Un plan porte deux listes (propriétaire / mandataire) ; on choisit selon le rôle
    (repli sur la liste commune/héritée `features`). L'`audience` du catalogue est
    AUTORITAIRE : la liste effective est toujours intersectée avec les fonctionnalités
    dont l'audience correspond au profil. Ainsi un gestionnaire propriétaire n'obtient
    JAMAIS une fonctionnalité réservée au mandataire (compta mandant, syndic, tampon),
    et inversement, quel que soit l'état du plan (repli legacy, plan « toutes »…).
    Cohérence garantie entre l'entitlement et ce qui est affiché.

    Rôle non gestionnaire (None) : pas de filtrage par profil (renvoie `features` tel
    quel) ; ces rôles ne sont de toute façon pas soumis au gating."""
    from app.core.feature_catalog import FEATURE_KEYS_ORDERED, allowed_keys_for_profile

    profile = _profile_for_role(role)
    if profile is None:
        return lic.get("features")

    # Liste accordée : spécifique au profil > commune/héritée > None (= toutes).
    granted = lic.get(f"features_{profile}")
    if granted is None:
        granted = lic.get("features")

    allowed = allowed_keys_for_profile(profile)
    if granted is None:
        # Plan « toutes les fonctionnalités » → toutes celles de l'audience du profil
        # (un GP « illimité » n'a toujours pas les fonctions mandataire-only).
        return [k for k in FEATURE_KEYS_ORDERED if k in allowed]
    # Intersection avec l'audience : retire toute fonctionnalité hors-profil.
    return [k for k in granted if k in allowed]


async def get_plan_features(db: AsyncSession, user_id: UUID) -> list[str] | None:
    """Fonctionnalités du plan du gestionnaire (via l'API Alice), résolues par profil.

    Retourne None s'il n'y a pas de plan/licence ou si la liste applicable n'est pas
    définie → interprété comme « toutes les fonctionnalités ». Fail-open si Alice est
    indisponible (le client renvoie None). Le profil (propriétaire / mandataire) est
    lu depuis le rôle du compte `user_id` : un plan expose une liste par profil."""
    lic = await alice_client.get_license(user_id)
    if not lic:
        return None
    role = await db.scalar(select(User.role).where(User.id == user_id))
    feats = _features_for_role(lic, role)
    return feats if isinstance(feats, list) else None


async def get_plan_name(db: AsyncSession, user_id: UUID) -> str | None:
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
