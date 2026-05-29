"""Tests unitaires de la mention de révision IRL à venir (Actualisation Étape 2) — sans DB."""
from datetime import date
from types import SimpleNamespace

from app.services.irl_notice import (
    next_revision_date, _month_after, notice_text, notice_html, inject_notice,
)


def _lease(start, last_rev=None, irl_quarter=2, base=140.0, rent=800.0):
    return SimpleNamespace(
        start_date=start, last_revision_date=last_rev,
        irl_quarter=irl_quarter, irl_base_index=base, rent_amount=rent,
    )


# ── next_revision_date : anniversaire ──────────────────────────────────────────

def test_next_revision_from_start_date():
    assert next_revision_date(_lease(date(2025, 3, 1))) == date(2026, 3, 1)


def test_next_revision_from_last_revision():
    assert next_revision_date(_lease(date(2020, 1, 1), last_rev=date(2025, 6, 15))) == date(2026, 6, 15)


def test_next_revision_leap_day():
    # 29 février → +365 jours (pas de 29 février l'année suivante)
    assert next_revision_date(_lease(date(2024, 2, 29))) == date(2025, 2, 28)


# ── _month_after ───────────────────────────────────────────────────────────────

def test_month_after_normal():
    assert _month_after(2026, 5) == (2026, 6)


def test_month_after_december_rolls_over():
    assert _month_after(2026, 12) == (2027, 1)


# ── notice_text / notice_html ──────────────────────────────────────────────────

def test_notice_text_with_amount():
    n = {"effective_date": "1 mars 2026", "old_rent": 800.0, "new_rent": 820.0,
         "irl_quarter": 2, "irl_year": 2025}
    t = notice_text(n)
    assert "820.00" in t and "800.00" in t and "1 mars 2026" in t and "T2 2025" in t


def test_notice_text_without_amount():
    n = {"effective_date": "1 mars 2026", "old_rent": 800.0, "new_rent": None,
         "irl_quarter": 2, "irl_year": None}
    t = notice_text(n)
    assert "publication de l'indice" in t and "820" not in t


def test_notice_html_contains_banner():
    n = {"effective_date": "1 mars 2026", "old_rent": 800.0, "new_rent": 820.0,
         "irl_quarter": 2, "irl_year": 2025}
    html = notice_html(n)
    assert "révision de loyer à venir" in html.lower() and "820.00" in html


# ── inject_notice ──────────────────────────────────────────────────────────────

def test_inject_before_body_close():
    n = {"effective_date": "1 mars 2026", "old_rent": 800.0, "new_rent": 820.0,
         "irl_quarter": 2, "irl_year": 2025}
    out = inject_notice("<html><body>X</body></html>", n)
    # le bloc est inséré AVANT </body>
    assert out.endswith("</body></html>")
    assert "820.00" in out and out.count("</body>") == 1


def test_inject_without_body_appends():
    n = {"effective_date": "1 mars 2026", "old_rent": 800.0, "new_rent": None,
         "irl_quarter": 2, "irl_year": None}
    out = inject_notice("<div>contenu</div>", n)
    assert out.startswith("<div>contenu</div>") and "révision de loyer" in out.lower()
