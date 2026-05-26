"""Bootstrap idempotent du schéma + seeds, exécuté une seule fois avant uvicorn.

Remplace `alembic upgrade head` en production : l'application est conçue pour
créer son schéma via SQLAlchemy `create_all` (checkfirst → idempotent), ce qui
évite les bugs de la chaîne de migrations Alembic et les races entre workers.
"""
import asyncio

import app.models  # noqa: F401 — enregistre tous les modèles sur Base.metadata
from app.database import engine, Base
from app.main import _apply_column_migrations, _seed_default_users


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _apply_column_migrations()
    await _seed_default_users()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
