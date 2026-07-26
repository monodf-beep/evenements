#!/usr/bin/env python3
"""Génère un post Instagram PRÊT À PUBLIER depuis un événement Agenda Sabauda.

Priorité de Franck : « surtout une description ». Ce module produit donc, sans coût
LLM (pur gabarit déterministe), une **légende** soignée (accroche → infos → appel à
l'action → hashtags), en **FR et en IT** (agenda bilingue), plus un **texte alternatif**
accessible. Il n'invente aucune donnée : il n'utilise que les champs réels de la fiche
(titre, date, lieu, ville, territoire, catégorie, réponse SEO si présente).

Bonnes pratiques appliquées (vérifiées en ligne, 2026) : accroche dans les 125 premiers
caractères (avant le « … plus »), date/lieu explicites, CTA « enregistre / partage » +
« lien en bio » (IG n'autorise pas de lien cliquable en légende), 3 hashtags ciblés
(au-delà, ça sent le spam et ça n'aide plus l'indexation). Le visuel/carrousel se
construit ailleurs (utils.social_image) — ici, le texte.

Un second mode, `caption_ai()`, réécrit la légende via LLM dans la voix éditoriale de
la maison (utils.voix, alimentée depuis Obsidian) + le ton Enrico Nos Alpes (factuel,
sobre, aucune emphase) + les principes anti-signes-IA (skill humanizer : pas de tiret
cadratin, pas de vocabulaire IA générique, CTA jamais recopié mot pour mot). C'est un
appel LLM PAYANT, à la demande (bouton), jamais automatique — cf. app.reseaux_rewrite.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from urllib.parse import quote

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

# Marque + 1 mot large de repli (utilisé seulement s'il reste de la place dans le
# plafond de 3 hashtags — cède la place en premier aux tags spécifiques).
_BRAND_TAG = "AgendaSabauda"
_BROAD_TAG = {"fr": "sortir", "it": "cosafare"}

_CTA = {
    "fr": ("🔖 Enregistre ce post pour ne pas oublier. Partage-le à la personne "
           "avec qui tu veux y aller.\n🔗 Toutes les infos : lien en bio."),
    "it": ("🔖 Salva questo post per non dimenticare. Condividilo con la persona "
           "con cui vuoi andarci.\n🔗 Tutte le info: link in bio."),
}

# Accroche « commente XXX » — PREMIÈRE ligne de la légende (avant le « … plus »
# d'Instagram, ~125 caractères) : c'est le déclencheur de la réponse privée
# automatique (webhook Instagram, cf. app.webhook_instagram). {kw} = mot-clé de
# l'événement (utils.social.dm_keyword).
_DM_CTA = {
    "fr": "💬 Commente « {kw} » et nous t'envoyons le lien en DM 👇",
    "it": "💬 Commenta « {kw} » e ti mandiamo il link in DM 👇",
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


def format_date(start: str, end: str, lang: str, today: "date | None" = None) -> str:
    """« vendredi ... » simplifié : « 15 août 2026 », « du 15 au 18 août 2026 », ou —
    pour un événement LONG déjà EN COURS (ex. exposition avril→octobre consultée en
    juillet) — « jusqu'au 31 octobre 2026 ». Afficher la date de début déjà passée
    laisserait croire à tort que l'événement est fini, ou pas encore commencé.
    `today` injectable pour les tests ; par défaut la date du jour."""
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
        try:
            d_start, d_end = date(y1, m1, d1), date(y2, m2, d2)
            if d_start < (today or date.today()) <= d_end:
                jusquau = "jusqu'au" if lang == "fr" else "fino al"
                return f"{jusquau} {d2} {months[m2]} {y2}"
        except ValueError:
            pass  # date invalide (ex. 31 février saisi par erreur) : repli sur le format normal
        du, au = ("du", "au") if lang == "fr" else ("dal", "al")
        if (y1, m1) == (y2, m2):
            return f"{du} {d1} {au} {d2} {months[m1]} {y1}"
        return f"{du} {d1} {months[m1]} {au} {d2} {months[m2]} {y2}"
    return f"{d1} {months[m1]} {y1}"


def hashtags(event: dict, lang: str, limit: int = 3) -> list[str]:
    """3 hashtags CIBLÉS (pas une liste large — au-delà, ça n'aide plus
    l'indexation et ça sent le spam, cf. bonnes pratiques 2026). Priorité aux tags
    SPÉCIFIQUES (ville, catégorie, territoire) sur les génériques (marque, mot large)."""
    ville = _camel(event.get("ville", ""))
    cat = _camel(event.get("llm_categorie", ""))
    tk = _terr_key(event.get("territoire", ""))
    terr_primary = (_TERR_TAGS.get(tk) or [""])[0]
    # Ordre de priorité : le plus spécifique/utile d'abord, la marque et le mot
    # large en dernier (ils cèdent la place les premiers si on dépasse le plafond).
    tags = [ville, cat, terr_primary, _BRAND_TAG, _BROAD_TAG[lang]]
    # Dédoublonne SANS tenir compte des accents (#Chambéry == #Chambery), en gardant
    # l'ordre et la 1ʳᵉ forme rencontrée.
    def _key(s):
        n = unicodedata.normalize("NFKD", s.lower())
        return "".join(c for c in n if not unicodedata.combining(c))
    seen, out = set(), []
    for t in tags:
        k = _key(t)
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out[:limit]


# Sources d'image soumises à ATTRIBUTION (licence) : Wikimedia Commons, Europeana,
# ou une page/OG/web externe. Le crédit (event['image_credit']) doit alors figurer
# dans la légende du post réseau, comme il figure déjà côté WordPress (as_image_credit).
# On n'ajoute JAMAIS de crédit pour 'banner' (visuel maison, aucune attribution due).
_CREDIT_SOURCES = {"og", "page", "commons", "europeana", "web"}


def image_credit_line(event: dict) -> str:
    """Ligne de crédit image discrète (« 📷 … ») à ajouter en fin de légende, ou ''
    si aucune attribution n'est requise. Requiert un crédit non vide ET une source
    licenciable (§_CREDIT_SOURCES, surtout PAS 'banner'). Défensif : '' si les
    champs manquent ou si la source est inconnue."""
    credit = (event.get("image_credit") or "").strip()
    source = (event.get("image_source") or "").strip().lower()
    if not credit or source not in _CREDIT_SOURCES:
        return ""
    return f"📷 {credit}"


def caption(event: dict, lang: str = "fr") -> str:
    """Légende Instagram complète pour l'événement, dans la langue demandée."""
    title = re.sub(r"\s+", " ", (event.get("title") or "")).strip()
    hook = _first_sentence(event.get("seo_answer") or "") or title
    keyword = (event.get("dm_keyword") or "").strip() or dm_keyword(title)
    lines = []
    if keyword:
        lines += [_DM_CTA[lang].format(kw=keyword), ""]
    lines += [hook, ""]
    dt = format_date(event.get("date_event_start", ""), event.get("date_event_end", ""), lang)
    if dt:
        lines.append(f"📅 {dt}")
    lieu = (event.get("lieu") or "").strip()
    ville = (event.get("ville") or "").strip()
    where = ", ".join([p for p in (lieu, ville) if p])
    # Mention organisateur : SEULEMENT si un handle a été CONFIRMÉ à la main par
    # Franck (utils.organizers) — jamais deviné ici (cette fonction reste pure,
    # aucun accès DB ; le champ est injecté par l'appelant avant caption()).
    handle = (event.get("_organizer_handle") or "").strip()
    if where and handle:
        lines.append(f"📍 {where} · @{handle}")
    elif where:
        lines.append(f"📍 {where}")
    elif handle:
        lines.append(f"📍 @{handle}")
    lines += ["", _CTA[lang], "", " ".join("#" + t for t in hashtags(event, lang))]
    credit = image_credit_line(event)
    if credit:
        lines += ["", credit]
    return "\n".join(lines).strip()


def alt_text(event: dict, lang: str = "fr") -> str:
    """Texte alternatif accessible pour l'image (à coller dans « Réglages avancés »)."""
    title = re.sub(r"\s+", " ", (event.get("title") or "")).strip()
    ville = (event.get("ville") or "").strip()
    if lang == "it":
        return f"Locandina dell'evento « {title} »{(' a ' + ville) if ville else ''}."
    return f"Visuel de l'événement « {title} »{(' à ' + ville) if ville else ''}."


def google_calendar_url(event: dict) -> str:
    """Lien Google Agenda « ajout en un clic » — même principe que cs_atc_urls()
    côté WordPress (deploy/wordpress/cs-add-to-calendar.php), reconstruit ici en
    Python pour ne pas dépendre du PHP au moment d'envoyer le bouton DM. Nos dates
    (`date_event_start`/`date_event_end`) sont toujours du « YYYY-MM-DD » sans heure
    (événements journée entière) : on suit donc la branche « allday » de la version
    PHP — fin exclusive (+1 jour). '' si la date de début est absente/invalide."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", (event.get("date_event_start") or "").strip())
    if not m:
        return ""
    start = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    me = re.match(r"(\d{4})-(\d{2})-(\d{2})", (event.get("date_event_end") or "").strip())
    end = date(int(me.group(1)), int(me.group(2)), int(me.group(3))) if me else start
    if end < start:
        end = start
    # Point de départ EFFECTIF : si l'événement est déjà en cours au moment du clic
    # (long événement démarré il y a des semaines, pas encore fini), on démarre
    # l'entrée d'agenda personnel à AUJOURD'HUI plutôt qu'à la vraie date de début —
    # sinon la personne qui clique aujourd'hui se retrouve avec un événement qui
    # « commence » trois mois dans le passé dans son propre agenda.
    today = date.today()
    if start < today <= end:
        start = today
    title = re.sub(r"\s+", " ", (event.get("title") or "")).strip()
    lieu = (event.get("lieu") or "").strip()
    ville = (event.get("ville") or "").strip()
    location = ", ".join(p for p in (lieu, ville) if p)
    dates = f"{start.strftime('%Y%m%d')}/{(end + timedelta(days=1)).strftime('%Y%m%d')}"
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={quote(title)}&dates={dates}&location={quote(location)}")


# Mots trop génériques pour servir de mot-clé « commente XXX » (déclencheur DM
# automatique) : ils reviennent dans plein de titres différents, donc n'identifient
# pas UN événement précis. Le mot-clé doit être mémorable ET propre à CET événement.
_DM_STOPWORDS = {
    "le", "la", "les", "l", "un", "une", "des", "du", "de", "d", "au", "aux", "à",
    "et", "en", "sur", "dans", "avec", "pour", "par", "ce", "cette", "ces", "son",
    "sa", "ses", "il", "elle", "on", "au fil", "the",
    "visite", "visites", "festival", "festivals", "concert", "concerts", "soiree",
    "soirees", "journee", "journees", "fete", "fetes", "expo", "exposition",
    "expositions", "spectacle", "spectacles", "atelier", "ateliers", "rencontre",
    "rencontres", "edition", "grande", "grand", "special", "speciale", "nouveau",
    "nouvelle", "annuel", "annuelle", "programme", "presente", "presentent",
    "international", "internazionale", "national", "nazionale", "regional",
    "regionale", "traditionnel", "traditionnelle", "tradizionale", "premiere",
    "prima", "gratuit", "gratuita", "gratuite", "libre",
}


def _strip_accents(s: str) -> str:
    n = unicodedata.normalize("NFKD", s)
    return "".join(c for c in n if not unicodedata.combining(c))


def dm_keyword(title: str) -> str:
    """Mot-clé « commente XXX pour recevoir le lien en DM », déduit du titre.

    Priorité aux mots CAPITALISÉS hors mots génériques (§_DM_STOPWORDS) — en
    français/italien, un nom propre en milieu de titre (lieu, artiste) qui identifie
    CET événement précis, pas juste sa catégorie ; un adjectif générique même long
    (« internazionale ») reste en minuscule et n'est choisi qu'en dernier recours.
    Parmi les candidats retenus, le plus long. Normalisé (majuscules, sans accent)
    pour une reconnaissance tolérante aux fautes/variantes dans les commentaires.
    '' si le titre ne donne rien d'exploitable — l'appelant retombe sur un mot fixe."""
    words = re.findall(r"[A-Za-zÀ-ÿ]{4,}", title or "")
    candidates = [w for w in words if _strip_accents(w).lower() not in _DM_STOPWORDS]
    if not candidates:
        return ""
    capitalized = [w for w in candidates if w[0].isupper()]
    best = max(capitalized or candidates, key=len)
    return _strip_accents(best).upper()


# ---------------------------------------------------------------------------------
# caption_ai — réécriture LLM, à la demande (PAYANT), pour les événements phares.
# ---------------------------------------------------------------------------------
_CAPTION_AI_RULES = """Tu écris la légende Instagram d'UN événement pour un compte
territorial d'Agenda Sabauda (agenda culturel alpin transfrontalier). Réponds en {lang_full}.

RÈGLES DE FOND (voix Enrico Nos Alpes — factuelle, sobre, jamais promotionnelle) :
- 1ʳᵉ ligne = l'accroche, DANS LES 125 PREMIERS CARACTÈRES : ce qui se passe, où,
  éventuellement quand — pas un slogan. Voix active, phrase concrète.
- Jamais de lieu cité sans être situé (ex. « à Chambéry, en Savoie »), si l'info est
  disponible dans les données fournies.
- Registre sobre : ZÉRO superlatif ni mot de communication (« exceptionnel »,
  « incontournable », « unique », « ambitieux », « innovant », « immanquable »,
  « magique », « féerique »). Zéro point d'exclamation.
- N'INVENTE AUCUNE INFORMATION. N'utilise QUE les données fournies ci-dessous. S'il
  manque une info (horaire, tarif...), ne la mentionne simplement pas.

RÈGLES ANTI-IA (le texte ne doit pas sonner généré) :
- Jamais de tiret cadratin « — ». Utilise la virgule ou le point.
- Aucun de ces mots/tics : « plongez », « découvrez un lieu unique », « au cœur de »,
  « véritable », « incontournable », vocabulaire creux type « riche », « dynamique »,
  formulations « ce n'est pas seulement X, c'est Y », rythme de phrases identique
  d'un bout à l'autre (varie la longueur).
- Le CTA de fin (inviter à enregistrer/partager) doit être écrit avec des mots
  différents à chaque fois — jamais la même phrase toute faite recopiée.

FORMAT DE SORTIE (JSON STRICT, rien d'autre) :
{{"caption": "texte complet prêt à publier (accroche, ligne vide, infos pratiques \\n
  avec emoji 📅/📍 si dispo, ligne vide, CTA + \\"lien en bio\\" puisqu'IG n'autorise pas
  de lien cliquable, ligne vide, hashtags), "hashtags": ["motcle1", "motcle2", ...]}}
- 3 hashtags MAXIMUM, ciblés (ville, catégorie, territoire) — pas de mots larges
  répétés à chaque post.
- Le champ "caption" contient DÉJÀ les hashtags à la fin (précédés de #), séparés
  par un espace, dans le même texte que le reste."""

_CAPTION_AI_EVENT = """Données de l'événement (les SEULES à utiliser — n'invente rien) :
Titre : {title}
Date : {dates}
Lieu : {lieu}
Ville : {ville}
Territoire : {territoire}
Catégorie : {categorie}
Description / matière disponible : {description}"""

_LANG_FULL = {"fr": "français", "it": "italien"}


def caption_ai(event: dict, lang: str, client, model: str) -> str | None:
    """Réécrit la légende via LLM (voix maison + Enrico Nos Alpes + anti-signes-IA).
    Appel PAYANT — à la demande uniquement (bouton back-office), jamais en boucle.
    Renvoie None si la réponse est illisible ; les erreurs API remontent à l'appelant
    (la route les gère, comme pour utils.seo.optimize_seo)."""
    import json as _json

    from utils.voix import voix_block

    dates = format_date(event.get("date_event_start", ""), event.get("date_event_end", ""), lang) \
        or (event.get("date_event_start") or "date à confirmer")
    material = re.sub(r"\s+", " ", (event.get("article_md") or event.get("description")
                                    or event.get("seo_answer") or "")).strip()
    user_text = _CAPTION_AI_EVENT.format(
        title=re.sub(r"\s+", " ", (event.get("title") or "")).strip(),
        dates=dates,
        lieu=event.get("lieu") or "",
        ville=event.get("ville") or "",
        territoire=event.get("territoire") or "",
        categorie=event.get("llm_categorie") or "",
        description=material[:900] or "(aucune description disponible)")
    system_text = voix_block() + _CAPTION_AI_RULES.format(lang_full=_LANG_FULL.get(lang, "français"))
    message = client.messages.create(
        model=model, max_tokens=700,
        system=system_text,
        messages=[{"role": "user", "content": user_text}],
    )
    try:
        from utils import usage
        usage.record_message(model, message, label="social_caption")
    except Exception:
        pass  # le suivi de coût ne doit jamais bloquer la génération
    raw = "".join(getattr(b, "text", "") for b in message.content
                  if getattr(b, "type", None) == "text").strip()
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        data = _json.loads(match.group())
    except _json.JSONDecodeError:
        return None
    text = (data.get("caption") or "").strip()
    return text or None


def instagram_post(event: dict) -> dict:
    """Paquet prêt pour le back-office : légendes FR + IT, hashtags, alt, langue conseillée."""
    return {
        "default_lang": default_lang(event.get("territoire", "")),
        "fr": {"caption": caption(event, "fr"), "alt": alt_text(event, "fr")},
        "it": {"caption": caption(event, "it"), "alt": alt_text(event, "it")},
    }
