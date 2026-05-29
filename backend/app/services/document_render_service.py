"""Rendu des documents PDF à partir des templates ENREGISTRÉS par l'utilisateur
(table document_templates, éditeur « Templates docs »).

Le contenu (`content_html`) utilise une syntaxe type Handlebars :
  - {{variable}}                  → substitution (valeur échappée)
  - {{#if variable}}...{{/if}}    → bloc conditionnel (gardé si la variable est non vide)

Mise en page (commune à tous les documents) — cadre « pro » sur fond blanc :
  • En-tête GAUCHE  : logo (icône) du gestionnaire puis son adresse.
  • En-tête DROITE  : les locataires empilés, puis l'adresse du bien en dessous.
  • CORPS (centre)  : les données du document (montants, etc.).
  • PIED DE PAGE    : mentions légales / coordonnées.

Si aucun template par défaut n'existe pour le gestionnaire + type, on retourne None
→ l'appelant retombe sur le fichier .j2 historique.
"""
from __future__ import annotations

import re
import os
import base64
import html as _html
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_template import DocumentTemplate


def eur(value) -> str:
    """Formate un montant en euros à la française : 1 234,56"""
    try:
        s = f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return ""
    return s.replace(",", " ").replace(".", ",")


_IF_RE = re.compile(r"\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}", re.DOTALL)
_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def substitute(content_html: str, variables: dict) -> str:
    """Applique les blocs {{#if}} puis substitue les {{variables}} (valeurs échappées)."""
    def _if_repl(m: re.Match) -> str:
        key, inner = m.group(1), m.group(2)
        val = variables.get(key)
        return inner if val not in (None, "", 0, "0", "0,00", "0.00") else ""

    out = _IF_RE.sub(_if_repl, content_html)

    def _var_repl(m: re.Match) -> str:
        key = m.group(1)
        val = variables.get(key)
        return _html.escape(str(val)) if val is not None else ""

    return _VAR_RE.sub(_var_repl, out)


def _logo_data_uri(logo_path: Optional[str]) -> Optional[str]:
    """Encode le logo en data-URI base64 (xhtml2pdf n'a pas de link_callback)."""
    try:
        if logo_path and os.path.exists(logo_path):
            ext = logo_path.rsplit(".", 1)[-1].lower()
            mime = {
                "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "svg": "image/svg+xml", "webp": "image/webp", "gif": "image/gif",
            }.get(ext, "image/png")
            with open(logo_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{b64}"
    except Exception:
        pass
    return None


def _wrap(
    template: DocumentTemplate,
    body_html: str,
    recipient_lines: list[str],
    property_address: str,
    layout: dict,
    sender_name: str = "",
    sender_addr: str = "",
) -> str:
    sp = (layout or {}).get("spacing", {}) if isinstance(layout, dict) else {}
    fs = int(sp.get("font_size", 10) or 10)
    line_height = sp.get("line_height", 1.5)
    accent = template.header_color or "#0d2f5c"
    company = _html.escape(sender_name or template.company_name or "Le Comptoir Immo")
    company_addr = _html.escape(sender_addr or template.company_address or "").replace("\n", "<br/>")
    footer = _html.escape(template.footer_text or "")
    prop = _html.escape(property_address or "").replace("\n", "<br/>")

    # En-tête gauche : logo (icône) du gestionnaire OU son nom en wordmark.
    logo_uri = _logo_data_uri(getattr(template, "logo_path", None))
    if logo_uri:
        sender_brand = f'<img src="{logo_uri}" style="width:150px; height:100px;" alt="logo"/>'
    else:
        sender_brand = f'<div class="sender-name">{company}</div>'

    recipient = "".join(
        f'<div class="rc-name">{_html.escape(n)}</div>' for n in (recipient_lines or [])
    )

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><style>
  @page {{ size: A4; margin: 1.6cm 1.8cm; }}
  body {{ font-family: Helvetica, Arial, sans-serif; font-size: {fs}pt; color: #1f2937; line-height: {line_height}; background: #ffffff; }}
  .hdr {{ width: 100%; border-collapse: collapse; margin-bottom: 8px; }}
  .hdr td {{ vertical-align: top; }}
  .sender-name {{ font-size: {fs + 4}pt; font-weight: bold; color: {accent}; }}
  .sender-addr {{ font-size: {fs - 1}pt; color: #6b7280; margin-top: 6px; }}
  .recipient {{ text-align: right; }}
  .rc-name {{ font-weight: bold; font-size: {fs + 1}pt; color: #111827; }}
  .rc-prop {{ font-size: {fs - 1}pt; color: #6b7280; margin-top: 8px; }}
  .rule {{ border: 0; border-top: 2px solid {accent}; margin: 6px 0 20px 0; }}
  .body {{ font-size: {fs}pt; }}
  .body h1, .body h2 {{ font-size: {fs + 6}pt; color: {accent}; text-align: center; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 2px 0; }}
  .body h3 {{ font-size: {fs + 1}pt; color: {accent}; border-left: 3px solid {accent}; padding-left: 7px; margin: 16px 0 6px 0; }}
  .body p {{ margin: 8px 0; }}
  .body table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
  .body td {{ padding: 7px 10px; border-bottom: 1px solid #eef2f7; font-size: {fs}pt; }}
  .footer {{ margin-top: 28px; border-top: 1px solid #e5e7eb; padding-top: 8px; font-size: 8pt; color: #9ca3af; text-align: center; }}
</style></head><body>
  <table class="hdr"><tr>
    <td style="width: 55%;">
      {sender_brand}
      {f'<div class="sender-addr">{company_addr}</div>' if company_addr else ''}
    </td>
    <td style="width: 45%;" class="recipient">
      {recipient}
      {f'<div class="rc-prop">{prop}</div>' if prop else ''}
    </td>
  </tr></table>
  <hr class="rule"/>
  <div class="body">{body_html}</div>
  {f'<div class="footer">{footer}</div>' if footer else ''}
</body></html>"""


async def render_saved_document(
    db: AsyncSession,
    *,
    template_type: str,
    gestionnaire_id: Optional[uuid.UUID],
    variables: dict,
    recipient_lines: list[str],
    property_address: str = "",
    layout: dict,
) -> Optional[str]:
    """Rend le HTML d'un document à partir du template par défaut enregistré.
    Retourne None si aucun template par défaut → fallback .j2 côté appelant."""
    if not gestionnaire_id:
        return None
    tmpl = (await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.gestionnaire_id == gestionnaire_id,
            DocumentTemplate.template_type == template_type,
            DocumentTemplate.is_default.is_(True),
            DocumentTemplate.is_active.is_(True),
        )
    )).scalar_one_or_none()
    if not tmpl or not tmpl.content_html:
        return None

    # En-tête : nom + adresse du gestionnaire. Priorité aux champs du template
    # (company_name/address), sinon repli sur le profil du gestionnaire.
    sender_name, sender_addr = "", ""
    try:
        from app.models.user import User
        user = (await db.execute(
            select(User).where(User.id == gestionnaire_id)
        )).scalar_one_or_none()
        if user:
            sender_name = tmpl.company_name or user.full_name or ""
            sender_addr = tmpl.company_address or getattr(user, "address", "") or ""
    except Exception:
        pass

    body = substitute(tmpl.content_html, variables)
    return _wrap(tmpl, body, recipient_lines, property_address, layout, sender_name, sender_addr)
