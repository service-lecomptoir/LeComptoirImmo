"""Module Syndic — phase 2a : budget, appels de fonds ventilés par tantièmes,
encaissements et comptes copropriétaires."""

from datetime import date

import pytest

from app.models.owner import Owner
from app.schemas.copropriete import (
    CoproprieteCreate,
    LotCreate,
    LotTantiemeIn,
    RepartitionKeyCreate,
)
from app.schemas.copropriete_compta import (
    BudgetCreate,
    BudgetLineIn,
    CoproPaymentIn,
)
from app.services.copro_compta_service import CoproComptaService, nb_periods, period_label
from app.services.copropriete_service import CoproprieteService

YEAR = 2026


async def _owner(db, manager, suffix):
    o = Owner(last_name=f"Copro{suffix}", first_name="Jean", created_by=manager.id)
    db.add(o)
    await db.flush()
    return o


async def _setup(db, manager):
    """Copro avec clé générale (10000) + ascenseur (1000), 2 lots, budget T1."""
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Résidence Compta"), created_by=manager.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    asc = await CoproprieteService.add_key(
        db, copro.id, RepartitionKeyCreate(name="Ascenseur", total_tantiemes=1000)
    )
    o1 = await _owner(db, manager, "1")
    o2 = await _owner(db, manager, "2")
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="Lot 1",
            owner_id=o1.id,
            tantiemes=[
                LotTantiemeIn(key_id=gen, tantiemes=6000),
                LotTantiemeIn(key_id=asc.id, tantiemes=600),
            ],
        ),
    )
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="Lot 2",
            owner_id=o2.id,
            tantiemes=[
                LotTantiemeIn(key_id=gen, tantiemes=4000),
                LotTantiemeIn(key_id=asc.id, tantiemes=400),
            ],
        ),
    )
    budget = await CoproComptaService.create_budget(
        db,
        copro.id,
        BudgetCreate(
            year=YEAR,
            periodicity="trimestriel",
            lines=[
                BudgetLineIn(key_id=gen, label="Charges générales", amount=12000),
                BudgetLineIn(key_id=asc.id, label="Ascenseur", amount=4000),
            ],
        ),
        created_by=manager.id,
    )
    return copro, budget, o1, o2


def test_period_helpers():
    assert nb_periods("trimestriel") == 4
    assert nb_periods("mensuel") == 12
    assert period_label("trimestriel", 1, YEAR) == "T1 2026"
    assert period_label("semestriel", 2, YEAR) == "2e semestre 2026"


@pytest.mark.asyncio
async def test_budget_total(db, gestionnaire_user):
    _, budget, *_ = await _setup(db, gestionnaire_user)
    assert budget["total"] == 16000
    assert budget["nb_periods"] == 4
    assert len(budget["lines"]) == 2


@pytest.mark.asyncio
async def test_generate_call_ventilation(db, gestionnaire_user):
    copro, budget, o1, o2 = await _setup(db, gestionnaire_user)
    call = await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 1, date(YEAR, 1, 15), created_by=gestionnaire_user.id
    )
    assert call["period_label"] == "T1 2026"
    by_owner = {i["owner_id"]: i for i in call["items"]}
    # Lot 1 : (12000*6000/10000 + 4000*600/1000)/4 = (7200+2400)/4 = 2400.
    assert by_owner[o1.id]["amount_due"] == 2400
    # Lot 2 : (12000*4000/10000 + 4000*400/1000)/4 = (4800+1600)/4 = 1600.
    assert by_owner[o2.id]["amount_due"] == 1600
    assert call["total_due"] == 4000


@pytest.mark.asyncio
async def test_generate_call_rejects_out_of_range_and_duplicate(db, gestionnaire_user):
    from app.core.exceptions import BadRequestException

    copro, budget, *_ = await _setup(db, gestionnaire_user)
    with pytest.raises(BadRequestException):
        await CoproComptaService.generate_call(
            db, copro.id, budget["id"], 5, None, created_by=gestionnaire_user.id
        )
    await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 2, None, created_by=gestionnaire_user.id
    )
    with pytest.raises(BadRequestException):
        await CoproComptaService.generate_call(
            db, copro.id, budget["id"], 2, None, created_by=gestionnaire_user.id
        )


@pytest.mark.asyncio
async def test_payment_and_accounts(db, gestionnaire_user):
    copro, budget, o1, o2 = await _setup(db, gestionnaire_user)
    call = await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 1, None, created_by=gestionnaire_user.id
    )
    item1 = next(i for i in call["items"] if i["owner_id"] == o1.id)

    res = await CoproComptaService.record_payment(
        db,
        copro.id,
        item1["id"],
        CoproPaymentIn(amount=1000, payment_date=date(YEAR, 1, 20)),
        created_by=gestionnaire_user.id,
    )
    assert res["status"] == "partial"
    assert res["amount_paid"] == 1000

    # Solde complet → statut payé.
    res = await CoproComptaService.record_payment(
        db,
        copro.id,
        item1["id"],
        CoproPaymentIn(amount=1400, payment_date=date(YEAR, 2, 1)),
        created_by=gestionnaire_user.id,
    )
    assert res["status"] == "paid"

    accounts = await CoproComptaService.accounts(db, copro.id, YEAR)
    by_owner = {a["owner_id"]: a for a in accounts}
    assert by_owner[o1.id]["total_due"] == 2400
    assert by_owner[o1.id]["total_paid"] == 2400
    assert by_owner[o1.id]["balance"] == 0
    assert by_owner[o2.id]["balance"] == 1600


@pytest.mark.asyncio
async def test_appel_pdf_context(db, gestionnaire_user):
    copro, budget, o1, _ = await _setup(db, gestionnaire_user)
    call = await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 1, None, created_by=gestionnaire_user.id
    )
    item1 = next(i for i in call["items"] if i["owner_id"] == o1.id)
    ctx = await CoproComptaService.appel_pdf_context(db, copro.id, item1["id"])
    assert ctx["total"] == 2400
    assert ctx["period_label"] == "T1 2026"
    assert len(ctx["detail"]) == 2  # 2 postes ventilés
    assert sum(d["amount"] for d in ctx["detail"]) == 2400


@pytest.mark.asyncio
async def test_update_budget_replaces_lines(db, gestionnaire_user):
    from app.schemas.copropriete_compta import BudgetUpdate

    copro, budget, *_ = await _setup(db, gestionnaire_user)
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    updated = await CoproComptaService.update_budget(
        db,
        copro.id,
        budget["id"],
        BudgetUpdate(
            periodicity="annuel", lines=[BudgetLineIn(key_id=gen, label="Tout", amount=5000)]
        ),
    )
    assert updated["periodicity"] == "annuel"
    assert updated["total"] == 5000
    assert len(updated["lines"]) == 1
    assert updated["nb_periods"] == 1
