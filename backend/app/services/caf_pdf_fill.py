"""Remplissage des formulaires PDF officiels de la CAF (CERFA AcroForm).

Le gestionnaire téléverse le PDF officiel ; on en extrait les champs de
formulaire, on les remplit avec les données de l'application (selon un mapping)
et on appose la signature du bailleur/mandataire. Pure Python (pypdf + reportlab).
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def extract_fields(pdf_bytes: bytes) -> list[str]:
    """Liste des noms de champs de formulaire (AcroForm) d'un PDF. [] si aucun."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        fields = reader.get_fields() or {}
        return [str(k) for k in fields.keys()]
    except Exception as exc:  # noqa: BLE001
        logger.warning("caf_pdf_fill.extract_fields: %r", exc)
        return []


def _data_uri_to_png(uri: str | None) -> bytes | None:
    """Décode une signature en data URI (data:image/png;base64,...) → octets PNG."""
    if not uri or "," not in uri:
        return None
    try:
        import base64

        return base64.b64decode(uri.split(",", 1)[1])
    except Exception:  # noqa: BLE001
        return None


def _signature_overlay(
    width: float, height: float, png: bytes, x_mm: float, y_mm: float, w_mm: float
) -> bytes | None:
    """Crée un PDF d'une page (taille width×height pt) avec la signature posée."""
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas

        mm = 72.0 / 25.4
        img = ImageReader(io.BytesIO(png))
        iw, ih = img.getSize()
        w_pt = w_mm * mm
        h_pt = w_pt * (ih / iw) if iw else (w_mm * 0.5 * mm)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(width, height))
        c.drawImage(
            img,
            x_mm * mm,
            y_mm * mm,
            width=w_pt,
            height=h_pt,
            mask="auto",
            preserveAspectRatio=True,
        )
        c.save()
        return buf.getvalue()
    except Exception as exc:  # noqa: BLE001
        logger.warning("caf_pdf_fill._signature_overlay: %r", exc)
        return None


def fill(
    template_bytes: bytes,
    values: dict,
    *,
    signature_png: bytes | None = None,
    sign_page: int = 1,
    sign_x_mm: float = 130,
    sign_y_mm: float = 20,
    sign_w_mm: float = 45,
) -> bytes:
    """Remplit les champs AcroForm avec `values` (champ→valeur texte) et appose la
    signature sur la page `sign_page` (1-based). Renvoie les octets du PDF rempli."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(template_bytes))
    writer = PdfWriter()
    writer.append(reader)

    # Valeurs en texte (ignore None/vides).
    str_values = {k: ("" if v is None else str(v)) for k, v in (values or {}).items()}
    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, str_values, auto_regenerate=False)
        except Exception as exc:  # noqa: BLE001 : un champ inconnu ne casse pas le reste
            logger.debug("update_page_form_field_values: %r", exc)

    # Forcer le rendu des champs par les lecteurs PDF.
    try:
        writer.set_need_appearances_writer(True)
    except Exception:  # noqa: BLE001
        try:
            from pypdf.generic import BooleanObject, NameObject

            writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)
        except Exception:  # noqa: BLE001
            pass

    # Signature : superposer l'image sur la page choisie.
    if signature_png:
        idx = max(0, min(len(writer.pages) - 1, int(sign_page) - 1))
        target = writer.pages[idx]
        try:
            w = float(target.mediabox.width)
            h = float(target.mediabox.height)
            ov = _signature_overlay(w, h, signature_png, sign_x_mm, sign_y_mm, sign_w_mm)
            if ov:
                from pypdf import PdfReader as _R

                ovp = _R(io.BytesIO(ov)).pages[0]
                target.merge_page(ovp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("caf_pdf_fill signature merge: %r", exc)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
