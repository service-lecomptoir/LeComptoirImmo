# -*- coding: utf-8 -*-
"""Tests — Équipe d'agents IA + liaison Telegram (Phase 1 déterministe)."""
import pytest
from tests.conftest import auth
from app.services import agent_team_service as ats


# ── Routeur déterministe (fonction pure, sans base) ──────────────────────────
class TestClassify:
    def test_help_and_empty(self):
        assert ats.classify("") == "help"
        assert ats.classify("   ") == "help"
        assert ats.classify("bonjour") == "help"
        assert ats.classify("aide") == "help"
        assert ats.classify("/start") == "help"

    def test_reminders(self):
        assert ats.classify("résumé") == "reminders"
        assert ats.classify("fais-moi un rappel") == "reminders"

    def test_comptable(self):
        assert ats.classify("quels sont mes impayés ?") == "comptable"
        assert ats.classify("combien j'ai encaissé ce mois") == "comptable"
        assert ats.classify("loyer en retard") == "comptable"

    def test_securite(self):
        assert ats.classify("un conflit de voisinage") == "securite"
        assert ats.classify("démarches en cours") == "securite"
        assert ats.classify("il y a un incident") == "securite"

    def test_administratif(self):
        assert ats.classify("combien de biens ai-je") == "administratif"
        assert ats.classify("mes locataires") == "administratif"
        assert ats.classify("contrats actifs") == "administratif"

    def test_help_content_lists_three_agents(self):
        h = ats._help()
        assert "Agent Comptable" in h
        assert "Agent Sécurité" in h
        assert "Agent Administratif" in h


# ── answer() bout-en-bout (admin, base de test) ──────────────────────────────
@pytest.mark.asyncio
class TestAnswer:
    async def test_help_route(self, db, admin_user):
        reply = await ats.answer(db, admin_user, "bonjour")
        assert "équipe d'agents" in reply.lower() or "Agent Comptable" in reply

    async def test_administratif_route(self, db, admin_user):
        reply = await ats.answer(db, admin_user, "combien de biens")
        assert "administrative" in reply.lower()
        assert "Biens" in reply

    async def test_comptable_route(self, db, admin_user):
        reply = await ats.answer(db, admin_user, "impayés")
        assert "📊" in reply

    async def test_securite_route(self, db, admin_user):
        reply = await ats.answer(db, admin_user, "démarches en cours")
        assert "🛡️" in reply

    async def test_reminders(self, db, admin_user):
        reply = await ats.reminders(db, admin_user)
        assert "point du jour" in reply.lower()


# ── Liaison Telegram (endpoints gestionnaire + webhook public) ───────────────
@pytest.mark.asyncio
class TestTelegramLink:
    async def test_link_code_status_and_unlink(self, client, gestionnaire_token):
        # Génération du code
        gen = await client.post("/api/v1/agents/telegram/link-code", headers=auth(gestionnaire_token))
        assert gen.status_code == 200, gen.text
        data = gen.json()
        assert data["code"] and len(data["code"]) == 8
        assert "enabled" in data

        # Statut initial : non lié
        st = await client.get("/api/v1/agents/telegram/status", headers=auth(gestionnaire_token))
        assert st.status_code == 200, st.text
        assert st.json()["linked"] is False

        # Webhook : /start <code> → liaison du chat
        wh = await client.post("/api/v1/telegram/webhook", json={
            "message": {"chat": {"id": 123456789}, "text": f"/start {data['code']}"},
        })
        assert wh.status_code == 200, wh.text

        # Statut après liaison : lié
        st2 = await client.get("/api/v1/agents/telegram/status", headers=auth(gestionnaire_token))
        assert st2.json()["linked"] is True

        # Délier
        unl = await client.post("/api/v1/agents/telegram/unlink", headers=auth(gestionnaire_token))
        assert unl.status_code == 200, unl.text
        assert unl.json()["linked"] is False

        st3 = await client.get("/api/v1/agents/telegram/status", headers=auth(gestionnaire_token))
        assert st3.json()["linked"] is False

    async def test_webhook_unknown_chat_is_noop_ok(self, client):
        wh = await client.post("/api/v1/telegram/webhook", json={
            "message": {"chat": {"id": 999000111}, "text": "impayés"},
        })
        assert wh.status_code == 200
        assert wh.json() == {"ok": True}

    async def test_webhook_requires_auth_for_link_endpoints(self, client):
        # Sans jeton → 401/403
        r = await client.post("/api/v1/agents/telegram/link-code")
        assert r.status_code in (401, 403)
