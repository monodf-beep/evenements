# SYNCED FROM observatoire-business-sabaudo — ne pas diverger (extraction future cultura-core)
# DIVERGENCE ASSUMÉE (Agenda) : pick_banner_image ne sert plus le repli « Observatoire
# économique » (fuite de marque, charte §9) — il résout exclusivement dans le set
# catégorie Agenda (config/territory_category_images.txt) et renvoie "" à défaut.
# À répercuter lors de l'extraction cultura-core (ne PAS écraser avec la version amont).
# DIVERGENCE ASSUMÉE (04/09) : onze fonctions sans appelant CÔTÉ AGENDA retirées (liste
# dans le docstring). L'Observatoire en utilise peut-être encore — domain_of/source_label
# créditaient SA newsletter, is_welcome_subject/is_newsletter_junk filtraient SES mails.
# Ne PAS porter ces suppressions à l'aveugle dans l'amont : y vérifier les appelants d'abord.
"""Filtres et registres de sources : ce qui se lit dans config/ et se teste sur un
titre, une URL ou une ville.

- presse (config/press_domains.txt) : sources radar, jamais créditées ni liées (charte §8) ;
- images : domaines proscrits, détection de logo, bannières territoire × catégorie
  (pick_banner_image, set Agenda hébergé sur agendasabauda.eu) ;
- newsletters suivies (config/newsletters.txt), sources larges, filtres radar / périmètre /
  hors-zone / événements exclus ;
- Comté de Nice : appartenance d'une commune (config/communes_comte_de_nice.json).

NETTOYÉ le 04/09 (audit du 31/08 §2.7) : ce module portait onze fonctions publiques sans
aucun appelant — mesuré par grep sur tout le dépôt, tests compris — dont quatre lisaient
des fichiers de config QUI N'EXISTENT PAS (official_links.txt, offtopic_keywords.txt,
economic_keywords.txt) et une lisait territory_images.txt, vidé exprès depuis la fuite de
marque Observatoire (charte §9). L'ancien docstring décrivait « le crédit des sources dans
la newsletter (favicon + nom) » : c'était domain_of/source_label, mortes aussi. Retirées :
strip_tracking, is_welcome_subject, is_newsletter_junk, load_topic_filter, is_offtopic,
load_territory_images, pick_image, load_official_links, resolve_official, domain_of,
source_label, est_comte_de_nice — plus le paramètre `fallback_images` de
pick_banner_image, ignoré ici mais encore chargé et passé pour rien par six scripts.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

_PRESS_FILE = Path(__file__).resolve().parent.parent / "config" / "press_domains.txt"


def load_press_domains(path: Path | None = None) -> set[str]:
    """Charge l'ensemble des domaines de presse (radar uniquement)."""
    path = path or _PRESS_FILE
    if not path.exists():
        return set()
    domains: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            domains.add(line.lstrip("."))
    return domains


def is_press(domain: str, press: set[str]) -> bool:
    """Vrai si le domaine (ou son domaine parent) figure dans la liste de presse."""
    domain = (domain or "").lower()
    return any(domain == p or domain.endswith("." + p) for p in press)


_BLOCKED_IMG_FILE = Path(__file__).resolve().parent.parent / "config" / "blocked_image_domains.txt"


def load_blocked_image_domains(path: Path | None = None) -> set[str]:
    """Charge les hôtes d'images PROSCRITS (CDN de presse, agrégateurs)."""
    path = path or _BLOCKED_IMG_FILE
    if not path.exists():
        return set()
    domains: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            domains.add(line.lstrip("."))
    return domains


# Motifs d'URL trahissant un LOGO / blason / icône (pas une vraie photo de sujet).
# Jetons de NOM DE FICHIER trahissant un logo / blason / icône / gabarit (pas une
# photo). Comparés au SEUL nom de fichier, BORNÉS par des non-alphanumériques :
#  • « default » matche « default.png » mais PAS le dossier Drupal « sites/default/
#    files » (faux positif classique : comune.torino.it & co.) ;
#  • « logo » matche « Logo-Escale.png » mais pas « catalogo.jpg » ;
#  • « flag » matche « flag.png » mais pas « flagship.jpg ».
_LOGO_NAME_TOKENS = frozenset((
    "logo", "logos", "sprite", "icon", "icons", "favicon", "placeholder",
    "default", "avatar", "blason", "stemma", "flag", "banner", "badge",
    "header", "footer", "wordmark", "brandmark", "emblem", "crest",
    # Icônes « suivez-nous » auto-hébergées par le site source (pas de vraie photo) —
    # repéré : une icône « facebook.png » locale glissée comme photo de contenu, non
    # bloquée par domaine (elle n'est PAS servie par facebook.com/fbcdn.net).
    "facebook", "twitter", "linkedin", "youtube", "pinterest", "whatsapp",
    "telegram", "tiktok", "share", "social",
))


