# -*- coding: utf-8 -*-
"""Équipe d'agents IA (Phase 1 — déterministe, gratuite).

Trois agents spécialisés répondent aux gestionnaires (via Telegram ou autre) :
  - Comptable     : paiements, impayés, encaissements, quittances.
  - Sécurité      : démarches / incidents / conflits de voisinage.
  - Administratif : biens, locataires, contrats, entretiens.

Phase 1 : routage par mots-clés + réponses construites à partir des données
existantes (lecture seule), strictement dans le périmètre du gestionnaire
(isolation par rôle). Aucune dépendance à un modèle externe → gratuit.

Phase 2 : si un LLM est configuré (`AGENT_LLM_API_KEY`), `answer()` lui confie
la COMPRÉHENSION du message et la RÉDACTION de la réponse, mais en l'ancrant sur
un INSTANTANÉ chiffré des vraies données (scopé par rôle) — le modèle a interdiction
d'inventer des chiffres. Sans clé (ou si l'appel échoue), repli automatique sur le
routeur déterministe de la Phase 1. Le canal et le périmètre restent identiques.
"""
from __future__ import annotations
import re
from datetime import date
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.user import User
from app.models.lease import Lease
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.services import llm_service

AGENTS = {
    "comptable": {"name": "Agent Comptable", "emoji": "📊",
                  "desc": "Paiements, impayés, encaissements, quittances."},
    "securite": {"name": "Agent Sécurité", "emoji": "🛡️",
                 "desc": "Démarches, incidents et conflits de voisinage."},
    "administratif": {"name": "Agent Administratif", "emoji": "🗂️",
                      "desc": "Biens, locataires, contrats et entretiens."},
}

_KEYWORDS = {
    "comptable": ("impay", "retard", "loyer", "encaiss", "revenu", "paiement", "paie", "quittance", "comptable", "argent", "solde"),
    "securite": ("démarche", "demarche", "incident", "conflit", "voisin", "litige", "sécur", "secur", "plainte", "trouble"),
    "administratif": ("bien", "logement", "propriété", "propriete", "locataire", "bail", "contrat", "administ", "entretien", "maintenance", "occupation"),
}


def classify(text: str) -> str:
    """Détermine l'agent compétent pour un message (défaut : aide)."""
    t = (text or "").lower()
    if not t.strip():
        return "help"
    if any(k in t for k in ("aide", "help", "bonjour", "salut", "menu", "/start")):
        return "help"
    if any(k in t for k in ("rappel", "résumé", "resume", "synthèse", "synthese", "/rappels")):
        return "reminders"
    best, score = "help", 0
    for agent, kws in _KEYWORDS.items():
        n = sum(1 for k in kws if k in t)
        if n > score:
            best, score = agent, n
    return best if score > 0 else "help"


# ── Périmètre (isolation rôle) ───────────────────────────────────────────────
async def _scope(db: AsyncSession, user: User):
    """Retourne ('all'|'include'|'exclude', set|None) sur les property_id."""
    role = Role(user.role)
    if role == Role.ADMIN:
        return "all", None
    if role == Role.GESTIONNAIRE_PROPRIO:
        ids = set((await db.execute(
            select(Property.id).where(Property.created_by == user.id)
        )).scalars().all())
        return "include", ids
    from app.api.v1._isolation import gp_property_ids
    return "exclude", await gp_property_ids(db)


def _apply(q, mode, ids):
    if mode == "include":
        return q.where(Property.id.in_(ids)) if ids else q.where(False)
    if mode == "exclude" and ids:
        return q.where(Property.id.notin_(ids))
    return q


