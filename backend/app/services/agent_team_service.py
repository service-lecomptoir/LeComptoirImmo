# -*- coding: utf-8 -*-
"""Équipe d'agents IA spécialisés au service du gestionnaire.

Trois experts métier, chacun avec SA spécialité, SON périmètre de données (scopé
par rôle) et SA personnalité :
  - 📊 Comptable     : loyers, impayés (ancienneté), encaissements, recouvrement,
                       échéances à venir, quittances, paiements.
  - 🛡️ Sécurité      : démarches/incidents, signalements de la résidence (bruit,
                       sécurité, ascenseur, propreté…), conflits de voisinage.
  - 🗂️ Administratif : biens (occupation/vacance), contrats, baux à échéance,
                       candidatures et visites, entretiens.

Architecture (inchangée, fail-open) :
  - Phase 1 : routage par mots-clés + réponses construites sur les VRAIES données
    (lecture seule, scopées). Aucune dépendance externe → gratuit.
  - Phase 2 : si un LLM est configuré, il RÉDIGE la réponse en endossant la
    PERSONA de l'agent compétent, ancré sur un INSTANTANÉ chiffré (interdiction
    d'inventer). Repli automatique sur la Phase 1 si le LLM est absent/échoue.
  - Phase 3 (agent_action_service) : actions avec confirmation.
"""
from __future__ import annotations
import re
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.user import User
from app.models.lease import Lease
from app.models.property import Property
from app.models.tenant import Tenant
from app.models.payment import Payment
from app.models.ticket import Ticket
from app.models.signalement import Signalement, SignalementStatus
from app.models.entretien import Entretien, EntretienStatus
from app.models.candidature import Candidature
from app.services import llm_service

AGENTS = {
    "comptable": {"name": "Agent Comptable", "emoji": "📊",
                  "desc": "Loyers, impayés, encaissements, recouvrement, quittances."},
    "securite": {"name": "Agent Sécurité", "emoji": "🛡️",
                 "desc": "Démarches, signalements de la résidence, voisinage."},
    "administratif": {"name": "Agent Administratif", "emoji": "🗂️",
                      "desc": "Biens, contrats, baux à échéance, candidatures, entretiens."},
}

_KEYWORDS = {
    "comptable": ("impay", "retard", "loyer", "encaiss", "revenu", "paiement", "paie",
                  "quittance", "comptable", "argent", "solde", "recouvr",
                  "régularis", "regularis", "relance", "caution", "dépôt", "depot"),
    "securite": ("démarche", "demarche", "incident", "conflit", "voisin", "litige",
                 "sécur", "secur", "plainte", "trouble", "signalement", "bruit",
                 "ascenseur", "propreté", "proprete", "dégrad", "degrad", "urgent", "résidence", "residence"),
    "administratif": ("bien", "logement", "propriété", "propriete", "locataire", "bail",
                      "baux", "contrat", "administ", "entretien", "maintenance", "occupation",
                      "vacant", "vacance", "candidat", "candidature", "visite", "dossier",
                      "renouvel", "échéance", "echeance", "préavis", "preavis"),
}


def classify(text: str) -> str:
    """Détermine l'agent compétent pour un message (défaut : aide)."""
    t = (text or "").lower()
    if not t.strip():
        return "help"
    if any(k in t for k in ("aide", "help", "bonjour", "salut", "menu", "/start", "/help")):
        return "help"
    if any(k in t for k in ("rappel", "résumé", "resume", "synthèse", "synthese", "point du jour", "/rappels")):
        return "reminders"
    best, score = "help", 0
    for agent, kws in _KEYWORDS.items():
        n = sum(1 for k in kws if k in t)
        if n > score:
            best, score = agent, n
    return best if score > 0 else "help"


def _is_help_command(t: str) -> bool:
    return any(k in t for k in ("aide", "help", "bonjour", "salut", "menu", "/start", "/help"))


def _is_reminders_command(t: str) -> bool:
    return any(k in t for k in ("rappel", "résumé", "resume", "synthèse", "synthese", "point du jour", "/rappels"))


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
    # Mandataire : uniquement les biens de SON agence
    from app.api.v1._isolation import agency_property_ids
    return "include", await agency_property_ids(db, user)


