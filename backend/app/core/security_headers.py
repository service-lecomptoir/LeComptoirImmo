"""Middleware ASGI ajoutant les en-têtes de sécurité HTTP à toutes les réponses.

Léger (ASGI pur, sans BaseHTTPMiddleware). Couvre l'API JSON et les fichiers
servis sous /uploads. Les en-têtes côté navigateur (SPA) sont en plus posés par
le reverse-proxy edge ; ceci est une défense en profondeur côté application.
"""
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Politique appliquée à toutes les réponses.
_BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
# HSTS : uniquement en production (servie en HTTPS derrière l'edge).
_HSTS = "max-age=63072000; includeSubDomains"


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, production: bool = False) -> None:
        self.app = app
        self.production = production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in _BASE_HEADERS.items():
                    headers.setdefault(key, value)
                if self.production:
                    headers.setdefault("Strict-Transport-Security", _HSTS)
            await send(message)

        await self.app(scope, receive, send_wrapper)
