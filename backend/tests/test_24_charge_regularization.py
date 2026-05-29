"""Tests unitaires de la régularisation des charges (Actualisation Étape 3) — sans DB."""
from datetime import date

from app.services.charge_regularization_service import months_between


def test_months_between_full_year():
    assert months_between(date(2025, 1, 1), date(2025, 12, 31)) == 12


def test_months_between_single_month():
    assert months_between(date(2026, 3, 1), date(2026, 3, 31)) == 1


def test_months_between_cross_year():
    # juin 2025 → mai 2026 inclus = 12 mois
    assert months_between(date(2025, 6, 1), date(2026, 5, 31)) == 12


def test_months_between_partial_span():
    # janvier → avril inclus = 4 mois
    assert months_between(date(2026, 1, 10), date(2026, 4, 20)) == 4


def test_months_between_end_before_start_defaults_to_one():
    assert months_between(date(2026, 5, 1), date(2026, 1, 1)) == 1


def test_balance_sign_convention():
    # provisions > réel → trop-perçu (positif, remboursement) ; sinon complément (négatif)
    provisions, real = 900.0, 720.0
    assert round(provisions - real, 2) == 180.0   # remboursement
    provisions, real = 600.0, 720.0
    assert round(provisions - real, 2) == -120.0  # complément dû