def _apply(q, mode, ids):
    if mode == "include":
        return q.where(Property.id.in_(ids)) if ids else q.where(False)
    if mode == "exclude" and ids:
        return q.where(Property.id.notin_(ids))
    return q


def _eur(v) -> str:
    return f"{float(v or 0):,.2f} €".replace(",", " ")


def _months_label(months: int) -> str:
    return MONTHS_FR[months] if 0 <= months < len(MONTHS_FR) else str(months)


MONTHS_FR = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]


# ── Collecteurs scopés (réutilisés par les réponses ET l'instantané LLM) ──────
async def _sum_paid_month(db, mode, ids, year, month) -> float:
    first = date(year, month, 1)
    nxt = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    q = _apply(
        select(func.coalesce(func.sum(Payment.amount_paid), 0))
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Property, Lease.property_id == Property.id)
        .where(Payment.payment_date >= first, Payment.payment_date < nxt), mode, ids)
    return float((await db.execute(q)).scalar_one() or 0)


async def _called_month(db, mode, ids, year, month) -> tuple[float, float]:
    """(total appelé, total encaissé) sur les échéances dont la période est ce mois."""
    q = _apply(
        select(func.coalesce(func.sum(Payment.amount_due), 0),
               func.coalesce(func.sum(Payment.amount_paid), 0))
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Property, Lease.property_id == Property.id)
        .where(Payment.period_year == year, Payment.period_month == month), mode, ids)
    due, paid = (await db.execute(q)).one()
    return float(due or 0), float(paid or 0)


async def _impayes_rows(db, mode, ids):
    today = date.today()
    q = _apply(
        select(Tenant.first_name, Tenant.last_name, Payment.amount_due, Payment.amount_paid,
               Payment.period_year, Payment.period_month, Payment.due_date)
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Property, Lease.property_id == Property.id)
        .join(Tenant, Payment.tenant_id == Tenant.id)
        .where(Payment.due_date < today, Payment.status.in_(["pending", "partial", "late"]))
        .order_by(Payment.due_date), mode, ids)
    return list((await db.execute(q)).all())


async def _a_venir(db, mode, ids, days=7) -> tuple[int, float]:
    today = date.today()
    until = today + timedelta(days=days)
    q = _apply(
        select(func.count(Payment.id), func.coalesce(func.sum(Payment.amount_due - Payment.amount_paid), 0))
        .join(Lease, Payment.lease_id == Lease.id)
        .join(Property, Lease.property_id == Property.id)
        .where(Payment.due_date >= today, Payment.due_date <= until,
               Payment.status.in_(["pending", "partial", "late"])), mode, ids)
    cnt, total = (await db.execute(q)).one()
    return int(cnt or 0), float(total or 0)


async def _tickets_open(db, mode, ids):
    q = _apply(
        select(Ticket.title, Ticket.status, Tenant.first_name, Tenant.last_name, Ticket.created_at)
        .join(Tenant, Ticket.tenant_id == Tenant.id)
        .join(Lease, Lease.tenant_id == Tenant.id)
        .join(Property, Lease.property_id == Property.id)
        .where(Ticket.status.in_(["open", "in_progress", "pending_closure"])), mode, ids)
    return list((await db.execute(q)).all())


async def _signalements_open(db, mode, ids):
    q = _apply(
        select(Signalement.category, Signalement.urgency, Signalement.title, Signalement.occurred_at)
        .join(Property, Signalement.property_id == Property.id)
        .where(Signalement.status.in_([SignalementStatus.NOUVEAU.value, SignalementStatus.EN_COURS.value]))
        .order_by(Signalement.occurred_at.desc()), mode, ids)
    return list((await db.execute(q)).all())


