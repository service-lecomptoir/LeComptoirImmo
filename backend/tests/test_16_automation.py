"""
Tests API — Automatisation (règles d'envoi + logs de communication).
Couvre : CRUD règles, toggle actif, isolation GP/mandataire, communication groupée.
"""
import pytest
from tests.conftest import auth

RULE_PAYLOAD = {
    "name": "Avis J-5",
    "rule_type": "avis_echeance",
    "trigger_days": 5,
    "channel": "email",
    "subject": "Votre loyer arrive à échéance",
    "body_template": "Bonjour {{first_name}}, votre loyer est dû dans {{days}} jours.",
    "is_active": True,
}


@pytest.mark.asyncio
class TestAutomationRuleCRUD:
    async def test_gestionnaire_can_create_rule(self, client, gestionnaire_token):
        resp = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Avis J-5"
        assert data["rule_type"] == "avis_echeance"
        assert data["is_active"] is True

    async def test_gp_can_create_rule(self, client, gp_token):
        resp = await client.post("/api/v1/automation/rules", headers=auth(gp_token), json={
            **RULE_PAYLOAD, "name": "Règle GP",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Règle GP"

    async def test_locataire_cannot_create_rule(self, client, locataire_token):
        resp = await client.post("/api/v1/automation/rules", headers=auth(locataire_token), json=RULE_PAYLOAD)
        assert resp.status_code == 403

    async def test_proprietaire_cannot_create_rule(self, client, proprietaire_token):
        resp = await client.post("/api/v1/automation/rules", headers=auth(proprietaire_token), json=RULE_PAYLOAD)
        assert resp.status_code == 403

    async def test_list_rules(self, client, gestionnaire_token):
        await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        resp = await client.get("/api/v1/automation/rules", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_get_rule_by_id(self, client, gestionnaire_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.get(f"/api/v1/automation/rules/{rule_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert resp.json()["id"] == rule_id

    async def test_get_unknown_rule_returns_404(self, client, gestionnaire_token):
        resp = await client.get(
            "/api/v1/automation/rules/00000000-0000-0000-0000-000000000099",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 404

    async def test_update_rule(self, client, gestionnaire_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/automation/rules/{rule_id}",
            headers=auth(gestionnaire_token),
            json={"trigger_days": 10, "subject": "Nouveau sujet"},
        )
        assert resp.status_code == 200
        assert resp.json()["trigger_days"] == 10
        assert resp.json()["subject"] == "Nouveau sujet"

    async def test_delete_rule(self, client, gestionnaire_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/automation/rules/{rule_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 204
        get = await client.get(f"/api/v1/automation/rules/{rule_id}", headers=auth(gestionnaire_token))
        assert get.status_code == 404

    async def test_toggle_rule_active(self, client, gestionnaire_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json={
            **RULE_PAYLOAD, "is_active": True,
        })
        rule_id = create.json()["id"]

        resp = await client.post(
            f"/api/v1/automation/rules/{rule_id}/toggle",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        resp2 = await client.post(
            f"/api/v1/automation/rules/{rule_id}/toggle",
            headers=auth(gestionnaire_token),
        )
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is True

    async def test_filter_rules_by_type(self, client, gestionnaire_token):
        await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json={
            **RULE_PAYLOAD, "rule_type": "rappel_impaye",
        })
        resp = await client.get(
            "/api/v1/automation/rules?rule_type=rappel_impaye",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 200
        for r in resp.json():
            assert r["rule_type"] == "rappel_impaye"


@pytest.mark.asyncio
class TestAutomationIsolation:
    """GP et mandataire ne voient pas les règles de l'autre."""

    async def test_gp_cannot_see_gestionnaire_rule(self, client, gestionnaire_token, gp_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.get(f"/api/v1/automation/rules/{rule_id}", headers=auth(gp_token))
        assert resp.status_code == 403

    async def test_gestionnaire_cannot_see_gp_rule(self, client, gp_token, gestionnaire_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gp_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.get(f"/api/v1/automation/rules/{rule_id}", headers=auth(gestionnaire_token))
        assert resp.status_code == 403

    async def test_gp_list_excludes_gestionnaire_rules(self, client, gestionnaire_token, gp_token):
        await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json={
            **RULE_PAYLOAD, "name": "RegleExcluDeGP",
        })
        resp = await client.get("/api/v1/automation/rules", headers=auth(gp_token))
        assert resp.status_code == 200
        assert not any(r["name"] == "RegleExcluDeGP" for r in resp.json())

    async def test_gestionnaire_list_excludes_gp_rules(self, client, gp_token, gestionnaire_token):
        await client.post("/api/v1/automation/rules", headers=auth(gp_token), json={
            **RULE_PAYLOAD, "name": "RegleExcluDeMand",
        })
        resp = await client.get("/api/v1/automation/rules", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert not any(r["name"] == "RegleExcluDeMand" for r in resp.json())

    async def test_gp_cannot_update_gestionnaire_rule(self, client, gestionnaire_token, gp_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.patch(
            f"/api/v1/automation/rules/{rule_id}",
            headers=auth(gp_token),
            json={"trigger_days": 99},
        )
        assert resp.status_code == 403

    async def test_gp_cannot_delete_gestionnaire_rule(self, client, gestionnaire_token, gp_token):
        create = await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json=RULE_PAYLOAD)
        rule_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/automation/rules/{rule_id}", headers=auth(gp_token))
        assert resp.status_code == 403

    async def test_admin_can_see_all_rules(self, client, admin_token, gestionnaire_token, gp_token):
        await client.post("/api/v1/automation/rules", headers=auth(gestionnaire_token), json={
            **RULE_PAYLOAD, "name": "AdminVoitMand",
        })
        await client.post("/api/v1/automation/rules", headers=auth(gp_token), json={
            **RULE_PAYLOAD, "name": "AdminVoitGP",
        })
        resp = await client.get("/api/v1/automation/rules", headers=auth(admin_token))
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()]
        assert "AdminVoitMand" in names
        assert "AdminVoitGP" in names


@pytest.mark.asyncio
class TestCommunicationLogs:
    async def test_gestionnaire_can_list_logs(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/automation/logs", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_gp_can_list_logs(self, client, gp_token):
        resp = await client.get("/api/v1/automation/logs", headers=auth(gp_token))
        assert resp.status_code == 200

    async def test_locataire_cannot_list_logs(self, client, locataire_token):
        resp = await client.get("/api/v1/automation/logs", headers=auth(locataire_token))
        assert resp.status_code == 403


@pytest.mark.asyncio
class TestGroupCommunication:
    async def test_gestionnaire_can_send_group_email(self, client, gestionnaire_token):
        resp = await client.post(
            "/api/v1/automation/send-group",
            headers=auth(gestionnaire_token),
            json={
                "subject": "Test communication groupée",
                "body": "Bonjour à tous les locataires.",
                "channel": "email",
                "all_tenants": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sent_count" in data
        assert "total_targets" in data

    async def test_locataire_cannot_send_group(self, client, locataire_token):
        resp = await client.post(
            "/api/v1/automation/send-group",
            headers=auth(locataire_token),
            json={
                "subject": "Hack",
                "body": "Hack.",
                "channel": "email",
            },
        )
        assert resp.status_code == 403
