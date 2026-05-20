from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse
from app.schemas.user import UserMeResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenResponse, summary="Connexion utilisateur")
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authentifie un utilisateur et retourne une paire de tokens JWT.

    - **access_token** : valide 30 minutes — à envoyer dans le header `Authorization: Bearer <token>`
    - **refresh_token** : valide 7 jours — à utiliser sur `/auth/refresh` uniquement
    """
    user = await AuthService.authenticate(db, data.email, data.password)
    return AuthService.generate_tokens(user)


@router.post("/refresh", response_model=AccessTokenResponse, summary="Renouveler l'access token")
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Renouvelle un access token expiré à partir d'un refresh token valide."""
    new_access_token = await AuthService.refresh_access_token(db, data.refresh_token)
    return AccessTokenResponse(access_token=new_access_token)


@router.get("/me", response_model=UserMeResponse, summary="Profil de l'utilisateur connecté")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Retourne les informations de l'utilisateur actuellement authentifié."""
    return current_user
