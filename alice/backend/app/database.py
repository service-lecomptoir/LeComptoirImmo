from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func, TIMESTAMP
from datetime import datetime, timezone
import uuid


def _utcnow() -> datetime:
    """Horodatage UTC tz-aware, calculé côté Python."""
    return datetime.now(timezone.utc)

from app.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base declarative ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    # eager_defaults : récupère les valeurs server_default / server_onupdate
    # immédiatement (RETURNING sur PostgreSQL) lors de l'INSERT/UPDATE, au lieu de
    # les expirer. Évite tout lazy-load post-flush hors contexte async
    # (MissingGreenlet) lors de la sérialisation Pydantic — pour TOUS les modèles.
    __mapper_args__ = {"eager_defaults": True}


class TimestampMixin:
    """Ajoute created_at et updated_at aux modèles qui en héritent.

    Les valeurs sont calculées côté Python (default/onupdate) ET côté serveur
    (server_default) : le Python évite que SQLAlchemy expire l'attribut après un
    flush (ce qui déclenchait un lazy-load hors contexte async -> MissingGreenlet
    lors de la sérialisation Pydantic) ; le server_default reste un filet de
    sécurité pour les insertions hors ORM (migrations, SQL brut).
    """
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
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
