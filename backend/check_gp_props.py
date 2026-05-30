"""Vérifie les biens et logements du GP."""
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
        rows = (await db.execute(text("""
            SELECT p.id, p.name, p.address, p.created_by,
                   u.email as creator,
                   COUNT(un.id) as unit_count
            FROM properties p
            LEFT JOIN users u ON p.created_by = u.id
            LEFT JOIN units un ON un.property_id = p.id
            GROUP BY p.id, p.name, p.address, p.created_by, u.email
            ORDER BY u.email NULLS LAST, p.name
        """))).fetchall()
        print("=== Biens et logements ===")
        for r in rows:
            creator = r[4] or 'NULL'
            print(f"  {r[1]:30s} | {r[2][:30] if r[2] else '':30s} | créé par: {creator:35s} | {r[5]} logement(s)")

asyncio.run(run())
