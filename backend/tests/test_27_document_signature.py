"""
Régression : la signature du gestionnaire n'est PLUS apposée sur les documents
de l'atelier rendus par BLOCS (quittance, avis, relance…). Elle est réservée au
bail et aux documents CAF (commit b221f38). Ce test verrouille la nouvelle règle.
"""

from unittest.mock import patch

import pytest

from app.services import document_blocks_pdf_service as blocks_svc


async def _render_quittance_html(db, user) -> str:
    captured = {}

    def fake_pdf(html):
        captured["html"] = html
        return b"%PDF-1.4 test"

    with patch.object(blocks_svc, "html_to_pdf", fake_pdf):
        out = await blocks_svc.render_blocks_document(
            db,
            user.id,
            "quittance",
            {"month": "Juin 2026", "tenant_name": "Jean Test"},
        )
    assert out == b"%PDF-1.4 test"
    return captured["html"]


@pytest.mark.asyncio
async def test_blocks_document_omet_signature_meme_si_presente(db, gestionnaire_user):
    """Un document d'atelier (quittance) n'inclut jamais la signature, même quand
    le gestionnaire en a configuré une."""
    gestionnaire_user.signature = "data:image/png;base64,SIGTEST=="
    await db.flush()

    html = await _render_quittance_html(db, gestionnaire_user)
    assert "data:image/png;base64,SIGTEST==" not in html  # signature non apposée
    assert 'width="70" height="23"' not in html  # ni image de signature dédiée


@pytest.mark.asyncio
async def test_blocks_document_no_signature_when_absent(db, gestionnaire_user):
    gestionnaire_user.signature = None
    await db.flush()
    html = await _render_quittance_html(db, gestionnaire_user)
    assert 'width="70" height="23"' not in html
