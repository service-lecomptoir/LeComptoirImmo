"""Recette « compta immobilière » des nouvelles features (mandataire + syndic).

Vérifie les invariants comptables sensibles : proratisation des honoraires sur
encaissement partiel, TVA, ventilation des appels de fonds SANS dérive d'arrondi
(le total appelé = budget de la période), régularisation et votes multi-lots,
fonds de travaux, et coffre de documents copro (isolation).
"""

from datetime import date

import pytest

from app.models.lease import Lease
from app.models.owner import Owner
from app.models.payment import Payment, PaymentStatus
from app.models.property import Property
from app.schemas.copropriete import (
    CoproprieteCreate,
    LotCreate,
    LotTantiemeIn,
    RepartitionKeyUpdate,
)
from app.schemas.copropriete_ag import AssemblyCreate, ResolutionCreate
from app.schemas.copropriete_compta import BudgetCreate, BudgetLineIn, ExpenseCreate
from app.services.copro_ag_service import CoproAGService
from app.services.copro_compta_service import CoproComptaService
from app.services.copropriete_service import CoproprieteService

YEAR = 2026


# ── Compta mandant : proratisation honoraires sur encaissement partiel + TVA ──
@pytest.mark.asyncio
async def test_mandant_partial_payment_proration_and_vat(db, gestionnaire_user):
    gestionnaire_user.mgmt_fee_rate = 8
    gestionnaire_user.mgmt_fee_vat_rate = 20
    await db.flush()
    owner = Owner(last_name="Bailleur", first_name="P", created_by=gestionnaire_user.id)
    db.add(owner)
    await db.flush()
    prop = Property(
        name="B1",
        address="1 R",
        zip_code="75001",
        city="Paris",
        country="France",
        property_type="appartement",
        owner_id=owner.id,
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()
    from app.models.tenant import Tenant

    t = Tenant(first_name="L", last_name="Loc", email="l@t.fr", created_by=gestionnaire_user.id)
    db.add(t)
    await db.flush()
    lease = Lease(
        tenant_id=t.id,
        property_id=prop.id,
        start_date=date(2025, 1, 1),
        rent_amount=800,
        charges_amount=100,
        lease_type="vide",
        payment_day=1,
        is_active=True,
        created_by=gestionnaire_user.id,
    )
    db.add(lease)
    await db.flush()
    # Encaissement PARTIEL : 450 sur 900 dû.
    db.add(
        Payment(
            lease_id=lease.id,
            tenant_id=t.id,
            period_year=YEAR,
            period_month=5,
            due_date=date(YEAR, 5, 1),
            amount_rent=800,
            amount_charges=100,
            amount_due=900,
            amount_paid=450,
            status=PaymentStatus.PARTIAL,
            payment_date=date(YEAR, 5, 3),
        )
    )
    await db.flush()

    from app.services.mandant_service import MandantService

    acc = await MandantService.get_account(db, owner.id, YEAR)
    # Part loyer encaissée = 450 * 800/900 = 400 ; charges = 50.
    assert acc["loyers_encaisses"] == 400
    assert acc["charges_encaissees"] == 50
    # Honoraires 8% de 400 = 32 HT ; TVA 20% = 6.40 ; TTC = 38.40.
    assert acc["honoraires"]["ht"] == 32
    assert acc["honoraires"]["vat"] == 6.4
    assert acc["honoraires"]["ttc"] == 38.4
    # Net dû = 450 - 38.40 = 411.60.
    assert acc["net_proprietaire"] == 411.6


# ── Appel de fonds : pas de dérive d'arrondi (Σ quote-parts == budget période) ──
@pytest.mark.asyncio
async def test_fund_call_no_rounding_drift(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Arrondi"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    # 3 lots à tantièmes égaux sur une base de 3 → 1/3 chacun (non décimal).
    await CoproprieteService.update_key(db, copro.id, gen, RepartitionKeyUpdate(total_tantiemes=3))
    owners = []
    for i in range(3):
        o = Owner(last_name=f"C{i}", first_name="x", created_by=gestionnaire_user.id)
        db.add(o)
        await db.flush()
        owners.append(o)
        await CoproprieteService.create_lot(
            db,
            copro.id,
            LotCreate(
                numero=f"L{i}", owner_id=o.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=1)]
            ),
        )
    budget = await CoproComptaService.create_budget(
        db,
        copro.id,
        BudgetCreate(
            year=YEAR,
            periodicity="annuel",
            lines=[BudgetLineIn(key_id=gen, label="Général", amount=10)],
        ),
        created_by=gestionnaire_user.id,
    )
    call = await CoproComptaService.generate_call(
        db, copro.id, budget["id"], 1, None, created_by=gestionnaire_user.id
    )
    # Σ des quote-parts == 10.00 (le résidu de 0,01 a été affecté), pas 9,99.
    assert call["total_due"] == 10.0
    assert round(sum(i["amount_due"] for i in call["items"]), 2) == 10.0


