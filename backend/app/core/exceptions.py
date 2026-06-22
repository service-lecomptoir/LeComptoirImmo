import logging
import uuid

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

# Journal dédié aux erreurs serveur (routé vers immo-error.log, supervisé par Portail360).
logger = logging.getLogger("app.errors")


# ── Exceptions métier ─────────────────────────────────────────────────────────
class AppException(HTTPException):
    """Base pour toutes les exceptions métier de l'application."""

    pass


class NotFoundException(AppException):
    def __init__(self, resource: str, resource_id: str | None = None):
        detail = f"{resource} introuvable"
        if resource_id:
            detail = f"{resource} '{resource_id}' introuvable"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BadRequestException(AppException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Authentification requise"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Accès refusé"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# ── Handlers globaux ──────────────────────────────────────────────────────────
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Référence courte partagée entre l'écran utilisateur et le journal d'erreurs,
    # pour retrouver l'incident côté supervision (Portail360).
    incident_id = uuid.uuid4().hex[:8]
    logger.exception("Erreur non gérée [%s] %s %s", incident_id, request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": (
                "Le service a rencontré un problème temporaire. Réessayez dans un "
                f"instant. Si le problème persiste, contactez le support (réf. {incident_id})."
            ),
            "status_code": 500,
            "incident_id": incident_id,
        },
    )
