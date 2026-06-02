# -*- coding: utf-8 -*-
"""Rendu de l'avis d'échéance « façon Foncia » à partir d'un modèle de BLOCS.

Le template stocke une liste ordonnée de blocs (`blocks`) + un thème (`theme`).
Chaque bloc a un type, un état activé/désactivé et des `props` (champs texte
pouvant contenir des {{variables}}). Ce service compose le HTML final (rendu
ensuite en PDF par xhtml2pdf), en reproduisant la mise en page Foncia :

  • bandeau d'en-tête (logo à gauche, titre + sous-titres à droite) ;
  • zone deux colonnes : sidebar d'infos (gauche) / corps (droite) ;
  • blocs pleine largeur : tableau détaillé des montants, pied légal.

On reste sur des <table> (pas de positionnement absolu) car xhtml2pdf les gère
de façon fiable. Couleurs et placements proviennent du thème.
"""
from __future__ import annotations

import html as _html
import re
from typing import Optional

from app.services.document_render_service import substitute, _logo_data_uri


# ── Thème Foncia (palette extraite du PDF de référence) ──────────────────────
FONCIA_THEME = {
    "navy": "#003D7C",          # titres / texte principal
    "orange": "#EB690B",        # bloc référence + accents
    "gray": "#949191",          # corps de la sidebar
    "teal": "#4BA282",          # bandeau « Montant à payer » / ligne total
    "section_bg": "#CCEBF1",    # en-tête de section du tableau
    "row_bg": "#F1F9FA",        # lignes alternées du tableau
    "col_header": "#3F3F46",    # en-têtes de colonnes (MONTANTS APPELÉS…)
    "header_cell_bg": "#FAFAFA",
    "footer_color": "#403E3E",
    "font_family": "Helvetica, Arial, sans-serif",
}


# ── Blocs par défaut de l'avis d'échéance (réordonnables côté éditeur) ───────
def default_avis_blocks() -> list[dict]:
    return [
        {"id": "header", "type": "header", "enabled": True, "props": {
            "title": "Avis d'échéance",
            "subtitle1": "{{period_range}}",
            "subtitle2": "MENSUEL / AVANCE",
        }},
        {"id": "sidebar", "type": "sidebar", "enabled": True, "props": {
            "sections": [
                {"title": "VOS INFORMATIONS",
                 "lines": ["{{tenant_name}}", "{{property_address}}",
                           "{{tenant_phone}}", "{{tenant_email}}"]},
                {"title": "VOS RÉFÉRENCES CLIENT",
                 "lines": ["Référence immeuble : {{property_reference}}"]},
                {"title": "VOTRE AGENCE",
                 "lines": ["{{company_name}}", "{{company_address}}"]},
                {"title": "VOS LOTS",
                 "lines": ["{{property_name}}"]},
                {"title": "VOTRE MODE DE PAIEMENT",
                 "lines": ["Virement / prélèvement"]},
            ],
        }},
        {"id": "recipient", "type": "recipient", "enabled": True, "props": {
            "date_text": "Le {{today_date}}",
            "lines": ["{{tenant_name}}", "{{property_name}}",
                      "{{property_address}}"],
        }},
        {"id": "reference", "type": "reference", "enabled": True, "props": {
            "lines": ["{{property_name}}", "{{property_address}}"],
            "ref_line": "Référence immeuble : {{property_reference}}",
            "tenant_line": "Locataire : {{tenant_name}}",
        }},
        {"id": "greeting", "type": "greeting", "enabled": True, "props": {
            "salutation": "Cher locataire,",
            "intro": "Veuillez trouver ci-après votre avis d'échéance {{period_range}}.",
        }},
        {"id": "amount_bar", "type": "amount_bar", "enabled": True, "props": {
            "title": "Votre avis d'échéance",
            "label": "Montant à payer (exigible le {{due_date}})",
            "amount": "{{total_due}}",
        }},
        {"id": "details", "type": "details_table", "enabled": True, "props": {
            "heading": "Détails de votre avis d'échéance",
            "section_label": "Situation de votre compte",
            "col_appel": "MONTANTS APPELÉS",
            "col_regle": "MONTANTS RÉGLÉS",
            "show_regle": True,
            "custom_rows": [],
            "total_label": "Total pour la période {{period_range}} : {{total_due}}",
            "pay_label": "Montant à payer (exigible le {{due_date}})",
        }},
        {"id": "footer", "type": "legal_footer", "enabled": True, "props": {
            "text": "{{company_name}} — {{company_address}}. "
                    "Document généré électroniquement, ne nécessite pas de signature.",
        }},
    ]


# ── Helpers ──────────────────────────────────────────────────────────────────
def _sub(text: Optional[str], variables: dict) -> str:
    """Substitue les {{variables}} et renvoie du HTML échappé (sauts de ligne -> <br/>)."""
    return substitute(text or "", variables)


