from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text as sa_text
import logging

from app.models.user import User
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.exceptions import UnauthorizedException
from app.schemas.auth import TokenResponse

logger = logging.getLogger(__name__)

_MANAGED_ROLES = {"gestionnaire", "gestionnaire_proprio"}


class AuthService:

    @staticmethod
    async def _check_proxygen_license(db: AsyncSession, user: User) -> None:
        """Vérifie que la licence ProxyGen n'est pas bloquée pour les gestionnaires."""
        if user.role not in _MANAGED_ROLES:
            return
        try:
            row = (await db.execute(
                sa_text("SELECT is_blocked FROM proxygen_licenses WHERE gestionnaire_user_id = :uid")
                .bindparams(uid=user.id)
            )).fetchone()
            if row is None:
                logger.warning(f"Aucune licence ProxyGen pour user {user.id} ({user.email})")
                return  # pas de licence → on laisse passer (voir task #8 pour la limite biens)
            if row[0]:  # is_blocked = True
                raise UnauthorizedException("Votre compte a été suspendu. Contactez l'administrateur.")
        except UnauthorizedException:
            raise
        except Exception as exc:
            logger.warning(f"ProxyGen license check failed for {user.id}: {exc}")

    @staticmethod
    async def authenticate(
        db: AsyncSession, email: str, password: str
    ) -> User:
        """Vérifie les identifiants et retourne l'utilisateur si valide."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Email ou mot de passe incorrect")
        if not user.is_active:
            raise UnauthorizedException("Compte désactivé. Contactez un administrateur.")
        await AuthService._check_proxygen_license(db, user)
        return user

    @staticmethod
    def generate_tokens(user: User) -> TokenResponse:
        """Génère une paire access + refresh token pour un utilisateur."""
        extra = {"role": user.role, "name": user.full_name}
        access_token = create_access_token(subject=str(user.id), extra_claims=extra)
        refresh_token = create_refresh_token(subject=str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession, refresh_token: str
    ) -> str:
        """Valide le refresh token et retourne un nouvel access token."""
        payload = decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedException("Refresh token invalide ou expiré")

        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedException("Utilisateur introuvable ou inactif")
        await AuthService._check_proxygen_license(db, user)

        extra = {"role": user.role, "name": user.full_name}
        return create_access_token(subject=str(user.id), extra_claims=extra)

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> User:
        """Valide l'access token et retourne l'utilisateur courant."""
        payload = decode_token(token)

        if not payload or payload.get("type") != "access":
            raise UnauthorizedException("Token invalide ou expiré")

        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Token malformé")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException("Utilisateur introuvable")
        if not user.is_active:
            raise UnauthorizedException("Compte désactivé")
        await AuthService._check_proxygen_license(db, user)

        return user
