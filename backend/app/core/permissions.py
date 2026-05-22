"""
RBAC — Role Based Access Control
=================================
Rôles disponibles (hiérarchie croissante) :
  lecture      → consultation uniquement
  comptable    → lecture + données financières en écriture
  gestionnaire → lecture + toutes les données métier en écriture
  admin        → accès total, gestion des utilisateurs
"""

from enum import Enum
from typing import Set
from fastapi import HTTPException, status


class Role(str, Enum):
    ADMIN = "admin"
    GESTIONNAIRE = "gestionnaire"
    PROPRIETAIRE = "proprietaire"
    LOCATAIRE = "locataire"
    # Legacy (gardés pour compatibilité DB, non utilisés dans la nouvelle archi)
    LECTURE = "lecture"
    COMPTABLE = "comptable"


# Hiérarchie : admin et gestionnaire ont accès à tout en gestion
# propriétaire et locataire ont accès limité à leurs propres données
ROLE_HIERARCHY: dict[Role, Set[Role]] = {
    Role.ADMIN:        {Role.ADMIN, Role.GESTIONNAIRE, Role.PROPRIETAIRE, Role.LOCATAIRE,
                        Role.LECTURE, Role.COMPTABLE},
    Role.GESTIONNAIRE: {Role.GESTIONNAIRE, Role.PROPRIETAIRE, Role.LOCATAIRE,
                        Role.LECTURE, Role.COMPTABLE},
    Role.PROPRIETAIRE: {Role.PROPRIETAIRE, Role.LECTURE},
    Role.LOCATAIRE:    {Role.LOCATAIRE},
    Role.LECTURE:      {Role.LECTURE},
    Role.COMPTABLE:    {Role.LECTURE, Role.COMPTABLE},
}

def is_manager(role: "Role") -> bool:
    """Retourne True si le rôle a accès au panneau de gestion complet."""
    return role in (Role.ADMIN, Role.GESTIONNAIRE)

def is_owner_or_manager(role: "Role") -> bool:
    """Retourne True si le rôle peut voir des biens immobiliers."""
    return role in (Role.ADMIN, Role.GESTIONNAIRE, Role.PROPRIETAIRE)


def role_has_permission(user_role: Role, required_role: Role) -> bool:
    """Vérifie si un rôle utilisateur satisfait le rôle requis."""
    return required_role in ROLE_HIERARCHY.get(user_role, set())


def require_role(required_role: Role):
    """
    Dependency FastAPI — vérifie que l'utilisateur courant a le rôle requis.

    Usage:
        @router.get("/", dependencies=[Depends(require_role(Role.GESTIONNAIRE))])
    """
    def _checker(current_user):
        user_role = Role(current_user.role)
        if not role_has_permission(user_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission insuffisante. Rôle requis : {required_role.value}",
            )
        return current_user
    return _checker
