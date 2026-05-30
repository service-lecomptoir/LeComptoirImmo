"""
Reset les mots de passe des comptes de démonstration.
"""
import asyncio
import sys
sys.path.insert(0, '.')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('DATABASE_URL'):
            db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

USERS = [
    ("gestionnaire@cabinet.fr",          "Gestionnaire1!"),
    ("gestionnaire-proprio@cabinet.fr",   "GestionnaireProprio1!"),
    ("proprietaire@email.fr",             "Proprietaire1!"),
    ("locataire@email.fr",                "Locataire1!"),
]

async def reset():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text
    from app.core.security import hash_password, verify_password

    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as db:
        for email, password in USERS:
            result = await db.execute(text(f"SELECT id, hashed_password FROM users WHERE email='{email}'"))
            row = result.fetchone()
            if not row:
                print(f"[SKIP] {email} — introuvable en base")
                continue
            new_hash = hash_password(password)
            await db.execute(text(f"UPDATE users SET hashed_password='{new_hash}' WHERE email='{email}'"))
            print(f"[OK] {email} | pwd: {password}")
        await db.commit()
        print("\nTous les mots de passe ont été réinitialisés.")

asyncio.run(reset())
