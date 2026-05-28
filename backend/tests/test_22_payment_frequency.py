"""Tests unitaires du calcul des périodes multi-mois (fréquence d'appel) — sans DB."""
from datetime import date
from types import SimpleNamespace

from app.services.billing_period import compute_period, is_trigger_month


def _lease(start, end=None, rule="calendrier", freq="mensuelle"):
    return SimpleNamespace(
        start_date=start, end_date=end, rent_call_rule=rule, payment_frequency=freq,
        payment_day=1, rent_amount=800, charges_amount=50,
        apl_tiers_payant=False, apl_amount=None,
    )


# ── Mensuel : comportement inchangé ────────────────────────────────────────────

def test_mensuelle_full_month():
    bp = compute_period(_lease(date(2026, 1, 1)), 2026, 3)
    assert (bp.key_year, bp.key_month) == (2026, 3)
    assert bp.factor_sum == 1.0 and bp.covered_count == 1
    assert bp.period_start == date(2026, 3, 1) and bp.period_end == date(2026, 3, 31)


def test_mensuelle_entry_prorata():
    bp = compute_period(_lease(date(2026, 1, 15)), 2026, 1)
    assert bp.period_start == date(2026, 1, 15) and bp.period_end == date(2026, 1, 31)
    assert round(bp.factor_sum, 6) == round(17 / 31, 6)


# ── Trimestriel calendaire : aligné année civile ───────────────────────────────

def test_trimestrielle_calendrier_full_quarter():
    lease = _lease(date(2026, 1, 1), freq="trimestrielle")
    # N'importe quel mois du T1 → période jan-mars, clé = janvier
    for m in (1, 2, 3):
        bp = compute_period(lease, 2026, m)
        assert (bp.key_year, bp.key_month) == (2026, 1)
        assert bp.period_start == date(2026, 1, 1) and bp.period_end == date(2026, 3, 31)
        assert bp.factor_sum == 3.0 and bp.covered_count == 3
    # Déclenchement uniquement en janvier
    assert is_trigger_month(lease, 2026, 1) is True
    assert is_trigger_month(lease, 2026, 2) is False
    assert is_trigger_month(lease, 2026, 3) is False
    # T2 = avril
    assert is_trigger_month(lease, 2026, 4) is True


def test_trimestrielle_calendrier_partial_first_period():
    # Entrée le 15 février, trimestriel calendaire : T1 = jan-mars mais couvert dès le 15/02
    lease = _lease(date(2026, 2, 15), freq="trimestrielle")
    bp = compute_period(lease, 2026, 2)
    # Clé = premier mois couvert = février
    assert (bp.key_year, bp.key_month) == (2026, 2)
    assert bp.period_start == date(2026, 2, 15) and bp.period_end == date(2026, 3, 31)
    assert bp.covered_count == 2  # février (partiel) + mars (plein)
    assert round(bp.factor_sum, 6) == round(14 / 28 + 1.0, 6)
    # Déclenché en février (pas en janvier ni mars)
    assert is_trigger_month(lease, 2026, 1) is False
    assert is_trigger_month(lease, 2026, 2) is True
    assert is_trigger_month(lease, 2026, 3) is False


# ── Trimestriel contractuel : aligné date d'entrée, loyer plein ────────────────

def test_trimestrielle_contractuelle():
    lease = _lease(date(2026, 1, 15), rule="contractuelle", freq="trimestrielle")
    bp = compute_period(lease, 2026, 1)
    assert (bp.key_year, bp.key_month) == (2026, 1)
    assert bp.period_start == date(2026, 1, 15)
    assert bp.period_end == date(2026, 4, 14)  # 3 mois date à date
    assert bp.factor_sum == 3.0 and bp.covered_count == 3
    # Période suivante démarre le 15 avril
    assert is_trigger_month(lease, 2026, 4) is True
    assert is_trigger_month(lease, 2026, 2) is False


# ── Sortie en cours de période : tronquée ──────────────────────────────────────

def test_trimestrielle_calendrier_exit_midperiod():
    # Bail jan-... mais résilié le 10 février : T1 couvre jan (plein) + fév (10/28)
    lease = _lease(date(2026, 1, 1), end=date(2026, 2, 10), freq="trimestrielle")
    bp = compute_period(lease, 2026, 1)
    assert bp.period_start == date(2026, 1, 1) and bp.period_end == date(2026, 2, 10)
    assert bp.covered_count == 2
    assert round(bp.factor_sum, 6) == round(1.0 + 10 / 28, 6)


# ── Annuel ─────────────────────────────────────────────────────────────────────

def test_annuelle_calendrier():
    lease = _lease(date(2026, 1, 1), freq="annuelle")
    bp = compute_period(lease, 2026, 7)
    assert (bp.key_year, bp.key_month) == (2026, 1)
    assert bp.period_start == date(2026, 1, 1) and bp.period_end == date(2026, 12, 31)
    assert bp.factor_sum == 12.0 and bp.covered_count == 12


# ── Hors couverture ────────────────────────────────────────────────────────────

def test_before_start_returns_none():
    lease = _lease(date(2026, 6, 1), freq="trimestrielle")
    assert compute_period(lease, 2026, 1) is None
