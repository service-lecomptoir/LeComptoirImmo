"""Recette : demande de pièces à un candidat + dépôt public + suivi.

Flux : le gestionnaire sélectionne les pièces et envoie un lien ; le candidat
dépose ses fichiers via le lien public (sans compte) ; le gestionnaire les
télécharge et fait évoluer le dossier.
"""
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import auth
from app.api.v1.candidatures import default_docs
from app.models.candidature import Candidature
from app.models.property import Property


async def _make_property(db, owner_user, name="Bien test"):
    prop = Property(
        name=name, address="1 rue de Test", zip_code="75001", city="Paris",
        property_type="appartement", created_by=owner_user.id,
    )
    db.add(prop)
    await db.flush()
    return prop


@pytest.mark.asyncio
async def test_request_documents_full_flow(client, db, gestionnaire_user, gestionnaire_token):
    prop = await _make_property(db, gestionnaire_user)
    cand = Candidature(
        property_id=prop.id, full_name="Jean Candidat", email="cand@test.fr",
        docs=default_docs(), source="manuel", created_by=gestionnaire_user.id,
    )
    db.add(cand)
    await db.commit()
    cid = str(cand.id)

    # 1) Le gestionnaire demande deux pièces.
    r = await client.post(
        f"/api/v1/candidatures/{cid}/request-documents",
        headers=auth(gestionnaire_token),
        json={"doc_keys": ["identite", "avis_imposition"], "message": "Merci de votre dossier"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "documents_demandes"
    assert data["upload_token"] and data["upload_url"] and "/candidature/" in data["upload_url"]
    required = {d["key"] for d in data["docs"] if d["required"]}
    assert required == {"identite", "avis_imposition"}
    token = data["upload_token"]

    # 2) Page publique : les deux pièces demandées, non encore fournies.
    pr = await client.get(f"/api/v1/public/candidature/{token}")
    assert pr.status_code == 200, pr.text
    docs = pr.json()["documents"]
    assert {d["key"] for d in docs} == {"identite", "avis_imposition"}
    assert all(not d["provided"] for d in docs)

    # 3) Le candidat dépose un fichier pour « identite ».
    ur = await client.post(
        f"/api/v1/public/candidature/{token}/upload",
        data={"key": "identite"},
        files={"file": ("piece.pdf", b"%PDF-1.4 contenu test", "application/pdf")},
    )
    assert ur.status_code == 200, ur.text

    # 4) La page publique reflète le dépôt. On expire l'identity map pour forcer
    #    une relecture depuis la base : garantit que la mutation JSONB a bien été
    #    PERSISTÉE (et pas seulement visible via l'objet en mémoire).
    db.expire_all()
    pub = (await client.get(f"/api/v1/public/candidature/{token}")).json()
    idd = next(d for d in pub["documents"] if d["key"] == "identite")
    assert idd["provided"] is True, "le dépôt n'a pas été persisté"
    assert pub["all_provided"] is False  # avis_imposition manque encore

    # 5) Le gestionnaire télécharge la pièce déposée.
    dl = await client.get(
        f"/api/v1/candidatures/{cid}/documents/identite/download",
        headers=auth(gestionnaire_token),
    )
    assert dl.status_code == 200

    # 6) Le candidat confirme le dépôt (notifie le gestionnaire).
    sub = await client.post(f"/api/v1/public/candidature/{token}/submit")
    assert sub.status_code == 200

    # 7) Le gestionnaire met le dossier à l'étude.
    up = await client.patch(
        f"/api/v1/candidatures/{cid}", headers=auth(gestionnaire_token),
        json={"status": "en_etude"},
    )
    assert up.status_code == 200 and up.json()["status"] == "en_etude"


@pytest.mark.asyncio
async def test_request_documents_requires_email(client, db, gestionnaire_user, gestionnaire_token):
    prop = await _make_property(db, gestionnaire_user, name="Bien sans email")
    cand = Candidature(
        property_id=prop.id, full_name="Sans Email", docs=default_docs(),
        source="manuel", created_by=gestionnaire_user.id,
    )
    db.add(cand)
    await db.commit()
    r = await client.post(
        f"/api/v1/candidatures/{cand.id}/request-documents",
        headers=auth(gestionnaire_token), json={"doc_keys": ["identite"]},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_visit_invitation_and_booking(client, db, gestionnaire_user, gestionnaire_token):
    prop = await _make_property(db, gestionnaire_user, name="Bien visite")
    cand = Candidature(
        property_id=prop.id, full_name="Paul Visite", email="paul@test.fr",
        docs=default_docs(), source="manuel", created_by=gestionnaire_user.id,
    )
    db.add(cand)
    await db.commit()
    cid = str(cand.id)
    h = auth(gestionnaire_token)

    # Sans créneau : l'invitation est refusée.
    r0 = await client.post(f"/api/v1/candidatures/{cid}/invite-visit", headers=h, json={})
    assert r0.status_code == 400

    # Crée un créneau futur (capacité 2).
    when = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    rs = await client.post("/api/v1/candidatures/visit-slots", headers=h, json={
        "property_id": str(prop.id), "starts_at": when, "duration_min": 30, "capacity": 2,
    })
    assert rs.status_code == 201, rs.text
    slot_id = rs.json()["id"]

    # Invitation OK.
    ri = await client.post(f"/api/v1/candidatures/{cid}/invite-visit", headers=h, json={})
    assert ri.status_code == 200, ri.text
    assert ri.json()["visit_invited"] is True
    token = ri.json()["upload_token"]

    # Page publique : le créneau est proposé (ref du bien, pas le nom).
    pv = (await client.get(f"/api/v1/public/candidature/{token}/visits")).json()
    assert pv["booked_slot_id"] is None
    assert any(s["id"] == slot_id for s in pv["slots"])

    # Réservation par le candidat.
    bk = await client.post(f"/api/v1/public/candidature/{token}/visits/{slot_id}/book")
    assert bk.status_code == 200, bk.text

    db.expire_all()
    pv2 = (await client.get(f"/api/v1/public/candidature/{token}/visits")).json()
    assert pv2["booked_slot_id"] == slot_id

    # Relance avant visite (manuelle) : nécessite un créneau réservé.
    rr = await client.post(f"/api/v1/candidatures/{cid}/remind-visit", headers=h)
    assert rr.status_code == 200, rr.text
    assert "email_sent" in rr.json()

    # Accusé de réception (manuel).
    rk = await client.post(f"/api/v1/candidatures/{cid}/acknowledge", headers=h, json={})
    assert rk.status_code == 200, rk.text

    # Acceptation finale.
    ra = await client.post(f"/api/v1/candidatures/{cid}/accept", headers=h, json={})
    assert ra.status_code == 200 and ra.json()["status"] == "retenue"


@pytest.mark.asyncio
async def test_remind_visit_requires_booking(client, db, gestionnaire_user, gestionnaire_token):
    prop = await _make_property(db, gestionnaire_user, name="Bien sans visite")
    cand = Candidature(
        property_id=prop.id, full_name="Sans Visite", email="sv@test.fr",
        docs=default_docs(), source="manuel", created_by=gestionnaire_user.id,
    )
    db.add(cand)
    await db.commit()
    r = await client.post(f"/api/v1/candidatures/{cand.id}/remind-visit", headers=auth(gestionnaire_token))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_public_upload_rejects_non_requested_doc(client, db, gestionnaire_user, gestionnaire_token):
    prop = await _make_property(db, gestionnaire_user, name="Bien upload")
    cand = Candidature(
        property_id=prop.id, full_name="Marie Candidat", email="marie@test.fr",
        docs=default_docs(), source="manuel", created_by=gestionnaire_user.id,
    )
    db.add(cand)
    await db.commit()
    r = await client.post(
        f"/api/v1/candidatures/{cand.id}/request-documents",
        headers=auth(gestionnaire_token), json={"doc_keys": ["identite"]},
    )
    token = r.json()["upload_token"]
    # Pièce non demandée → refus.
    ur = await client.post(
        f"/api/v1/public/candidature/{token}/upload",
        data={"key": "dossier_garant"},
        files={"file": ("g.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert ur.status_code == 400