async def _biens_stats(db, mode, ids) -> tuple[int, int, int]:
    """(biens, biens occupés, contrats actifs)."""
    props = (await db.execute(_apply(select(func.count(Property.id)), mode, ids))).scalar_one() or 0
    occ = (await db.execute(_apply(
        select(func.count(func.distinct(Lease.property_id)))
        .join(Property, Lease.property_id == Property.id)
        .where(Lease.is_active.is_(True)), mode, ids))).scalar_one() or 0
    leases = (await db.execute(_apply(
        select(func.count(Lease.id))
        .join(Property, Lease.property_id == Property.id)
        .where(Lease.is_active.is_(True)), mode, ids))).scalar_one() or 0
    return int(props), int(occ), int(leases)


async def _baux_echeance(db, mode, ids, days=90):
    today = date.today()
    until = today + timedelta(days=days)
    q = _apply(
        select(Tenant.first_name, Tenant.last_name, Lease.end_date, Property.name)
        .join(Property, Lease.property_id == Property.id)
        .join(Tenant, Lease.tenant_id == Tenant.id)
        .where(Lease.is_active.is_(True), Lease.end_date.isnot(None),
               Lease.end_date >= today, Lease.end_date <= until)
        .order_by(Lease.end_date), mode, ids)
    return list((await db.execute(q)).all())


async def _candidatures_stats(db, mode, ids) -> tuple[int, int]:
    """(candidatures en cours, visites proposées)."""
    en_cours = (await db.execute(_apply(
        select(func.count(Candidature.id))
        .join(Property, Candidature.property_id == Property.id)
        .where(Candidature.status.in_(["nouvelle", "documents_demandes", "en_etude"])), mode, ids))).scalar_one() or 0
    visites = (await db.execute(_apply(
        select(func.count(Candidature.id))
        .join(Property, Candidature.property_id == Property.id)
        .where(Candidature.visit_invited_at.isnot(None), Candidature.status != "refusee"), mode, ids))).scalar_one() or 0
    return int(en_cours), int(visites)


async def _entretiens_avenir(db, mode, ids, limit=10):
    today = date.today()
    q = _apply(
        select(Entretien.title, Entretien.scheduled_date, Property.name)
        .join(Property, Entretien.property_id == Property.id)
        .where(Entretien.scheduled_date >= today, Entretien.status != EntretienStatus.TERMINE)
        .order_by(Entretien.scheduled_date).limit(limit), mode, ids)
    return list((await db.execute(q)).all())


# ── Agent Comptable ──────────────────────────────────────────────────────────
async def _comptable(db, user, t, mode, ids) -> str:
    today = date.today()
    if any(k in t for k in ("recouvr", "taux")):
        due, paid = await _called_month(db, mode, ids, today.year, today.month)
        taux = (paid / due * 100) if due else 100.0
        return (f"📊 <b>Recouvrement {_months_label(today.month)} :</b> "
                f"{taux:.0f}% ({_eur(paid)} sur {_eur(due)} appelés).")
    if any(k in t for k in ("à venir", "a venir", "échéance", "echeance", "prochain")):
        cnt, total = await _a_venir(db, mode, ids, 7)
        if not cnt:
            return "📊 Aucune échéance à régler dans les 7 prochains jours."
        return f"📊 <b>À venir (7 jours) :</b> {cnt} échéance(s), reste à encaisser {_eur(total)}."
    if any(k in t for k in ("revenu", "encaiss", "encaissé", "ce mois")):
        total = await _sum_paid_month(db, mode, ids, today.year, today.month)
        return f"📊 Encaissé depuis le 1er du mois : <b>{_eur(total)}</b>."
    # défaut comptable : impayés en cours (avec ancienneté)
    rows = await _impayes_rows(db, mode, ids)
    if not rows:
        return "📊 Aucun impayé en cours. 👍"
    lines = ["📊 <b>Impayés en cours :</b>"]
    total = 0.0
    for fn, ln, due, paid, py, pm, due_date in rows[:15]:
        bal = float(due) - float(paid)
        total += max(0.0, bal)
        retard = (today - due_date).days if due_date else 0
        suffix = f", +{retard} j" if retard > 0 else ""
        lines.append(f"• {fn} {ln} : {_eur(bal)} ({pm:02d}/{py}{suffix})")
    if len(rows) > 15:
        lines.append(f"… et {len(rows) - 15} autre(s).")
    lines.append(f"<b>Total dû : {_eur(total)}</b>")
    return "\n".join(lines)


