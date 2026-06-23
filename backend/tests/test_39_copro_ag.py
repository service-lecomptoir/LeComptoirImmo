"""Module Syndic — phase 3 : assemblées générales, résolutions, votes pondérés
par les tantièmes de la clé générale et dépouillement selon la majorité."""

import pytest

from app.models.owner import Owner
from app.schemas.copropriete import (
    CoproprieteCreate,
    LotCreate,
    LotTantiemeIn,
    RepartitionKeyUpdate,
)
from app.schemas.copropriete_ag import AssemblyCreate, ResolutionCreate
from app.services.copro_ag_service import CoproAGService, evaluate_resolution
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


def _o(*args, **kwargs):
    return evaluate_resolution(*args, **kwargs)[0]


def test_outcome_rules():
    # art24 : majorité des exprimés (abstention exclue).
    assert _o("art24", 6000, 4000, 0, 10000) == "adopted"
    assert _o("art24", 4000, 6000, 0, 10000) == "rejected"
    # art25 : majorité absolue de tous les tantièmes.
    assert _o("art25", 6000, 0, 0, 10000) == "adopted"
    # art25 direct échoue mais < 1/3 → rejet (pas de passerelle).
    assert _o("art25", 3000, 0, 0, 10000) == "rejected"
    # unanimité.
    assert _o("unanimite", 10000, 0, 0, 10000) == "adopted"
    assert _o("unanimite", 6000, 0, 4000, 10000) == "rejected"
    # aucun vote => pending.
    assert _o("art24", 0, 0, 0, 10000) == "pending"


def test_passerelle_art25_1():
    # 5000/10000 : pas la majorité absolue (>5000) MAIS >= 1/3 et pour > contre
    # → adoptée au 2nd vote (passerelle art. 25-1).
    outcome, note = evaluate_resolution("art25", 5000, 0, 0, 10000)
    assert outcome == "adopted"
    assert note and "25-1" in note
    # 4000 pour / 4500 contre : >= 1/3 mais pour <= contre → non adoptée.
    outcome, _note = evaluate_resolution("art25", 4000, 4500, 0, 10000)
    assert outcome == "rejected"


def test_double_majorite_art26():
    # 2/3 des tantièmes ET majorité en nombre des copropriétaires (2 sur 3).
    assert evaluate_resolution("art26", 7000, 0, 0, 10000, 3, 2)[0] == "adopted"
    # 2/3 des tantièmes mais minorité en nombre (1 sur 3) → rejetée + note.
    outcome, note = evaluate_resolution("art26", 7000, 0, 0, 10000, 3, 1)
    assert outcome == "rejected"
    assert note and "copropriétaires" in note
    # Majorité en nombre mais pas les 2/3 des tantièmes → rejetée.
    assert evaluate_resolution("art26", 6000, 0, 0, 10000, 3, 3)[0] == "rejected"


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
async def test_art26_integration_members_vs_tantiemes(db, gestionnaire_user):
    """art. 26 : un seul copropriétaire majoritaire en tantièmes (7000/9000) ne
    suffit pas sans la majorité EN NOMBRE des copropriétaires."""
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="AG26"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen = detail["keys"][0]["id"]
    await CoproprieteService.update_key(
        db, copro.id, gen, RepartitionKeyUpdate(total_tantiemes=9000)
    )
    owners = []
    for i, t in enumerate((7000, 1000, 1000)):
        o = Owner(last_name=f"M{i}", first_name="x", created_by=gestionnaire_user.id)
        db.add(o)
        await db.flush()
        owners.append(o)
        await CoproprieteService.create_lot(
            db,
            copro.id,
            LotCreate(
                numero=f"L{i}", owner_id=o.id, tantiemes=[LotTantiemeIn(key_id=gen, tantiemes=t)]
            ),
        )
    ag = await CoproAGService.create_assembly(
        db, copro.id, AssemblyCreate(title="AG"), created_by=gestionnaire_user.id
    )
    d = await CoproAGService.add_resolution(
        db, copro.id, ag["id"], ResolutionCreate(title="Travaux", majority="art26")
    )
    rid = d["resolutions"][0]["id"]
    # Seul le gros copropriétaire (7000/9000) vote pour : 2/3 des tantièmes OK,
    # mais 1 copropriétaire sur 3 → majorité en nombre NON atteinte → rejetée.
    d = await CoproAGService.set_vote(db, copro.id, ag["id"], rid, owners[0].id, "pour")
    r = d["resolutions"][0]
    assert r["pour"] == 7000
    assert r["outcome"] == "rejected"
    assert r["outcome_note"] and "copropriétaires" in r["outcome_note"]
    # Deux copropriétaires sur trois votent pour (7000+1000=8000) → adoptée.
    d = await CoproAGService.set_vote(db, copro.id, ag["id"], rid, owners[1].id, "pour")
    assert d["resolutions"][0]["outcome"] == "adopted"


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