# ── Régularisation : copropriétaire multi-lots ────────────────────────────────
@pytest.mark.asyncio
async def test_regularization_multi_lot_owner(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="MultiLot"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]  # base 10000
    o = Owner(last_name="Multi", first_name="x", created_by=gestionnaire_user.id)
    db.add(o)
    await db.flush()
    # Même propriétaire, 2 lots : 6000 + 1000 = 7000/10000.
    for num, t in (("L1", 6000), ("L2", 1000)):
        await CoproprieteService.create_lot(
            db,
            copro.id,
            LotCreate(
                numero=num, owner_id=o.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=t)]
            ),
        )
    await CoproComptaService.create_expense(
        db,
        copro.id,
        ExpenseCreate(year=YEAR, key_id=gen, label="Charges", amount=10000),
        created_by=gestionnaire_user.id,
    )
    regul = await CoproComptaService.regularization(db, copro.id, YEAR)
    row = next(r for r in regul["rows"] if r["owner_id"] == o.id)
    # Quote-part réelle = 10000 * 7000/10000 = 7000 (cumul des 2 lots).
    assert row["reel"] == 7000
    assert row["appele"] == 0  # aucun appel généré
    assert row["solde"] == -7000  # complément à appeler


# ── AG : poids = somme des tantièmes des lots ; art24 exclut l'abstention ──────
@pytest.mark.asyncio
async def test_ag_multilot_weight_and_art24(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="AGmulti"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    o1 = Owner(last_name="A", first_name="x", created_by=gestionnaire_user.id)
    o2 = Owner(last_name="B", first_name="x", created_by=gestionnaire_user.id)
    db.add_all([o1, o2])
    await db.flush()
    # o1 a 2 lots (3000+2000=5000), o2 un lot 4000, 1000 non attribués (sans propriétaire).
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="L1", owner_id=o1.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=3000)]
        ),
    )
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="L2", owner_id=o1.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=2000)]
        ),
    )
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="L3", owner_id=o2.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=4000)]
        ),
    )

    voters = await CoproAGService.voters(db, copro.id)
    by = {v["owner_id"]: v["tantiemes"] for v in voters}
    assert by[o1.id] == 5000  # cumul des 2 lots
    assert by[o2.id] == 4000

    ag = await CoproAGService.create_assembly(
        db, copro.id, AssemblyCreate(title="AG"), created_by=gestionnaire_user.id
    )
    d = await CoproAGService.add_resolution(
        db, copro.id, ag["id"], ResolutionCreate(title="R", majority="art24")
    )
    rid = d["resolutions"][0]["id"]
    # o1 pour (5000), o2 abstention (4000) → art24 : 5000 > 0 contre → adoptée.
    await CoproAGService.set_vote(db, copro.id, ag["id"], rid, o1.id, "pour")
    d = await CoproAGService.set_vote(db, copro.id, ag["id"], rid, o2.id, "abstention")
    r = d["resolutions"][0]
    assert r["pour"] == 5000
    assert r["abstention"] == 4000
    assert r["outcome"] == "adopted"


# ── Coffre de documents copro : entité + isolation inter-agences ──────────────
@pytest.mark.asyncio
async def test_copro_document_vault_and_isolation(db, gestionnaire_user, gp_user2):
    from app.api.v1._isolation import assert_document_access
    from app.core.exceptions import ForbiddenException
    from app.models.document import DocumentType, EntityType
    from app.services.document_service import DocumentService

    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Coffre"), created_by=gestionnaire_user.id
    )
    doc = await DocumentService.save_generated(
        db,
        content=b"%PDF-1.4 rcp",
        file_name="RCP.pdf",
        entity_type=EntityType.COPROPRIETE,
        entity_id=copro.id,
        document_type=DocumentType.AUTRE,
        label="Règlement de copropriété",
        uploaded_by=gestionnaire_user.id,
    )
    listed = await DocumentService.list_by_entity(db, EntityType.COPROPRIETE, copro.id)
    assert len(listed) == 1 and listed[0].id == doc.id

    # Le gestionnaire créateur y accède.
    await assert_document_access(db, gestionnaire_user, doc)
    # Un gestionnaire d'une AUTRE agence est refusé.
    with pytest.raises(ForbiddenException):
        await assert_document_access(db, gp_user2, doc)