# ── Agent Sécurité ───────────────────────────────────────────────────────────
async def _securite(db, user, t, mode, ids) -> str:
    lines: list[str] = []
    # Signalements de la résidence (le cœur du métier « sécurité »)
    sigs = await _signalements_open(db, mode, ids)
    if sigs:
        urgents = sum(1 for c, u, ti, oc in sigs if u == "urgent")
        head = f"🛡️ <b>Signalements de la résidence ({len(sigs)}"
        head += f", dont {urgents} urgent(s)" if urgents else ""
        lines.append(head + ") :</b>")
        for cat, urg, title, _oc in sigs[:8]:
            flag = "🔴 " if urg == "urgent" else ""
            lines.append(f"• {flag}{title or cat.capitalize()} ({cat})")
    # Démarches / incidents en cours
    tickets = await _tickets_open(db, mode, ids)
    if tickets:
        seen = set()
        lines.append("🛡️ <b>Démarches en cours :</b>")
        for title, status, fn, ln, _ca in tickets:
            key = (title, fn, ln)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"• {title} : {fn} {ln} ({status})")
            if len(seen) >= 10:
                break
    if not lines:
        return "🛡️ Aucune démarche ni signalement en cours. Tout est calme. 👍"
    return "\n".join(lines)


# ── Agent Administratif ──────────────────────────────────────────────────────
async def _administratif(db, user, t, mode, ids) -> str:
    props, occ, leases = await _biens_stats(db, mode, ids)
    vacants = max(0, props - occ)
    lines = ["🗂️ <b>Synthèse administrative :</b>",
             f"• Biens : {props} (occupés : {occ}, vacants : {vacants})",
             f"• Contrats actifs : {leases}"]
    baux = await _baux_echeance(db, mode, ids, 90)
    if baux:
        lines.append(f"• Baux à échéance (< 90 j) : {len(baux)}")
        for fn, ln, end, pname in baux[:5]:
            lines.append(f"   ◦ {fn} {ln} ({pname}) : {end.strftime('%d/%m/%Y')}")
    cand, visites = await _candidatures_stats(db, mode, ids)
    if cand or visites:
        lines.append(f"• Candidatures en cours : {cand} (visites proposées : {visites})")
    ents = await _entretiens_avenir(db, mode, ids, 5)
    if ents:
        lines.append(f"• Entretiens à venir : {len(ents)}")
        for title, sd, pname in ents[:5]:
            lines.append(f"   ◦ {title} ({pname}) : {sd.strftime('%d/%m/%Y')}")
    return "\n".join(lines)


def _help() -> str:
    lines = ["👋 <b>Votre équipe d'agents Le Comptoir Immo :</b>"]
    for a in AGENTS.values():
        lines.append(f"{a['emoji']} <b>{a['name']}</b> : {a['desc']}")
    lines.append("")
    lines.append("💬 <b>Questions</b> (exemples) :")
    lines.append("• 📊 « impayés », « recouvrement du mois », « échéances à venir »")
    lines.append("• 🛡️ « signalements en cours », « démarches en cours »")
    lines.append("• 🗂️ « biens vacants », « baux à échéance », « candidatures », « entretiens »")
    lines.append("• « résumé » pour le point du jour complet")
    lines.append("")
    lines.append("⚡ <b>Actions</b> (je demande toujours confirmation) :")
    lines.append("• « génère l'avis de juin pour Dupont »")
    lines.append("• « envoie la quittance de mai à Martin »")
    lines.append("• « enregistre le paiement de Dupont pour ce mois »")
    lines.append("• « ouvre une démarche pour Martin : fuite d'eau »")
    return "\n".join(lines)


