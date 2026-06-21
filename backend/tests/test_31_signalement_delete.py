"""Suppression d'un signalement par le locataire (Allô gardien !)."""
import pytest

from tests.conftest import auth


async def _make_sig(db, gestionnaire_user, locataire_user):
    from app.models.property import Property
    from app.models.signalement import Signalement

    prop = Property(
        name="Résidence Test",
        address="1 rue du Gardien",
        zip_code="75001",
        city="Paris",
        country="France",
        property_type="appartement",
        created_by=gestionnaire_user.id,
    )
    db.add(prop)
    await db.flush()
    sig = Signalement(
        category="bruit",
        description="Voisin bruyant",
        created_by=locataire_user.id,
        property_id=prop.id,
    )
    db.add(sig)
    await db.flush()
    return sig


@pytest.mark.asyncio
async def test_locataire_deletes_own_signalement(
    client, db, gestionnaire_user, locataire_user, locataire_token
):
    sig = await _make_sig(db, gestionnaire_user, locataire_user)
    r = await client.delete(f"/api/v1/signalements/{sig.id}", headers=auth(locataire_token))
    assert r.status_code == 204, r.text

    from app.models.signalement import Signalement

    assert await db.get(Signalement, sig.id) is None


@pytest.mark.asyncio
async def test_other_user_cannot_delete_signalement(
    client, db, gestionnaire_user, locataire_user, proprietaire_token
):
    sig = await _make_sig(db, gestionnaire_user, locataire_user)
    r = await client.delete(f"/api/v1/signalements/{sig.id}", headers=auth(proprietaire_token))
    assert r.status_code == 403, r.text
