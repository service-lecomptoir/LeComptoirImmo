"""Tests — périmètre de l'espace bailleur réglé par le gestionnaire.

Le gestionnaire choisit, à la création du compte bailleur, les rubriques visibles
(préréglage restreint par défaut). L'accès est appliqué côté backend : un bailleur
reçoit 403 sur une rubrique non autorisée (cohérent avec le menu masqué).
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.proprio_sections import DEFAULT_NEW_PROPRIO_KEYS
from app.models.user import User as UserModel
from tests.conftest import auth


@pytest.mark.asyncio
class TestProprioSectionEnforcement:
    async def test_section_non_autorisee_403(
        self, client, db, proprietaire_user, proprietaire_token
    ):
        # Le gestionnaire restreint ce bailleur au seul tableau de bord.
        proprietaire_user.proprio_visibility = ["dashboard"]
        await db.flush()
        # Rubrique fiscale non autorisée → 403.
        r = await client.get("/api/v1/dashboard/fiscal/2025", headers=auth(proprietaire_token))
        assert r.status_code == 403, r.text
        # Rubrique « revenus » non autorisée → 403 (endpoint partagé /payments).
        r2 = await client.get("/api/v1/payments", headers=auth(proprietaire_token))
        assert r2.status_code == 403, r2.text

    async def test_section_autorisee_passe(self, client, db, proprietaire_user, proprietaire_token):
        proprietaire_user.proprio_visibility = ["dashboard"]
        await db.flush()
        # Le tableau de bord est autorisé → pas de 403 (le contrôle de section passe).
        r = await client.get(
            "/api/v1/dashboard/proprietaire-stats", headers=auth(proprietaire_token)
        )
        assert r.status_code != 403, r.text

    async def test_non_proprietaire_non_impacte(self, client, gestionnaire_token):
        # Un gestionnaire n'est jamais filtré par le périmètre bailleur.
        r = await client.get("/api/v1/payments", headers=auth(gestionnaire_token))
        assert r.status_code != 403


@pytest.mark.asyncio
class TestPresetAtCreation:
    async def test_nouveau_bailleur_prereglage_restreint(self, client, db, gestionnaire_token):
        r = await client.post(
            "/api/v1/users",
            headers=auth(gestionnaire_token),
            json={
                "full_name": "Bailleur Test",
                "email": "bailleur_preset@test.fr",
                "role": "proprietaire",
            },
        )
        assert r.status_code == 201, r.text
        uid = uuid.UUID(r.json()["id"])
        created = (await db.execute(select(UserModel).where(UserModel.id == uid))).scalar_one()
        assert set(created.proprio_visibility or []) == set(DEFAULT_NEW_PROPRIO_KEYS)
