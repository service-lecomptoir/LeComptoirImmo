"""Module Syndic (copropriété) — phase 1 : copropriété, clés de répartition,
lots et tantièmes. CRUD + contrôle d'équilibre des tantièmes + isolation."""

import pytest

from app.models.owner import Owner
from app.schemas.copropriete import (
    CoproprieteCreate,
    CoproprieteUpdate,
    LotCreate,
    LotTantiemeIn,
    RepartitionKeyCreate,
)
from app.services.copropriete_service import CoproprieteService


async def _make_owner(db, manager, suffix="a"):
    o = Owner(last_name=f"Copro{suffix}", first_name="Jean", created_by=manager.id)
    db.add(o)
    await db.flush()
    return o


@pytest.mark.asyncio
async def test_create_copro_has_ref_and_default_general_key(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Résidence Test", city="Paris"), created_by=gestionnaire_user.id
    )
    assert copro.ref_code and copro.ref_code.startswith("CP")
    detail = await CoproprieteService.get_detail(db, copro.id)
    # Une clé générale par défaut est créée.
    assert len(detail["keys"]) == 1
    assert detail["keys"][0]["is_general"] is True
    assert detail["keys"][0]["total_tantiemes"] == 10000


@pytest.mark.asyncio
async def test_lots_and_tantiemes_balance(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Equilibre"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen_key = detail["keys"][0]["id"]
    # Clé spéciale ascenseur (base 1000).
    asc = await CoproprieteService.add_key(
        db, copro.id, RepartitionKeyCreate(name="Ascenseur", total_tantiemes=1000)
    )

    o1 = await _make_owner(db, gestionnaire_user, "1")
    o2 = await _make_owner(db, gestionnaire_user, "2")
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(
            numero="Lot 1",
            owner_id=o1.id,
            tantiemes=[
                LotTantiemeIn(key_id=gen_key, tantiemes=6000),
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
                LotTantiemeIn(key_id=gen_key, tantiemes=4000),
                LotTantiemeIn(key_id=asc.id, tantiemes=400),
            ],
        ),
    )

    detail = await CoproprieteService.get_detail(db, copro.id)
    assert len(detail["lots"]) == 2
    by_id = {k["id"]: k for k in detail["keys"]}
    # Clé générale : 6000 + 4000 = 10000 → équilibrée.
    assert by_id[gen_key]["assigned_tantiemes"] == 10000
    assert by_id[gen_key]["balanced"] is True
    # Ascenseur : 600 + 400 = 1000 → équilibrée.
    assert by_id[asc.id]["assigned_tantiemes"] == 1000
    assert by_id[asc.id]["balanced"] is True
    # owner_name renseigné depuis la fiche Owner.
    assert any(lot["owner_name"] for lot in detail["lots"])


@pytest.mark.asyncio
async def test_unbalanced_key_flagged(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Desequilibre"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen_key = detail["keys"][0]["id"]
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(numero="Lot A", tantiemes=[LotTantiemeIn(key_id=gen_key, tantiemes=5000)]),
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    k = detail["keys"][0]
    assert k["assigned_tantiemes"] == 5000
    assert k["balanced"] is False  # 5000 != 10000


@pytest.mark.asyncio
async def test_update_lot_replaces_tantiemes(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="MajLot"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen_key = detail["keys"][0]["id"]
    lot = await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(numero="Lot 1", tantiemes=[LotTantiemeIn(key_id=gen_key, tantiemes=3000)]),
    )
    from app.schemas.copropriete import LotUpdate

    await CoproprieteService.update_lot(
        db,
        copro.id,
        lot.id,
        LotUpdate(numero="Lot 1 bis", tantiemes=[LotTantiemeIn(key_id=gen_key, tantiemes=7000)]),
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    assert detail["lots"][0]["numero"] == "Lot 1 bis"
    assert detail["lots"][0]["tantiemes"][str(gen_key)] == 7000
    assert detail["keys"][0]["assigned_tantiemes"] == 7000


@pytest.mark.asyncio
async def test_delete_copro_cascades(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="ASupprimer"), created_by=gestionnaire_user.id
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    gen_key = detail["keys"][0]["id"]
    await CoproprieteService.create_lot(
        db,
        copro.id,
        LotCreate(numero="Lot 1", tantiemes=[LotTantiemeIn(key_id=gen_key, tantiemes=10000)]),
    )
    await CoproprieteService.delete(db, copro.id)
    from app.core.exceptions import NotFoundException

    with pytest.raises(NotFoundException):
        await CoproprieteService.get_by_id(db, copro.id)


@pytest.mark.asyncio
async def test_update_copro_fields(db, gestionnaire_user):
    copro = await CoproprieteService.create(
        db, CoproprieteCreate(name="Init"), created_by=gestionnaire_user.id
    )
    await CoproprieteService.update(
        db, copro.id, CoproprieteUpdate(name="Renommée", immatriculation="AB123456")
    )
    detail = await CoproprieteService.get_detail(db, copro.id)
    assert detail["name"] == "Renommée"
    assert detail["immatriculation"] == "AB123456"