# ── Agent Comptable ──────────────────────────────────────────────────────────
async def _comptable(db, user, t, mode, ids) -> str:
    today = date.today()
    if any(k in t for k in ("revenu", "encaiss", "encaissé", "ce mois")):
        first = today.replace(day=1)
        q = _apply(
            select(func.coalesce(func.sum(Payment.amount_paid), 0))
            .join(Lease, Payment.lease_id == Lease.id)
            .join(Property, Lease.property_id == Property.id)
            .where(Payment.payment_date >= first), mode, ids)
        total = float((await db.execute(q)).scalar_one() or 0)
        return f"📊 Encaissé depuis le 1er du mois : <b>{total:,.2f} €</b>".replace(",", " ")
    # défaut comptable : impayés en cours
    q = _apply(
        select(Tenant.first_name, Tenant.last_name, Payment.amount_due, Payment.amount_paid, Payment.period_year, Payment.period_month)
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Property, Lease.property_id == Property.id)
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(Payment.due_date < today, Payment.status.in_(["pending", "partial", "late"])), mode, ids)
    rows = list((await db.execute(q)).all())
    if not rows:
        return "📊 Aucun impayé en cours. 👍"
    lines = ["📊 <b>Impayés en cours :</b>"]
    total = 0.0
    for fn, ln, due, paid, py, pm in rows[:15]:
        bal = float(due) - float(paid)
        total += max(0.0, bal)
        lines.append(f"• {fn} {ln} — {bal:,.2f} € ({pm:02d}/{py})".replace(",", " "))
    lines.append(f"<b>Total dû : {total:,.2f} €</b>".replace(",", " "))
    return "\n".join(lines)


# ── Agent Sécurité ───────────────────────────────────────────────────────────
async def _securite(db, user, t, mode, ids) -> str:
    q = _apply(
        select(Ticket.title, Ticket.status, Tenant.first_name, Tenant.last_name)
        .join(Tenant, Ticket.tenant_id == Tenant.id)
        .join(Lease, Lease.tenant_id == Tenant.id)
        .join(Property, Lease.property_id == Property.id)
        .where(Ticket.status.in_(["open", "in_progress", "pending_closure"])), mode, ids)
    rows = list((await db.execute(q)).all())
    if not rows:
        return "🛡️ Aucune démarche en cours. Tout est calme. 👍"
    seen = set(); lines = ["🛡️ <b>Démarches en cours :</b>"]
    for title, status, fn, ln in rows:
        key = (title, fn, ln)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"• {title} — {fn} {ln} ({status})")
        if len(lines) > 15:
            break
    return "\n".join(lines)


# ── Agent Administratif ──────────────────────────────────────────────────────
async def _administratif(db, user, t, mode, ids) -> str:
    props = (await db.execute(_apply(select(func.count(Property.id)), mode, ids))).scalar_one() or 0
    occ = (await db.execute(_apply(
        select(func.count(func.distinct(Lease.property_id)))
        .join(Property, Lease.property_id == Property.id)
        .where(Lease.is_active.is_(True)), mode, ids))).scalar_one() or 0
    leases = (await db.execute(_apply(
        select(func.count(Lease.id))
        .join(Property, Lease.property_id == Property.id)
        .where(Lease.is_active.is_(True)), mode, ids))).scalar_one() or 0
    return (f"🗂️ <b>Synthèse administrative :</b>\n"
            f"• Biens : {props} (occupés : {occ})\n"
            f"• Contrats actifs : {leases}")


def _help() -> str:
    lines = ["👋 <b>Votre équipe d'agents Le Comptoir Immo :</b>"]
    for a in AGENTS.values():
        lines.append(f"{a['emoji']} <b>{a['name']}</b> — {a['desc']}")
    lines.append("")
    lines.append("💬 <b>Questions</b> : « impayés », « démarches en cours », « combien de biens », « résumé ».")
    lines.append("⚡ <b>Actions</b> (je demande confirmation avant) :")
    lines.append("• « génère l'avis de juin pour Dupont »")
    lines.append("• « envoie la quittance de mai à Martin »")
    lines.append("• « enregistre le paiement de Dupont pour ce mois »")
    lines.append("• « ouvre une démarche pour Martin : fuite d'eau »")
    return "\n".join(lines)


async def reminders(db: AsyncSession, user: User) -> str:
    """Synthèse multi-agents (utilisée pour « résumé » et les rappels planifiés)."""
    mode, ids = await _scope(db, user)
    parts = [
        await _comptable(db, user, "impayés", mode, ids),
        await _securite(db, user, "démarches", mode, ids),
        await _administratif(db, user, "synthèse", mode, ids),
    ]
    return "🔔 <b>Votre point du jour</b>\n\n" + "\n\n".join(parts)


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")


async def _echeances_du_mois(db, mode, ids) -> str:
    """Synthèse des avis d'échéance / loyers appelés sur le mois en cours."""
    today = date.today()
    first = today.replace(day=1)
    nxt = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)
    q = _apply(
        select(
            func.count(Payment.id),
            func.coalesce(func.sum(Payment.amount_due), 0),
            func.coalesce(func.sum(Payment.amount_paid), 0),
        )
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Property, Lease.property_id == Property.id)
        .where(Payment.due_date >= first, Payment.due_date < nxt), mode, ids)
    cnt, due, paid = (await db.execute(q)).one()
    return (f"Échéances du mois en cours : {int(cnt or 0)} avis émis, "
            f"total appelé {float(due or 0):.2f} €, encaissé {float(paid or 0):.2f} €.")


