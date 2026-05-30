"""Crée un logement 'Principal' pour les biens non-immeuble qui n'en ont pas."""
import asyncio, sys
sys.path.insert(0, '.')
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=',1)[1].strip().strip('"').strip("'")
            break

PROPERTY_TO_UNIT_TYPE = {
    'maison':          'maison',
    'appartement':     'T2',
    'local_commercial': 'local',
}

async def run():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        # Trouver les biens non-immeuble sans logement
        rows = (await db.execute(text("""
            SELECT p.id, p.name, p.property_type
            FROM properties p
            WHERE p.property_type != 'immeuble'
            AND NOT EXISTS (SELECT 1 FROM units u WHERE u.property_id = p.id)
        """))).fetchall()

        print(f"Biens sans logement : {len(rows)}")
        for prop_id, name, ptype in rows:
            unit_type = PROPERTY_TO_UNIT_TYPE.get(ptype, 'autre')
            await db.execute(text("""
                INSERT INTO units (id, property_id, unit_ref, unit_type, base_rent, charges_amount, deposit_months, is_occupied, is_available, created_at, updated_at)
                VALUES (gen_random_uuid(), :prop_id, 'Principal', :unit_type, 0, 0, 1, false, true, now(), now())
            """), {'prop_id': str(prop_id), 'unit_type': unit_type})
            print(f"  -> Créé logement '{unit_type}' pour '{name}'")

        await db.commit()
        print("\nBackfill terminé.")

        # Vérification
        rows2 = (await db.execute(text("""
            SELECT p.name, p.property_type, COUNT(u.id) as unit_count
            FROM properties p
            LEFT JOIN units u ON u.property_id = p.id
            GROUP BY p.id, p.name, p.property_type
            ORDER BY p.name
        """))).fetchall()
        print("\n=== Biens et logements ===")
        for r in rows2:
            print(f"  {r[0]:30s} [{r[1]:20s}] {r[2]} logement(s)")

asyncio.run(run())
