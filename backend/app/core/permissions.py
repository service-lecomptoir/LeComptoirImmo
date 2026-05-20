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
    LECTURE = "lecture"
    COMPTABLE = "comptable"
    GESTIONNAIRE = "gestionnaire"
    ADMIN = "admin"


# Hiérarchie : chaque rôle inclut les permissions des rôles inférieurs
ROLE_HIERARCHY: dict[Role, Set[Role]] = {
    Role.LECTURE:      {Role.LECTURE},
    Role.COMPTABLE:    {Role.LECTURE, Role.COMPTABLE},
    Role.GESTIONNAIRE: {Role.LECTURE, Role.COMPTABLE, Role.GESTIONNAIRE},
    Role.ADMIN:        {Role.LECTURE, Role.COMPTABLE, Role.GESTIONNAIRE, Role.ADMIN},
}


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
