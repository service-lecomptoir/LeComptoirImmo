"""Module Syndic — phase 2b : dépenses réelles + régularisation annuelle
(réel ventilé par tantièmes vs provisions appelées) par copropriétaire."""

from datetime import date

import pytest

from app.models.owner import Owner
from app.schemas.copropriete import (
    CoproprieteCreate,
    LotCreate,
    LotTantiemeIn,
    RepartitionKeyCreate,
)
from app.schemas.copropriete_compta import BudgetCreate, BudgetLineIn, ExpenseCreate, ExpenseUpdate
from app.services.copro_compta_service import CoproComptaService
from app.services.copropriete_service import CoproprieteService

YEAR = 2026


async def _owner(db, manager, suffix):
    o = Owner(last_name=f"Regul{suffix}", first_name="Jean", created_by=manager.id)
    db.add(o)
    await db.flush()
    return o


async def _setup(db, manager):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Résidence Régul"), created_by=manager.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    asc_key = await CoproprieteService.add_key(
        db, copro.id, RepartitionKeyCreate(name="Ascenseur", total_tantiemes=1000)
    )
    asc = asc_key.id
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
                LotTantiemeIn(key_id=asc, tantiemes=600),
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
                LotTantiemeIn(key_id=asc, tantiemes=400),
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
                BudgetLineIn(key_id=asc, label="Ascenseur", amount=4000),
            ],
        ),
        created_by=manager.id,
    )
    return copro, budget, gen, asc, o1, o2


@pytest.mark.asyncio
async def test_expenses_crud(db, gestionnaire_user):
    copro, _b, gen, _asc, *_ = await _setup(db, gestionnaire_user)
    e = await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=gen, label="Entretien parties communes", amount=10000),
        created_by=gestionnaire_user.id,
    )
    assert e["key_name"] == "Charges générales"
    lst = await CoproComptaService.list_expenses(db, copro.id, YEAR)
    assert len(lst) == 1 and lst[0]["amount"] == 10000
    await CoproComptaService.update_expense(db, copro.id, e["id"], ExpenseUpdate(amount=11000))
    lst = await CoproComptaService.list_expenses(db, copro.id, YEAR)
    assert lst[0]["amount"] == 11000
    await CoproComptaService.delete_expense(db, copro.id, e["id"])
    assert await CoproComptaService.list_expenses(db, copro.id, YEAR) == []


@pytest.mark.asyncio
async def test_regularization_computation(db, gestionnaire_user):
    copro, budget, gen, asc, o1, o2 = await _setup(db, gestionnaire_user)
    # Provisions appelées : 1 appel T1 (un quart de l'annuel).
    await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 1, None, created_by=gestionnaire_user.id
    )
    # Dépenses réelles.
    await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=gen, label="Général", amount=10000),
        created_by=gestionnaire_user.id,
    )
    await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=asc, label="Ascenseur", amount=2000),
        created_by=gestionnaire_user.id,
    )

    regul = await CoproComptaService.regularization(db, copro.id, YEAR)
    assert regul["budget_total"] == 16000
    assert regul["expenses_total"] == 12000
    assert regul["appele_total"] == 4000  # T1 : 2400 + 1600
    by_owner = {r["owner_id"]: r for r in regul["rows"]}
    # o1 : réel = 10000*0.6 + 2000*0.6 = 7200 ; appelé T1 = 2400 ; solde = -4800.
    assert by_owner[o1.id]["reel"] == 7200
    assert by_owner[o1.id]["appele"] == 2400
    assert by_owner[o1.id]["solde"] == -4800
    # o2 : réel = 4000 + 800 = 4800 ; appelé = 1600 ; solde = -3200.
    assert by_owner[o2.id]["reel"] == 4800
    assert by_owner[o2.id]["solde"] == -3200


@pytest.mark.asyncio
async def test_regul_pdf_context(db, gestionnaire_user):
    copro, budget, gen, asc, o1, _o2 = await _setup(db, gestionnaire_user)
    await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 1, None, created_by=gestionnaire_user.id
    )
    await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=gen, label="Général", amount=10000),
        created_by=gestionnaire_user.id,
    )
    await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=asc, label="Ascenseur", amount=2000),
        created_by=gestionnaire_user.id,
    )
    ctx = await CoproComptaService.regul_pdf_context(db, copro.id, o1.id, YEAR)
    assert ctx["reel_total"] == 7200
    assert ctx["appele"] == 2400
    assert ctx["solde"] == -4800
    assert len(ctx["detail"]) == 2
    assert sum(d["amount"] for d in ctx["detail"]) == 7200


@pytest.mark.asyncio
async def test_regularization_template_renders(db, gestionnaire_user):
    from app.services.pdf_service import render_template
    from app.services.template_layout_service import get_layout

    copro, budget, gen, _asc, o1, _o2 = await _setup(db, gestionnaire_user)
    await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=gen, label="Général", amount=10000),
        created_by=gestionnaire_user.id,
    )
    ctx = await CoproComptaService.regul_pdf_context(db, copro.id, o1.id, YEAR)
    html = render_template(
        "copro_regul.html.j2",
        {
            "ctx": ctx,
            "layout": get_layout(),
            "manager_name": "Syndic Test",
            "manager_address": "",
            "signature_uri": "",
            "tampon_uri": "",
        },
    )
    assert "Décompte de régularisation" in html
    assert ctx["owner_name"] in html
