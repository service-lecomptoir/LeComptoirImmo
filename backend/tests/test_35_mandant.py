"""Compta mandant : honoraires configurables, compte mandant (encaissé, honoraires
HT/TVA/TTC, net, solde à reverser), CRUD reversements et rendu du CRG.
"""

from datetime import date

import pytest

from app.models.lease import Lease
from app.models.owner import Owner
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.models.tenant import Tenant
from app.schemas.owner_reversement import ReversementCreate
from app.services.mandant_service import MandantService, resolve_period
from app.services.owner_service import OwnerService

YEAR = 2026


async def _setup_owner(db, manager, *, suffix="a"):
    """Propriétaire + bien + bail + un loyer PAYÉ (800 loyer + 100 charges)."""
    owner = Owner(
        last_name=f"Bailleur{suffix}",
        first_name="Jean",
        email=f"bail.{suffix}@test.fr",
        created_by=manager.id,
    )
    db.add(owner)
    await db.flush()
    prop = Property(
        name=f"Bien {suffix}",
        address="2 Rue",
        zip_code="75001",
        city="Paris",
        country="France",
        property_type="appartement",
        owner_id=owner.id,
        created_by=manager.id,
    )
    db.add(prop)
    await db.flush()
    tenant = Tenant(
        first_name="Paul",
        last_name="Loc",
        email=f"loc.{suffix}@test.fr",
        created_by=manager.id,
    )
    db.add(tenant)
    await db.flush()
    lease = Lease(
        tenant_id=tenant.id,
        property_id=prop.id,
        start_date=date(2025, 1, 1),
        rent_amount=800,
        charges_amount=100,
        lease_type="vide",
        payment_day=1,
        is_active=True,
        created_by=manager.id,
    )
    db.add(lease)
    await db.flush()
    db.add(
        Payment(
            lease_id=lease.id,
            tenant_id=tenant.id,
            period_year=YEAR,
            period_month=5,
            due_date=date(YEAR, 5, 1),
            amount_rent=800,
            amount_charges=100,
            amount_due=900,
            amount_paid=900,
            status=PaymentStatus.PAID,
            payment_date=date(YEAR, 5, 3),
        )
    )
    await db.flush()
    return owner


# ── Taux effectif (mandat > mandataire > défaut 8%) ──────────────────────────
@pytest.mark.asyncio
async def test_fee_rate_default_is_8(db, gestionnaire_user):
    owner = await _setup_owner(db, gestionnaire_user, suffix="def")
    rate, vat = await OwnerService.fee_config(db, owner)
    assert rate == 8.0
    assert vat == 0.0


@pytest.mark.asyncio
async def test_fee_rate_manager_override(db, gestionnaire_user):
    gestionnaire_user.mgmt_fee_rate = 10
    gestionnaire_user.mgmt_fee_vat_rate = 20
    await db.flush()
    owner = await _setup_owner(db, gestionnaire_user, suffix="mgr")
    rate, vat = await OwnerService.fee_config(db, owner)
    assert rate == 10.0
    assert vat == 20.0


@pytest.mark.asyncio
async def test_fee_rate_owner_override_wins(db, gestionnaire_user):
    gestionnaire_user.mgmt_fee_rate = 10
    await db.flush()
    owner = await _setup_owner(db, gestionnaire_user, suffix="own")
    owner.mgmt_fee_rate = 5
    await db.flush()
    rate, _ = await OwnerService.fee_config(db, owner)
    assert rate == 5.0


# ── Compte mandant : honoraires HT/TVA/TTC + solde à reverser ────────────────
@pytest.mark.asyncio
async def test_account_fees_and_balance(db, gestionnaire_user):
    gestionnaire_user.mgmt_fee_rate = 8
    gestionnaire_user.mgmt_fee_vat_rate = 20
    await db.flush()
    owner = await _setup_owner(db, gestionnaire_user, suffix="acc")

    acc = await MandantService.get_account(db, owner.id, YEAR)
    # Loyer encaissé = 800, charges = 100.
    assert acc["loyers_encaisses"] == 800.0
    assert acc["charges_encaissees"] == 100.0
    assert acc["total_encaisse"] == 900.0
    # Honoraires : 8% de 800 = 64 HT ; TVA 20% = 12.80 ; TTC = 76.80.
    assert acc["honoraires"]["ht"] == 64.0
    assert acc["honoraires"]["vat"] == 12.8
    assert acc["honoraires"]["ttc"] == 76.8
    # Net dû = 900 - 76.80 = 823.20 ; aucun reversement → solde = net.
    assert acc["net_proprietaire"] == 823.2
    assert acc["total_reverse"] == 0.0
    assert acc["solde_a_reverser"] == 823.2


