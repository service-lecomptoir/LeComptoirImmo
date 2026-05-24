from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import JWTError, jwt
import bcrypt

from app.config import get_settings

settings = get_settings()


# ── Password hashing (bcrypt direct) ─────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(subject: Any, extra_claims: dict | None = None) -> str:
    """Crée un JWT d'accès pour un admin ProxyGen."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
        "app": "proxygen",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Décode et valide un token JWT. Retourne None si invalide."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
