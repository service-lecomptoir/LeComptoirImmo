import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import sys
sys.path.insert(0, '.')

# Lire DATABASE_URL depuis .env
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

print('DB URL (truncated):', db_url[:50], '...')

async def check():
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        result = await db.execute(text("SELECT email, role, is_active FROM users ORDER BY created_at LIMIT 10"))
        rows = result.fetchall()
        print(f"\n{len(rows)} utilisateurs trouvés:")
        for r in rows:
            print(r)

asyncio.run(check())
