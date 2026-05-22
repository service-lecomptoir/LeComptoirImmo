"""
Tests API — Documents.
"""
import pytest
from tests.conftest import auth


@pytest.mark.asyncio
class TestDocumentList:
    async def test_gestionnaire_lists_documents(self, client, gestionnaire_token):
        resp = await client.get("/api/v1/documents", headers=auth(gestionnaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_locataire_lists_own_documents(self, client, locataire_token):
        resp = await client.get("/api/v1/documents", headers=auth(locataire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_proprietaire_lists_own_documents(self, client, proprietaire_token):
        resp = await client.get("/api/v1/documents", headers=auth(proprietaire_token))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_unauthenticated_denied(self, client):
        resp = await client.get("/api/v1/documents")
        assert resp.status_code in (401, 403)

    async def test_locataire_without_tenant_returns_empty(self, client, locataire_token):
        """Locataire sans dossier locataire associé → liste vide."""
        resp = await client.get("/api/v1/documents", headers=auth(locataire_token))
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
class TestDocumentIsolation:
    async def test_locataire_only_sees_own_docs(
        self, client, locataire_token, locataire_user, db
    ):
        """Locataire lié à un tenant voit uniquement ses documents."""
        from app.models.tenant import Tenant
        from app.models.document import Document, EntityType, DocumentType
        import uuid

        # Créer le tenant lié au locataire
        tenant = Tenant(
            first_name="Doc", last_name="Test",
            email="doc.test@test.fr",
            user_id=locataire_user.id,
        )
        db.add(tenant)
        await db.flush()

        # Créer un document pour ce tenant
        doc = Document(
            entity_type=EntityType.TENANT,
            entity_id=tenant.id,
            document_type=DocumentType.CNI,
            file_name="cni_test.pdf",
            file_path="/tmp/cni_test.pdf",
            mime_type="application/pdf",
            file_size=12345,
        )
        db.add(doc)

        # Créer un autre document lié à un autre tenant
        other_tenant = Tenant(
            first_name="Other", last_name="Tenant",
            email="other.tenant@test.fr",
        )
        db.add(other_tenant)
        await db.flush()

        other_doc = Document(
            entity_type=EntityType.TENANT,
            entity_id=other_tenant.id,
            document_type=DocumentType.PASSEPORT,
            file_name="passeport_other.pdf",
            file_path="/tmp/passeport_other.pdf",
            mime_type="application/pdf",
        )
        db.add(other_doc)
        await db.flush()

        resp = await client.get("/api/v1/documents", headers=auth(locataire_token))
        assert resp.status_code == 200
        returned_ids = [d["id"] for d in resp.json()]

        assert str(doc.id) in returned_ids
        assert str(other_doc.id) not in returned_ids

    async def test_get_nonexistent_document(self, client, gestionnaire_token):
        resp = await client.get(
            "/api/v1/documents/00000000-0000-0000-0000-000000000000",
            headers=auth(gestionnaire_token),
        )
        assert resp.status_code == 404