def _money(text: Optional[str], variables: dict) -> str:
    """Comme _sub mais empêche le retour à la ligne des montants
    (xhtml2pdf ignore white-space:nowrap → on force des espaces insécables)."""
    s = _sub(text, variables)
    return re.sub(r'[\s\u00a0\u202f]', '\u00a0', s)


def _theme(theme: Optional[dict]) -> dict:
    t = dict(FONCIA_THEME)
    if isinstance(theme, dict):
        t.update({k: v for k, v in theme.items() if v})
    return t


# ── Rendu de chaque type de bloc ─────────────────────────────────────────────
def _render_header(props: dict, t: dict, variables: dict, logo_path) -> str:
    logo_uri = _logo_data_uri(logo_path)
    # Emplacement du logo TOUJOURS réservé (hauteur fixe) : s'il n'y a pas de logo,
    # la case reste vide mais la mise en page ne remonte pas.
    if logo_uri:
        brand = (f'<div style="height:64px;">'
                 f'<img src="{logo_uri}" style="max-width:170px; max-height:64px;" alt="logo"/></div>')
    else:
        brand = '<div style="height:64px;">&nbsp;</div>'
    title = _sub(props.get("title"), variables)
    sub1 = _sub(props.get("subtitle1"), variables)
    sub2 = _sub(props.get("subtitle2"), variables)
    return f"""
    <table class="band"><tr>
      <td style="width:50%; vertical-align:middle;">{brand}</td>
      <td style="width:50%; text-align:right; vertical-align:middle;">
        <div style="font-size:23pt; font-weight:bold; color:{t['navy']};">{title}</div>
        <div style="font-size:9pt; font-weight:bold; color:{t['navy']}; letter-spacing:.5px;">{sub1}</div>
        <div style="font-size:9pt; font-weight:bold; color:{t['navy']}; letter-spacing:.5px;">{sub2}</div>
      </td>
    </tr></table>
    <hr class="rule"/>
    """


def _render_sidebar(props: dict, t: dict, variables: dict) -> str:
    out = []
    for sec in props.get("sections", []):
        title = _sub(sec.get("title"), variables)
        lines = "".join(
            f'<div style="color:{t["gray"]}; font-size:6.8pt; margin:1px 0;">{_sub(l, variables)}</div>'
            for l in sec.get("lines", []) if (l or "").strip()
        )
        out.append(
            f'<div style="margin-bottom:10px;">'
            f'<div style="color:{t["navy"]}; font-weight:bold; font-size:7pt; '
            f'text-transform:uppercase; letter-spacing:.4px; margin-bottom:3px;">{title}</div>'
            f'{lines}</div>'
        )
    return "".join(out)


def _render_recipient(props: dict, t: dict, variables: dict) -> str:
    date_html = ""
    if props.get("date_text"):
        date_html = (f'<div style="color:{t["navy"]}; font-size:8pt; margin-bottom:10px;">'
                     f'{_sub(props.get("date_text"), variables)}</div>')
    lines = "".join(
        f'<div style="color:{t["navy"]}; font-size:8pt; line-height:1.35;">{_sub(l, variables)}</div>'
        for l in props.get("lines", []) if (l or "").strip()
    )
    return f'{date_html}<div style="text-align:right; margin-bottom:14px;">{lines}</div>'


def _render_reference(props: dict, t: dict, variables: dict) -> str:
    lines = "".join(
        f'<div style="color:{t["orange"]}; font-size:8.5pt; line-height:1.4;">{_sub(l, variables)}</div>'
        for l in props.get("lines", []) if (l or "").strip()
    )
    ref = (f'<div style="color:{t["orange"]}; font-size:8.5pt; font-weight:bold; margin-top:2px;">'
           f'{_sub(props.get("ref_line"), variables)}</div>') if props.get("ref_line") else ""
    ten = (f'<div style="color:{t["navy"]}; font-size:8.5pt; margin-top:6px;">'
           f'{_sub(props.get("tenant_line"), variables)}</div>') if props.get("tenant_line") else ""
    return f'<div style="margin-bottom:12px;">{lines}{ref}{ten}</div>'


def _render_greeting(props: dict, t: dict, variables: dict) -> str:
    sal = (f'<div style="color:{t["navy"]}; font-size:9pt; margin-bottom:6px;">'
           f'{_sub(props.get("salutation"), variables)}</div>') if props.get("salutation") else ""
    intro = (f'<div style="color:{t["navy"]}; font-size:9pt; line-height:1.5;">'
             f'{_sub(props.get("intro"), variables)}</div>') if props.get("intro") else ""
    return f'<div style="margin-bottom:14px;">{sal}{intro}</div>'


