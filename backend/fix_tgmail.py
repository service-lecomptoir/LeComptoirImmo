"""Marque t@gmail.com comme créé par gestionnaire-proprio@cabinet.fr."""
import asyncio, sys
sys.path.insert(0, '.')
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=',1)[1].strip().strip('"').strip("'")
            break

GP_ID = '42a92e89-0b2f-4bf8-86fc-01101cdfa9cc'  # gestionnaire-proprio@cabinet.fr

async def run():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        result = await db.execute(text(
            f"UPDATE users SET created_by='{GP_ID}' WHERE email='t@gmail.com'"
        ))
        await db.commit()
        print(f"Rows updated: {result.rowcount}")

        # Verification
        rows = (await db.execute(text(
            "SELECT u.email, u.role, c.email as creator FROM users u "
            "LEFT JOIN users c ON u.created_by=c.id "
            "WHERE u.role IN ('locataire','proprietaire') ORDER BY u.email"
        ))).fetchall()
        print("\n=== Users locataire/proprietaire avec leur createur ===")
        for r in rows:
            print(f"  {r[0]:35s} [{r[1]}] cree par: {r[2] or 'NULL (admin/system)'}")

asyncio.run(run())
