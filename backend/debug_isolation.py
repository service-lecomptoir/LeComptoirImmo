"""Debug : vérifie les données réelles pour l'isolation GP."""
import asyncio
import sys
sys.path.insert(0, '.')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

async def debug():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text

    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        print("=== USERS (gestionnaire_proprio) ===")
        rows = (await db.execute(text(
            "SELECT id, email, role FROM users WHERE role='gestionnaire_proprio'"
        ))).fetchall()
        for r in rows:
            print(f"  id={r[0]}  email={r[1]}")

        print("\n=== PROPERTIES ===")
        rows = (await db.execute(text(
            "SELECT id, name, owner_user_id, created_by FROM properties ORDER BY created_at DESC LIMIT 10"
        ))).fetchall()
        for r in rows:
            print(f"  name={r[1]!r:30s}  owner_user_id={r[2]}  created_by={r[3]}")

        print("\n=== TENANTS ===")
        rows = (await db.execute(text(
            "SELECT id, first_name, last_name, created_by FROM tenants ORDER BY created_at DESC LIMIT 10"
        ))).fetchall()
        for r in rows:
            print(f"  name={r[1]+' '+r[2]:25s}  created_by={r[3]}")

asyncio.run(debug())
