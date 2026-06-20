"""Aide IA à la rédaction d'une démarche par le locataire.

À partir du TYPE de signalement choisi (et d'un éventuel mot du locataire), propose
un Sujet + une Description polis et clairs. LLM si configuré (ancré, sans inventer
de détails non fournis) ; sinon repli déterministe (modèle). Jamais bloquant.
"""

from __future__ import annotations

_TOPIC = {
    "logement": {
        "label": "un problème dans le logement (ex. fuite d'eau, panne de chauffage, équipement défectueux)",
        "title": "Problème dans le logement",
    },
    "voisinage": {
        "label": "un problème de voisinage (ex. nuisances sonores, conflit, parties communes)",
        "title": "Problème de voisinage",
    },
    "autre": {
        "label": "une demande à son gestionnaire",
        "title": "Demande au gestionnaire",
    },
}


def _fallback(topic: str, hint: str) -> dict:
    meta = _TOPIC.get(topic, _TOPIC["autre"])
    hint = (hint or "").strip()
    title = meta["title"]
    if topic == "logement":
        body = (
            "Bonjour,\n\nJe vous signale un problème dans le logement"
            + (f" : {hint}" if hint else ".")
            + "\n\nPourriez-vous m'indiquer la marche à suivre et programmer une intervention "
            "si nécessaire ? Je reste disponible pour convenir d'un rendez-vous.\n\nCordialement."
        )
    elif topic == "voisinage":
        body = (
            "Bonjour,\n\nJe souhaite vous signaler un problème de voisinage"
            + (f" : {hint}" if hint else ".")
            + "\n\nPouvez-vous m'indiquer les démarches possibles ? Je vous remercie de votre "
            "aide.\n\nCordialement."
        )
    else:
        body = (
            "Bonjour,\n\n"
            + (f"{hint}" if hint else "J'ai une demande concernant mon logement.")
            + "\n\nJe vous remercie par avance de votre retour.\n\nCordialement."
        )
    return {"title": title, "description": body, "source": "modele"}


async def generate_ticket_draft(topic: str | None, hint: str | None) -> dict:
    key = (topic or "autre").strip().lower()
    if key not in _TOPIC:
        key = "autre"
    hint = (hint or "").strip()

    from app.services import llm_service

    if llm_service.enabled():
        try:
            import json
            import re as _re

            system = (
                "Tu aides un LOCATAIRE à rédiger une demande claire et polie à son gestionnaire "
                "immobilier, en français, à la première personne. Reste factuel ; n'invente pas de "
                "détails précis que le locataire n'a pas fournis (garde des formulations générales si "
                "besoin). Réponds STRICTEMENT en JSON valide, sans texte autour : "
                '{"title": "<sujet court, max 70 caractères>", "description": "<message de 40 à 120 mots>"}.'
            )
            user = f"Type de signalement : {_TOPIC[key]['label']}.\n"
            user += (
                f"Précisions du locataire : {hint}"
                if hint
                else "Précisions du locataire : (aucune)"
            )
            reply = await llm_service.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.6,
                max_tokens=400,
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
    return _fallback(key, hint)