async def reminders(db: AsyncSession, user: User) -> str:
    """Point du jour multi-agents (« résumé » + rappels planifiés), scopé par rôle."""
    mode, ids = await _scope(db, user)
    today = date.today()
    parts = []

    # Comptable : impayés + à venir + recouvrement
    impayes = await _impayes_rows(db, mode, ids)
    total_du = sum(max(0.0, float(d) - float(p)) for _, _, d, p, _, _, _ in impayes)
    cnt_venir, total_venir = await _a_venir(db, mode, ids, 7)
    due, paid = await _called_month(db, mode, ids, today.year, today.month)
    taux = (paid / due * 100) if due else 100.0
    c = [f"📊 <b>Comptable</b> : {len(impayes)} impayé(s) ({_eur(total_du)}), "
         f"recouvrement {taux:.0f}%."]
    if cnt_venir:
        c.append(f"À venir 7 j : {cnt_venir} échéance(s), {_eur(total_venir)}.")
    parts.append("\n".join(c))

    # Sécurité : signalements + démarches
    sigs = await _signalements_open(db, mode, ids)
    urgents = sum(1 for _c, u, _t, _o in sigs if u == "urgent")
    tickets = await _tickets_open(db, mode, ids)
    s = f"🛡️ <b>Sécurité</b> : {len(sigs)} signalement(s)"
    s += f" (dont {urgents} urgent)" if urgents else ""
    s += f", {len({(t, f, l) for t, _st, f, l, _ca in tickets})} démarche(s) en cours."
    parts.append(s)

    # Administratif : vacance + baux à échéance + visites
    props, occ, leases = await _biens_stats(db, mode, ids)
    baux = await _baux_echeance(db, mode, ids, 90)
    cand, visites = await _candidatures_stats(db, mode, ids)
    a = (f"🗂️ <b>Administratif</b> : {max(0, props - occ)} bien(s) vacant(s), "
         f"{len(baux)} bail/baux à échéance, {cand} candidature(s)")
    a += f", {visites} visite(s) proposée(s)." if visites else "."
    parts.append(a)

    return "🔔 <b>Votre point du jour</b>\n\n" + "\n\n".join(parts)


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")


async def _snapshot(db, user, mode, ids) -> str:
    """Instantané chiffré et scopé (contexte LLM). Réutilise les collecteurs réels
    → aucun chiffre inventé. Trois sections, une par spécialité."""
    encaisse = await _comptable(db, user, "encaissé ce mois", mode, ids)
    recouvrement = await _comptable(db, user, "recouvrement", mode, ids)
    avenir = await _comptable(db, user, "à venir", mode, ids)
    impayes = await _comptable(db, user, "impayés", mode, ids)
    secu = await _securite(db, user, "signalements démarches", mode, ids)
    admin = await _administratif(db, user, "synthèse", mode, ids)
    parts = [
        "[COMPTABLE]\n" + "\n".join(_strip_html(x) for x in (encaisse, recouvrement, avenir, impayes)),
        "[SÉCURITÉ]\n" + _strip_html(secu),
        "[ADMINISTRATIF]\n" + _strip_html(admin),
    ]
    return "\n\n".join(parts)


# ── Personas LLM (Phase 2) : un expert par spécialité ────────────────────────
_COMMON_RULES = (
    "RÈGLES :\n"
    "1. Réponds en français, concis et professionnel, adapté à une messagerie (Telegram). "
    "Tu peux utiliser <b>gras</b> et des puces « • ».\n"
    "2. Pour tout CHIFFRE (montants, nombres, noms), utilise EXCLUSIVEMENT la section DONNÉES. "
    "N'invente JAMAIS une valeur absente des données.\n"
    "3. Tu peux répondre à des questions générales de gestion locative avec tes connaissances, "
    "en restant factuel et bref.\n"
    "4. TU PEUX RÉALISER DES ACTIONS (via une confirmation gérée par le système) : générer/envoyer "
    "un avis d'échéance, générer/envoyer une quittance, enregistrer un paiement reçu, ouvrir une "
    "démarche. Ne dis JAMAIS que tu es en lecture seule. S'il manque une info (locataire, mois), "
    "invite à reformuler en une phrase, ex. : « génère l'avis de juin pour Dupont ».\n"
    "5. Si une donnée demandée n'est pas dans DONNÉES, dis-le et propose ce que tu peux fournir.\n"
    "6. Montants en euros (€). Va à l'essentiel ; pas de longue introduction."
)

