"""Communications de candidature pilotées par « Communication et automatisation ».

Chaque e-mail adressé à un candidat correspond à un type de règle (AutomationRule)
éditable par le gestionnaire : interrupteur on/off (is_active + send_email), objet,
corps et signature. C'est le lien entre le module Annonce/Candidatures et le module
Communication : le gestionnaire règle le ton et l'activation de chaque message au
même endroit que ses avis et quittances.

Repli : si la règle est absente ou ses champs vides, le sender garde son contenu
par défaut (aucune régression). Les candidats n'ont pas de langue enregistrée :
on reste en français (champ `subject`/`body_template` de la règle, pas le modèle
multilingue réservé aux locataires).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation import AutomationRule
from app.services.automation_engine import _msg_templates, render_rule_body, render_subject

# Types de règles « candidature » (event-driven).
ACCUSE = "candidature_accuse"
PIECES = "candidature_pieces"
VISITE = "candidature_visite"
RELANCE_VISITE = "candidature_relance_visite"
ACCEPTATION = "candidature_acceptation"
REFUS = "candidature_refus"

CANDIDATURE_RULE_TYPES = [ACCUSE, PIECES, VISITE, RELANCE_VISITE, ACCEPTATION, REFUS]


async def resolve(db: AsyncSession, gestionnaire_id, rule_type: str, ctx: dict) -> dict:
    """Résout l'e-mail candidat depuis la règle du gestionnaire.

    Retourne {active, subject, body_html, signature} :
      - active=False → ne PAS envoyer (le gestionnaire a coupé cet e-mail) ;
      - subject / body_html / signature = None → utiliser le défaut du sender.
    Fail-open : toute erreur ⇒ comportement par défaut (actif, contenu standard)."""
    default = {"active": True, "subject": None, "body_html": None, "signature": None}
    if not gestionnaire_id:
        return default
    try:
        rule = (
            await db.execute(
                select(AutomationRule)
                .where(
                    AutomationRule.created_by == gestionnaire_id,
                    AutomationRule.rule_type == rule_type,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
    except Exception:  # noqa: BLE001
        return default
    if rule is None:
        return default
    # Contenu : modèle « Communication » sélectionné (fr) si présent, sinon les
    # champs de la règle ; placeholders rendus avec le contexte de la candidature.
    try:
        subj_tmpl, body_tmpl, _sms = await _msg_templates(db, rule, "fr")
    except Exception:  # noqa: BLE001
        subj_tmpl, body_tmpl = rule.subject, rule.body_template
    return {
        "active": bool(rule.is_active) and bool(rule.send_email),
        "subject": render_subject(subj_tmpl, ctx),
        "body_html": render_rule_body(body_tmpl, ctx),
        "signature": (rule.signature or "").strip() or None,
    }
