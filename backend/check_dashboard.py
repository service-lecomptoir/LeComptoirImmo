"""Vérifie les stats dashboard pour mandataire vs GP."""
import asyncio
import httpx

async def run():
    async with httpx.AsyncClient() as client:
        for email, pwd, label in [
            ('gestionnaire@cabinet.fr', 'Gestionnaire1!', 'Mandataire'),
            ('gestionnaire-proprio@cabinet.fr', 'GestionnaireProprio1!', 'GP'),
        ]:
            resp = await client.post('http://localhost:8000/api/v1/auth/login',
                json={'email': email, 'password': pwd})
            data = resp.json()
            if 'access_token' not in data:
                print(f"{label}: login failed: {data}")
                continue
            token = data['access_token']
            resp2 = await client.get('http://localhost:8000/api/v1/dashboard/stats',
                headers={'Authorization': f'Bearer {token}'})
            stats = resp2.json()
            print(f"\n=== {label} ===")
            print(f"  total_tenants    : {stats.get('total_tenants')}")
            print(f"  total_properties : {stats.get('total_properties')}")
            print(f"  total_leases     : {stats.get('total_leases_active')}")
            print(f"  top_properties   : {[p['property_name'] for p in stats.get('top_properties', [])]}")

asyncio.run(run())
