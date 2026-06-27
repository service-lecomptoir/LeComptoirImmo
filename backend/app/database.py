from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Vérifie la connexion avant utilisation
    pool_recycle=3600,  # Recycle les connexions après 1h
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base declarative avec champs communs ──────────────────────────────────────
class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Ajoute created_at et updated_at à tous les modèles qui en héritent."""

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── Dependency FastAPI ────────────────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """Fournit une session DB à chaque requête, fermée proprement après."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Audit exhaustif (db.create/update/delete) : l'import enregistre les écouteurs
# SQLAlchemy sur la classe Session → actif partout (app ET tests), dès que la
# couche base de données est chargée. (Import en fin de fichier : pas de cycle,
# audit_listeners n'importe les modèles qu'à l'exécution.)
from app.core import audit_listeners as _audit_listeners  # noqa: E402,F401

