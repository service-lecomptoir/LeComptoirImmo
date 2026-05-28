"""Rendu des documents PDF à partir des templates ENREGISTRÉS par l'utilisateur
(table document_templates, éditeur « Templates docs »).

Le contenu (`content_html`) utilise une syntaxe type Handlebars :
  - {{variable}}                  → substitution
  - {{#if variable}}...{{/if}}    → bloc conditionnel (gardé si la variable est non vide)

Si aucun template par défaut n'existe pour le gestionnaire + type, on retourne None
→ l'appelant retombe sur le fichier .j2 historique (comportement inchangé).
"""
from __future__ import annotations

import re
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


def _wrap(template: DocumentTemplate, body_html: str, recipient_lines: list[str], layout: dict) -> str:
    sp = (layout or {}).get("spacing", {}) if isinstance(layout, dict) else {}
    page_margin = sp.get("page_margin", "2cm 2.5cm")
    font_size = sp.get("font_size", 10)
    line_height = sp.get("line_height", 1.5)
    header_color = template.header_color or "#1e3a5f"
    company = _html.escape(template.company_name or "Le Comptoir Immo")
    company_addr = _html.escape(template.company_address or "")
    footer = _html.escape(template.footer_text or "")

    recipient = "".join(
        f'<div class="rc-name">{_html.escape(n)}</div>' for n in (recipient_lines or [])
    )

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><style>
  @page {{ size: A4; margin: {page_margin}; }}
  body {{ font-family: Arial, sans-serif; font-size: {font_size}pt; color: #111; line-height: {line_height}; }}
  .doc-header {{ border-bottom: 3px solid {header_color}; padding-bottom: 8px; margin-bottom: 16px; }}
  .company {{ font-size: {int(font_size) + 3}pt; font-weight: bold; color: {header_color}; }}
  .company-addr {{ font-size: {int(font_size) - 1}pt; color: #555; }}
  .recipient {{ text-align: right; margin-bottom: 18px; }}
  .rc-name {{ font-weight: bold; font-size: {int(font_size) + 1}pt; color: #111; }}
  .doc-body table {{ width: 100%; border-collapse: collapse; }}
  .doc-body td {{ padding: 4px 8px; }}
  .doc-footer {{ margin-top: 20px; border-top: 1px solid #e5e5e5; padding-top: 6px; font-size: 8pt; color: #888; }}
  h1, h2, h3 {{ color: {header_color}; }}
</style></head><body>
  <div class="doc-header">
    <div class="company">{company}</div>
    {f'<div class="company-addr">{company_addr}</div>' if company_addr else ''}
  </div>
  {f'<div class="recipient">{recipient}</div>' if recipient else ''}
  <div class="doc-body">{body_html}</div>
  {f'<div class="doc-footer">{footer}</div>' if footer else ''}
</body></html>"""


async def render_saved_document(
    db: AsyncSession,
    *,
    template_type: str,
    gestionnaire_id: Optional[uuid.UUID],
    variables: dict,
    recipient_lines: list[str],
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
    body = substitute(tmpl.content_html, variables)
    return _wrap(tmpl, body, recipient_lines, layout)
