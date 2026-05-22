"""
Fixtures partagées — suite de tests LeComptoirImmo.

Stratégie d'isolation :
  - Chaque test utilise une session fraîche
  - Le `commit()` est remplacé par un `flush()` → données visibles dans le test
    mais jamais écrites définitivement en base
  - Un `rollback()` final annule tout → base propre après chaque test
  - Le client HTTP override `get_db` pour utiliser la même session de test
"""
import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ── Configuration test ────────────────────────────────────────────────────────
TEST_DB_URL = (
    "postgresql+asyncpg://locataire_user:devpassword123"
    "@localhost:5432/locataire_cloud_test"
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)


# ── Event loop unique pour toute la session ───────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Session DB : commit remplacé par flush, rollback final ───────────────────
@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """
    Session de test isolée.
    - commit() → flush() (données visibles dans le test, jamais persistées)
    - rollback() final → base propre
    """
    session = AsyncSession(test_engine, expire_on_commit=False, autoflush=False)

    # Intercepter commit → flush uniquement
    original_commit = session.commit
    async def _fake_commit():
        await session.flush()
    session.commit = _fake_commit  # type: ignore[method-assign]

    try:
        yield session
    finally:
        session.commit = original_commit  # type: ignore[method-assign]
        await session.rollback()
        await session.close()


# ── Client HTTP FastAPI avec DB injectée ─────────────────────────────────────
@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _create_user(db: AsyncSession, email: str, password: str, role: str, name: str = None):
    from app.models.user import User
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=name or f"Test {role.capitalize()}",
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _get_token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures utilisateurs par rôle ────────────────────────────────────────────
@pytest_asyncio.fixture
async def admin_user(db):
    return await _create_user(db, f"admin_{uuid.uuid4().hex[:8]}@test.fr", "AdminPass1!", "admin")


@pytest_asyncio.fixture
async def gestionnaire_user(db):
    return await _create_user(db, f"gest_{uuid.uuid4().hex[:8]}@test.fr", "GestPass1!", "gestionnaire")


@pytest_asyncio.fixture
async def proprietaire_user(db):
    return await _create_user(db, f"prop_{uuid.uuid4().hex[:8]}@test.fr", "PropPass1!", "proprietaire")


@pytest_asyncio.fixture
async def locataire_user(db):
    return await _create_user(db, f"loc_{uuid.uuid4().hex[:8]}@test.fr", "LocPass1!", "locataire")


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    return await _get_token(client, admin_user.email, "AdminPass1!")


@pytest_asyncio.fixture
async def gestionnaire_token(client, gestionnaire_user):
    return await _get_token(client, gestionnaire_user.email, "GestPass1!")


@pytest_asyncio.fixture
async def proprietaire_token(client, proprietaire_user):
    return await _get_token(client, proprietaire_user.email, "PropPass1!")


@pytest_asyncio.fixture
async def locataire_token(client, locataire_user):
    return await _get_token(client, locataire_user.email, "LocPass1!")
