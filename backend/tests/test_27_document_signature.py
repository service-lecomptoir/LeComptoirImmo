"""
Régression : la signature du gestionnaire (User.signature) doit être injectée
dans les documents rendus par BLOCS (quittance, avis…) — auparavant le chemin
« blocs » ne passait pas signature_uri, donc la signature manquait en pied.
"""
from unittest.mock import patch

import pytest

from app.services import document_blocks_pdf_service as blocks_svc


@pytest.mark.asyncio
async def test_blocks_document_includes_signature(db, gestionnaire_user):
    gestionnaire_user.signature = "data:image/png;base64,SIGTEST=="
    await db.flush()

    captured = {}

    def fake_pdf(html):
        captured["html"] = html
        return b"%PDF-1.4 test"

    with patch.object(blocks_svc, "html_to_pdf", fake_pdf):
        out = await blocks_svc.render_blocks_document(
            db, gestionnaire_user.id, "quittance",
            {"month": "Juin 2026", "tenant_name": "Jean Test"},
        )

    assert out == b"%PDF-1.4 test"
    assert "data:image/png;base64,SIGTEST==" in captured["html"]


@pytest.mark.asyncio
async def test_blocks_document_no_signature_when_absent(db, gestionnaire_user):
    gestionnaire_user.signature = None
    await db.flush()
    captured = {}
    with patch.object(blocks_svc, "html_to_pdf", lambda html: captured.setdefault("html", html) or b"x"):
        await blocks_svc.render_blocks_document(
            db, gestionnaire_user.id, "quittance", {"month": "Juin 2026"},
        )
    # Pas de signature → pas d'image de signature (width/height dédiés).
    assert 'width="70" height="23"' not in captured["html"]
