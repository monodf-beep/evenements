#!/usr/bin/env python3
"""SEO / GEO / AEO d'un événement — pour les événements PHARES, à la demande.

Deux volets (cf. docs/AGENT_SEO_DASHBOARD_SPEC.md) :
  • DÉTERMINISTE, gratuit : le JSON-LD schema.org/Event, construit depuis la base
    (aucun appel LLM). C'est la donnée structurée réutilisable pour l'export
    WordPress (Cultura Sabauda aujourd'hui, Agenda Sabaudo demain).
  • LLM, à la demande : title/méta/réponse directe (AEO)/FAQ — la langue et le
    jugement. Réservé aux phares (coût maîtrisé).

Règle maison LLM_OU_CODE : le schema = code ; la langue = LLM.
"""
from __future__ import annotations
import json
import re

# Territoire → (region lisible, code pays ISO) pour PostalAddress.
_TERRITORY_GEO = {
    "Savoie": ("Savoie / Haute-Savoie", "FR"),
    "Piemonte": ("Piemonte", "IT"),
    "Vallee-Aoste": ("Vallée d'Aoste", "IT"),
    "Nice": ("Alpes-Maritimes", "FR"),
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def build_event_jsonld(ev: dict) -> dict | None:
    """Construit le JSON-LD schema.org/Event depuis les champs de la base.
    Déterministe, sans LLM. Renvoie None si l'événement n'a pas le minimum
    requis par Google (nom + date de début)."""
    name = _clean(ev.get("title"))
    start = (ev.get("date_event_start") or "").strip()
    if not name or not start:
        return None  # name + startDate sont requis (règle Google)

    region, country = _TERRITORY_GEO.get(ev.get("territoire") or "", ("", "FR"))
    # location : Place + PostalAddress (adresse rue/géo non stockées → on met ce
    # qu'on a : nom du lieu, ville, région, pays).
    address = {"@type": "PostalAddress"}
    if ev.get("ville"):
        address["addressLocality"] = _clean(ev["ville"])
    if region:
        address["addressRegion"] = region
    address["addressCountry"] = country
    place = {"@type": "Place", "address": address}
    if ev.get("lieu"):
        place["name"] = _clean(ev["lieu"])
    elif ev.get("ville"):
        place["name"] = _clean(ev["ville"])

    data = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": name,
        "startDate": start,
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": place,
        "inLanguage": "fr",
        "publisher": {
            "@type": "Organization", "name": "Agenda Sabaudo",
            "parentOrganization": {"@type": "Organization", "name": "Cultura Sabauda"},
        },
    }
    end = (ev.get("date_event_end") or "").strip()
    if end and end != start:
        data["endDate"] = end
    desc = _clean(ev.get("description"))
    if desc:
        data["description"] = desc[:300]
    if ev.get("url_image"):
        data["image"] = [ev["url_image"]]
    if ev.get("organisateur"):
        data["organizer"] = {"@type": "Organization", "name": _clean(ev["organisateur"])}
    return data


def event_jsonld_str(ev: dict) -> str:
    """JSON-LD prêt à coller dans un <script type="application/ld+json">."""
    data = build_event_jsonld(ev)
    if data is None:
        return ""
    return json.dumps(data, ensure_ascii=False, indent=2)


SEO_PROMPT = """Tu optimises le référencement d'un événement culturel pour un agenda en
ligne bilingue (Savoie, Piémont, Vallée d'Aoste, Nice). Style sobre, factuel, jamais racoleur
(pas de « incontournable », « magique »). Géographie nommée (ville, territoire).

Événement :
Titre : {title}
Catégorie : {categorie}
Lieu : {lieu}, {ville} ({territoire})
Dates : {dates}
Description : {description}

Produis, en français, en JSON strict :
{{"seo_title": "<titre SEO 50-60 caractères, avec le lieu/ville ; suffixe ' — Agenda Sabaudo'>",
  "seo_meta": "<meta description 150-160 caractères, factuelle : quoi, où, quand>",
  "seo_answer": "<réponse directe de 40-60 mots (AEO) : synthèse de l'événement, réutilisable en chapô>",
  "seo_faq": [
    {{"q": "<question naturelle, ex. Quand a lieu … ?>", "a": "<réponse courte et factuelle>"}},
    {{"q": "<Où se déroule … ?>", "a": "<…>"}},
    {{"q": "<Est-ce gratuit ? / Faut-il réserver ?>", "a": "<…>"}}
  ]}}
Réponds UNIQUEMENT le JSON, sans texte avant/après."""


def optimize_seo(ev: dict, client, model: str) -> dict | None:
    """Passe LLM : title/méta/réponse directe/FAQ. Renvoie un dict validé ou None.
    Les exceptions API (crédit, réseau) remontent à l'appelant (la route les gère)."""

    def _dates(ev):
        s = (ev.get("date_event_start") or "").strip()
        e = (ev.get("date_event_end") or "").strip()
        if s and e and e != s:
            return f"du {s} au {e}"
        return s or "date à confirmer"

    prompt = SEO_PROMPT.format(
        title=_clean(ev.get("title")),
        categorie=ev.get("llm_categorie") or "",
        lieu=ev.get("lieu") or "",
        ville=ev.get("ville") or "",
        territoire=ev.get("territoire") or "",
        dates=_dates(ev),
        description=_clean(ev.get("description"))[:600],
    )
    message = client.messages.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        from utils import usage
        usage.record_message(model, message, label="seo")
    except Exception:
        pass  # le suivi de coût ne doit jamais bloquer la génération
    raw = "".join(getattr(b, "text", "") for b in message.content
                  if getattr(b, "type", None) == "text").strip()
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    # Validation légère : on garde ce qui est exploitable.
    faq = data.get("seo_faq") or []
    faq = [{"q": _clean(x.get("q")), "a": _clean(x.get("a"))}
           for x in faq if isinstance(x, dict) and x.get("q") and x.get("a")]
    return {
        "seo_title": _clean(data.get("seo_title"))[:70],
        "seo_meta": _clean(data.get("seo_meta"))[:180],
        "seo_answer": _clean(data.get("seo_answer")),
        "seo_faq": faq,
    }


def faq_jsonld_str(faq: list[dict]) -> str:
    """JSON-LD FAQPage depuis la FAQ générée."""
    if not faq:
        return ""
    data = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": x["q"],
             "acceptedAnswer": {"@type": "Answer", "text": x["a"]}}
            for x in faq
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
