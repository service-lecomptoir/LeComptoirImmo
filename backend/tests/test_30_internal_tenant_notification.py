"""
Tests — endpoint interne de notification d'un locataire (appelé par LeComptoirMarket).
"""

import pytest
from sqlalchemy import select

from app.config import get_settings
from tests.conftest import auth  # noqa: F401 (cohérence imports tests)

INTERNAL_HEADERS = {"X-Internal-Key": get_settings().ALICE_INTERNAL_KEY}


async def _make_tenant_with_account(db, locataire_user, email="loc.market@test.fr"):
    from app.models.tenant import Tenant

    tenant = Tenant(
        first_name="Loc",
        last_name="Market",
        email=email,
        user_id=locataire_user.id,
    )
    db.add(tenant)
    await db.flush()
    return tenant


@pytest.mark.asyncio
class TestInternalTenantNotification:
    async def test_creates_notification_for_known_tenant(
        self, client, locataire_user, db
    ):
        await _make_tenant_with_account(db, locataire_user, email="known@test.fr")

        resp = await client.post(
            "/internal/notifications/tenant",
            headers=INTERNAL_HEADERS,
            json={
                "tenant_email": "Known@Test.fr",  # casse différente : doit matcher
                "title": "Promo de votre commerce partenaire",
                "message": "-10% ce week-end !",
                "source": "market",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["created"] is True

        from app.models.notification import Notification

        notifs = (
            (
                await db.execute(
                    select(Notification).where(Notification.user_id == locataire_user.id)
                )
            )
            .scalars()
            .all()
        )
        assert any(n.title == "Promo de votre commerce partenaire" for n in notifs)

    async def test_unknown_email_is_noop(self, client, db):
        resp = await client.post(
            "/internal/notifications/tenant",
            headers=INTERNAL_HEADERS,
            json={"tenant_email": "nobody@nowhere.fr", "title": "X", "message": "Y"},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["created"] is False

    async def test_requires_internal_key(self, client):
        resp = await client.post(
            "/internal/notifications/tenant",
            json={"tenant_email": "x@test.fr", "title": "X", "message": "Y"},
        )
        assert resp.status_code == 401
