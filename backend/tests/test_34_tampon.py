"""
Tampon / cachet professionnel du mandataire : apposé À CÔTÉ de la signature sur
le bail et les documents CAF (mêmes documents que la signature). Ces tests
verrouillent : (1) le tampon apparaît dans le HTML du bail quand il est présent
et seulement à ce moment ; (2) caf_pdf_fill.fill accepte un tampon et produit un
PDF ; (3) la mise à jour du profil enregistre/efface le tampon.
"""

import pytest

from app.services import caf_pdf_fill
from app.services.pdf_service import render_template

_TAMPON = "data:image/png;base64,TAMPONTEST=="
_SIG = "data:image/png;base64,SIGTEST=="


def _bail_ctx(**over) -> dict:
    ctx = {
        "is_morale": False,
        "is_furnished": False,
        "lease_type": "vide",
        "bailleur_name": "SCI Test",
        "bailleur_address": "1 rue Test",
        "bailleur_addr1": "1 rue Test",
        "bailleur_addr2": "75001 Paris",
        "bailleur_email": "b@test.fr",
        "is_mandataire": True,
        "mandataire_name": "Agence Test",
        "mandataire_address": "2 rue Agence",
        "mandataire_company": "Agence SARL",
        "mandataire_national_id": "12345678900012",
        "has_guarantor": False,
        "guarantor_name": "",
        "tenant_name": "Jean Test",
        "tenant_email": "j@test.fr",
        "tenant2_name": "",
        "tenant2_email": "",
        "logement_address": "3 rue Bail",
        "logement_cp": "75002",
        "logement_city": "Paris",
        "floor": "",
        "surface": "40",
        "nb_pieces": "2",
        "heating": "",
        "dpe": "",
        "year_built": "",
        "start_date": "01/07/2026",
        "duration_morale": False,
        "rent": "800.00",
        "charges": "50.00",
        "total": "850.00",
        "payment_day": 1,
        "deposit": "800.00",
        "irl_quarter": None,
        "tenant_names": "Jean Test",
        "today": "22/06/2026",
        "signature_uri": "",
        "tampon_uri": "",
    }
    ctx.update(over)
    return ctx


def test_bail_html_inclut_le_tampon_quand_present():
    html = render_template("lease_bail.html.j2", _bail_ctx(signature_uri=_SIG, tampon_uri=_TAMPON))
    assert _TAMPON in html
    assert 'alt="Cachet"' in html
    assert _SIG in html  # signature toujours présente à côté


def test_bail_html_sans_tampon_si_absent():
    html = render_template("lease_bail.html.j2", _bail_ctx(signature_uri=_SIG, tampon_uri=""))
    assert 'alt="Cachet"' not in html
    assert _SIG in html  # la signature seule reste apposée


def test_caf_fill_accepte_tampon(monkeypatch):
    """fill() avec un tampon PNG ne lève pas et renvoie des octets PDF."""
    captured = {}

    def fake_overlay(width, height, png, x_mm, y_mm, w_mm):
        captured.setdefault("pngs", []).append(png)
        return None  # pas de merge réel : on vérifie seulement l'acheminement

    # PDF AcroForm minimal : un template vide suffit (pypdf gère 0 champ).
    import io

    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    w.write(buf)
    template = buf.getvalue()

    monkeypatch.setattr(caf_pdf_fill, "_signature_overlay", fake_overlay)
    out = caf_pdf_fill.fill(
        template,
        {},
        signature_png=b"SIGPNG",
        tampon_png=b"TAMPONPNG",
    )
    assert out.startswith(b"%PDF")
    assert b"SIGPNG" in captured["pngs"]
    assert b"TAMPONPNG" in captured["pngs"]


def test_data_uri_to_png_decode_tampon():
    import base64

    raw = b"hello-cachet"
    uri = "data:image/png;base64," + base64.b64encode(raw).decode()
    assert caf_pdf_fill._data_uri_to_png(uri) == raw
    assert caf_pdf_fill._data_uri_to_png(None) is None


@pytest.mark.asyncio
async def test_profile_update_set_and_clear_tampon(db, gestionnaire_user):
    from app.schemas.user import UserUpdate
    from app.services.user_service import UserService

    await UserService.update(db, gestionnaire_user.id, UserUpdate(tampon=_TAMPON))
    await db.refresh(gestionnaire_user)
    assert gestionnaire_user.tampon == _TAMPON

    # Chaîne vide => suppression explicite.
    await UserService.update(db, gestionnaire_user.id, UserUpdate(tampon=""))
    await db.refresh(gestionnaire_user)
    assert gestionnaire_user.tampon is None
