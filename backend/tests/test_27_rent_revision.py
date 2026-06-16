"""Révision de loyer/charges « par champ » avec date d'effet (logique pure, sans DB).

Vérifie : une hausse ne touche pas le mois en cours mais s'applique à la date
d'effet (mois suivant par défaut) ; loyer et charges sont indépendants ; on
retrouve toujours le montant précédent.
"""
from datetime import date
from types import SimpleNamespace

from app.services.rent_revision_service import RentRevisionService, first_of_next_month
from app.models.rent_revision import RentRevision


def _rev(kind: str, eff: date, amount: float) -> RentRevision:
    return RentRevision(kind=kind, effective_date=eff, amount=amount)


def test_first_of_next_month():
    assert first_of_next_month(date(2026, 6, 16)) == date(2026, 7, 1)
    assert first_of_next_month(date(2026, 12, 10)) == date(2027, 1, 1)
    assert first_of_next_month(date(2026, 1, 31)) == date(2026, 2, 1)


def test_no_revision_uses_lease():
    lease = SimpleNamespace(rent_amount=750.0, charges_amount=50.0)
    assert RentRevisionService.effective_amounts(lease, [], date(2026, 6, 1)) == (750.0, 50.0)


def test_rent_increase_keeps_current_month_applies_next():
    lease = SimpleNamespace(rent_amount=750.0, charges_amount=50.0)
    revs = [_rev("rent", date(2026, 7, 1), 800.0)]
    # Mois en cours (juin) : ancien loyer, charges inchangées.
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 6, 30)) == (750.0, 50.0)
    # Mois suivant (juillet) : nouveau loyer, charges inchangées.
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 7, 1)) == (800.0, 50.0)


def test_rent_and_charges_are_independent():
    lease = SimpleNamespace(rent_amount=750.0, charges_amount=50.0)
    revs = [
        _rev("rent", date(2026, 7, 1), 800.0),
        _rev("charges", date(2026, 9, 1), 60.0),
    ]
    # Juillet : loyer révisé, charges encore anciennes.
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 7, 1)) == (800.0, 50.0)
    # Septembre : les deux révisés, chacun selon sa propre date d'effet.
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 9, 1)) == (800.0, 60.0)


def test_latest_applicable_per_field():
    lease = SimpleNamespace(rent_amount=700.0, charges_amount=40.0)
    revs = [_rev("rent", date(2025, 7, 1), 750.0), _rev("rent", date(2026, 7, 1), 800.0)]
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 1, 1)) == (750.0, 40.0)
    assert RentRevisionService.effective_amounts(lease, revs, date(2026, 8, 1)) == (800.0, 40.0)
    assert RentRevisionService.effective_amounts(lease, revs, date(2025, 1, 1)) == (700.0, 40.0)