def _render_amount_bar(props: dict, t: dict, variables: dict) -> str:
    title = (f'<div style="color:{t["navy"]}; font-size:17pt; font-weight:bold; margin:6px 0 8px 0;">'
             f'{_sub(props.get("title"), variables)}</div>') if props.get("title") else ""
    label = _sub(props.get("label"), variables)
    amount = _money(props.get("amount"), variables)
    return f"""{title}
    <table class="amount-bar"><tr>
      <td style="background:{t['teal']}; color:#fff; font-weight:bold; font-size:9.5pt; padding:7px 10px;">{label}</td>
      <td style="background:{t['teal']}; color:#fff; font-weight:bold; font-size:11pt; padding:7px 10px; text-align:right; width:110px;">{amount}</td>
    </tr></table>"""


def _render_free_text(props: dict, t: dict, variables: dict) -> str:
    return (f'<div style="color:{t["navy"]}; font-size:9pt; line-height:1.5; margin-bottom:12px;">'
            f'{_sub(props.get("text"), variables)}</div>')


def _render_details_table(props: dict, t: dict, variables: dict, line_items: list) -> str:
    show_regle = props.get("show_regle", True)
    heading = _sub(props.get("heading"), variables)
    section = _sub(props.get("section_label"), variables)
    col_appel = _sub(props.get("col_appel") or "MONTANTS APPELÉS", variables)
    col_regle = _sub(props.get("col_regle") or "MONTANTS RÉGLÉS", variables)

    # Lignes : items auto (line_items) + custom_rows du bloc.
    rows = list(line_items or [])
    for cr in props.get("custom_rows", []):
        rows.append({
            "label": _sub(cr.get("label"), variables),
            "appele": _money(cr.get("appele"), variables),
            "regle": _money(cr.get("regle"), variables),
            "date": _sub(cr.get("date"), variables),
        })

    ncols = 3 if show_regle else 2
    aw = 92  # largeur fixe (px) des colonnes de montants (cf. note ci-dessous)
    body = []
    # En-tête de section (fond cyan).
    body.append(
        f'<tr><td colspan="{ncols}" style="background:{t["section_bg"]}; color:{t["navy"]}; '
        f'font-weight:bold; font-size:9pt; padding:6px 10px;">{section}</td></tr>'
    )
    for i, r in enumerate(rows):
        bg = t["row_bg"] if i % 2 == 0 else "#ffffff"
        label = r.get("label", "")
        date = r.get("date", "")
        label_cell = label
        if date:
            label_cell = f'<span style="color:{t["navy"]}; font-weight:bold;">{date}</span> &nbsp; {label}'
        appele = re.sub(r'\s', '\u00a0', str(r.get('appele', '')))
        regle = re.sub(r'\s', '\u00a0', str(r.get('regle', '')))
        cells = (
            f'<td style="background:{bg}; color:{t["navy"]}; font-weight:bold; font-size:8pt; padding:6px 10px;">{label_cell}</td>'
            f'<td width="{aw}" style="background:{bg}; color:{t["navy"]}; font-style:italic; font-size:8pt; padding:6px 8px; text-align:right;">{appele or "&nbsp;"}</td>'
        )
        if show_regle:
            cells += (f'<td width="{aw}" style="background:{bg}; color:{t["navy"]}; font-style:italic; font-size:8pt; '
                      f'padding:6px 8px; text-align:right;">{regle or "&nbsp;"}</td>')
        body.append(f"<tr>{cells}</tr>")

    # Ligne total (fond cyan section).
    total_label = _sub(props.get("total_label"), variables)
    if total_label:
        body.append(
            f'<tr><td colspan="{ncols}" style="background:{t["section_bg"]}; color:{t["navy"]}; '
            f'font-weight:bold; font-size:9pt; padding:6px 10px;">{total_label}</td></tr>'
        )
    # Ligne « Montant à payer » (fond teal, blanc) — montant sous « APPELÉS ».
    pay_label = _sub(props.get("pay_label"), variables)
    pay_amount = _money("{{total_due}}", variables)
    if pay_label:
        pay = (f'<tr><td style="background:{t["teal"]}; color:#fff; font-weight:bold; font-size:9.5pt; '
               f'padding:8px 10px;">{pay_label}</td>'
               f'<td width="{aw}" style="background:{t["teal"]}; color:#fff; font-weight:bold; font-size:9.5pt; '
               f'padding:8px; text-align:right;">{pay_amount}</td>')
        if show_regle:
            pay += f'<td width="{aw}" style="background:{t["teal"]};">&nbsp;</td>'
        pay += "</tr>"
        body.append(pay)

    # En-têtes de colonnes — passage à la ligne forcé (xhtml2pdf ne wrappe pas
    # dans une cellule étroite et ferait déborder le texte sur la colonne voisine).
    col_appel_html = col_appel.replace(" ", "<br/>")
    col_regle_html = col_regle.replace(" ", "<br/>")
    head = f'<td style="background:{t["header_cell_bg"]};">&nbsp;</td>'
    head += (f'<td width="{aw}" style="background:{t["header_cell_bg"]}; color:{t["col_header"]}; font-size:7.8pt; '
             f'padding:6px 8px; text-align:right; vertical-align:bottom;">{col_appel_html}</td>')
    if show_regle:
        head += (f'<td width="{aw}" style="background:{t["header_cell_bg"]}; color:{t["col_header"]}; font-size:7.8pt; '
                 f'padding:6px 8px; text-align:right; vertical-align:bottom;">{col_regle_html}</td>')

    heading_html = (f'<div style="color:{t["navy"]}; font-size:17pt; font-weight:bold; margin:6px 0 10px 0;">'
                    f'{heading}</div>') if heading else ""
    return f"""{heading_html}
    <table class="details">
      <tr>{head}</tr>
      {''.join(body)}
    </table>"""


