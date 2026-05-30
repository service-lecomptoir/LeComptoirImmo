import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import sys
sys.path.insert(0, '.')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

async def check():
    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        result = await db.execute(text("SELECT email, hashed_password FROM users WHERE email='gestionnaire@cabinet.fr'"))
        row = result.fetchone()
        if row and row[0]:
            from app.core.security import verify_password
            for pwd in ['password123', 'Password123', 'password', 'admin', 'gestionnaire', 'test123', 'changeme', 'lecomptoirimmo', 'Admin123', 'admin123']:
                try:
                    ok = verify_password(pwd, row[1])
                    if ok:
                        print(f"MOT DE PASSE TROUVE: {pwd}")
                        break
                except Exception as e:
                    print(f"Erreur {pwd}: {e}")
            else:
                print("Aucun mot de passe standard ne correspond")
                print("Hash complet:", row[1])

asyncio.run(check())