_STORY_PLACES = {
    "savoie", "haute", "piemonte", "piedmont", "piemontese", "torino", "turin", "aoste",
    "aosta", "valdotaine", "valdostano", "vallee", "nice", "nizza", "alcotra", "alpes",
    "alpine", "provence", "azur", "monaco", "france", "italie", "europe", "europeen",
    "europeens", "region", "regionale",
}
_STORY_STOP = {
    "pour", "avec", "dans", "les", "des", "une", "sur", "par", "plus", "leur", "cette",
    "leurs", "entre", "vers", "sans", "sous", "cet", "ces", "qui", "que", "son", "ses",
}


def same_story(a: str, b: str) -> bool:
    """Vrai si deux titres décrivent le MÊME sujet (pour ne pas répéter la une dans les
    signaux). Repère un NOM PROPRE distinctif partagé (RareEarth, EIC, Mont-Blanc…) ou
    un fort recouvrement de mots significatifs — en ignorant les noms de lieux."""
    import re

    def words(s: str) -> list[str]:
        return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'-]+", s or "")

    def sig(s: str) -> set:
        return {_strip_accents(w).lower() for w in words(s)
                if len(w) >= 4 and _strip_accents(w).lower() not in _STORY_STOP}

    # Noms propres distinctifs : majuscule INTERNE (RareEarth, EIC, Mont-Blanc).
    def proper(s: str) -> set:
        return {_strip_accents(w).lower() for w in words(s) if any(c.isupper() for c in w[1:])}

    shared_proper = (proper(a) & proper(b)) - _STORY_PLACES - _STORY_STOP
    if shared_proper:
        return True
    return len((sig(a) & sig(b)) - _STORY_PLACES) >= 3


def is_logo_image(url: str) -> bool:
    """Vrai si l'URL ressemble à un logo / blason / icône (à écarter), pas une photo.

    On juge sur le NOM DE FICHIER (mots bornés), PAS sur le chemin complet : un
    dossier banal comme « sites/default/files » (Drupal) ne doit pas faire un faux
    positif. Les .svg sont toujours écartés (pictogrammes vectoriels)."""
    u = (url or "").lower()
    if not u:
        return False
    path = urlparse(u).path            # ignore la query (…/img.svg?v=2 reste un svg)
    if path.endswith(".svg"):
        return True
    name = path.rsplit("/", 1)[-1]     # nom de fichier seul
    words = set(re.split(r"[^a-z0-9]+", name))
    if words & _LOGO_NAME_TOKENS:
        return True
    # Dossiers d'UI de thème (icônes d'interface) — signal net et rare.
    return "/ui/" in path or "/icons/" in path


def is_blocked_image(url: str, blocked: set[str]) -> bool:
    """Vrai si l'URL d'image provient d'un hôte proscrit (presse/agrégateur).

    Empêche qu'une vignette tierce sans rapport (typiquement une photo de média
    récupérée par un agrégateur) ne s'affiche : on retombe sur la bannière.
    """
    if not url or not blocked:
        return False
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == b or host.endswith("." + b) for b in blocked)


_NEWSLETTERS_FILE = Path(__file__).resolve().parent.parent / "config" / "newsletters.txt"


def load_newsletters(path: Path | None = None) -> list[dict]:
    """Charge le registre des newsletters suivies : [{nom, domaine, territoire, statut}]."""
    path = path or _NEWSLETTERS_FILE
    if not path.exists():
        return []
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 4:
            continue
        nom, domaine, territoire, statut = parts[0], parts[1], parts[2], parts[3].lower()
        if nom and domaine:
            out.append({"nom": nom, "domaine": domaine.lower(),
                        "territoire": territoire, "statut": statut})
    return out


def _load_keywords(path: Path) -> list[str]:
    if not path.exists():
        return []
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(_strip_accents(line).lower())
    return out


