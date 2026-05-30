from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.database import get_db
from app.models.admin import AliceAdmin
from app.schemas.auth import LoginRequest, TokenResponse, AdminOut
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_alice_admin

router = APIRouter(prefix="/auth", tags=["Auth"])

_executor = ThreadPoolExecutor(max_workers=2)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authentification admin Alice."""
    result = await db.execute(
        select(AliceAdmin).where(AliceAdmin.email == request.email)
    )
    admin = result.scalar_one_or_none()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    # bcrypt est synchrone — exécuter dans un thread
    loop = asyncio.get_event_loop()
    pwd_ok = await loop.run_in_executor(
        _executor, verify_password, request.password, admin.hashed_password
    )

    if not pwd_ok or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    token = create_access_token(str(admin.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AdminOut)
async def me(
    current_admin: AliceAdmin = Depends(get_current_alice_admin),
):
    """Retourne le profil de l'admin connecté."""
    return current_admin
