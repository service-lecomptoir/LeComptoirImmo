"""Marque les users proprietaire/locataire sans created_by comme créés par le gestionnaire mandataire."""
import asyncio, sys
sys.path.insert(0, '.')
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=',1)[1].strip().strip('"').strip("'")
            break

async def run():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        # Récupérer l'ID du mandataire
        row = (await db.execute(text(
            "SELECT id, email FROM users WHERE email='gestionnaire@cabinet.fr'"
        ))).fetchone()
        if not row:
            print("ERREUR: gestionnaire@cabinet.fr introuvable")
            return
        mandataire_id, mandataire_email = row
        print(f"Mandataire: {mandataire_email} ({mandataire_id})")

        # Afficher les users concernés
        rows = (await db.execute(text(
            "SELECT id, email, role FROM users "
            "WHERE created_by IS NULL AND role IN ('proprietaire','locataire')"
        ))).fetchall()
        print(f"\nUsers à backfiller ({len(rows)}):")
        for r in rows:
            print(f"  [{r[2]:15s}] {r[1]}")

        # Backfill
        result = await db.execute(text(
            f"UPDATE users SET created_by='{mandataire_id}' "
            "WHERE created_by IS NULL AND role IN ('proprietaire','locataire')"
        ))
        await db.commit()
        print(f"\nRows updated: {result.rowcount}")

        # Vérification finale
        rows2 = (await db.execute(text(
            "SELECT u.email, u.role, c.email as creator FROM users u "
            "LEFT JOIN users c ON u.created_by=c.id "
            "WHERE u.role IN ('proprietaire','locataire') ORDER BY u.role, u.email"
        ))).fetchall()
        print("\n=== Etat final proprietaire/locataire ===")
        for r in rows2:
            print(f"  [{r[1]:15s}] {r[0]:35s} cree par: {r[2] or 'NULL'}")

asyncio.run(run())
