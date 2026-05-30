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
        result = await db.execute(text("SELECT email, hashed_password FROM users LIMIT 6"))
        rows = result.fetchall()
        for row in rows:
            print('email:', row[0])
            print('hash prefix:', row[1][:30] if row[1] else 'NULL')
            print()

    # Test bcrypt verification
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    engine2 = create_async_engine(db_url)
    async with AsyncSession(engine2) as db:
        result = await db.execute(text("SELECT hashed_password FROM users WHERE email='gestionnaire@cabinet.fr'"))
        row = result.fetchone()
        if row and row[0]:
            for pwd in ['password123', 'Password123', 'password', 'admin', 'gestionnaire', 'test123', 'changeme']:
                try:
                    ok = pwd_context.verify(pwd, row[0])
                    if ok:
                        print(f"MOT DE PASSE TROUVE: {pwd}")
                        break
                except Exception as e:
                    print(f"Erreur verify {pwd}: {e}")
            else:
                print("Aucun mot de passe courant ne correspond")
                print("Hash complet:", row[0])

asyncio.run(check())