PERSONAS = {
    "comptable": (
        "Tu es l'Agent Comptable de « Le Comptoir Immo », expert en gestion financière locative : "
        "appels de loyer, encaissements, impayés et leur ancienneté, taux de recouvrement, "
        "régularisation de charges, quittances et relances. Tu raisonnes comme un comptable rigoureux : "
        "tu priorises les impayés les plus anciens, tu signales les risques et tu proposes l'action "
        "utile (relancer, encaisser, quittancer). Tu t'appuies sur la section [COMPTABLE] des données.\n\n"
        + _COMMON_RULES
    ),
    "securite": (
        "Tu es l'Agent Sécurité de « Le Comptoir Immo », spécialiste de la tranquillité et de la "
        "sûreté des résidences : signalements (bruit, sécurité des accès, ascenseur, propreté des "
        "communs, dégradations), démarches et incidents, conflits de voisinage. Tu hiérarchises par "
        "URGENCE, tu alertes sur ce qui doit être traité vite et tu suggères d'ouvrir/suivre une "
        "démarche. Tu t'appuies sur la section [SÉCURITÉ] des données.\n\n"
        + _COMMON_RULES
    ),
    "administratif": (
        "Tu es l'Agent Administratif de « Le Comptoir Immo », expert du cycle de vie locatif : biens "
        "et leur occupation/vacance, contrats, baux arrivant à échéance et renouvellements, "
        "candidatures et visites, entretiens et interventions. Tu anticipes les échéances (bail qui "
        "se termine, vacance à combler, entretien à planifier) et tu proposes l'étape suivante. "
        "Tu t'appuies sur la section [ADMINISTRATIF] des données.\n\n"
        + _COMMON_RULES
    ),
    "general": (
        "Tu es l'équipe d'agents IA de « Le Comptoir Immo » (Comptable, Sécurité, Administratif). "
        "Tu réponds avec la spécialité la plus pertinente à partir des DONNÉES fournies.\n\n"
        + _COMMON_RULES
    ),
}
# Rétro-compat : ancien nom du prompt unique.
_SYSTEM_PROMPT = PERSONAS["general"]


async def answer(db: AsyncSession, user: User, text: str) -> str:
    """Point d'entrée : route le message et renvoie la réponse.

    Commandes explicites (aide / résumé) → menu déterministe. Sinon, si un LLM est
    configuré, l'agent compétent RÉDIGE la réponse (persona dédiée, ancrée sur les
    données). Repli déterministe par spécialité si le LLM est absent/échoue.
    """
    t = (text or "").strip()
    if not t:
        return _help()
    tl = t.lower()
    if _is_help_command(tl):
        return _help()
    if _is_reminders_command(tl):
        return await reminders(db, user)

    mode, ids = await _scope(db, user)
    agent = classify(text)
    domain = agent if agent in ("comptable", "securite", "administratif") else "general"

    # ── Phase 2 : LLM en persona spécialisée, ancré sur les données réelles ──
    if llm_service.enabled():
        try:
            snapshot = await _snapshot(db, user, mode, ids)
            reply = await llm_service.chat([
                {"role": "system", "content": PERSONAS.get(domain, _SYSTEM_PROMPT)},
                {"role": "user", "content": f"DONNÉES (périmètre de l'utilisateur) :\n{snapshot}\n\n"
                                            f"QUESTION : {text}"},
            ])
            if reply:
                return reply
        except Exception:  # noqa: BLE001 : ne jamais casser le canal
            pass

    # ── Phase 1 : repli déterministe par spécialité ──
    if domain == "comptable":
        return await _comptable(db, user, tl, mode, ids)
    if domain == "securite":
        return await _securite(db, user, tl, mode, ids)
    if domain == "administratif":
        return await _administratif(db, user, tl, mode, ids)
    return _help()
