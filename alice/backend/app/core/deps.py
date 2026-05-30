import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.core.security import decode_token
from app.models.admin import AliceAdmin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_alice_admin(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> AliceAdmin:
    """Vérifie le JWT et retourne l'admin Alice connecté."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou session expirée",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    # Vérifier que c'est bien un token Alice
    if payload.get("app") != "alice":
        raise credentials_exception

    admin_id_str: str | None = payload.get("sub")
    if not admin_id_str:
        raise credentials_exception

    try:
        admin_id = uuid.UUID(admin_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(AliceAdmin).where(AliceAdmin.id == admin_id))
    admin = result.scalar_one_or_none()

    if admin is None or not admin.is_active:
        raise credentials_exception

    return admin
