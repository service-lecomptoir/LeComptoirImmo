# -*- coding: utf-8 -*-
"""Phase 3 — Actions exécutées par les agents IA (avec confirmation).

Boucle sûre : le LLM interprète la demande → action structurée (liste blanche),
résolue dans le PÉRIMÈTRE du gestionnaire → résumé + demande de confirmation →
sur « OUI » l'action s'exécute. Aucune action n'est exécutée sans confirmation.

Actions (v1) : générer/envoyer un avis d'échéance, générer/envoyer une quittance,
enregistrer un paiement reçu, créer une démarche (ticket).
"""
from __future__ import annotations
import json
import re
import uuid
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.models.user import User
from app.models.tenant import Tenant
from app.models.lease import Lease
from app.models.payment import Payment, PaymentStatus
from app.services import llm_service

_MANAGER_ROLES = (Role.GESTIONNAIRE, Role.GESTIONNAIRE_PROPRIO, Role.ADMIN)
_CONFIRM_WORDS = {"oui", "ok", "okay", "confirme", "confirmer", "je confirme", "valide",
                  "valider", "go", "yes", "d'accord", "daccord", "c'est bon"}
_CANCEL_WORDS = {"non", "annule", "annuler", "stop", "cancel", "abandonne", "laisse tomber"}

_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "décembre": 12, "decembre": 12,
}


def is_confirmation(text: str) -> bool:
    return (text or "").strip().lower().rstrip("!. ") in _CONFIRM_WORDS


def is_cancellation(text: str) -> bool:
    return (text or "").strip().lower().rstrip("!. ") in _CANCEL_WORDS


def is_manager(user: User) -> bool:
    try:
        return Role(user.role) in _MANAGER_ROLES
    except ValueError:
        return False


# ── Interprétation LLM → action structurée ───────────────────────────────────
_ACTION_PROMPT = (
    "Tu analyses un message d'un GESTIONNAIRE immobilier pour détecter s'il demande "
    "une ACTION à exécuter. Réponds UNIQUEMENT par un objet JSON valide, sans texte autour.\n\n"
    "Schéma :\n"
    "{\n"
    '  "action": "avis" | "quittance" | "paiement" | "demarche" | "none",\n'
    '  "tenant": "<nom du locataire mentionné, sinon null>",\n'
    '  "month": <numéro de mois 1-12 ou null>,\n'
    '  "year": <année AAAA ou null>,\n'
    '  "amount": <montant en euros ou null>,\n'
    '  "method": "virement" | "cheque" | "prelevement" | "especes" | null,\n'
    '  "send_email": <true si le message demande explicitement d\'ENVOYER au locataire, sinon false>,\n'
    '  "title": "<titre court si action=demarche, sinon null>",\n'
    '  "note": "<contenu/description si demarche, sinon null>"\n'
    "}\n\n"
    "Règles : 'action'='avis' pour générer/envoyer un avis d'échéance ; 'quittance' pour une quittance ; "
    "'paiement' pour enregistrer un loyer encaissé ; 'demarche' pour ouvrir une démarche/note. "
    "Même si la demande est formulée comme une QUESTION (« peux-tu générer un avis ? », « tu sais "
    "faire une quittance ? ») ou si le nom du locataire n'est pas précisé, renvoie quand même "
    "l'action correspondante (NE mets PAS 'none'). Mets 'none' UNIQUEMENT pour une demande "
    "d'information pure qui n'implique aucune de ces 4 opérations (ex. « combien d'impayés ? », "
    "« qu'est-ce qu'un avis d'échéance ? »). Ne devine pas un locataire : si aucun nom n'est cité, mets null."
)


def _parse_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return None


async def _llm_intent(text: str) -> Optional[dict]:
    if not llm_service.enabled():
        return None
    raw = await llm_service.chat(
        [{"role": "system", "content": _ACTION_PROMPT}, {"role": "user", "content": text}],
        temperature=0.0, max_tokens=300,
    )
    return _parse_json(raw or "")


