"""Chiffrement symétrique des secrets stockés en base (clés Stripe/SumUp).

Utilise Fernet (cryptography, déjà présent via python-jose[cryptography]). La clé
est dérivée du SECRET_KEY de l'application : aucun secret de paiement n'est lisible
en clair dans la base, même en cas de fuite du dump SQL.
"""
import base64
import hashlib
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    secret = (get_settings().SECRET_KEY or "").encode("utf-8")
    # Dérive une clé Fernet (32 octets, base64 url-safe) à partir du SECRET_KEY.
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    """Chiffre une valeur secrète. None/chaîne vide → None (pas de secret)."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(token: Optional[str]) -> Optional[str]:
    """Déchiffre une valeur. None ou jeton invalide → None (jamais d'exception)."""
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None