def _render_legal_footer(props: dict, t: dict, variables: dict) -> str:
    return (f'<div style="margin-top:18px; border-top:1px solid #e5e7eb; padding-top:6px; '
            f'color:{t["footer_color"]}; font-size:6.5pt; text-align:center;">'
            f'{_sub(props.get("text"), variables)}</div>')


# Blocs qui vont dans la colonne de DROITE de la zone deux-colonnes.
_BODY_TYPES = {"recipient", "reference", "greeting", "amount_bar", "free_text"}
# Blocs pleine largeur (rendus après la zone deux-colonnes, dans l'ordre).
_FULL_TYPES = {"details_table", "legal_footer"}


def render_avis_blocks_html(
    blocks: list[dict],
    theme: Optional[dict],
    variables: dict,
    line_items: Optional[list] = None,
    logo_path: Optional[str] = None,
    page_margin: str = "1.3cm 1.4cm",
) -> str:
    """Compose le HTML complet de l'avis d'échéance à partir des blocs."""
    t = _theme(theme)
    blocks = blocks or []
    line_items = line_items or []

    header_html = ""
    sidebar_html = ""
    body_parts: list[str] = []
    full_parts: list[str] = []

    for b in blocks:
        if not isinstance(b, dict) or not b.get("enabled", True):
            continue
        btype = b.get("type")
        props = b.get("props", {}) or {}
        if btype == "header":
            header_html = _render_header(props, t, variables, logo_path)
        elif btype == "sidebar":
            sidebar_html = _render_sidebar(props, t, variables)
        elif btype == "recipient":
            body_parts.append(_render_recipient(props, t, variables))
        elif btype == "reference":
            body_parts.append(_render_reference(props, t, variables))
        elif btype == "greeting":
            body_parts.append(_render_greeting(props, t, variables))
        elif btype == "amount_bar":
            body_parts.append(_render_amount_bar(props, t, variables))
        elif btype == "free_text":
            body_parts.append(_render_free_text(props, t, variables))
        elif btype == "details_table":
            full_parts.append(_render_details_table(props, t, variables, line_items))
        elif btype == "legal_footer":
            full_parts.append(_render_legal_footer(props, t, variables))

    # Zone deux colonnes (sidebar + corps). Si pas de sidebar, le corps prend
    # toute la largeur.
    body_html = "".join(body_parts)
    if sidebar_html:
        twocol = f"""
        <table class="twocol"><tr>
          <td class="col-side">{sidebar_html}</td>
          <td class="col-main">{body_html}</td>
        </tr></table>"""
    else:
        twocol = f'<div>{body_html}</div>'

    full_html = "".join(full_parts)

    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><style>
  @page {{ size: A4; margin: {page_margin}; }}
  body {{ font-family: {t['font_family']}; color: {t['navy']}; background: #fff; }}
  .band {{ width:100%; border-collapse:collapse; }}
  .band td {{ vertical-align: middle; }}
  .rule {{ border:0; border-top:2px solid {t['navy']}; margin:8px 0 14px 0; }}
  .twocol {{ width:100%; border-collapse:collapse; }}
  .col-side {{ width:27%; vertical-align:top; padding-right:14px; }}
  .col-main {{ width:73%; vertical-align:top; }}
  .amount-bar {{ width:100%; border-collapse:collapse; margin:4px 0 8px 0; }}
  .details {{ width:100%; border-collapse:collapse; margin-top:6px; }}
  .details td {{ border-bottom:1px solid #ffffff; }}
</style></head><body>
  {header_html}
  {twocol}
  {full_html}
</body></html>"""
