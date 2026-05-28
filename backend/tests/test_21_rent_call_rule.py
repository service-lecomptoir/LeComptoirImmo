"""Tests unitaires de la règle d'appel de loyer (prorata) — fonction pure, sans DB."""
from datetime import date
from types import SimpleNamespace

from app.services.avis_echeance_service import AvisEcheanceService as S


def _lease(start, end=None, rule="calendrier"):
    return SimpleNamespace(start_date=start, end_date=end, rent_call_rule=rule, payment_day=1)


def test_calendrier_full_month():
    ps, pe, f = S._period_and_factor(_lease(date(2026, 1, 1)), 2026, 3)
    assert (ps, pe) == (date(2026, 3, 1), date(2026, 3, 31))
    assert f == 1.0


def test_calendrier_entry_midmonth_prorata():
    # Entrée le 15 janvier (mois de 31 jours) → 17 jours couverts / 31
    ps, pe, f = S._period_and_factor(_lease(date(2026, 1, 15)), 2026, 1)
    assert ps == date(2026, 1, 15) and pe == date(2026, 1, 31)
    assert round(f, 6) == round(17 / 31, 6)


def test_calendrier_exit_midmonth_prorata():
    # Sortie le 10 mars → du 1er au 10 = 10 jours / 31
    ps, pe, f = S._period_and_factor(_lease(date(2026, 1, 1), end=date(2026, 3, 10)), 2026, 3)
    assert ps == date(2026, 3, 1) and pe == date(2026, 3, 10)
    assert round(f, 6) == round(10 / 31, 6)


def test_calendrier_no_overlap_before_start():
    ps, pe, f = S._period_and_factor(_lease(date(2026, 2, 1)), 2026, 1)
    assert ps is None and f == 0.0


def test_contractuelle_full_rent_date_to_date():
    # Entrée le 15 janvier, règle contractuelle → période 15/01 → 14/02, loyer plein
    ps, pe, f = S._period_and_factor(_lease(date(2026, 1, 15), rule="contractuelle"), 2026, 1)
    assert ps == date(2026, 1, 15) and pe == date(2026, 2, 14)
    assert f == 1.0


def test_contractuelle_no_proration_even_partial_first_month():
    # Mois suivant : 15/02 → 14/03, plein
    ps, pe, f = S._period_and_factor(_lease(date(2026, 1, 15), rule="contractuelle"), 2026, 2)
    assert ps == date(2026, 2, 15) and pe == date(2026, 3, 14)
    assert f == 1.0
