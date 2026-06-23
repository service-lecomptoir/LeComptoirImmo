"""Module Syndic — phase 4 : fonds de travaux (ALUR) et carnet d'entretien."""

from datetime import date

import pytest

from app.schemas.copropriete import CoproprieteCreate
from app.schemas.copropriete_extras import (
    MaintenanceCreate,
    MaintenanceUpdate,
    WorksFundEntryCreate,
)
from app.services.copro_extras_service import CoproExtrasService
from app.services.copropriete_service import CoproprieteService


async def _copro(db, manager):
    return await CoproprieteService.create(
        db, CoproprieteCreate(name="Résidence Extras"), created_by=manager.id
    )


@pytest.mark.asyncio
async def test_works_fund_balance(db, gestionnaire_user):
    copro = await _copro(db, gestionnaire_user)
    await CoproExtrasService.add_works_entry(
        db,
        copro.id,
        WorksFundEntryCreate(
            entry_date=date(2026, 1, 1), kind="contribution", label="Cotisation 2026", amount=5000
        ),
        created_by=gestionnaire_user.id,
    )
    await CoproExtrasService.add_works_entry(
        db,
        copro.id,
        WorksFundEntryCreate(
            entry_date=date(2026, 6, 1), kind="depense", label="Ravalement", amount=2000
        ),
        created_by=gestionnaire_user.id,
    )
    fund = await CoproExtrasService.works_fund(db, copro.id)
    assert fund["total_contributions"] == 5000
    assert fund["total_depenses"] == 2000
    assert fund["balance"] == 3000
    assert len(fund["entries"]) == 2


@pytest.mark.asyncio
async def test_works_fund_delete(db, gestionnaire_user):
    copro = await _copro(db, gestionnaire_user)
    e = await CoproExtrasService.add_works_entry(
        db,
        copro.id,
        WorksFundEntryCreate(
            entry_date=date(2026, 1, 1), kind="contribution", label="C", amount=1000
        ),
        created_by=gestionnaire_user.id,
    )
    await CoproExtrasService.delete_works_entry(db, copro.id, e["id"])
    fund = await CoproExtrasService.works_fund(db, copro.id)
    assert fund["balance"] == 0


@pytest.mark.asyncio
async def test_works_entry_validation():
    with pytest.raises(ValueError):
        WorksFundEntryCreate(entry_date=date(2026, 1, 1), kind="autre", label="x", amount=10)
    with pytest.raises(ValueError):
        WorksFundEntryCreate(entry_date=date(2026, 1, 1), kind="depense", label="x", amount=0)


@pytest.mark.asyncio
async def test_maintenance_crud(db, gestionnaire_user):
    copro = await _copro(db, gestionnaire_user)
    m = await CoproExtrasService.add_maintenance(
        db,
        copro.id,
        MaintenanceCreate(
            entry_date=date(2026, 3, 1),
            category="Ascenseur",
            description="Visite annuelle",
            supplier="OTIS",
            cost=350,
        ),
        created_by=gestionnaire_user.id,
    )
    assert m["category"] == "Ascenseur"
    assert m["cost"] == 350
    rows = await CoproExtrasService.list_maintenance(db, copro.id)
    assert len(rows) == 1
    await CoproExtrasService.update_maintenance(
        db, copro.id, m["id"], MaintenanceUpdate(cost=400, supplier="KONE")
    )
    rows = await CoproExtrasService.list_maintenance(db, copro.id)
    assert rows[0]["cost"] == 400
    assert rows[0]["supplier"] == "KONE"
    await CoproExtrasService.delete_maintenance(db, copro.id, m["id"])
    assert await CoproExtrasService.list_maintenance(db, copro.id) == []
