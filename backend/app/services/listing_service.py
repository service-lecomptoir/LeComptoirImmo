# -*- coding: utf-8 -*-
"""Diffusion des annonces : contenu/photos pré-enregistrés par bien, publication
sur une page d'annonce hébergée + partage, et programmation de la publication.

Le canal de diffusion est une PAGE D'ANNONCE PUBLIQUE (URL à jeton non devinable)
servie par Le Comptoir ; les « plateformes » sont des cibles de partage libres
définies par le gestionnaire. La programmation s'appuie sur le scheduler APScheduler
(job `publish_scheduled_listings`).
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.models.document import Document
from app.models.publishing import Listing


_PROPERTY_TYPE_LABELS = {
    "appartement": "Appartement", "maison": "Maison",
    "local_commercial": "Local commercial", "autre": "Bien",
}
_AMENITIES = [
    ("furnished", "meublé"), ("kitchen_equipped", "cuisine équipée"),
    ("has_elevator", "ascenseur"), ("has_balcony", "balcon"),
    ("has_terrace", "terrasse"), ("has_garden", "jardin"),
    ("has_parking", "parking"), ("has_cellar", "cave"),
    ("has_fiber", "fibre optique"), ("has_air_conditioning", "climatisation"),
]


def _property_facts(prop, price=None) -> list[str]:
    """Liste des caractéristiques CONNUES du bien (jamais inventées)."""
    facts: list[str] = []
    ptype = _PROPERTY_TYPE_LABELS.get(getattr(prop, "property_type", None) or "", "Bien")
    facts.append(f"Type : {ptype}")
    if getattr(prop, "typology", None):
        facts.append(f"Typologie : {prop.typology}")
    if getattr(prop, "area_sqm", None):
        facts.append(f"Surface : {float(prop.area_sqm):g} m²")
    if getattr(prop, "floor", None) is not None:
        facts.append(f"Étage : {prop.floor}")
    if getattr(prop, "bathrooms", None):
        facts.append(f"Salle(s) d'eau : {prop.bathrooms}")
    if getattr(prop, "heating_type", None):
        facts.append(f"Chauffage : {prop.heating_type}")
    if getattr(prop, "energy_class", None):
        facts.append(f"Classe énergie (DPE) : {prop.energy_class}")
    loc = " ".join(p for p in [getattr(prop, "zip_code", None), getattr(prop, "city", None)] if p)
    if loc:
        facts.append(f"Localisation : {loc}")
    equip = [label for attr, label in _AMENITIES if getattr(prop, attr, False)]
    if equip:
        facts.append("Équipements : " + ", ".join(equip))
    if price:
        facts.append(f"Loyer indicatif : {float(price):g} € / mois")
    return facts


def _fallback_draft(prop, facts: list[str]) -> dict:
    """Brouillon déterministe (sans LLM) à partir des caractéristiques connues."""
    ptype = _PROPERTY_TYPE_LABELS.get(getattr(prop, "property_type", None) or "", "Bien")
    bits = [ptype]
    if getattr(prop, "typology", None):
        bits.append(str(prop.typology))
    if getattr(prop, "area_sqm", None):
        bits.append(f"{float(prop.area_sqm):g} m²")
    title = " ".join(bits)
    if getattr(prop, "city", None):
        title += f" à {prop.city}"
    equip = [label for attr, label in _AMENITIES if getattr(prop, attr, False)]
    sentences = [f"{ptype}" + (f" de type {prop.typology}" if getattr(prop, 'typology', None) else "")
                 + (f" d'environ {float(prop.area_sqm):g} m²" if getattr(prop, 'area_sqm', None) else "")
                 + (f", situé à {prop.city}" if getattr(prop, 'city', None) else "") + "."]
    if equip:
        sentences.append("Il dispose de : " + ", ".join(equip) + ".")
    if getattr(prop, "energy_class", None):
        sentences.append(f"Classe énergétique (DPE) : {prop.energy_class}.")
    sentences.append("Disponible à la location : contactez-nous pour organiser une visite.")
    return {"title": title[:120], "description": " ".join(sentences)}


async def generate_listing_draft(prop, price=None) -> dict:
    """Génère un brouillon { title, description } depuis les caractéristiques du bien.

    Utilise le LLM s'il est configuré (ancré sur les seules caractéristiques connues,
    interdiction d'inventer) ; sinon repli déterministe. Le résultat est proposé à
    l'édition côté gestionnaire (jamais enregistré automatiquement)."""
    import json
    import re as _re
    from app.services import llm_service

    facts = _property_facts(prop, price)
    if llm_service.enabled():
        try:
            system = (
                "Tu es concepteur-rédacteur immobilier en France, spécialisé dans les annonces "
                "de location au style vivant et premium (le ton des belles annonces d'agence). "
                "Ta mission : à partir des SEULES caractéristiques fournies, écrire une annonce "
                "qui donne envie de visiter.\n"
                "Règles :\n"
                "- N'invente JAMAIS un fait absent (surface, étage, pièces, équipement, atout, "
                "proximité) : tu n'utilises que ce qui est listé.\n"
                "- Transforme chaque caractéristique en BÉNÉFICE concret du quotidien "
                "(ex. « cuisine équipée » → « on s'installe sans rien acheter » ; « fibre » → "
                "« télétravail et streaming sans accroc »). Vocabulaire concret et varié, "
                "zéro cliché creux, zéro superlatif gratuit, pas de MAJUSCULES criardes.\n"
                "- Description structurée en 3 temps fluides (sans titres) : une accroche qui "
                "plante le décor, les atouts du logement, puis une clôture qui invite à la visite. "
                "Phrases courtes et rythmées, 150 à 230 mots.\n"
                "- Titre accrocheur et spécifique : type + typologie + ville + 1 atout fort, "
                "80 caractères max, sans point final.\n"
                'Réponds STRICTEMENT en JSON valide, sans texte autour : '
                '{"title": "...", "description": "..."}.'
            )
            reply = await llm_service.chat(
                [{"role": "system", "content": system},
                 {"role": "user", "content": "CARACTÉRISTIQUES DU BIEN :\n- " + "\n- ".join(facts)
                  + "\n\nRédige maintenant le titre et la description."}],
                temperature=0.8, max_tokens=800,
            )
            if reply:
                txt = _re.sub(r"^```(?:json)?|```$", "", reply.strip(), flags=_re.MULTILINE).strip()
                data = json.loads(txt)
                title = (data.get("title") or "").strip()
                desc = (data.get("description") or "").strip()
                if title and desc:
                    return {"title": title[:200], "description": desc, "source": "ia"}
        except Exception:  # noqa: BLE001 : repli déterministe
            pass
    return {**_fallback_draft(prop, facts), "source": "modele"}