@pytest.mark.asyncio
async def test_reversement_reduces_balance(db, gestionnaire_user):
    owner = await _setup_owner(db, gestionnaire_user, suffix="rev")
    before = await MandantService.get_account(db, owner.id, YEAR)
    net = before["net_proprietaire"]

    rev = await MandantService.create_reversement(
        db,
        owner.id,
        ReversementCreate(
            period_year=YEAR, amount=200, method="virement", reversement_date=date(YEAR, 6, 1)
        ),
        created_by=gestionnaire_user.id,
    )
    after = await MandantService.get_account(db, owner.id, YEAR)
    assert after["total_reverse"] == 200.0
    assert after["solde_a_reverser"] == round(net - 200, 2)

    # Suppression : le solde revient à l'état initial.
    await MandantService.delete_reversement(db, owner.id, rev.id)
    restored = await MandantService.get_account(db, owner.id, YEAR)
    assert restored["total_reverse"] == 0.0
    assert restored["solde_a_reverser"] == net


@pytest.mark.asyncio
async def test_reversement_amount_must_be_positive():
    with pytest.raises(ValueError):
        ReversementCreate(period_year=YEAR, amount=0, reversement_date=date(YEAR, 1, 1))


# ── Périodicité (mensuel / trimestriel / semestriel / annuel) ────────────────
def test_resolve_period_ranges_and_labels():
    assert resolve_period(2026, "mensuel", 6) == (6, 6, "Juin 2026")
    assert resolve_period(2026, "trimestriel", 2) == (4, 6, "T2 2026")
    assert resolve_period(2026, "semestriel", 1) == (1, 6, "1er semestre 2026")
    assert resolve_period(2026, "semestriel", 2) == (7, 12, "2e semestre 2026")
    assert resolve_period(2026, "annuel", 1) == (1, 12, "Année 2026")
    # Hors bornes => replié.
    assert resolve_period(2026, "trimestriel", 9)[0:2] == (10, 12)


@pytest.mark.asyncio
async def test_account_period_filters_payment(db, gestionnaire_user):
    # Le loyer payé est sur le mois 5.
    owner = await _setup_owner(db, gestionnaire_user, suffix="per")

    mai = await MandantService.get_account(db, owner.id, YEAR, "mensuel", 5)
    assert mai["loyers_encaisses"] == 800.0
    assert mai["period_label"] == "Mai 2026"

    juin = await MandantService.get_account(db, owner.id, YEAR, "mensuel", 6)
    assert juin["loyers_encaisses"] == 0.0  # rien encaissé en juin

    t2 = await MandantService.get_account(db, owner.id, YEAR, "trimestriel", 2)  # avr-juin
    assert t2["loyers_encaisses"] == 800.0
    t1 = await MandantService.get_account(db, owner.id, YEAR, "trimestriel", 1)  # jan-mars
    assert t1["loyers_encaisses"] == 0.0


@pytest.mark.asyncio
async def test_reversement_attribution_by_month(db, gestionnaire_user):
    owner = await _setup_owner(db, gestionnaire_user, suffix="att")
    await MandantService.create_reversement(
        db,
        owner.id,
        ReversementCreate(
            period_year=YEAR, period_month=5, amount=100, reversement_date=date(YEAR, 5, 10)
        ),
        created_by=gestionnaire_user.id,
    )
    # Le reversement de mai compte pour T2 (avr-juin) et l'annuel, pas pour T1.
    assert (await MandantService.get_account(db, owner.id, YEAR, "trimestriel", 2))[
        "total_reverse"
    ] == 100.0
    assert (await MandantService.get_account(db, owner.id, YEAR, "trimestriel", 1))[
        "total_reverse"
    ] == 0.0
    assert (await MandantService.get_account(db, owner.id, YEAR, "annuel", 1))[
        "total_reverse"
    ] == 100.0


# ── CRG : le template se rend avec le compte mandant ─────────────────────────
@pytest.mark.asyncio
async def test_crg_template_renders(db, gestionnaire_user):
    from app.services.pdf_service import render_template
    from app.services.template_layout_service import get_layout

    owner = await _setup_owner(db, gestionnaire_user, suffix="crg")
    acc = await MandantService.get_account(db, owner.id, YEAR)
    html = render_template(
        "crg.html.j2",
        {
            "account": acc,
            "layout": get_layout(),
            "period_label": f"Année {YEAR}",
            "manager_name": "Agence Test",
            "manager_address": "1 rue Agence, 75001 Paris",
            "signature_uri": "",
            "tampon_uri": "",
        },
    )
    assert "Compte rendu de gestion" in html
    assert "Honoraires retenus (TTC)" in html
    assert acc["owner_name"] in html
