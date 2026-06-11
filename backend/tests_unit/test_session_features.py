"""Tests unitaires (sans DB) de la logique métier ajoutée récemment :
bailleur (type personne/société), rédaction IA des annonces et des démarches,
métriques de candidature. Placés hors de tests/ pour ne pas dépendre du conftest DB.
"""
import asyncio
from types import SimpleNamespace

from app.models.user import User
from app.services import listing_service, ticket_ai
from app.api.v1 import candidatures


def _prop(**kw):
    base = dict(
        property_type="appartement", typology="T3", area_sqm=65, city="Lyon",
        zip_code="69003", floor=2, bathrooms=1, heating_type=None, energy_class="C",
        furnished=True, kitchen_equipped=True, has_elevator=False, has_balcony=True,
        has_terrace=False, has_garden=False, has_parking=False, has_cellar=False,
        has_fiber=True, has_air_conditioning=False,
    )
    base.update(kw)
    return SimpleNamespace(**base)


# ── Bailleur : nom retenu selon le type ───────────────────────────────────────
def test_bailleur_name_personne():
    u = User(owner_kind="personne", owner_full_name="Jean Dupont", owner_company="SCI X")
    assert u.bailleur_name == "Jean Dupont"


def test_bailleur_name_societe():
    u = User(owner_kind="societe", owner_full_name="Jean Dupont", owner_company="SCI X")
    assert u.bailleur_name == "SCI X"


def test_bailleur_name_fallback_when_company_empty():
    u = User(owner_kind="societe", owner_full_name="Jean", owner_company="")
    assert u.bailleur_name == "Jean"


# ── Rédaction IA des annonces (repli déterministe) ────────────────────────────
def test_property_facts_includes_known_attrs():
    facts = listing_service._property_facts(_prop(), 800)
    joined = " ".join(facts)
    assert "Surface" in joined and "Lyon" in joined and "Loyer" in joined


def test_listing_fallback_draft():
    prop = _prop()
    d = listing_service._fallback_draft(prop, listing_service._property_facts(prop, None))
    assert "Appartement" in d["title"]
    assert d["description"]


def test_generate_listing_draft_returns_title_and_desc():
    res = asyncio.run(listing_service.generate_listing_draft(_prop(area_sqm=None, typology=None), None))
    assert res["title"] and res["description"]
    assert res["source"] in ("modele", "ia")


# ── Aide IA à la rédaction des démarches (repli déterministe) ─────────────────
def test_ticket_ai_fallback_all_topics():
    for topic in ("logement", "voisinage", "autre"):
        d = ticket_ai._fallback(topic, "fuite d'eau")
        assert d["title"] and d["description"] and d["source"] == "modele"


def test_generate_ticket_draft_async():
    res = asyncio.run(ticket_ai.generate_ticket_draft("logement", "fuite d'eau sous l'évier"))
    assert res["title"] and res["description"]


# ── Candidatures : checklist + métriques d'analyse ────────────────────────────
def test_candidature_default_docs():
    docs = candidatures.default_docs()
    assert len(docs) == len(candidatures.CANDIDATURE_DOC_KEYS)
    assert all(d["provided"] is False and d["verified"] is False for d in docs)


def test_candidature_metrics_effort_and_score():
    c = SimpleNamespace(docs=candidatures.default_docs(), monthly_income=3000, has_guarantor=True)
    m = candidatures._metrics(c, 900)  # taux d'effort = 900/3000 = 0.30
    assert m["effort_ratio"] == 0.3
    assert m["docs_total"] == len(candidatures.CANDIDATURE_DOC_KEYS)
    assert 0 <= m["score"] <= 100


def test_candidature_metrics_no_income():
    c = SimpleNamespace(docs=[], monthly_income=None, has_guarantor=False)
    m = candidatures._metrics(c, 900)
    assert m["effort_ratio"] is None
    assert m["score"] >= 0
