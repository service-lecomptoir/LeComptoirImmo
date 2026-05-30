"""Surveille les nouvelles propriétés en temps réel."""
import asyncio, sys
sys.path.insert(0, '.')
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=',1)[1].strip().strip('"').strip("'")
            break

USERS = {
    'e7266d06-5794-4cac-a3d9-09b37cb3cf60': 'gestionnaire@cabinet.fr (MANDATAIRE)',
    '42a92e89-0b2f-4bf8-86fc-01101cdfa9cc': 'gestionnaire-proprio@cabinet.fr (GP)',
    'ec44733a-61b8-4c5f-97cd-0e75c02fba8e': 'residence.tatie@outlook.com (GP)',
    '1eec44a1-df1d-4c87-91d9-fc24ccb861a9': 'proprietaire@email.fr',
}

async def run():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        print("=== PROPRIETES (toutes) ===")
        rows = (await db.execute(text(
            "SELECT id, name, created_by, created_at FROM properties ORDER BY created_at DESC"
        ))).fetchall()
        for r in rows:
            creator = USERS.get(str(r[2]), f'inconnu ({r[2]})')
            print(f"  [{r[3].strftime('%d/%m %H:%M')}] {r[1]:30s} cree par: {creator}")

        print("\n=== LOCATAIRES (tous) ===")
        rows = (await db.execute(text(
            "SELECT id, first_name, last_name, created_by, created_at FROM tenants ORDER BY created_at DESC"
        ))).fetchall()
        for r in rows:
            creator = USERS.get(str(r[3]), f'inconnu ({r[3]})')
            print(f"  [{r[4].strftime('%d/%m %H:%M')}] {r[1]+' '+r[2]:25s} cree par: {creator}")

asyncio.run(run())
