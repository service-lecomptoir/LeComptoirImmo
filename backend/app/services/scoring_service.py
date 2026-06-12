# -*- coding: utf-8 -*-
"""Scoring de qualité de payeur des locataires.

Le score (0–100) agrège quatre facteurs pondérés :
  - Ponctualité de paiement (35 %)
  - Impayés en cours (25 %)
  - Taux d'effort = (loyer + charges) / revenus déclarés (20 %)
  - Relation locataire = événements relationnels saisis sur le contrat (20 %)

Aucun score n'est stocké : il est recalculé à la lecture (toujours à jour).
"""
from __future__ import annotations
from datetime import date
from typing import Optional

# ── Taxonomie des événements de relation (liste éditable sur le contrat) ───────
# Chaque type porte un poids appliqué au sous-score « relation » (base 70).
RELATION_BASE = 70
KIND_META: dict[str, dict] = {
    # Positifs
    "paiement_spontane": {"label": "Paiement spontané / en avance", "polarity": "positif", "weight": 10},
    "bon_contact":       {"label": "Bon contact / coopératif",       "polarity": "positif", "weight": 8},
    "regularisation":    {"label": "Régularisation d'un impayé",     "polarity": "positif", "weight": 12},
    "assurance_ok":      {"label": "Assurance habitation à jour",    "polarity": "positif", "weight": 5},
    # Neutres
    "contact":           {"label": "Prise de contact",               "polarity": "neutre",  "weight": 0},
    "autre":             {"label": "Autre",                          "polarity": "neutre",  "weight": 0},
    # Négatifs
    "retard_repete":     {"label": "Retards répétés",                "polarity": "negatif", "weight": -12},
    "impaye":            {"label": "Impayé constaté",                "polarity": "negatif", "weight": -18},
    "cheque_rejete":     {"label": "Chèque / prélèvement rejeté",    "polarity": "negatif", "weight": -12},
    "degradation":       {"label": "Dégradation du logement",        "polarity": "negatif", "weight": -15},
    "trouble_voisinage": {"label": "Trouble de voisinage",           "polarity": "negatif", "weight": -12},
    "injoignable":       {"label": "Locataire injoignable",          "polarity": "negatif", "weight": -10},
    "litige":            {"label": "Litige / contentieux",           "polarity": "negatif", "weight": -20},
    "refus_paiement":    {"label": "Refus de paiement",              "polarity": "negatif", "weight": -25},
}

# Pondérations des facteurs (somme = 1)
W_PONCTUALITE = 0.35
W_IMPAYES = 0.25
W_EFFORT = 0.20
W_RELATION = 0.20


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def event_kinds() -> list[dict]:
    """Catalogue des types d'événements pour le frontend (libellé + polarité)."""
    return [{"kind": k, **v} for k, v in KIND_META.items()]


