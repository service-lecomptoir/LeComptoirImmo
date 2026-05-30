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
        print("=== USERS ===")
        for r in (await db.execute(text("SELECT id, email, role FROM users ORDER BY role"))).fetchall():
            print(f"  [{r[2]:25s}] {r[1]:40s} id={r[0]}")

        print("\n=== PROPERTIES (created_by, owner_user_id) ===")
        for r in (await db.execute(text("SELECT id, name, created_by, owner_user_id FROM properties ORDER BY created_at DESC"))).fetchall():
            print(f"  {r[1]:30s} created_by={r[2]}  owner_user_id={r[3]}")

        print("\n=== TENANTS (created_by) ===")
        for r in (await db.execute(text("SELECT id, first_name, last_name, created_by FROM tenants ORDER BY created_at DESC"))).fetchall():
            print(f"  {r[1]+' '+r[2]:25s} created_by={r[3]}")

asyncio.run(run())
