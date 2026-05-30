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
}

async def run():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        # Voir la structure de la table users
        print("=== COLONNES de la table users ===")
        cols = (await db.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"
        ))).fetchall()
        for c in cols:
            print(f"  {c[0]}")

        print("\n=== TOUS LES USERS (avec created_by si existe) ===")
        try:
            rows = (await db.execute(text(
                "SELECT id, email, role, created_by FROM users ORDER BY created_at DESC"
            ))).fetchall()
            for r in rows:
                creator = USERS.get(str(r[3]), f'inconnu ({r[3]})')
                print(f"  [{r[2]:25s}] {r[1]:40s} created_by={creator}")
        except Exception as e:
            print(f"  Pas de colonne created_by: {e}")
            rows = (await db.execute(text(
                "SELECT id, email, role FROM users ORDER BY created_at DESC"
            ))).fetchall()
            for r in rows:
                print(f"  [{r[2]:25s}] {r[1]}")

        print("\n=== TENANTS (avec user_id et created_by) ===")
        rows = (await db.execute(text(
            "SELECT id, first_name, last_name, user_id, created_by FROM tenants ORDER BY created_at DESC"
        ))).fetchall()
        for r in rows:
            creator = USERS.get(str(r[4]), f'inconnu ({r[4]})')
            linked_user = str(r[3]) if r[3] else 'NULL'
            print(f"  {r[1]+' '+r[2]:25s} user_id={linked_user}  created_by={creator}")

asyncio.run(run())
