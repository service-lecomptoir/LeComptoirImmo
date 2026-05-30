"""
Backfill created_by sur les users créés par des gestionnaire_proprio.
On utilise la chaîne Tenant.created_by -> Tenant.user_id pour retrouver
les locataires déjà liés à un tenant GP.
"""
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
        # Récupérer les GP users
        gp_rows = (await db.execute(text(
            "SELECT id, email FROM users WHERE role='gestionnaire_proprio'"
        ))).fetchall()
        print(f"GP users: {len(gp_rows)}")

        for gp_id, gp_email in gp_rows:
            # Trouver les tenants créés par ce GP
            tenant_rows = (await db.execute(text(
                f"SELECT id, first_name, last_name, user_id FROM tenants WHERE created_by='{gp_id}'"
            ))).fetchall()
            print(f"  {gp_email}: {len(tenant_rows)} tenants")
            for t_id, fname, lname, user_id in tenant_rows:
                if user_id:
                    # Le locataire a un compte user -> marquer created_by
                    await db.execute(text(
                        f"UPDATE users SET created_by='{gp_id}' WHERE id='{user_id}' AND created_by IS NULL"
                    ))
                    print(f"    -> backfill user_id={user_id} ({fname} {lname})")

        await db.commit()
        print("\nBackfill termine.")

        # Verification
        print("\n=== USERS apres backfill ===")
        rows = (await db.execute(text(
            "SELECT u.email, u.role, u.created_by, c.email as creator_email "
            "FROM users u LEFT JOIN users c ON u.created_by=c.id "
            "ORDER BY u.role, u.email"
        ))).fetchall()
        for r in rows:
            creator = r[3] if r[3] else 'NULL'
            print(f"  [{r[1]:25s}] {r[0]:40s} created_by={creator}")

asyncio.run(run())
