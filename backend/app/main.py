from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.api.v1.router import api_router
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage et nettoyage à l'arrêt."""
    logger.info(f"Démarrage de {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Vérifie la connexion DB (ping)
    logger.info("Vérification de la connexion PostgreSQL...")
    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL OK")

    # Crée le premier admin si la BDD est vide
    logger.info("Vérification compte admin...")
    await _create_first_admin()

    # Démarre le scheduler de tâches automatiques
    logger.info("Démarrage du scheduler...")
    start_scheduler()

    logger.info("Application prête ✓")
    yield

    stop_scheduler()
    logger.info("Arrêt de l'application")
    await engine.dispose()


async def _create_first_admin() -> None:
    """Crée un compte admin par défaut si aucun utilisateur n'existe."""
    from sqlalchemy import select
    from app.models.user import User
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate
    from app.core.permissions import Role

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        if result.first() is not None:
            return  # Des utilisateurs existent déjà

        logger.info("Création du compte administrateur par défaut...")
        user_data = UserCreate(
            email=settings.FIRST_ADMIN_EMAIL,
            password=settings.FIRST_ADMIN_PASSWORD,
            full_name=settings.FIRST_ADMIN_NAME,
            role=Role.ADMIN,
        )
        await UserService.create(db, user_data)
        await db.commit()
        logger.info(f"Admin créé : {settings.FIRST_ADMIN_EMAIL}")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API de gestion locative — LeComptoirImmo",
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middlewares ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de vérification de santé — utilisé par Docker et le load balancer."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
