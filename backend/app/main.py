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

    # Crée les comptes de démonstration s'ils sont absents
    logger.info("Vérification des comptes par défaut...")
    await _seed_default_users()

    # Démarre le scheduler de tâches automatiques
    logger.info("Démarrage du scheduler...")
    start_scheduler()

    logger.info("Application prête ✓")
    yield

    stop_scheduler()
    logger.info("Arrêt de l'application")
    await engine.dispose()


async def _seed_default_users() -> None:
    """Crée ou resynchronise les mots de passe des comptes de démonstration."""
    from sqlalchemy import select
    from app.models.user import User
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate
    from app.core.security import hash_password, verify_password
    from app.core.permissions import Role

    default_users = [
        UserCreate(
            email=settings.FIRST_ADMIN_EMAIL,
            password=settings.FIRST_ADMIN_PASSWORD,
            full_name=settings.FIRST_ADMIN_NAME,
            role=Role.ADMIN,
        ),
        UserCreate(
            email="gestionnaire@cabinet.fr",
            password="Gestionnaire1!",
            full_name="Gestionnaire Demo",
            role=Role.GESTIONNAIRE,
        ),
        UserCreate(
            email="proprietaire@email.fr",
            password="Proprietaire1!",
            full_name="Propriétaire Demo",
            role=Role.PROPRIETAIRE,
        ),
        UserCreate(
            email="locataire@email.fr",
            password="Locataire1!",
            full_name="Locataire Demo",
            role=Role.LOCATAIRE,
        ),
    ]

    async with AsyncSessionLocal() as db:
        created, updated = [], []
        for user_data in default_users:
            result = await db.execute(select(User).where(User.email == user_data.email))
            existing = result.scalar_one_or_none()
            if existing is None:
                await UserService.create(db, user_data)
                created.append(user_data.email)
            elif not verify_password(user_data.password, existing.hashed_password):
                existing.hashed_password = hash_password(user_data.password)
                updated.append(user_data.email)
        await db.commit()
        for email in created:
            logger.info(f"Compte créé : {email}")
        for email in updated:
            logger.info(f"Mot de passe resynchronisé : {email}")


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