async def _snapshot(db, user, mode, ids) -> str:
    """Instantané chiffré des données scopées du gestionnaire (contexte LLM).

    Réutilise les agents déterministes (chiffres réels uniquement) ; les balises
    HTML sont retirées pour un contexte propre."""
    encaisse = await _comptable(db, user, "encaissé ce mois", mode, ids)
    impayes = await _comptable(db, user, "impayés", mode, ids)
    echeances = await _echeances_du_mois(db, mode, ids)
    secu = await _securite(db, user, "démarches", mode, ids)
    admin = await _administratif(db, user, "synthèse", mode, ids)
    parts = [
        "[COMPTABLE]\n" + _strip_html(encaisse) + "\n" + echeances + "\n" + _strip_html(impayes),
        "[SÉCURITÉ]\n" + _strip_html(secu),
        "[ADMINISTRATIF]\n" + _strip_html(admin),
    ]
    return "\n\n".join(parts)


_SYSTEM_PROMPT = (
    "Tu es l'équipe d'agents IA de « Le Comptoir Immo », une application de gestion "
    "locative. Tu réunis trois spécialités : Agent Comptable (impayés, encaissements, "
    "quittances), Agent Sécurité (démarches, incidents, conflits de voisinage) et Agent "
    "Administratif (biens, locataires, contrats, entretiens).\n\n"
    "RÈGLES :\n"
    "1. Réponds en français, de façon concise et professionnelle, adaptée à une messagerie "
    "(Telegram). Tu peux utiliser <b>gras</b> et des puces « • ».\n"
    "2. Pour tout CHIFFRE (montants, nombres, noms), utilise EXCLUSIVEMENT la section DONNÉES. "
    "N'invente JAMAIS une valeur absente des données.\n"
    "3. Tu peux répondre à des questions générales sur la gestion locative (ex. « qu'est-ce "
    "qu'un avis d'échéance ? », « comment réviser un loyer ? ») avec tes connaissances, en "
    "restant factuel et bref.\n"
    "4. Tu es en LECTURE SEULE : tu ne génères pas de document et n'effectues pas d'action. "
    "Si on te demande de produire/envoyer un document (avis d'échéance, quittance, etc.), "
    "explique où le faire dans l'application Le Comptoir Immo (ex. menu « Ma papeterie » pour "
    "les modèles, fiche du paiement pour la quittance, « Avis d'échéances » pour les avis) et "
    "propose un résumé des données pertinentes que tu possèdes.\n"
    "5. Si une donnée précise demandée n'est pas dans DONNÉES, dis-le et propose ce que tu peux fournir.\n"
    "6. Les montants sont en euros (€). Va à l'essentiel ; pas de longue introduction."
)


async def answer(db: AsyncSession, user: User, text: str) -> str:
    """Point d'entrée : route le message et renvoie la réponse.

    Phase 2 (si LLM configuré) : le modèle traite TOUTE question, ancré sur un
    instantané chiffré scopé. Repli sur le routeur déterministe (Phase 1) si le LLM
    est désactivé ou échoue. Message vide → menu d'aide.
    """
    t = (text or "").strip()
    if not t:
        return _help()
    mode, ids = await _scope(db, user)

    # ── Phase 2 : LLM ancré sur les données réelles (gère toutes les questions) ──
    if llm_service.enabled():
        try:
            snapshot = await _snapshot(db, user, mode, ids)
            reply = await llm_service.chat([
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"DONNÉES (périmètre de l'utilisateur) :\n{snapshot}\n\n"
                                            f"QUESTION : {text}"},
            ])
            if reply:
                return reply
        except Exception:  # noqa: BLE001 — ne jamais casser le canal
            pass

    # ── Phase 1 : repli déterministe (mots-clés) ──
    agent = classify(text)
    if agent == "help":
        return _help()
    if agent == "reminders":
        return await reminders(db, user)
    tl = t.lower()
    if agent == "comptable":
        return await _comptable(db, user, tl, mode, ids)
    if agent == "securite":
        return await _securite(db, user, tl, mode, ids)
    return await _administratif(db, user, tl, mode, ids)
