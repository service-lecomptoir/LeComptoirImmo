"""Révision de loyer/charges avec date d'effet (logique pure, sans DB).

Vérifie le cœur du comportement demandé : une hausse ne touche pas le mois en
cours mais s'applique à partir de la date d'effet (mois suivant par défaut), et
l'on retrouve toujours le montant précédent.
"""
from datetime import date
from types import SimpleNamespace

from app.services.rent_revision_service import RentRevisionService, first_of_next_month
from app.models.rent_revision import RentRevision


def _rev(eff: date, rent: float, charges: float) -> RentRevision:
    return RentRevision(effective_date=eff, rent_amount=rent, charges_amount=charges)


def test_first_of_next_month():
    assert first_of_next_month(date(2026, 6, 16)) == date(2026, 7, 1)
    assert first_of_next_month(date(2026, 12, 10)) == date(2027, 1, 1)
    assert first_of_next_month(date(2026, 1, 31)) == date(2026, 2, 1)


def test_effective_amounts_no_revision_uses_lease():
    lease = SimpleNamespace(rent_amount=750.0, charges_amount=50.0)
    assert RentRevisionService.effective_amounts(lease, [], date(2026, 6, 1)) == (750.0, 50.0)


def test_increase_keeps_current_month_applies_next_month():
    lease = SimpleNamespace(rent_amount=750.0, charges_amount=50.0)
    revs = [_rev(date(2026, 7, 1), 800.0, 60.0)]
    # Mois en cours (juin) : la révision (1er juillet) n'est pas encore en vigueur → ancien.
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 6, 1)) == (750.0, 50.0)
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 6, 30)) == (750.0, 50.0)
    # Mois suivant (juillet) : nouvelle valeur.
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 7, 1)) == (800.0, 60.0)


def test_effective_amounts_picks_latest_applicable():
    lease = SimpleNamespace(rent_amount=700.0, charges_amount=40.0)
    revs = [_rev(date(2025, 7, 1), 750.0, 50.0), _rev(date(2026, 7, 1), 800.0, 60.0)]
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 1, 1)) == (750.0, 50.0)
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 8, 1)) == (800.0, 60.0)
    # Avant toute révision : montants du bail.
    assert RentRevisionService.effective_amounts(lease, revs, date(2025, 1, 1)) == (700.0, 40.0)
