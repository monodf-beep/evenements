#!/usr/bin/env python3
"""Génère un post Instagram PRÊT À PUBLIER depuis un événement Agenda Sabauda.

Priorité de Franck : « surtout une description ». Ce module produit donc, sans coût
LLM (pur gabarit déterministe), une **légende** soignée (accroche → infos → appel à
l'action → hashtags), en **FR et en IT** (agenda bilingue), plus un **texte alternatif**
accessible. Il n'invente aucune donnée : il n'utilise que les champs réels de la fiche
(titre, date, lieu, ville, territoire, catégorie, réponse SEO si présente).

Bonnes pratiques appliquées : accroche courte en 1ʳᵉ ligne (avant le « … plus »),
date/lieu explicites, CTA « enregistre / partage » + « lien en bio » (IG n'autorise
pas de lien cliquable en légende), 5–12 hashtags mêlant marque + territoire + ville +
catégorie. Le visuel/carrousel se construit ailleurs (skill carousel) — ici, le texte.
"""
from __future__ import annotations

import re
import unicodedata

_MONTHS = {
    "fr": ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "it": ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
           "agosto", "settembre", "ottobre", "novembre", "dicembre"],
}

# Hashtags de territoire (noms de lieux, valables dans les deux langues).
_TERR_TAGS = {
    "savoie":       ["Savoie", "HauteSavoie", "Chambéry", "Annecy"],
    "piemonte":     ["Piemonte", "Torino", "Piedmont"],
    "vallee-aoste": ["ValléedAoste", "ValleDAosta", "Aosta"],
    "nice":         ["Nice", "Nizza", "CôtedAzur", "AlpesMaritimes"],
}

_BASE_TAGS = {
    "fr": ["AgendaSabauda", "Alpes", "sortir", "évènement", "culture"],
    "it": ["AgendaSabauda", "Alpi", "cosafare", "eventi", "cultura"],
}

_CTA = {
    "fr": ("🔖 Enregistre ce post pour ne pas oublier — et partage-le à la personne "
           "avec qui tu veux y aller.\n🔗 Toutes les infos : lien en bio."),
    "it": ("🔖 Salva questo post per non dimenticare — e condividilo con la persona "
           "con cui vuoi andarci.\n🔗 Tutte le info: link in bio."),
}


def _terr_key(territoire: str) -> str:
    t = (territoire or "").lower()
    if "piemont" in t:
        return "piemonte"
    if "aost" in t or "aoste" in t:
        return "vallee-aoste"
    if "nice" in t or "nizza" in t or "maritim" in t:
        return "nice"
    if "savoie" in t or "savoia" in t:
        return "savoie"
    return ""


def default_lang(territoire: str) -> str:
    """Langue de départ selon le territoire (IT côté italien, FR sinon)."""
    return "it" if _terr_key(territoire) in ("piemonte", "vallee-aoste") else "fr"


def _camel(text: str) -> str:
    """Transforme « Val d'Aoste » → « ValdAoste » (hashtag propre, sans accents perdus)."""
    t = unicodedata.normalize("NFKD", (text or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    parts = re.split(r"[^0-9A-Za-z]+", t)
    return "".join(p.capitalize() for p in parts if p)


def _first_sentence(text: str, limit: int = 150) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return ""
    m = re.search(r"(.+?[.!?])(\s|$)", text)
    s = m.group(1).strip() if m else text
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s


def format_date(start: str, end: str, lang: str) -> str:
    """« vendredi ... » simplifié : « 15 août 2026 », ou « du 15 au 18 août 2026 »."""
    def parts(d):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", (d or "").strip())
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    ps, pe = parts(start), parts(end)
    months = _MONTHS[lang]
    if not ps:
        return ""
    y1, m1, d1 = ps
    if pe and pe != ps:
        y2, m2, d2 = pe
        du, au = ("du", "au") if lang == "fr" else ("dal", "al")
        if (y1, m1) == (y2, m2):
            return f"{du} {d1} {au} {d2} {months[m1]} {y1}"
        return f"{du} {d1} {months[m1]} {au} {d2} {months[m2]} {y2}"
    return f"{d1} {months[m1]} {y1}"


def hashtags(event: dict, lang: str) -> list[str]:
    tags: list[str] = list(_BASE_TAGS[lang])
    tk = _terr_key(event.get("territoire", ""))
    if tk:
        tags += _TERR_TAGS.get(tk, [])
    ville = _camel(event.get("ville", ""))
    if ville and ville not in tags:
        tags.append(ville)
    cat = _camel(event.get("llm_categorie", ""))
    if cat and cat not in tags:
        tags.append(cat)
    # Dédoublonne SANS tenir compte des accents (#Chambéry == #Chambery), en gardant
    # l'ordre et la 1ʳᵉ forme rencontrée ; plafonne à 12.
    def _key(s):
        n = unicodedata.normalize("NFKD", s.lower())
        return "".join(c for c in n if not unicodedata.combining(c))
    seen, out = set(), []
    for t in tags:
        k = _key(t)
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out[:12]


def caption(event: dict, lang: str = "fr") -> str:
    """Légende Instagram complète pour l'événement, dans la langue demandée."""
    title = re.sub(r"\s+", " ", (event.get("title") or "")).strip()
    hook = _first_sentence(event.get("seo_answer") or "") or title
    lines = [hook, ""]
    dt = format_date(event.get("date_event_start", ""), event.get("date_event_end", ""), lang)
    if dt:
        lines.append(f"📅 {dt}")
    lieu = (event.get("lieu") or "").strip()
    ville = (event.get("ville") or "").strip()
    where = ", ".join([p for p in (lieu, ville) if p])
    if where:
        lines.append(f"📍 {where}")
    lines += ["", _CTA[lang], "", " ".join("#" + t for t in hashtags(event, lang))]
    return "\n".join(lines).strip()


def alt_text(event: dict, lang: str = "fr") -> str:
    """Texte alternatif accessible pour l'image (à coller dans « Réglages avancés »)."""
    title = re.sub(r"\s+", " ", (event.get("title") or "")).strip()
    ville = (event.get("ville") or "").strip()
    if lang == "it":
        return f"Locandina dell'evento « {title} »{(' a ' + ville) if ville else ''}."
    return f"Visuel de l'événement « {title} »{(' à ' + ville) if ville else ''}."


def instagram_post(event: dict) -> dict:
    """Paquet prêt pour le back-office : légendes FR + IT, hashtags, alt, langue conseillée."""
    return {
        "default_lang": default_lang(event.get("territoire", "")),
        "fr": {"caption": caption(event, "fr"), "alt": alt_text(event, "fr")},
        "it": {"caption": caption(event, "it"), "alt": alt_text(event, "it")},
    }
