"""Job de rétention RGPD — anonymise les données dont la durée de conservation
est dépassée (locataires partis, candidatures refusées anciennes).

Lancé par Portail360 (batch « Rétention RGPD ») :
    docker exec locataire_backend python rgpd_retention.py
Aperçu sans rien modifier :
    docker exec locataire_backend python rgpd_retention.py --dry-run
"""
import asyncio
import sys

from app.database import AsyncSessionLocal
from app.services import rgpd_service, audit_service


async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    async with AsyncSessionLocal() as db:
        result = await rgpd_service.apply_retention(db, dry_run=dry_run)
        if not dry_run:
            await audit_service.log(
                db, action="rgpd.retention", details=result,
            )
            await db.commit()
        print("Rétention RGPD :", result)


if __name__ == "__main__":
    asyncio.run(main())
