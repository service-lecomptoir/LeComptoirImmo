from contextlib import asynccontextmanager
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings
from app.database import engine, Base, AsyncSessionLocal
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)
settings = get_settings()

_executor = ThreadPoolExecutor(max_workers=1)


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage et nettoyage à l'arrêt."""
    logger.info(f"Démarrage de {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Vérifie la connexion DB
    from sqlalchemy import text
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("PostgreSQL OK")

    # Crée les tables Alice si elles n'existent pas (idempotent)
    # Note : cela n'affecte pas les tables LeCI existantes
    import app.models  # noqa — charge tous les modèles Alice
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables Alice verifiees / creees")

    # Migrations légères : colonnes ajoutées après coup (idempotent)
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE alice_licenses ADD COLUMN IF NOT EXISTS phone VARCHAR(30)"))
            await conn.execute(text("ALTER TABLE alice_licenses ADD COLUMN IF NOT EXISTS address TEXT"))
            await conn.execute(text("ALTER TABLE alice_licenses ADD COLUMN IF NOT EXISTS access_until TIMESTAMP"))
            await conn.execute(text("ALTER TABLE alice_plans ADD COLUMN IF NOT EXISTS features JSONB"))
        logger.info("Migrations colonnes Alice appliquees")
    except Exception as exc:
        logger.warning("Migration colonnes Alice ignoree : %s", exc)

    # Seed superadmin si absent
    await _seed_superadmin()

    # Seed plans par défaut
    await _seed_default_plans()

    logger.info("Alice pret")
    yield

    _executor.shutdown(wait=False)
    await engine.dispose()
    logger.info("Arret de Alice")


async def _seed_superadmin() -> None:
    """Crée le superadmin Alice si aucun admin n'existe."""
    from sqlalchemy import select
    from app.models.admin import AliceAdmin
    from app.core.security import hash_password, verify_password
    import uuid

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AliceAdmin).where(AliceAdmin.email == settings.FIRST_ADMIN_EMAIL))
        existing = result.scalar_one_or_none()

        if existing is None:
            loop = asyncio.get_event_loop()
            hashed = await loop.run_in_executor(_executor, hash_password, settings.FIRST_ADMIN_PASSWORD)
            admin = AliceAdmin(
                id=uuid.uuid4(),
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=hashed,
                full_name=settings.FIRST_ADMIN_NAME,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            logger.info(f"Superadmin cree : {settings.FIRST_ADMIN_EMAIL}")
        else:
            logger.info(f"Superadmin existant : {settings.FIRST_ADMIN_EMAIL}")


async def _seed_default_plans() -> None:
    """Crée les 3 plans par défaut si aucun plan n'existe."""
    from sqlalchemy import select
    from app.models.plan import AlicePlan
    import uuid

    default_plans = [
        {"name": "Starter", "description": "Pour les petits portefeuilles", "property_limit": 3, "monthly_price": 15.00},
        {"name": "Junior", "description": "Pour les portefeuilles en croissance", "property_limit": 6, "monthly_price": 30.00},
        {"name": "Intermédiaire", "description": "Pour les gestionnaires confirmés", "property_limit": 12, "monthly_price": 60.00},
        {"name": "VIP", "description": "Sans limite, support prioritaire", "property_limit": None, "monthly_price": 199.90},
    ]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AlicePlan))
        existing = result.scalars().all()

        if not existing:
            for plan_data in default_plans:
                plan = AlicePlan(id=uuid.uuid4(), **plan_data)
                db.add(plan)
            await db.commit()
            logger.info("Plans par defaut crees : Starter, Junior, Intermédiaire, VIP")
        else:
            logger.info(f"{len(existing)} plan(s) existant(s)")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Alice — Plateforme d'administration SaaS pour LeComptoirImmo",
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

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de vérification de santé."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
