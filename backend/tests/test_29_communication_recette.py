"""Recette « Communication et automatisation » : helpers moteur + modèles
multilingues + assistance IA. Vérifie CC gestionnaire, signature par type,
sélection de langue (repli fr), et isolation des modèles.
"""
import pytest
from httpx import AsyncClient

from app.models.automation import AutomationRule
from app.models.message_template import MessageTemplate
from app.services import automation_engine as ae
from tests.conftest import auth


# ── Helpers purs ──────────────────────────────────────────────────────────────

def test_signature_par_type():
    assert ae._signature_for("rappel_impaye") == "Service contentieux"
    assert ae._signature_for("relance_1") == "Service contentieux"
    assert ae._signature_for("relance_2") == "Service contentieux"
    assert ae._signature_for("avis_echeance") == "Service Gestion Locative"
    assert ae._signature_for("quittance") == "Service Gestion Locative"
    assert ae._signature_for("rapport_mensuel") == "Service Gestion Locative"


@pytest.mark.asyncio
async def test_cc_inclut_gestionnaire_et_dedup(db, gestionnaire_user):
    rule = AutomationRule(name="Avis", rule_type="avis_echeance",
                          created_by=gestionnaire_user.id,
                          cc_emails=f"agence@x.fr, {gestionnaire_user.email.upper()}")
    db.add(rule)
    await db.flush()
    cc = await ae._cc_with_manager(db, rule)
    parts = [p.strip().lower() for p in cc.split(",")]
    # Gestionnaire présent…
    assert gestionnaire_user.email.lower() in parts
    # …une seule fois (dédup casse-insensible)…
    assert parts.count(gestionnaire_user.email.lower()) == 1
    # …et le CC d'origine conservé.
    assert "agence@x.fr" in parts


@pytest.mark.asyncio
async def test_cc_ajoute_gestionnaire_si_cc_vide(db, gestionnaire_user):
    rule = AutomationRule(name="Relance", rule_type="relance_1",
                          created_by=gestionnaire_user.id, cc_emails=None)
    db.add(rule)
    await db.flush()
    cc = await ae._cc_with_manager(db, rule)
    assert cc and gestionnaire_user.email.lower() in cc.lower()


# ── Sélection de langue des modèles ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_msg_templates_langue_locataire_et_repli(db, gestionnaire_user):
    rule = AutomationRule(name="Avis", rule_type="avis_echeance",
                          created_by=gestionnaire_user.id,
                          subject="DEF subj", body_template="DEF body")
    db.add(rule)
    db.add(MessageTemplate(
        gestionnaire_id=gestionnaire_user.id, rule_type="avis_echeance", name="Std",
        is_selected=True, is_active=True,
        content={"fr": {"subject": "FR s", "body": "FR b", "sms": "FR sms"},
                 "en": {"subject": "EN s", "body": "EN b", "sms": "EN sms"}},
    ))
    await db.flush()

    # Langue présente → contenu de cette langue.
    subj, body, sms = await ae._msg_templates(db, rule, "en")
    assert (subj, body, sms) == ("EN s", "EN b", "EN sms")
    # Langue absente (pt-BR) → repli français.
    subj, _, _ = await ae._msg_templates(db, rule, "pt-BR")
    assert subj == "FR s"


@pytest.mark.asyncio
async def test_msg_templates_repli_regle_si_pas_de_modele(db, gestionnaire_user):
    rule = AutomationRule(name="Quittance", rule_type="quittance",
                          created_by=gestionnaire_user.id,
                          subject="RULE subj", body_template="RULE body")
    db.add(rule)
    await db.flush()
    subj, body, sms = await ae._msg_templates(db, rule, "fr")
    assert subj == "RULE subj" and body == "RULE body"


# ── API modèles de courrier ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_message_templates_crud_et_select(client: AsyncClient, gestionnaire_token):
    h = auth(gestionnaire_token)
    # Création de 2 modèles pour le même type.
    r1 = await client.post("/api/v1/message-templates", headers=h, json={
        "rule_type": "avis_echeance", "name": "A",
        "content": {"fr": {"subject": "a", "body": "b", "sms": "s"}}, "is_selected": True})
    assert r1.status_code == 201, r1.text
    r2 = await client.post("/api/v1/message-templates", headers=h, json={
        "rule_type": "avis_echeance", "name": "B",
        "content": {"fr": {"subject": "a2", "body": "b2", "sms": "s2"}}})
    assert r2.status_code == 201
    id2 = r2.json()["id"]

    # Sélectionner B doit désélectionner A.
    rs = await client.post(f"/api/v1/message-templates/{id2}/select", headers=h)
    assert rs.status_code == 200 and rs.json()["is_selected"] is True
    lst = (await client.get("/api/v1/message-templates?rule_type=avis_echeance", headers=h)).json()
    selected = [t for t in lst if t["is_selected"]]
    assert len(selected) == 1 and selected[0]["id"] == id2


@pytest.mark.asyncio
async def test_message_templates_isolation(client: AsyncClient, gestionnaire_token, gp_token):
    h1 = auth(gestionnaire_token)
    await client.post("/api/v1/message-templates", headers=h1, json={
        "rule_type": "quittance", "name": "Privé",
        "content": {"fr": {"subject": "x", "body": "y", "sms": "z"}}})
    # Un autre gestionnaire ne voit pas les modèles du premier.
    other = (await client.get("/api/v1/message-templates", headers=auth(gp_token))).json()
    assert all(t["name"] != "Privé" for t in other)


@pytest.mark.asyncio
async def test_ai_assist_repli_defaut(client: AsyncClient, gestionnaire_token):
    """Sans LLM configuré, l'assistance IA renvoie les modèles par défaut."""
    r = await client.post("/api/v1/message-templates/ai-assist", headers=auth(gestionnaire_token),
                          json={"rule_type": "relance_1", "langs": ["fr", "en"]})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "content" in data and "fr" in data["content"]
    assert data["content"]["fr"].get("subject")


@pytest.mark.asyncio
async def test_tenant_language_persiste(client: AsyncClient, gestionnaire_token):
    h = auth(gestionnaire_token)
    r = await client.post("/api/v1/tenants", headers=h, json={
        "first_name": "Jean", "last_name": "Test", "email": "jeantest@x.fr",
        "language": "ht"})
    assert r.status_code in (200, 201), r.text
    assert r.json().get("language") == "ht"
