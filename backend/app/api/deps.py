from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.core.permissions import Role, require_role

# ── Bearer token extractor ─────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency principale — retourne l'utilisateur courant authentifié."""
    return await AuthService.get_current_user(db, credentials.credentials)


async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — réservé aux administrateurs."""
    from fastapi import HTTPException, status
    checker = require_role(Role.ADMIN)
    return checker(current_user)


async def get_current_gestionnaire(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — gestionnaire ou supérieur."""
    checker = require_role(Role.GESTIONNAIRE)
    return checker(current_user)


async def get_current_comptable(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — comptable ou supérieur."""
    checker = require_role(Role.COMPTABLE)
    return checker(current_user)