# ── Résolution d'entités dans le périmètre ───────────────────────────────────
async def _find_tenants(db: AsyncSession, user: User, name: str) -> list[Tenant]:
    """Locataires correspondant au nom, restreints au périmètre du gestionnaire."""
    from app.services.tenant_service import TenantService
    from app.api.v1._isolation import agency_member_ids
    tenants, _ = await TenantService.list_all(db, search=name, limit=25)
    role = Role(user.role)
    if role == Role.ADMIN:
        return list(tenants)
    if role == Role.GESTIONNAIRE_PROPRIO:
        return [t for t in tenants if t.created_by == user.id]
    # Mandataire : uniquement les locataires de SON agence
    members = await agency_member_ids(db, user)
    return [t for t in tenants if t.created_by in members]


async def _active_lease(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[Lease]:
    return (await db.execute(
        select(Lease).where(Lease.tenant_id == tenant_id, Lease.is_active.is_(True))
        .order_by(Lease.start_date.desc())
    )).scalars().first()


async def _payment(db, lease_id, year, month) -> Optional[Payment]:
    return (await db.execute(
        select(Payment).where(
            Payment.lease_id == lease_id,
            Payment.period_year == year,
            Payment.period_month == month,
        )
    )).scalar_one_or_none()


def _eur(v) -> str:
    return f"{float(v or 0):,.2f} €".replace(",", " ")


# ── Construction de la proposition (avec confirmation) ───────────────────────
async def interpret(db: AsyncSession, user: User, text: str) -> Optional[dict]:
    """Retourne :
      - None  → pas une action (l'appelant bascule sur la Q&R) ;
      - {"reply": str}  → message immédiat (erreur / clarification, pas d'action en attente) ;
      - {"reply": str, "pending": {...}}  → proposition à confirmer (à stocker).
    """
    if not is_manager(user):
        return None
    intent = await _llm_intent(text)
    if not intent or intent.get("action") in (None, "none", ""):
        return None

    action = intent["action"]
    today = date.today()
    year = intent.get("year") or today.year
    month = intent.get("month") or today.month
    try:
        year, month = int(year), int(month)
    except Exception:  # noqa: BLE001
        year, month = today.year, today.month

    # Démarche : pas besoin d'un paiement, mais d'un locataire + titre
    _LABELS = {"avis": "générer un avis d'échéance", "quittance": "générer une quittance",
               "paiement": "enregistrer un paiement", "demarche": "ouvrir une démarche"}
    name = (intent.get("tenant") or "").strip()
    if not name and action in ("avis", "quittance", "paiement", "demarche"):
        ex = {"avis": "génère l'avis de juin pour Dupont",
              "quittance": "envoie la quittance de mai à Dupont",
              "paiement": "enregistre le paiement de Dupont pour ce mois",
              "demarche": "ouvre une démarche pour Dupont : fuite d'eau"}.get(action, "")
        return {"reply": (f"Oui, je peux <b>{_LABELS.get(action, 'le faire')}</b> 👍 "
                          f"Indiquez le locataire en une phrase, ex. : « {ex} ».")}

    tenants = await _find_tenants(db, user, name)
    if not tenants:
        return {"reply": f"Aucun locataire « {name} » trouvé dans votre portefeuille."}
    if len(tenants) > 1:
        noms = ", ".join(t.full_name for t in tenants[:6])
        return {"reply": f"Plusieurs locataires correspondent à « {name} » : {noms}. Précisez le nom complet."}
    tenant = tenants[0]

    lease = await _active_lease(db, tenant.id)
    if action in ("avis", "quittance", "paiement") and not lease:
        return {"reply": f"{tenant.full_name} n'a pas de bail actif."}

    mois_lbl = f"{month:02d}/{year}"
    send_email = bool(intent.get("send_email"))

    if action == "avis":
        pending = {
            "action": "avis", "tenant_id": str(tenant.id), "lease_id": str(lease.id),
            "year": year, "month": month, "send_email": send_email,
        }
        envoi = " et l'<b>envoyer par e-mail</b>" if send_email else ""
        return {"reply": (f"📄 Je vais générer l'avis d'échéance <b>{mois_lbl}</b> pour "
                          f"<b>{tenant.full_name}</b>{envoi}.\nConfirmez ? Répondez <b>OUI</b>."),
                "pending": pending}

    if action == "quittance":
        pay = await _payment(db, lease.id, year, month)
        if not pay:
            return {"reply": f"Aucun loyer trouvé pour {tenant.full_name} en {mois_lbl}."}
        if pay.status not in (PaymentStatus.PAID, PaymentStatus.PARTIAL,
                              PaymentStatus.PAID.value, PaymentStatus.PARTIAL.value):
            return {"reply": (f"Le loyer {mois_lbl} de {tenant.full_name} n'est pas réglé "
                              f"(statut : {pay.status}). Une quittance n'est émise que pour un loyer payé.")}
        pending = {
            "action": "quittance", "tenant_id": str(tenant.id), "payment_id": str(pay.id),
            "year": year, "month": month, "send_email": send_email,
        }
        envoi = " et l'<b>envoyer</b> au locataire" if send_email else ""
        return {"reply": (f"🧾 Je vais générer la quittance <b>{mois_lbl}</b> pour "
                          f"<b>{tenant.full_name}</b>{envoi}.\nConfirmez ? Répondez <b>OUI</b>."),
                "pending": pending}

    if action == "paiement":
        pay = await _payment(db, lease.id, year, month)
        if not pay:
            return {"reply": f"Aucun loyer trouvé pour {tenant.full_name} en {mois_lbl}."}
        balance = float(pay.amount_due) - float(pay.amount_paid)
        amount = intent.get("amount")
        try:
            amount = float(amount) if amount is not None else max(0.0, balance)
        except Exception:  # noqa: BLE001
            amount = max(0.0, balance)
        if amount <= 0:
            return {"reply": f"Le loyer {mois_lbl} de {tenant.full_name} est déjà soldé."}
        method = intent.get("method") or "virement"
        pending = {
            "action": "paiement", "tenant_id": str(tenant.id), "payment_id": str(pay.id),
            "amount": amount, "method": method, "year": year, "month": month,
        }
        return {"reply": (f"💶 Je vais enregistrer un paiement de <b>{_eur(amount)}</b> "
                          f"({method}) pour <b>{tenant.full_name}</b> : loyer {mois_lbl}.\n"
                          f"Confirmez ? Répondez <b>OUI</b>."),
                "pending": pending}

    if action == "demarche":
        title = (intent.get("title") or "Démarche").strip()[:200]
        note = (intent.get("note") or title).strip()
        pending = {
            "action": "demarche", "tenant_id": str(tenant.id),
            "title": title, "note": note,
        }
        return {"reply": (f"🗂️ Je vais ouvrir une démarche « <b>{title}</b> » pour "
                          f"<b>{tenant.full_name}</b>.\nConfirmez ? Répondez <b>OUI</b>."),
                "pending": pending}

    return None


# ── Exécution (après confirmation) ───────────────────────────────────────────
async def execute(db: AsyncSession, user: User, pending: dict) -> str:
    action = pending.get("action")
    try:
        if action == "avis":
            return await _exec_avis(db, user, pending)
        if action == "quittance":
            return await _exec_quittance(db, user, pending)
        if action == "paiement":
            return await _exec_paiement(db, user, pending)
        if action == "demarche":
            return await _exec_demarche(db, user, pending)
    except Exception as exc:  # noqa: BLE001
        return f"❌ Échec de l'action : {exc}"
    return "Action inconnue."


async def _exec_avis(db, user, p) -> str:
    from app.services.avis_echeance_service import AvisEcheanceService
    from app.models.avis_echeance import AvisEcheance
    from app.core.exceptions import ConflictException
    lease = await db.get(Lease, uuid.UUID(p["lease_id"]))
    tenant = await db.get(Tenant, uuid.UUID(p["tenant_id"]))
    year, month = int(p["year"]), int(p["month"])
    mois = f"{month:02d}/{year}"
    already = False
    try:
        avis = await AvisEcheanceService.generate_for_lease(
            db, lease, year, month, generated_by=user.id
        )
        await db.commit()
    except ConflictException:
        # Un avis de loyer existe déjà pour cette période → on le récupère au lieu
        # d'échouer. Filtrer kind='loyer' (un avis d'apurement de la même période
        # ne doit pas faire remonter 2 lignes → MultipleResultsFound).
        await db.rollback()
        avis = (await db.execute(
            select(AvisEcheance).where(
                AvisEcheance.lease_id == lease.id,
                AvisEcheance.period_year == year,
                AvisEcheance.period_month == month,
                (AvisEcheance.kind == "loyer") | (AvisEcheance.kind.is_(None)),
            )
        )).scalar_one_or_none()
        if avis is None:
            return (f"ℹ️ Un avis d'échéance {mois} existe déjà pour {tenant.full_name} "
                    f"(consultable dans « Avis d'échéances »).")
        already = True
    extra = ""
    if p.get("send_email") and tenant and tenant.email:
        try:
            from app.services.email_service import send_avis_echeance
            ok = await send_avis_echeance(
                to=tenant.email,
                tenant_name=tenant.full_name or tenant.email,
                period_label=getattr(avis, "period_range_label", None) or mois,
                amount_total=float(avis.amount_total),
                due_date=avis.due_date.strftime("%d/%m/%Y") if getattr(avis, "due_date", None) else "",
            )
            extra = " et envoyé par e-mail" if ok else " (e-mail non envoyé : SMTP désactivé)"
        except Exception:  # noqa: BLE001
            extra = " (e-mail non envoyé)"
    verbe = "existait déjà" if already else "généré"
    return f"✅ Avis d'échéance {mois} {verbe} pour {tenant.full_name} : {_eur(avis.amount_total)}{extra}."


async def _exec_quittance(db, user, p) -> str:
    from app.services.payment_service import PaymentService
    pay = await PaymentService.send_quittance(db, uuid.UUID(p["payment_id"]))
    await db.commit()
    tenant = await db.get(Tenant, uuid.UUID(p["tenant_id"]))
    mois = f"{int(p['month']):02d}/{int(p['year'])}"
    extra = ""
    if p.get("send_email") and tenant and tenant.email:
        try:
            from app.services.email_service import send_quittance as email_quittance
            ok = await email_quittance(
                to=tenant.email,
                tenant_name=tenant.full_name or tenant.email,
                period_label=mois,
                amount=float(pay.amount_paid),
            )
            extra = " et envoyée par e-mail" if ok else " (e-mail non envoyé : SMTP désactivé)"
        except Exception:  # noqa: BLE001
            extra = " (e-mail non envoyé)"
    return (f"✅ Quittance {mois} prête pour {tenant.full_name}{extra}. "
            f"Téléchargeable dans l'application (Paiements / Quittances).")


async def _exec_paiement(db, user, p) -> str:
    from app.services.payment_service import PaymentService
    from app.schemas.payment import PaymentRecordIn
    data = PaymentRecordIn(
        amount_paid=float(p["amount"]),
        payment_date=date.today(),
        payment_method=p.get("method") or "virement",
        notes="Enregistré via agent IA",
    )
    pay = await PaymentService.record_payment(db, uuid.UUID(p["payment_id"]), data)
    await db.commit()
    tenant = await db.get(Tenant, uuid.UUID(p["tenant_id"]))
    balance = float(pay.amount_due) - float(pay.amount_paid)
    solde = "soldé ✅" if balance <= 0 else f"reste dû {_eur(balance)}"
    return (f"✅ Paiement de {_eur(p['amount'])} enregistré pour {tenant.full_name} "
            f"(loyer {int(p['month']):02d}/{int(p['year'])}) : statut : {pay.status}, {solde}.")


async def _exec_demarche(db, user, p) -> str:
    from app.services.ticket_service import TicketService
    tenant = await db.get(Tenant, uuid.UUID(p["tenant_id"]))
    ticket = await TicketService.create_for_tenant(
        db, tenant_id=uuid.UUID(p["tenant_id"]),
        title=p["title"], description=p.get("note") or p["title"],
        author_user_id=user.id,
    )
    await db.commit()
    return f"✅ Démarche « {ticket.title} » ouverte pour {tenant.full_name}."
