from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role, role_has_permission
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# ── Bearer token extractor ─────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency principale — retourne l'utilisateur courant authentifié."""
    return await AuthService.get_current_user(db, credentials.credentials)


def require_role(required_role: Role):
    """
    Crée une dependency FastAPI qui vérifie le rôle de l'utilisateur connecté.
    Usage: current_user: User = Depends(require_role(Role.GESTIONNAIRE))
    """

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if not role_has_permission(Role(current_user.role), required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission insuffisante. Rôle requis : {required_role.value}",
            )
        return current_user

    return _checker


async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — administrateurs et gestionnaires (rôles de gestion)."""
    role = Role(current_user.role)
    if role not in (Role.ADMIN, Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Réservé aux gestionnaires et administrateurs",
        )
    return current_user


async def get_current_gestionnaire(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — gestionnaire ou supérieur."""
    if not role_has_permission(Role(current_user.role), Role.GESTIONNAIRE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux gestionnaires"
        )
    return current_user


async def get_manager_or_owner(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — gestionnaire (ou supérieur) OU propriétaire. Pour les vues en
    LECTURE seule accessibles au bailleur sur SON propre périmètre (mise en
    location). L'isolation par bien est appliquée dans chaque endpoint ; les
    écritures restent réservées aux gestionnaires."""
    role = Role(current_user.role)
    if role == Role.PROPRIETAIRE or role_has_permission(role, Role.GESTIONNAIRE):
        return current_user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


async def get_current_comptable(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — comptable ou supérieur."""
    if not role_has_permission(Role(current_user.role), Role.COMPTABLE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux comptables")
    return current_user