def grade_for(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "E"


_STRATEGY = {
    "A": "Bon payeur : aucune action. Renouvellement recommandé.",
    "B": "Payeur fiable : surveillance de routine.",
    "C": "Vigilance : relancer rapidement à chaque retard ; sécuriser (garant / assurance).",
    "D": "À risque : relances soutenues, prise de contact directe, proposer un plan d'apurement.",
    "E": "Risque élevé : contact physique et mise en demeure ; envisager le non-renouvellement ou la résiliation.",
}


def _relation_subscore(events: Optional[list]) -> tuple[float, int]:
    if not events:
        return float(RELATION_BASE), 0
    total = RELATION_BASE
    for e in events:
        meta = KIND_META.get((e or {}).get("kind", ""), None)
        if meta:
            total += meta["weight"]
    return _clamp(total), len(events)


def compute(tenant, lease, payments: list, today: Optional[date] = None) -> dict:
    """Calcule le score d'un locataire à partir de données préchargées.

    `tenant` : modèle Tenant. `lease` : bail actif (ou None). `payments` : liste
    de Payment du locataire. Retourne un dict sérialisable (score, note, stratégie,
    facteurs détaillés, statistiques).
    """
    today = today or date.today()

    # ── Ponctualité & impayés ────────────────────────────────────────────────
    due = [p for p in payments if str(p.status) != "cancelled" and p.due_date and p.due_date <= today]
    total_due = len(due)
    on_time = 0
    overdue_count = 0
    outstanding = 0.0
    for p in due:
        status = str(p.status)
        paid_full = status == "paid"
        late = (status == "late") or (paid_full and p.payment_date and p.payment_date > p.due_date)
        unpaid_pastdue = status in ("pending", "partial", "late")
        if paid_full and not late:
            on_time += 1
        if unpaid_pastdue:
            overdue_count += 1
            try:
                outstanding += float(p.balance)
            except Exception:
                outstanding += max(0.0, float(p.amount_due) - float(p.amount_paid))

    if total_due > 0:
        on_time_rate = on_time / total_due
        ponctualite = round(on_time_rate * 100)
        ponct_detail = f"{on_time}/{total_due} échéance(s) payée(s) à l'heure"
    else:
        on_time_rate = None
        ponctualite = 75  # neutre : pas encore d'échéance due
        ponct_detail = "Aucune échéance échue à ce jour"

    impayes_score = round(_clamp(100 - overdue_count * 30))
    if overdue_count == 0:
        impayes_detail = "Aucun impayé en cours"
    else:
        impayes_detail = f"{overdue_count} échéance(s) impayée(s) — {outstanding:.2f} € dus"

    # ── Taux d'effort ────────────────────────────────────────────────────────
    income = float(tenant.monthly_income) if getattr(tenant, "monthly_income", None) else None
    monthly_total = float(lease.total_monthly) if lease else None
    effort_rate = None
    if income and monthly_total:
        effort_rate = monthly_total / income
        # 33 % → 100 ; 70 % → 0 (linéaire)
        effort_score = round(_clamp((0.70 - effort_rate) / (0.70 - 0.33) * 100))
        effort_detail = f"Taux d'effort {effort_rate * 100:.0f}% (loyer+charges {monthly_total:.0f} € / revenus {income:.0f} €)"
    else:
        effort_score = 50  # neutre, faute de données
        effort_detail = "Revenus non renseignés" if not income else "Loyer non disponible"

    # ── Relation ─────────────────────────────────────────────────────────────
    rel_events = getattr(lease, "relationship_events", None) if lease else None
    relation_score, rel_count = _relation_subscore(rel_events)
    relation_score = round(relation_score)
    relation_detail = (f"{rel_count} événement(s) de relation enregistré(s)"
                       if rel_count else "Aucun événement de relation")

    # ── Score global ─────────────────────────────────────────────────────────
    score = round(
        W_PONCTUALITE * ponctualite
        + W_IMPAYES * impayes_score
        + W_EFFORT * effort_score
        + W_RELATION * relation_score
    )
    grade = grade_for(score)

    return {
        "score": int(score),
        "grade": grade,
        "strategy": _STRATEGY[grade],
        "factors": [
            {"key": "ponctualite", "label": "Ponctualité de paiement", "score": ponctualite,
             "weight": int(W_PONCTUALITE * 100), "detail": ponct_detail},
            {"key": "impayes", "label": "Impayés en cours", "score": impayes_score,
             "weight": int(W_IMPAYES * 100), "detail": impayes_detail},
            {"key": "effort", "label": "Taux d'effort", "score": effort_score,
             "weight": int(W_EFFORT * 100), "detail": effort_detail},
            {"key": "relation", "label": "Relation locataire", "score": relation_score,
             "weight": int(W_RELATION * 100), "detail": relation_detail},
        ],
        "stats": {
            "income": income,
            "monthly_total": monthly_total,
            "effort_rate": round(effort_rate, 3) if effort_rate is not None else None,
            "on_time_rate": round(on_time_rate, 3) if on_time_rate is not None else None,
            "payments_due": total_due,
            "overdue_count": overdue_count,
            "outstanding": round(outstanding, 2),
            "relationship_events_count": rel_count,
        },
    }
