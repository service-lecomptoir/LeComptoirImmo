"""
Tests API — Ajustements ad hoc d'une échéance (suppléments / restitutions).

Couvre : net recalculé, plancher à 0, surplus de restitution reporté en crédit
(bail actif) déduit de la prochaine échéance, surplus traité en remboursement
(locataire en départ), suppression d'une ligne, lignes dans l'avis et la quittance.
"""

from datetime import date

import pytest

from tests.conftest import auth


async def _make_lease(db, gestionnaire_user, *, active=True, email="adj@test.fr"):
    from app.models.lease import Lease
    from app.models.property import Property
    from app.models.tenant import Tenant

    prop = Property(
        name="Prop Adj",
        address="9 Rue",
        zip_code="75009",
        city="Paris",
        country="France",
        property_type="appartement",
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()

    tenant = Tenant(
        first_name="Adj",
        last_name="Locataire",
        email=email,
        created_by=gestionnaire_user.id,
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        tenant_id=tenant.id,
        property_id=prop.id,
        start_date=date(2020, 1, 1),
        rent_amount=800.00,
        charges_amount=100.00,
        lease_type="vide",
        payment_day=1,
        is_active=active,
        created_by=gestionnaire_user.id,
    )
    db.add(lease)
    await db.flush()
    return lease


async def _make_payment(db, lease, *, year=2026, month=6):
    from app.models.payment import Payment, PaymentStatus

    pay = Payment(
        lease_id=lease.id,
        tenant_id=lease.tenant_id,
        period_year=year,
        period_month=month,
        due_date=date(year, month, 1),
        amount_rent=800.00,
        amount_charges=100.00,
        amount_due=900.00,
        status=PaymentStatus.PENDING,
    )
    db.add(pay)
    await db.flush()
    return pay


@pytest.mark.asyncio
class TestPaymentAdjustments:
    async def test_supplement_increases_net(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="sup@test.fr")
        pay = await _make_payment(db, lease)

        resp = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "supplement", "libelle": "Réparation", "montant": 50},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["amount_due"] == 950.0
        assert len(data["adjustments"]) == 1
        assert data["adjustments"][0]["type"] == "supplement"

    async def test_restitution_within_month_reduces_net(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="res1@test.fr")
        pay = await _make_payment(db, lease)

        resp = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "restitution", "libelle": "Avoir", "montant": 200},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["amount_due"] == 700.0
        assert data["restitution_credit"] == 0.0
        assert data["restitution_refund"] == 0.0

    async def test_restitution_surplus_active_lease_becomes_credit(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="res2@test.fr")
        pay = await _make_payment(db, lease, year=2026, month=6)

        # Restitution > loyer+charges (900) → net plancher 0, surplus 300 en crédit.
        resp = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "restitution", "libelle": "Dépôt de garantie", "montant": 1200},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["amount_due"] == 0.0
        assert data["restitution_credit"] == 300.0
        assert data["restitution_refund"] == 0.0

        # La prochaine échéance déduit automatiquement ce crédit.
        gen = await client.post(
            "/api/v1/payments",
            headers=auth(gestionnaire_token),
            json={"lease_id": str(lease.id), "period_year": 2026, "period_month": 7},
        )
        assert gen.status_code == 201, gen.text
        nxt = gen.json()
        assert nxt["credit_applied"] == 300.0

    async def test_restitution_surplus_departed_lease_is_refund(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        # Bail résilié (congé) : pas de mois suivant → remboursement, pas crédit.
        lease = await _make_lease(db, gestionnaire_user, active=False, email="res3@test.fr")
        pay = await _make_payment(db, lease, year=2026, month=6)

        resp = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "restitution", "libelle": "Dépôt de garantie", "montant": 1200},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["amount_due"] == 0.0
        assert data["restitution_refund"] == 300.0
        assert data["restitution_credit"] == 0.0

    async def test_delete_adjustment_restores_net(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="del@test.fr")
        pay = await _make_payment(db, lease)

        add = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "supplement", "montant": 120},
        )
        assert add.status_code == 201
        adj_id = add.json()["adjustments"][0]["id"]

        rm = await client.delete(
            f"/api/v1/payments/{pay.id}/adjustments/{adj_id}",
            headers=auth(gestionnaire_token),
        )
        assert rm.status_code == 200, rm.text
        assert rm.json()["amount_due"] == 900.0
        assert rm.json()["adjustments"] == []

    async def test_locataire_cannot_add_adjustment(
        self, client, locataire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="forbid@test.fr")
        pay = await _make_payment(db, lease)
        resp = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(locataire_token),
            json={"type": "supplement", "montant": 50},
        )
        assert resp.status_code == 403

    async def test_adjustment_rejects_zero_amount(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="zero@test.fr")
        pay = await _make_payment(db, lease)
        resp = await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "supplement", "montant": 0},
        )
        assert resp.status_code == 422

    async def test_quittance_pdf_includes_adjustment(
        self, client, gestionnaire_token, gestionnaire_user, db
    ):
        lease = await _make_lease(db, gestionnaire_user, email="quit@test.fr")
        pay = await _make_payment(db, lease)
        await client.post(
            f"/api/v1/payments/{pay.id}/adjustments",
            headers=auth(gestionnaire_token),
            json={"type": "supplement", "libelle": "Frais", "montant": 50},
        )
        # Solder le mois (net = 900 + 50) pour pouvoir générer la quittance.
        rec = await client.post(
            f"/api/v1/payments/{pay.id}/record",
            headers=auth(gestionnaire_token),
            json={"amount_paid": 950, "payment_date": "2026-06-05", "payment_method": "virement"},
        )
        assert rec.status_code == 200, rec.text
        resp = await client.get(
            f"/api/v1/payments/{pay.id}/quittance", headers=auth(gestionnaire_token)
        )
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
