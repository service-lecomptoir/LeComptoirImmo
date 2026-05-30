"""Vérifie qu'un paiement PENDING est créé automatiquement à la génération d'un avis."""
import asyncio, sys, json
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
    import httpx

    engine = create_async_engine(db_url)

    async with httpx.AsyncClient() as client:
        # Login mandataire
        resp = await client.post('http://localhost:8000/api/v1/auth/login',
            json={'email': 'gestionnaire@cabinet.fr', 'password': 'Gestionnaire1!'})
        token = resp.json()['access_token']

        # Récupérer un bail actif
        resp2 = await client.get('http://localhost:8000/api/v1/leases',
            headers={'Authorization': f'Bearer {token}'}, params={'limit': 5})
        leases = resp2.json().get('items', [])
        if not leases:
            print("Aucun bail actif pour le mandataire")
            return

        lease = leases[0]
        lease_id = lease['id']
        print(f"Bail test: {lease_id} | loyer={lease['rent_amount']} charges={lease['charges_amount']}")

        # Générer un avis pour un mois futur (évite les conflits)
        year, month = 2030, 2
        resp3 = await client.post('http://localhost:8000/api/v1/avis-echeances/generate',
            headers={'Authorization': f'Bearer {token}'},
            json={'lease_id': lease_id, 'period_year': year, 'period_month': month})
        print(f"Generate avis: HTTP {resp3.status_code}")
        if resp3.status_code not in (200, 201):
            print(f"  Error: {resp3.text}")
            return
        avis = resp3.json()
        print(f"  Avis créé: {avis['id']} | montant={avis['amount_total']}")

        # Vérifier le paiement en base
        async with AsyncSession(engine) as db:
            row = (await db.execute(text(
                f"SELECT id, status, amount_due, amount_paid, amount_apl "
                f"FROM payments WHERE lease_id='{lease_id}' "
                f"AND period_year={year} AND period_month={month}"
            ))).fetchone()
            if row:
                print(f"  Paiement cree: id={str(row[0])[:8]}... | status={row[1]} | due={row[2]} | paid={row[3]} | apl={row[4]}")
                has_apl = row[4] and float(row[4]) > 0
                if has_apl:
                    assert row[1] in ('partial', 'paid'), f"Status inattendu avec APL: {row[1]}"
                    print(f"  OK: paiement {row[1].upper()} (APL {row[4]} pre-credite)")
                else:
                    assert row[1] == 'pending', f"Status attendu: pending, obtenu: {row[1]}"
                    assert float(row[3]) == 0, f"amount_paid attendu: 0, obtenu: {row[3]}"
                    print("  OK: paiement PENDING cree automatiquement")
            else:
                print("  ERREUR: aucun paiement cree!")

        # Nettoyage : supprimer l'avis de test
        await client.delete(f"http://localhost:8000/api/v1/avis-echeances/{avis['id']}",
            headers={'Authorization': f'Bearer {token}'})
        async with AsyncSession(engine) as db:
            await db.execute(text(
                f"DELETE FROM payments WHERE lease_id='{lease_id}' "
                f"AND period_year={year} AND period_month={month}"
            ))
            await db.commit()
        print("  Nettoyage OK")

asyncio.run(run())
