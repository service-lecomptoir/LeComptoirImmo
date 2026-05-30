"""Audit complet de l'isolation mandataire vs GP sur tous les endpoints de liste."""
import asyncio
import httpx

BASE = "http://localhost:8000/api/v1"

ACCOUNTS = [
    ('gestionnaire@cabinet.fr',        'Gestionnaire1!',        'MANDATAIRE'),
    ('gestionnaire-proprio@cabinet.fr', 'GestionnaireProprio1!', 'GP'),
]

ENDPOINTS = [
    ('GET', '/properties',      'Biens'),
    ('GET', '/tenants',         'Locataires'),
    ('GET', '/leases',          'Contrats'),
    ('GET', '/tickets',         'Tickets'),
    ('GET', '/avis-echeances',  'Avis écheances'),
    ('GET', '/entretiens',      'Entretiens'),
    ('GET', '/users',           'Users'),
    ('GET', '/payments',        'Paiements'),
    ('GET', '/units',           'Logements'),
]

async def run():
    async with httpx.AsyncClient() as client:
        tokens = {}
        for email, pwd, label in ACCOUNTS:
            resp = await client.post(f'{BASE}/auth/login', json={'email': email, 'password': pwd})
            data = resp.json()
            if 'access_token' in data:
                tokens[label] = data['access_token']
                print(f"Login OK: {label}")
            else:
                print(f"Login FAILED: {label}: {data}")

        print("\n" + "="*80)
        print(f"{'Endpoint':<25} {'MANDATAIRE':>30} {'GP':>30}")
        print("="*80)

        for method, path, name in ENDPOINTS:
            results = {}
            for label, token in tokens.items():
                try:
                    resp = await client.get(f'{BASE}{path}',
                        headers={'Authorization': f'Bearer {token}'},
                        params={'limit': 100})
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list):
                            count = len(data)
                            items = data
                        elif isinstance(data, dict) and 'items' in data:
                            count = data.get('total', len(data['items']))
                            items = data['items']
                        else:
                            count = '?'
                            items = []
                        # Extraire identifiants pour comparaison
                        ids = set()
                        for item in (items if isinstance(items, list) else []):
                            for key in ('id', 'email', 'name', 'first_name'):
                                if key in item:
                                    ids.add(str(item[key])[:20])
                                    break
                        results[label] = (count, ids)
                    else:
                        results[label] = (f'HTTP {resp.status_code}', set())
                except Exception as e:
                    results[label] = (f'ERR: {e}', set())

            m_count, m_ids = results.get('MANDATAIRE', ('?', set()))
            gp_count, gp_ids = results.get('GP', ('?', set()))
            overlap = m_ids & gp_ids

            overlap_str = f" [!] OVERLAP:{len(overlap)}" if overlap else ""
            print(f"{name:<25} {str(m_count):>10} items      {str(gp_count):>10} items{overlap_str}")
            if overlap:
                print(f"  {'':25} Overlap: {list(overlap)[:3]}")

        print("="*80)

asyncio.run(run())
