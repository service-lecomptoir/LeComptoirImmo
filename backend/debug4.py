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
        print("=== TOUS LES USERS avec created_by ===")
        rows = (await db.execute(text(
            "SELECT u.email, u.role, c.email as creator, u.created_at "
            "FROM users u LEFT JOIN users c ON u.created_by=c.id "
            "ORDER BY u.role, u.created_at DESC"
        ))).fetchall()
        for r in rows:
            creator = r[2] if r[2] else "NULL (system/inconnu)"
            print(f"  [{r[1]:25s}] {r[0]:40s} cree par: {creator}")

        print("\n=== TEST API: mandataire voit quoi via GET /users ? ===")
        import httpx
        async with httpx.AsyncClient() as client:
            # Login mandataire
            resp = await client.post("http://localhost:8000/api/v1/auth/login",
                json={"email": "gestionnaire@cabinet.fr", "password": "Gestionnaire1!"})
            token = resp.json()["access_token"]
            # GET users
            resp2 = await client.get("http://localhost:8000/api/v1/users",
                headers={"Authorization": f"Bearer {token}"})
            users = resp2.json()
            print(f"  Mandataire voit {len(users)} users:")
            for u in users:
                print(f"    [{u['role']:15s}] {u['email']}")

asyncio.run(run())
