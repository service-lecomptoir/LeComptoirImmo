"""Limitation de débit (anti brute-force) sur les endpoints sensibles.

Basé sur slowapi. La clé est l'IP client réelle (1er maillon de X-Forwarded-For
posé par l'edge nginx), avec repli sur l'adresse de pair. Activé uniquement en
production : en dev/test, la limite est désactivée pour ne pas gêner la suite de
tests ni le développement.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import get_settings


def client_ip(request: Request) -> str:
    """IP client réelle derrière le reverse-proxy (X-Forwarded-For, 1er maillon)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_ip,
    enabled=get_settings().is_production,
    headers_enabled=True,
)