def _compile_keywords(words: list[str]):
    """Compile une alternation \\b(mot1|mot2|…)\\b (accents déjà retirés)."""
    if not words:
        return None
    # Tri par longueur décroissante pour que les expressions multi-mots priment.
    parts = sorted((re.escape(w) for w in words), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b")


_RADAR_CULTURAL_FILE = Path(__file__).resolve().parent.parent / "config" / "radar_cultural_exceptions.txt"


def load_radar_cultural_filter(path: Path | None = None):
    """Regex des marqueurs culturels/touristiques (config/radar_cultural_exceptions.txt)
    — filtre POSITIF pour les sources radar, voir is_radar_relevant()."""
    return _compile_keywords(_load_keywords(path or _RADAR_CULTURAL_FILE))


_EXCLUDED_EVENTS_FILE = Path(__file__).resolve().parent.parent / "config" / "excluded_event_keywords.txt"


class ExclusionsEvenements:
    """Les deux portées d'une règle d'exclusion : PARTOUT, ou dans le TITRE seul.

    La distinction vient d'un faux positif réel (2026-08-04) : « btob » cherché dans les
    descriptions a attrapé le Salone Auto Torino — salon automobile GRAND PUBLIC, dans
    le périmètre — parce que l'article mentionnait au passage son volet BtoB. Le mot
    n'était pas mauvais, le CHAMP l'était : un événement public peut avoir une journée
    pro, et sa description en parle. Dans un TITRE en revanche, « Afterwork » ou « B2B »
    ne trompe personne — c'est l'événement lui-même qui se nomme ainsi.

    D'où deux portées, déclarées dans le fichier par les marqueurs `[partout]` (défaut)
    et `[titre]`. Règle du pouce pour choisir : une expression qui décrit le PUBLIC
    (« réservé aux professionnels ») ou un domaine va partout ; un mot qui peut n'être
    qu'une mention au fil du texte va dans `[titre]`."""

    def __init__(self, partout=None, titre=None):
        self.partout = partout
        self.titre = titre

    def __bool__(self) -> bool:
        return bool(self.partout or self.titre)


def _load_keywords_par_portee(path: Path) -> tuple[list[str], list[str]]:
    """Lit le fichier d'exclusions en séparant les portées `[partout]` / `[titre]`."""
    partout: list[str] = []
    titre: list[str] = []
    if not path.exists():
        return partout, titre
    courant = partout
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        marqueur = line.lower()
        if marqueur == "[titre]":
            courant = titre
            continue
        if marqueur == "[partout]":
            courant = partout
            continue
        courant.append(_strip_accents(line).lower())
    return partout, titre


def load_excluded_events_filter(path: Path | None = None) -> ExclusionsEvenements:
    """Règles des événements à NE JAMAIS valoriser (config/excluded_event_keywords.txt).

    Règle éditoriale explicite (ex. « jamais le 27e/23e BCA »), pas un jugement de
    pertinence — rejet déterministe et gratuit, avant tout appel LLM. Extensible sans
    code : une ligne = une expression, sous `[partout]` (défaut) ou `[titre]`."""
    partout, titre = _load_keywords_par_portee(path or _EXCLUDED_EVENTS_FILE)
    return ExclusionsEvenements(_compile_keywords(partout), _compile_keywords(titre))


def is_excluded_event(title: str, description: str, exclusions, url: str = "") -> bool:
    """Vrai si la fiche matche une règle d'exclusion éditoriale, selon sa portée.

    L'URL SOURCE est cherchée avec les règles `[partout]` depuis le 2026-08-04 : un
    domaine signe parfois seul ce qu'aucun mot du titre ne dit (`businessfrance.fr`).
    Les points d'un domaine étant des frontières de mot, une ligne `businessfrance`
    suffit — inutile d'écrire l'URL entière."""
    if not exclusions:
        return False
    titre_seul = _strip_accents(title or "").lower()
    if exclusions.titre is not None and exclusions.titre.search(titre_seul):
        return True
    if exclusions.partout is None:
        return False
    text = _strip_accents(f"{title or ''} {description or ''} {url or ''}").lower()
    return bool(exclusions.partout.search(text))


_PERIMETER_FILE = Path(__file__).resolve().parent.parent / "config" / "perimeter_keywords.txt"
_BROAD_FILE = Path(__file__).resolve().parent.parent / "config" / "broad_sources.txt"


def load_perimeter_filter(path: Path | None = None):
    """Regex des lieux du périmètre (Savoie, Piémont, VDA, Nice, Alcotra…)."""
    return _compile_keywords(_load_keywords(path or _PERIMETER_FILE))


def mentions_perimeter(text: str, perimeter_re) -> bool:
    """Vrai si le texte cite un lieu du périmètre sabaudo. Sert à filtrer les sources
    LARGES (ex. EU-Startups, pan-européen) pour ne garder que ce qui nous concerne."""
    if perimeter_re is None:
        return True  # pas de filtre configuré → on ne bloque rien
    return bool(perimeter_re.search(_strip_accents(text or "").lower()))


_OUT_OF_ZONE_FILE = Path(__file__).resolve().parent.parent / "config" / "out_of_zone.txt"


def load_out_of_zone(path: Path | None = None):
    """Regex des marqueurs HORS ZONE (Lyon, Avignon, Milano…). Détection POSITIVE :
    sert à purger le bruit que les sources larges/radar ramènent hors périmètre."""
    return _compile_keywords(_load_keywords(path or _OUT_OF_ZONE_FILE))


def mentions_out_of_zone(text: str, out_re) -> bool:
    """Vrai si le texte cite un lieu clairement hors des 4 territoires."""
    if out_re is None:
        return False  # pas de liste configurée → on n'affirme rien
    return bool(out_re.search(_strip_accents(text or "").lower()))


def is_out_of_scope(text: str, out_re, perimeter_re) -> bool:
    """Hors périmètre de façon DÉTERMINISTE : le texte cite un lieu hors zone
    ET aucun lieu couvert. Un lieu couvert cité (même en passant) lève le doute
    et laisse la décision au LLM (cas « tournée / comparaison »)."""
    return mentions_out_of_zone(text, out_re) and not mentions_perimeter(text, perimeter_re)


def load_broad_sources(path: Path | None = None) -> set[str]:
    """Domaines des sources LARGES (non locales) à filtrer par périmètre géographique."""
    path = path or _BROAD_FILE
    if not path.exists():
        return set()
    out: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lower()
        if line and not line.startswith("#"):
            out.add(line.lstrip("."))
    return out


def is_broad_source(domain: str, broad: set[str]) -> bool:
    domain = (domain or "").lower()
    return any(domain == b or domain.endswith("." + b) for b in broad)


def is_radar_relevant(text: str, cultural_re) -> bool:
    """Vrai si un texte radar (presse généraliste) mentionne un marqueur culturel/
    touristique connu (config/radar_cultural_exceptions.txt) — filtre POSITIF pour
    les sources radar : plus robuste qu'une liste de mots hors-sujet à énumérer (le
    vocabulaire du fait-divers est trop varié — « chute », « percute », « noyade »…
    jamais exhaustif), alors qu'un vrai signal culturel porte quasi toujours un mot
    du champ lexical (festival, concert, musée, patrimoine…). Sans configuration
    (cultural_re=None), on ne filtre rien (True, comportement permissif par défaut).
    """
    if cultural_re is None:
        return True
    if not text:
        return False
    return bool(cultural_re.search(_strip_accents(text).lower()))


_CATEGORY_IMAGES_FILE = Path(__file__).resolve().parent.parent / "config" / "territory_category_images.txt"


def load_territory_category_images(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Charge les images de substitution par (territoire, catégorie) :
    {territoire: {catégorie: url}} — le SEUL set de repli (config/
    territory_category_images.txt, hébergé sur agendasabauda.eu). Sans catégorie
    connue, pick_banner_image pioche dans le territoire ; sinon "" (charte §9)."""
    path = path or _CATEGORY_IMAGES_FILE
    images: dict[str, dict[str, str]] = {}
    if not path.exists():
        return images
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.count(";") < 2:
            continue
        territory, category, url = (p.strip() for p in line.split(";", 2))
        if territory and category and url:
            images.setdefault(territory, {})[category] = url
    return images


def _canon_territory(value: str) -> str:
    """Normalise une valeur de territoire vers la clé CANONIQUE du set catégorie
    (`Savoie` | `Piemonte` | `Vallee-Aoste` | `Nice`), ou "" si non reconnue.

    Tolérant : minuscule + accents retirés, insensible aux slashes/tirets. Absorbe
    toutes les variantes rencontrées en base (« Haute-Savoie », « Piémont »,
    « Vallée d'Aoste », « Comté de Nice », « Nice/Alpes-Maritimes », slugs
    « nice-alpes-maritimes »…). Même logique de détection par mot-clé que
    scripts/publisher_as.py:_map_territoire, mais renvoie les clés du set CATÉGORIE
    (config/territory_category_images.txt) et non les slugs WP.
    """
    v = _strip_accents(value or "").lower()
    if not v:
        return ""
    if "savoi" in v:                                     # Savoie / Haute-Savoie / Savoia (IT)
        return "Savoie"
    if "piemont" in v or "piedmont" in v:                # Piémont / Piemonte / Piedmont
        return "Piemonte"
    if "aost" in v:                                      # Vallée d'Aoste / Valle d'Aosta / Aoste
        return "Vallee-Aoste"
    # bilingue FR/IT : « Nizza » / « Contea di Nizza » ne contiennent pas « nice »
    if "nice" in v or "nizza" in v or "maritim" in v or "azur" in v:
        return "Nice"                                    # Nice / Nizza / Alpes-Maritimes / Côte d'Azur
    return ""


def pick_banner_image(territory: str, category: str, key: str,
                      cat_images: dict[str, dict[str, str]]) -> str:
    """Visuel de repli Agenda, TOUJOURS pris dans le set catégorie (hébergé sur
    agendasabauda.eu). Ne sert JAMAIS la bannière « Observatoire économique » —
    charte §9 : « pas d'image plutôt qu'un visuel inadapté ».

    Résolution :
      1. `_canon_territory(territory)` → clé du set catégorie ; si inconnu → "" ;
      2. dans le sous-dico du territoire, la catégorie exacte si présente ;
      3. sinon, à défaut de catégorie, une image Agenda DÉTERMINISTE (hash de `key`)
         parmi les valeurs du territoire — jamais la bannière de marque territoriale ;
      4. sinon → "" (aucune image ; PAS de repli Observatoire).

    Le paramètre `fallback_images` (bannières de marque de territory_images.txt) a été
    retiré le 04/09 : ignoré ici depuis le retrait du repli Observatoire (charte §9),
    il était encore chargé et passé par six scripts pour rien.
    """
    import hashlib

    canon = _canon_territory(territory)
    if not canon:
        return ""
    by_cat = cat_images.get(canon) or {}
    if category in by_cat:
        return by_cat[category]
    if by_cat:
        pool = sorted(by_cat.values())              # ordre stable → choix reproductible
        idx = int(hashlib.md5((key or "").encode("utf-8")).hexdigest(), 16) % len(pool)
        return pool[idx]
    return ""


def _strip_accents(text: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


# --------------------------------------------------------------------------- #
# Territoire « Comté de Nice » — appartenance d'une commune
# --------------------------------------------------------------------------- #
# ARBITRAGE FRANCK, 2026-08-02 : le Comté de Nice = toutes les communes de
# l'ARRONDISSEMENT DE NICE ; celles de l'arrondissement de GRASSE en sont exclues.
# Attention à la nuance, elle n'est pas intuitive : les communes de Grasse restent
# DANS le périmètre géographique de la charte (§2 « Nice/Alpes-Maritimes »), elles
# ne reçoivent simplement pas l'étiquette de territoire `comte-de-nice`.
#
# Pourquoi une liste et pas une règle géographique : sans elle, l'attribution se
# faisait au jugé, et le jugé se trompe. Le CSV « événements sans visuel de repli »
# du 2026-08-02 proposait `comte-de-nice` pour Mandelieu-la-Napoule, Mouans-Sartoux,
# Saint-Paul-de-Vence et Saint-Laurent-du-Var — quatre communes provençales, à
# l'ouest du Var. Le critère administratif, lui, se vérifie.
_COMTE_NICE_FILE = Path(__file__).resolve().parent.parent / "config" / "communes_comte_de_nice.json"
_comte_nice_cache: "set | None" = None


def _cle_commune(nom: str) -> str:
    """Nom de commune comparable : sans accents, sans casse, sans ponctuation."""
    import unicodedata as _ud
    s = _ud.normalize("NFD", nom or "")
    s = "".join(c for c in s if _ud.category(c) != "Mn").lower()
    return re.sub(r"[^a-z]", "", s)


def _cherche_commune(ville: str, ensemble: set[str]) -> bool:
    """La ville appartient-elle à cet ensemble de communes, y compris sous une forme
    ENRICHIE d'un quartier, d'une mention postale ou d'un nom d'usage ?

    Le nom exact ne suffit pas : la donnée réelle contient « Cannes-la-Bocca » (la Bocca
    est un quartier de Cannes), « Antibes Juan-les-Pins » (nom d'usage de la commune
    d'Antibes) et « Nice Cedex 1 ». Mesuré le 2026-08-03 : ces trois formes passaient au
    travers du filtre, donc trois façons d'écrire Cannes ou Antibes échappaient à
    l'exclusion de l'arrondissement de Grasse.

    On essaie donc le nom complet, puis des PRÉFIXES DE MOTS de plus en plus courts, en
    gardant le plus long qui corresponde. On travaille sur des MOTS et jamais sur des
    sous-chaînes : « Saint-Paul-de-Vence » ne doit pas être confondu avec « Vence », qui
    est une commune distincte — or l'une contient l'autre en sous-chaîne. Le préfixe d'un
    seul mot n'est retenu qu'à partir de 4 lettres, pour ne pas apparier sur « la »,
    « le » ou « les ».

    Limite assumée : un homonyme hors zone dont le nom commence comme une commune d'ici
    (« Le Mas-d'Agenais » face au « Mas » niçois) serait rattaché à tort. La conséquence
    est d'écarter un événement qui était de toute façon hors périmètre — l'erreur va donc
    dans le sens prudent."""
    if not (ville or "").strip():
        return False
    if _cle_commune(ville) in ensemble:
        return True
    mots = [m for m in re.split(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ]+", ville) if m]
    for n in range(len(mots) - 1, 0, -1):
        prefixe = _cle_commune("".join(mots[:n]))
        if (n >= 2 or len(prefixe) >= 4) and prefixe in ensemble:
            return True
    return False


def communes_comte_de_nice() -> set[str]:
    global _comte_nice_cache
    if _comte_nice_cache is None:
        try:
            import json as _json
            data = _json.loads(_COMTE_NICE_FILE.read_text(encoding="utf-8"))
            _comte_nice_cache = {_cle_commune(c)
                                 for c in data.get("arrondissement_de_nice", [])}
        except (OSError, ValueError):
            _comte_nice_cache = set()
    return _comte_nice_cache


_grasse_cache: "set | None" = None


def communes_arrondissement_grasse() -> set[str]:
    global _grasse_cache
    if _grasse_cache is None:
        try:
            import json as _json
            data = _json.loads(_COMTE_NICE_FILE.read_text(encoding="utf-8"))
            _grasse_cache = {_cle_commune(c)
                             for c in data.get("arrondissement_de_grasse", [])}
        except (OSError, ValueError):
            _grasse_cache = set()
    return _grasse_cache


def est_arrondissement_grasse(ville: str) -> bool:
    """La commune est-elle dans l'arrondissement de GRASSE — donc HORS PÉRIMÈTRE ?

    ARBITRAGE FRANCK, 2026-08-02 : « aucune étiquette, on ne devrait pas avoir
    d'événements sur ces territoires pour le moment ». Cannes, Antibes, Grasse,
    Cagnes-sur-Mer, Vence, Saint-Paul-de-Vence, Mandelieu-la-Napoule, Mouans-Sartoux,
    Saint-Laurent-du-Var… sortent donc du catalogue, alors que la charte les incluait
    jusqu'ici sous « Nice/Alpes-Maritimes » (§2, corrigé depuis).

    Pourquoi une liste de communes plutôt que des mots-clés dans config/out_of_zone.txt :
    ce fichier prévient lui-même de n'y mettre que des noms NON AMBIGUS, et ceux-ci le
    sont tous — « Vence » est contenu dans « Provence », « Grasse » dans « grasse
    matinée », « Biot » et « Opio » sont trop courts pour être cherchés dans du texte
    libre. Comparée au champ `ville`, la liste est exacte ; cherchée dans une
    description, elle produirait des faux positifs.

    Les deux listes se recoupent : 101 communes (Nice) + 62 (Grasse) = 163, le compte
    exact des Alpes-Maritimes. Elles sont donc complètes et disjointes.
    """
    if not (ville or "").strip():
        return False           # ville inconnue : on n'exclut jamais sur une absence
    return _cherche_commune(ville, communes_arrondissement_grasse())
