from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role, role_has_permission
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# ── Bearer token extractor ─────────────────────────────────────────────────────
# auto_error=False : on gère nous-mêmes l'absence de jeton pour renvoyer un 401
# (et non le 403 par défaut de HTTPBearer) — cohérent avec Alice/Séjour : « non
# authentifié » = 401, « authentifié mais sans droit » = 403.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency principale — retourne l'utilisateur courant authentifié."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await AuthService.get_current_user(db, credentials.credentials)
    # Acteur courant pour l'audit exhaustif (db.*) des écritures de cette requête.
    try:
        from app.core.audit_context import update_actor

        update_actor(user_id=user.id, user_email=user.email)
    except Exception:  # noqa: BLE001
        pass
    return user


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


# Personnel d'agence autorisé en LECTURE sur les écrans de gestion. Inclut le
# COMPTABLE (sous-compte en lecture seule) SANS élargir aux propriétaires/locataires
# : remplace get_current_gestionnaire sur les endpoints GET de gestion. Les
# écritures restent protégées par get_current_gestionnaire (le comptable est exclu).
_MANAGER_READ_ROLES = (Role.ADMIN, Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO, Role.COMPTABLE)


async def get_current_manager(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency LECTURE pour les écrans de gestion (gestionnaire/admin/comptable)."""
    if Role(current_user.role) not in _MANAGER_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Réservé au personnel de gestion"
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


def require_proprio_section(section: str):
    """Dépendance : 403 si un BAILLEUR (rôle propriétaire) accède à une rubrique
    que son gestionnaire ne lui a pas ouverte. Sans effet pour les autres rôles
    (gestionnaire/admin) : l'isolation par bien reste gérée dans chaque endpoint.

    Le périmètre visible est calculé par `effective_sections_for` (surcharge du
    compte ∩ défaut d'agence ∩ plan) : même source que le menu, donc cohérent."""

    async def _dep(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if Role(current_user.role) == Role.PROPRIETAIRE:
            from app.services.proprio_visibility_service import effective_sections_for

            allowed = await effective_sections_for(db, current_user)
            if section not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cette rubrique n'est pas disponible dans votre espace.",
                )
        return current_user

    return _dep


async def get_current_comptable(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency — comptable ou supérieur."""
    if not role_has_permission(Role(current_user.role), Role.COMPTABLE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux comptables")
    return current_user


# ── Comptable : LECTURE seule globale, sauf encaissement / avis / quittances ─────
# Le comptable a le MÊME périmètre de lecture que son gestionnaire (hiérarchie de
# rôles). Ce garde global, monté sur /api/v1, bloque ses ÉCRITURES partout sauf :
# encaissement (record/validate/refuse), avis d'échéance, quittances, et son propre
# compte. Les lectures et les autres rôles ne sont pas affectés.
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _comptable_write_allowed(path: str) -> bool:
    if path.startswith("/api/v1/auth/"):
        return True  # self-service : profil, mot de passe, logo, session
    if path.startswith("/api/v1/avis-echeances"):
        return True  # avis d'échéance : génération / envoi / acquittement
    if path.startswith("/api/v1/payments/"):
        return (
            path.endswith("/record")
            or path.endswith("/validate-declaration")
            or path.endswith("/refuse-declaration")
            or "/quittance" in path
        )
    return False


async def enforce_comptable_readonly(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> None:
    if request.method not in _WRITE_METHODS or credentials is None:
        return
    try:
        user = await AuthService.get_current_user(db, credentials.credentials)
    except Exception:
        return  # jeton invalide / absent : laissé aux dépendances de l'endpoint
    if Role(user.role) == Role.COMPTABLE and not _comptable_write_allowed(request.url.path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comptable : lecture seule (encaissement, avis d'échéance et quittances uniquement).",
        )
