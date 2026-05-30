import asyncio, sys
sys.path.insert(0, '.')

async def run():
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post('http://localhost:8000/api/v1/auth/login',
            json={'email': 'gestionnaire-proprio@cabinet.fr', 'password': 'GestionnaireProprio1!'})
        data = resp.json()
        if 'access_token' not in data:
            print(f"Login failed: {data}")
            return
        token = data['access_token']

        resp2 = await client.get('http://localhost:8000/api/v1/users',
            headers={'Authorization': f'Bearer {token}'})
        users = resp2.json()
        print(f'GP voit {len(users)} users:')
        for u in users:
            print(f'  [{u["role"]:20s}] {u["email"]}')

asyncio.run(run())