def build_photo_url(file_path: Optional[str]) -> Optional[str]:
    """URL servie pour un document uploadé (mount StaticFiles « /uploads »).

    `file_path` est stocké sous la forme « uploads/property/<id>/<fichier> » ;
    le fichier est exposé à « /uploads/property/<id>/<fichier> »."""
    if not file_path:
        return None
    p = str(file_path).replace("\\", "/").lstrip("/")
    return "/" + p


def _token() -> str:
    """Jeton d'URL publique court et non devinable."""
    return secrets.token_urlsafe(12)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ListingService:
    @staticmethod
    async def get_or_create(db: AsyncSession, property_id, user_id) -> Listing:
        listing = (await db.execute(
            select(Listing).where(Listing.property_id == property_id)
        )).scalar_one_or_none()
        if listing is None:
            listing = Listing(property_id=property_id, status="draft", created_by=user_id)
            db.add(listing)
            await db.flush()
        return listing

    @staticmethod
    async def update(db: AsyncSession, listing: Listing, fields: dict) -> Listing:
        """Applique les champs RÉELLEMENT fournis (clé présente) ; une valeur `null`
        EFFACE le champ (titre/description/loyer) : on ne confond plus « champ vidé »
        et « champ non transmis ». `fields` = data.model_dump(exclude_unset=True)."""
        if "title" in fields:
            v = fields["title"]
            listing.title = (v.strip() or None) if isinstance(v, str) else None
        if "description" in fields:
            v = fields["description"]
            listing.description = (v.strip() or None) if isinstance(v, str) else None
        if "price" in fields:
            listing.price = fields["price"]  # None = loyer effacé
        if "charges" in fields:
            listing.charges = fields["charges"]  # None = charges effacées
        if fields.get("photo_ids") is not None:
            listing.photo_ids = [str(x) for x in fields["photo_ids"]]
        if fields.get("platform_ids") is not None:
            listing.platform_ids = [str(x) for x in fields["platform_ids"]]
        await db.flush()
        return listing

    @staticmethod
    async def publish(db: AsyncSession, listing: Listing) -> Listing:
        if not listing.public_token:
            listing.public_token = _token()
        listing.status = "published"
        listing.published_at = _now()
        listing.scheduled_at = None
        await db.flush()
        return listing

    @staticmethod
    async def schedule(db: AsyncSession, listing: Listing, when: datetime) -> Listing:
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when <= _now():
            raise BadRequestException("La date de publication doit être dans le futur.")
        if not listing.public_token:
            listing.public_token = _token()
        listing.status = "scheduled"
        listing.scheduled_at = when
        await db.flush()
        return listing

    @staticmethod
    async def unpublish(db: AsyncSession, listing: Listing) -> Listing:
        listing.status = "unpublished"
        listing.scheduled_at = None
        await db.flush()
        return listing

    @staticmethod
    async def publish_due(db: AsyncSession) -> int:
        """Publie les annonces programmées dont l'échéance est atteinte (scheduler)."""
        now = _now()
        rows = (await db.execute(
            select(Listing).where(
                Listing.status == "scheduled",
                Listing.scheduled_at.isnot(None),
                Listing.scheduled_at <= now,
            )
        )).scalars().all()
        for listing in rows:
            listing.status = "published"
            listing.published_at = now
        return len(rows)

    @staticmethod
    async def property_photos(db: AsyncSession, property_id) -> list[dict]:
        """Documents-images rattachés au bien, candidats pour l'annonce."""
        docs = (await db.execute(
            select(Document).where(
                Document.entity_type == "property",
                Document.entity_id == property_id,
            ).order_by(Document.created_at)
        )).scalars().all()
        out = []
        for d in docs:
            mime = (d.mime_type or "").lower()
            if not mime.startswith("image/"):
                continue
            out.append({
                "id": str(d.id),
                "url": build_photo_url(d.file_path),
                "label": d.label or d.file_name,
            })
        return out
