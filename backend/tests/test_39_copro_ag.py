"""Module Syndic — phase 3 : assemblées générales, résolutions, votes pondérés
par les tantièmes de la clé générale et dépouillement selon la majorité."""

import pytest

from app.models.owner import Owner
from app.schemas.copropriete import CoproprieteCreate, LotCreate, LotTantiemeIn
from app.schemas.copropriete_ag import AssemblyCreate, ResolutionCreate
from app.services.copro_ag_service import CoproAGService, _outcome
from app.services.copropriete_service import CoproprieteService


async def _owner(db, manager, suffix):
    o = Owner(last_name=f"AG{suffix}", first_name="Jean", created_by=manager.id)
    db.add(o)
    await db.flush()
    return o


async def _setup(db, manager):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Résidence AG"), created_by=manager.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    o1 = await _owner(db, manager, "1")
    o2 = await _owner(db, manager, "2")
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="Lot 1", owner_id=o1.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=6000)]
        ),
    )
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="Lot 2", owner_id=o2.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=4000)]
        ),
    )
    return copro, o1, o2


def test_outcome_rules():
    # art24 : majorité des exprimés (abstention exclue).
    assert _outcome("art24", 6000, 4000, 0, 10000) == "adopted"
    assert _outcome("art24", 4000, 6000, 0, 10000) == "rejected"
    # art25 : majorité absolue de tous les tantièmes.
    assert _outcome("art25", 6000, 0, 0, 10000) == "adopted"
    assert _outcome("art25", 5000, 0, 0, 10000) == "rejected"  # 5000 n'est pas > 5000
    # art26 : deux tiers.
    assert _outcome("art26", 6667, 0, 0, 10000) == "adopted"
    assert _outcome("art26", 6000, 0, 0, 10000) == "rejected"
    # unanimité.
    assert _outcome("unanimite", 10000, 0, 0, 10000) == "adopted"
    assert _outcome("unanimite", 6000, 0, 4000, 10000) == "rejected"
    # aucun vote => pending.
    assert _outcome("art24", 0, 0, 0, 10000) == "pending"


@pytest.mark.asyncio
async def test_voters(db, gestionnaire_user):
    copro, o1, o2 = await _setup(db, gestionnaire_user)
    voters = await CoproAGService.voters(db, copro.id)
    by = {v["owner_id"]: v["tantiemes"] for v in voters}
    assert by[o1.id] == 6000
    assert by[o2.id] == 4000


@pytest.mark.asyncio
async def test_assembly_resolution_and_votes(db, gestionnaire_user):
    copro, o1, o2 = await _setup(db, gestionnaire_user)
    ag = await CoproAGService.create_assembly(
        db,
        copro.id,
        AssemblyCreate(title="AG 2026", kind="ordinaire"),
        created_by=gestionnaire_user.id,
    )
    detail = await CoproAGService.add_resolution(
        db,
        copro.id,
        ag["id"],
        ResolutionCreate(title="Approbation des comptes", majority="art24"),
    )
    res_id = detail["resolutions"][0]["id"]

    # o1 (6000) pour, o2 (4000) contre → art24 adoptée.
    detail = await CoproAGService.set_vote(db, copro.id, ag["id"], res_id, o1.id, "pour")
    detail = await CoproAGService.set_vote(db, copro.id, ag["id"], res_id, o2.id, "contre")
    r = detail["resolutions"][0]
    assert r["pour"] == 6000
    assert r["contre"] == 4000
    assert r["base_tantiemes"] == 10000
    assert r["outcome"] == "adopted"

    # Changement de vote o1 → contre : pour 0, contre 10000 → rejetée.
    detail = await CoproAGService.set_vote(db, copro.id, ag["id"], res_id, o1.id, "contre")
    assert detail["resolutions"][0]["outcome"] == "rejected"

    # Retrait du vote o1.
    detail = await CoproAGService.clear_vote(db, copro.id, ag["id"], res_id, o1.id)
    r = detail["resolutions"][0]
    assert r["contre"] == 4000  # ne reste que o2
    assert len(r["votes"]) == 1


@pytest.mark.asyncio
async def test_pdf_context(db, gestionnaire_user):
    copro, o1, _o2 = await _setup(db, gestionnaire_user)
    ag = await CoproAGService.create_assembly(
        db, copro.id, AssemblyCreate(title="AG 2026"), created_by=gestionnaire_user.id
    )
    await CoproAGService.add_resolution(
        db,
        copro.id,
        ag["id"],
        ResolutionCreate(title="Travaux toiture", majority="art25"),
    )
    ctx = await CoproAGService.pdf_context(db, copro.id, ag["id"])
    assert ctx["copro_name"] == "Résidence AG"
    assert ctx["resolutions"][0]["majority_label"].startswith("Majorité absolue")


@pytest.mark.asyncio
async def test_pdf_templates_render(db, gestionnaire_user):
    from app.services.pdf_service import render_template
    from app.services.template_layout_service import get_layout

    copro, o1, _o2 = await _setup(db, gestionnaire_user)
    ag = await CoproAGService.create_assembly(
        db, copro.id, AssemblyCreate(title="AG 2026"), created_by=gestionnaire_user.id
    )
    await CoproAGService.add_resolution(
        db,
        copro.id,
        ag["id"],
        ResolutionCreate(title="Budget prévisionnel", majority="art24"),
    )
    ctx = await CoproAGService.pdf_context(db, copro.id, ag["id"])
    common = {
        "ctx": ctx,
        "layout": get_layout(),
        "manager_name": "Syndic Test",
        "manager_address": "",
        "signature_uri": "",
        "tampon_uri": "",
    }
    conv = render_template("copro_convocation.html.j2", common)
    pv = render_template("copro_pv.html.j2", common)
    assert "Convocation à l'assemblée générale" in conv
    assert "Procès-verbal" in pv
    assert "Budget prévisionnel" in conv
