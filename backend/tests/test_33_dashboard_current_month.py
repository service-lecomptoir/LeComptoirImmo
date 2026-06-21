"""Tests Dashboard — « Loyers attendus / mois » ne compte que le mois courant.

Un bail qui démarre le mois prochain (ou plus tard) ne doit pas gonfler les
statistiques du mois : ni les loyers attendus, ni l'occupation.
"""
from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from tests.conftest import auth


async def _make_lease(db, gestionnaire_user, *, name, email, start_date, rent, charges=0.0):
    from app.models.lease import Lease
    from app.models.property import Property
    from app.models.tenant import Tenant

    prop = Property(
        name=name, address="1 Rue", zip_code="75001",
        city="Paris", country="France", property_type="appartement",
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()

    tenant = Tenant(
        first_name="T", last_name=name, email=email,
        created_by=gestionnaire_user.id,
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        tenant_id=tenant.id, property_id=prop.id,
        start_date=start_date, rent_amount=rent, charges_amount=charges,
        lease_type="vide", payment_day=1, is_active=True,
        created_by=gestionnaire_user.id,
    )
    db.add(lease)
    await db.flush()
    return lease


@pytest.mark.asyncio
class TestDashboardCurrentMonth:
    async def test_future_lease_excluded_from_expected_and_occupancy(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        today = date.today()
        next_month = today.replace(day=1) + relativedelta(months=1)

        # Bail en cours ce mois-ci : doit compter (800 + 100 = 900).
        await _make_lease(
            db, gestionnaire_user, name="EnCours", email="encours@test.fr",
            start_date=today, rent=800.0, charges=100.0,
        )
        # Bail qui démarre le mois prochain : NE doit PAS compter.
        await _make_lease(
            db, gestionnaire_user, name="Futur", email="futur@test.fr",
            start_date=next_month, rent=500.0, charges=50.0,
        )
        await db.commit()

        resp = await client.get("/api/v1/dashboard/stats", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        data = resp.json()

        # Seul le bail en cours est compté : 900 €, pas 1450 €.
        assert data["financial"]["total_rent_expected"] == 900.0
        # Une seule unité occupée ce mois-ci (le bien du bail futur est vacant).
        assert data["occupancy"]["occupied_units"] == 1
        # Contrats : 1 actif (mois courant), 1 à venir (mois prochain).
        assert data["total_leases_active"] == 1
        assert data["total_leases_future"] == 1
