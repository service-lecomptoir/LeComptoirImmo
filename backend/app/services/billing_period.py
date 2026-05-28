"""Calcul des périodes d'appel de loyer (source de vérité partagée).

Une « période de facturation » dépend de deux champs du bail :
  - `rent_call_rule` : 'calendrier' (mois civils) ou 'contractuelle' (date à date) ;
  - `payment_frequency` : nombre de mois couverts par un appel.

Ce module est PUR (aucun accès DB) afin d'être réutilisé par AvisEcheanceService
et PaymentService — les deux chemins doivent produire des montants identiques.

Alignement des périodes :
  - calendrier   : aligné sur l'année civile (N ∈ {1,2,3,6,12} divise 12, donc une
                   période ne traverse jamais l'année). Trimestriel → T1=jan-mars,
                   T2=avr-juin, etc. Loyer proratisé au nombre de jours pour les mois
                   d'entrée/sortie partiels.
  - contractuelle: aligné sur la date d'entrée du bail, période date à date, loyer
                   plein (pas de prorata).

La clé d'unicité (period_year, period_month) d'une période = son PREMIER mois
réellement couvert (= le mois où la période est facturée). Pour une première période
partielle (entrée en cours de période calendaire), c'est le mois d'entrée.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

# Fréquence → nombre de mois couverts par un appel
FREQ_MONTHS = {
    "mensuelle": 1,
    "bimestrielle": 2,
    "trimestrielle": 3,
    "semestrielle": 6,
    "annuelle": 12,
}


def months_for_frequency(freq: Optional[str]) -> int:
    return FREQ_MONTHS.get(freq or "mensuelle", 1)


def _add_months(year: int, month: int, k: int) -> tuple[int, int]:
    """Retourne (année, mois) après ajout de k mois (k peut être négatif)."""
    idx = year * 12 + (month - 1) + k
    return idx // 12, idx % 12 + 1


def _first_of_next_month(year: int, month: int) -> date:
    return date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)


def month_period_and_factor(
    lease_start: date,
    lease_end: Optional[date],
    rule: str,
    year: int,
    month: int,
) -> tuple[Optional[date], Optional[date], float]:
    """Période couverte et facteur de prorata pour UN mois (year, month).

    - calendrier   : mois civil borné aux dates du bail ; prorata au nb de jours.
    - contractuelle: période date à date depuis le jour d'entrée ; loyer plein.

    Retourne (period_start, period_end, factor). (None, None, 0.0) si non couvert.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, days_in_month)
    rule = rule or "calendrier"

    if rule == "contractuelle":
        anniv = lease_start.day
        p_start = date(year, month, min(anniv, days_in_month))
        nxt = _first_of_next_month(year, month)
        nxt_days = calendar.monthrange(nxt.year, nxt.month)[1]
        p_end = date(nxt.year, nxt.month, min(anniv, nxt_days)) - timedelta(days=1)
        p_start = max(p_start, lease_start)
        if lease_end:
            p_end = min(p_end, lease_end)
        if p_start > p_end:
            return None, None, 0.0
        return p_start, p_end, 1.0

    # calendrier
    p_start = max(month_start, lease_start)
    p_end = min(month_end, lease_end) if lease_end else month_end
    if p_start > p_end:
        return None, None, 0.0
    covered = (p_end - p_start).days + 1
    factor = 1.0 if covered >= days_in_month else round(covered / days_in_month, 6)
    return p_start, p_end, factor


@dataclass
class BillingPeriod:
    # Clé d'unicité = premier mois réellement couvert
    key_year: int
    key_month: int
    # Étendue réellement couverte (bornée aux dates du bail)
    period_start: date
    period_end: date
    # Somme des facteurs de prorata (mois pleins = 1.0 chacun)
    factor_sum: float
    # Nombre de mois (au moins partiellement) couverts — sert au calcul de l'APL
    covered_count: int
    # Nombre de mois nominal de la fréquence (1, 2, 3, 6, 12)
    months_total: int

    @property
    def is_multi_month(self) -> bool:
        return self.months_total > 1


def _anchor_period_start(
    lease_start: date, freq_n: int, rule: str, year: int, month: int
) -> tuple[int, int]:
    """Mois de DÉBUT (calendaire/contractuel) de la période contenant (year, month)."""
    if rule == "contractuelle":
        months_since = (year - lease_start.year) * 12 + (month - lease_start.month)
        # floor division gère les valeurs négatives ; la couverture filtrera ensuite
        period_index = months_since // freq_n
        return _add_months(lease_start.year, lease_start.month, period_index * freq_n)
    # calendrier : aligné année civile (freq_n divise 12)
    am = ((month - 1) // freq_n) * freq_n + 1
    return year, am


def compute_period(lease, year: int, month: int) -> Optional[BillingPeriod]:
    """Calcule la période de facturation contenant (year, month) pour ce bail.

    Retourne None si le bail ne couvre aucun mois de cette période (avant l'entrée
    ou après la sortie)."""
    freq_n = months_for_frequency(getattr(lease, "payment_frequency", None))
    rule = getattr(lease, "rent_call_rule", None) or "calendrier"
    lease_start: date = lease.start_date
    lease_end: Optional[date] = getattr(lease, "end_date", None)

    ay, am = _anchor_period_start(lease_start, freq_n, rule, year, month)

    slots = []
    for k in range(freq_n):
        sy, sm = _add_months(ay, am, k)
        ps, pe, f = month_period_and_factor(lease_start, lease_end, rule, sy, sm)
        if ps is not None and f > 0:
            slots.append((sy, sm, ps, pe, f))

    if not slots:
        return None

    first, last = slots[0], slots[-1]
    return BillingPeriod(
        key_year=first[0],
        key_month=first[1],
        period_start=first[2],
        period_end=last[3],
        factor_sum=round(sum(s[4] for s in slots), 6),
        covered_count=len(slots),
        months_total=freq_n,
    )


def is_trigger_month(lease, year: int, month: int) -> bool:
    """True si (year, month) est le mois où la période qui le contient est facturée
    (= premier mois couvert). Sert au scheduler / à la génération en masse pour ne
    générer qu'UN document par période."""
    bp = compute_period(lease, year, month)
    return bp is not None and bp.key_year == year and bp.key_month == month
