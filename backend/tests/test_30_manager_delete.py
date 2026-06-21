"""Suppression définitive en cascade d'un gestionnaire (endpoint interne).

Vérifie qu'un gérant et TOUTE sa chaîne (biens → baux → paiements, locataires,
propriétaires + comptes liés) sont supprimés, sans toucher aux données d'un AUTRE
gérant (isolation), et sans laisser d'orphelin sur les tables clés.
"""
import uuid
from datetime import date

import pytest
from sqlalchemy import text

from app.api.v1.internal_admin import delete_manager


async def _full_chain(db, manager):
    """Crée Property → Tenant (avec compte locataire) → Lease → Payment pour `manager`.
    Retourne (prop, tenant, lease, payment, locataire_user)."""
    from app.core.security import hash_password
    from app.models.lease import Lease
    from app.models.payment import Payment, PaymentStatus
    from app.models.property import Property
    from app.models.tenant import Tenant
    from app.models.user import User

    loc_user = User(
        email=f"loc_{uuid.uuid4().hex[:8]}@test.fr",
        hashed_password=hash_password("LocPass1!"),
        full_name="Locataire Lié",
        role="locataire",
        is_active=True,
        created_by=manager.id,
    )
    db.add(loc_user)
    await db.flush()

    prop = Property(
        name="Bien à supprimer",
        address="1 rue Delete",
        zip_code="75001",
        city="Paris",
        country="France",
        property_type="appartement",
        area_sqm=40.0,
        created_by=manager.id,
    )
    db.add(prop)
    await db.flush()

    tenant = Tenant(
        first_name="Jean",
        last_name="Supprime",
        email=f"t_{uuid.uuid4().hex[:8]}@test.fr",
        created_by=manager.id,
        user_id=loc_user.id,
    )
    db.add(tenant)
    await db.flush()

    lease = Lease(
        tenant_id=tenant.id,
        property_id=prop.id,
        start_date=date.today(),
        rent_amount=700.0,
        charges_amount=50.0,
        lease_type="vide",
        payment_day=5,
        is_active=True,
        created_by=manager.id,
    )
    db.add(lease)
    await db.flush()

    payment = Payment(
        lease_id=lease.id,
        tenant_id=tenant.id,
        period_year=2026,
        period_month=6,
        due_date=date.today(),
        amount_rent=700.0,
        amount_charges=50.0,
        amount_due=750.0,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    await db.flush()

    return prop, tenant, lease, payment, loc_user


@pytest.mark.asyncio
async def test_delete_manager_cascade_and_isolation(db, gestionnaire_user, gp_user2):
    # Gérant cible : graphe complet.
    prop, tenant, lease, payment, loc_user = await _full_chain(db, gestionnaire_user)
    # Autre gérant : doit survivre intégralement.
    other_prop, other_tenant, other_lease, other_payment, _ = await _full_chain(db, gp_user2)

    await delete_manager(gestionnaire_user.id, _=None, db=db)

    async def exists(table, _id):
        return await db.scalar(text(f"SELECT 1 FROM {table} WHERE id = :id"), {"id": _id})

    # Tout le périmètre du gérant cible a disparu.
    assert await exists("users", gestionnaire_user.id) is None
    assert await exists("properties", prop.id) is None
    assert await exists("tenants", tenant.id) is None
    assert await exists("leases", lease.id) is None
    assert await exists("payments", payment.id) is None
    assert await exists("users", loc_user.id) is None

    # L'autre gérant et ses données sont intacts.
    assert await exists("users", gp_user2.id) is not None
    assert await exists("properties", other_prop.id) is not None
    assert await exists("tenants", other_tenant.id) is not None
    assert await exists("leases", other_lease.id) is not None
    assert await exists("payments", other_payment.id) is not None


@pytest.mark.asyncio
async def test_delete_unknown_manager_404(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await delete_manager(uuid.uuid4(), _=None, db=db)
    assert exc.value.status_code == 404
