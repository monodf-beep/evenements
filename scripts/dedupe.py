#!/usr/bin/env python3
"""Déduplication multi-sources des événements.

Un même événement arrive souvent par plusieurs flux (officiel + radar + office de
tourisme). On regroupe les doublons, on garde une fiche CANONIQUE (la source la
plus autoritaire/riche) et on FUSIONNE sans rien perdre :

- socle canonique = meilleur score (tier curé puis richesse) → lien officiel,
  attribution, statut ;
- MATIÈRE préservée : on complète les champs manquants du gagnant depuis les autres,
  on garde le texte le PLUS LONG du groupe (même venu d'un radar gratuit), et on NE
  SUPPRIME PAS les doublons (statut='merged', duplicate_of=gagnant) → la rédaction
  pourra puiser dans toute la matière du groupe.

LLM ? NON — 100 % déterministe (heuristique same_story + score). Voir docs/LLM_OU_CODE.md.
Cron : 0 8 * * * (après scraping/gmail, avant l'évaluation de 9h) — évite aussi de
payer l'évaluation LLM sur des doublons.

DRY-RUN (ajouté le 05/09) : `.venv/bin/python scripts/dedupe.py --dry-run [--rescan]`
imprime chaque groupe qu'il FUSIONNERAIT — gagnant et perdants, avec titre, statut,
source — et n'écrit RIEN. Jusque-là ce script écrivait d'office, à rebours de la règle
4 du dépôt (« dry-run d'abord, toujours ») : impossible de LIRE ce qu'un changement de
critère fusionnerait avant qu'il parte en production au déploiement automatique de
7h50. Le cron, lui, ne change pas (pas de --apply exigé : la ligne du crontab reste
valable telle quelle). La garde « suspicion d'annulation » n'est PAS évaluée en
dry-run — elle écrit en base — donc l'aperçu peut montrer un groupe que le vrai passage
retiendrait ; il ne montre jamais moins.

COÏNCIDENCE lieu + dates + jeton (ajoutée le 08/09, cas Pinocchio WP#6413/WP#8193) :
troisième chemin de `_groups`, qui rapproche deux fiches du même territoire, aux mêmes
dates, dans la même ville ou le même lieu, dont les titres partagent au moins un mot
distinctif — là où la ressemblance de titres ne voit rien. Par défaut ce script LISTE ces
groupes sans les fusionner (log et --dry-run) ; `--coincidence` les fusionne ; et c'est
`verifier_doublons_publies --en-ligne` (9h50) qui les signale sur les fiches publiées.
Doctrine, mesure et limites : docs/DEDOUBLONNAGE.md.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger
from utils.sources import same_story, is_logo_image
from utils.annulation import load_annulation_filter, marqueur_annulation
from utils import slack
from scripts.scraper_events import init_db
from dotenv import load_dotenv

log = get_logger("dedupe")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Priorité de source (tier curé dans config/sources.txt).
TIER_RANK = {"officielle": 3, "institution": 2, "institutionnel": 2, "tourisme": 1, "radar": 0}
_FIELDS = ("date_start", "lieu", "ville", "organisateur")

# --- Déduplication INTER-LANGUE (FR/IT) -----------------------------------
# same_story compare les titres → rate « Festa del Jambon de Bosses » vs « Fête du
# Jambon de Bosses » (langues différentes). On rapproche ces paires par les TOKENS
# SIGNIFICATIFS (noms propres, années), invariants d'une langue à l'autre — on
# retire les mots-outils ET les mots génériques d'événement FR/IT (festa/fête,
# sagra, concerto/concert…) qui, eux, diffèrent selon la langue.
_STOP = {
    # articles / prépositions / conjonctions FR + IT
    "le", "la", "les", "un", "une", "des", "du", "de", "au", "aux", "et", "en",
    "dans", "sur", "pour", "par", "avec", "ce", "cette", "il", "lo", "gli", "dei",
    "degli", "delle", "del", "della", "dello", "di", "da", "al", "alla", "allo",
    "con", "per", "the", "of", "and",
    # ADVERBES / PRONOMS / VERBES COURANTS — ajoutés le 2026-08-02 après une fusion à
    # tort bien réelle : « Une semaine pas plus » (théâtre, Chambéry) apparié à « Fête du
    # lac 2026 : les spectateurs qui n'habitent PAS Annecy paieront PLUS cher » (article
    # Google News). Tokens communs = {pas, plus}, soit 2 mots strictement grammaticaux —
    # assez pour passer le seuil de 2, et comme le recouvrement se mesure sur le PLUS
    # COURT des deux titres (3 tokens ici), le ratio atteignait 0,67 > 0,5. Un titre bref
    # composé de mots-outils s'appariait ainsi avec presque n'importe quoi. Conséquence en
    # cascade : la description Google News passait dans l'événement gagnant, puis nourrissait
    # la rédaction (enrich.py agrège la matière des doublons) et la traduction — d'où une
    # fiche IT publiée sous le titre « Festa del Lago 2026 » sur un spectacle de théâtre.
    # ⚠️ RÉVISÉ le 2026-08-02 : la première version de cette liste retirait aussi
    # « est », « fra », « ete », « son », « cher »/« chere ». Ces six-là sont des
    # HOMOGRAPHES d'un mot de contenu, et les neutraliser cassait de vrais
    # rapprochements : « Le Grand Est en fête » ↔ « Il Grand Est in festa » tombait à
    # {grand} (un seul token, sous le seuil de 2 → plus aucun appariement), « Fra
    # Angelico » à {angelico}, et « été » (la saison, présente dans quantité de titres
    # d'été) disparaissait purement et simplement. Un mot-outil ne mérite sa place ici
    # que s'il n'est JAMAIS porteur de sens dans un titre d'événement. Rappel : ces
    # tokens servent aussi au contrôle titre↔fiche de scripts/batch_report.py — trop
    # élaguer y fabrique aussi de fausses alertes.
    "pas", "plus", "qui", "que", "quoi", "dont", "tout", "tous", "toute", "toutes",
    "sans", "sous", "entre", "chez", "mais", "donc", "non", "ans", "ses",
    "sont", "leur", "leurs", "moins", "tres", "bien",
    "piu", "che", "chi", "cui", "tutto", "tutti", "tutta", "tutte", "senza", "sotto",
    "sono", "suo", "sua", "suoi", "anni", "anno", "meno", "molto",
    # mots génériques d'événement (diffèrent selon la langue → non distinctifs)
    "fete", "festa", "feste", "sagra", "sagre", "fiera", "foire", "marche",
    "mercato", "concert", "concerto", "spectacle", "spettacolo", "expo",
    "esposizione", "mostra", "festival", "edizione", "edition", "rassegna",
    "salon", "salone", "notte", "nuit", "giornata", "journee",
}


def _sig_tokens(title: str) -> set[str]:
    """Tokens SIGNIFICATIFS d'un titre (sans accents, sans mots-outils/génériques).
    Garde les mots de 3+ lettres et les nombres (années)."""
    s = unicodedata.normalize("NFD", (title or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    toks = re.findall(r"[a-z0-9]+", s)
    return {t for t in toks if len(t) >= 3 and t not in _STOP}


def _text_len(html: str | None) -> int:
    """Longueur du TEXTE VISIBLE d'une description (balises et URLs retirées).

    Sert à comparer la SUBSTANCE de deux descriptions, jamais leur volume brut : un item
    Google News RSS se réduit à un `<a href="https://news.google.com/rss/articles/CBMi…">`
    dont l'URL encodée pèse des centaines de caractères pour zéro mot de contenu. Comparé
    en longueur brute, il écrase n'importe quelle vraie description (cf. merge_group).
    """
    import html as _html
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", html or "")
    s = re.sub(r"<[^>]+>", " ", s)                  # balises
    s = _html.unescape(s)
    s = re.sub(r"https?://\S+", " ", s)             # URLs nues restantes
    return len(re.sub(r"\s+", " ", s).strip())


def _title_years(title: str) -> set[str]:
    """Années (nombres à 4 chiffres) présentes dans un titre, via les tokens
    significatifs — exactement l'extraction utilisée par cross_lang_same."""
    return {t for t in _sig_tokens(title) if t.isdigit() and len(t) == 4}


def _years_incompatible(a: str, b: str) -> bool:
    """True si les DEUX titres portent une année et qu'elles sont DISJOINTES
    (deux éditions d'années différentes → NE PAS fusionner). Règle identique à
    cross_lang_same. Conservateur : si au moins un titre n'a pas d'année, on ne
    bloque pas (renvoie False) — en cas de doute on ne prive pas d'une fusion
    légitime, on ajoute seulement une garde contre les fusions à tort."""
    ya, yb = _title_years(a), _title_years(b)
    return bool(ya and yb and ya.isdisjoint(yb))


# Écart maximal toléré entre deux fiches supposées décrire le MÊME événement, quand les
# deux sont datées. Deux sources qui couvrent un même festival citent au pire son
# ouverture d'un côté et une soirée précise de l'autre : elles se chevauchent, ou passent
# à quelques jours près. Un mois d'écart, non.
MERGE_MAX_GAP_DAYS = int(os.getenv("DEDUPE_MAX_GAP_DAYS", "14"))


def _jour(valeur) -> str:
    s = str(valeur or "").strip()
    return s[:10] if re.match(r"\d{4}-\d{2}-\d{2}", s) else ""


def _dates_incompatible(a: dict, b: dict) -> bool:
    """True si les périodes CONNUES des deux fiches sont trop éloignées pour être le
    même événement.

    Attrape la famille de fusions à tort la plus massive de l'audit du 2026-08-02 : les
    RUBRIQUES RÉCURRENTES d'un même flux — « COSA FARE DAL 15 AL 21 GIUGNO IN VALLE
    D'AOSTA » ↔ « COSA FARE NEL FINE SETTIMANA IN VALLE D'AOSTA », « Que faire à Nice ce
    week-end du 12 juin » ↔ « … du 24 juillet », « Les idées de sorties d'ICI Pays de
    Savoie pour ce week-end du … ». Leur titre est composé à 80 % du gabarit fixe de la
    rubrique : les tokens significatifs partagés (cosa/fare/valle/aosta) suffisent à faire
    dire OUI à same_story ET à cross_lang_same, alors que ce sont deux semaines
    différentes. Aucune liste de mots-outils ne corrigera ça — le gabarit est fait de
    vrais mots de contenu. La DATE, elle, les sépare sans ambiguïté et sans dépendre de
    la langue.
    `_years_incompatible` ne couvre pas ce cas : ces titres portent la même année, ou
    aucune.

    ⚠️ PORTÉE RÉELLE, MESURÉE — à ne pas confondre avec l'intention. La garde ne tranche
    QUE si les DEUX fiches sont datées. Or les rubriques récurrentes sont, par
    définition, celles qui disent « ce week-end » ou « nel fine settimana » SANS date :
    `parse_dates` rend ('', '', 'none') dessus. Rejoué le 2026-08-02 sur la vraie chaîne
    (parse_dates puis _groups), deux des trois exemples cités ci-dessus passent ENCORE :
    « COSA FARE DAL 15 AL 21 GIUGNO » ↔ « COSA FARE NEL FINE SETTIMANA » fusionne (la
    seconde n'a pas de date), et « Les idées de sorties … pour ce week-end » aussi. Seul
    le cas « du 12 juin » ↔ « du 24 juillet » est bien coupé.
    La garde est donc utile mais PARTIELLE : elle ne ferme pas « la famille la plus
    massive », elle en coupe la moitié datée. Le cas fréquent « une datée / une non
    datée » reste ouvert et demandera un autre signal (reconnaissance du gabarit de
    rubrique, ou refus de fusionner deux fiches d'un MÊME flux radar). Écrit ici pour
    que le prochain lecteur ne croie pas le problème résolu.
    Compare des INTERVALLES, pas des jours : une source qui n'a que l'ouverture et une
    autre qui a la période complète se chevauchent, donc ne sont jamais séparées."""
    sa, sb = _jour(a.get("date_event_start")), _jour(b.get("date_event_start"))
    if not sa or not sb:
        return False
    ea = _jour(a.get("date_event_end")) or sa
    eb = _jour(b.get("date_event_end")) or sb
    if sa <= eb and sb <= ea:
        return False                                   # périodes qui se chevauchent
    from datetime import date as _date

    def _d(s: str) -> _date:
        return _date(int(s[:4]), int(s[5:7]), int(s[8:10]))

    try:
        gap = (_d(sb) - _d(ea)).days if sb > ea else (_d(sa) - _d(eb)).days
    except ValueError:
        return False                                   # date aberrante : on ne tranche pas
    return gap > MERGE_MAX_GAP_DAYS


def cross_lang_same(a: str, b: str) -> bool:
    """True si deux titres décrivent le MÊME événement malgré des langues différentes.

    Signal robuste : forte intersection de tokens significatifs (noms propres/années).
    Conservateur pour éviter les fusions à tort : ≥ 2 tokens communs, Jaccard ≥ 0,5,
    et années compatibles (deux éditions d'années différentes ne fusionnent pas)."""
    ta, tb = _sig_tokens(a), _sig_tokens(b)
    if len(ta) < 2 or len(tb) < 2:
        return False
    shared = ta & tb
    if _years_incompatible(a, b):
        return False                      # éditions d'années différentes
    # Il faut ≥ 2 tokens communs qui NE SOIENT PAS des années : deux vrais mots
    # distinctifs partagés (noms propres). L'année seule (+ un genre comme « jazz »)
    # ne suffit pas → évite de fusionner deux événements différents de la même année.
    shared_words = {t for t in shared if not (t.isdigit() and len(t) == 4)}
    if len(shared_words) < 2:
        return False
    # Recouvrement suffisant par rapport au plus court des deux titres.
    if len(shared) / min(len(ta), len(tb)) < 0.5:
        return False
    return True


# --- Appariement par COÏNCIDENCE lieu + dates + jeton distinctif (2026-09-08) ----------
#
# D'OÙ ÇA VIENT. Le 08/09 au soir, Franck a vu sur le hub Vallée d'Aoste, côte à côte dans
# « L'agenda à venir », deux pages pour le même événement :
#
#     WP#6413  « Pinocchio traverse les Alpes : quand un bicentenaire ravive la Vallée d'Aoste »
#     WP#8193  « Pinocchio fait étape au Forte di Bard pour les 200 ans de Carlo Collodi »
#
# 19–20 septembre, Bard, les deux. Mesuré sur le code tel qu'il était :
#   · same_story (utils/sources.py:106-126) rend False — aucun « nom propre à majuscule
#     interne » partagé, et UN seul mot significatif commun (« pinocchio ») là où il en
#     faut trois ;
#   · cross_lang_same (ci-dessus) rend False — un seul jeton commun là où il en faut deux,
#     et de toute façon il n'est appelé qu'avec --cross-lang ;
#   · _groups ne lit NI la ville NI le lieu, et la date n'y sert qu'en NÉGATIF
#     (_dates_incompatible sépare, elle ne rapproche jamais).
# Deux articles de presse rédigés par deux journalistes sur le même fait ne partagent
# souvent que le NOM de la chose. La ressemblance de titre ne suffit donc pas ; ce qui
# suffit, c'est la conjonction : même lieu, mêmes dates, et ce nom-là en commun.
#
# CE QUE LA RÈGLE EXIGE, cumulativement (chaque condition seule est banale) :
#   1. même territoire (déjà imposé par _groups) ;
#   2. mêmes dates : date_event_start ÉGALES et date_event_end ÉGALES (fin absente = début).
#      Pas d'inclusion : une exposition de mai à septembre « contient » chaque visite
#      guidée qu'on y donne, ce sont pourtant des fiches distinctes. Une fiche sans date
#      n'est jamais appariée par ici (donnée manquante, règle 5) ;
#   3. même ville (utils.lieux.canon, alias compris) OU même lieu (plié) — un lieu
#      GÉNÉRIQUE (« salle des fêtes », utils.lieux.GENERIQUES) ne compte pas, cent
#      communes en ont un ;
#   4. au moins un JETON DISTINCTIF commun aux deux titres : ≥ 5 lettres, pas un nombre,
#      hors mots-outils FR/IT, hors mots génériques du domaine (_NON_DISTINCTIFS), hors
#      noms de lieux (_STORY_PLACES) et hors mots du lieu/ville des deux fiches — « forte »
#      et « bard » partagés par deux événements AU Forte di Bard ne disent rien ;
#   5. jamais une paire liée par translation_of : deux langues, pas deux doublons.
#
# CE QU'ELLE PRODUIT : un CANDIDAT, pas une fusion. Ce dépôt ne distingue pas « certain »
# et « à confirmer » dans dedupe — tout ce que _groups renvoie est fusionné — et une
# fusion à tort coûte plus qu'un statut : la matière du perdant nourrit la rédaction du
# gagnant (docs/BACKLOG.md, « contamination de contenu »). Une règle qui repose sur UN mot
# commun mérite un regard. Donc : par défaut, dedupe LISTE ces groupes (log et --dry-run)
# sans les fusionner ; `--coincidence` les fusionne, pour qui a lu le dry-run. Et le
# rouvreur automatique (règle 3) est `verifier_doublons_publies --en-ligne` (cron 9h50),
# qui applique cette règle sur les fiches PUBLIÉES et propose la corbeille — c'est là que
# la paire Pinocchio aurait dû remonter, et c'est là qu'elle remonte désormais.
# Détail et limites : docs/DEDOUBLONNAGE.md.
from utils.lieux import GENERIQUES as _LIEUX_GENERIQUES, canon as _canon_ville, \
    est_generique as _lieu_generique, plie as _plie  # noqa: E402
from utils.sources import _STORY_PLACES  # noqa: E402

_NON_DISTINCTIFS: frozenset[str] = frozenset(_STOP | _STORY_PLACES | {
    # Types d'événement et d'activité (FR/IT), au singulier et au pluriel : deux fiches
    # qui partagent « mostra » ou « visite » partagent un GENRE, pas un événement.
    "concerts", "concerti", "spectacles", "spettacoli", "mostre", "exposition",
    "expositions", "esposizioni", "visite", "visites", "visita", "guidata", "guidate",
    "guidee", "guidees", "guide", "teatro", "theatre", "teatrale", "museo", "musee",
    "musees", "musei", "ville", "citta", "saison", "stagione", "evento", "eventi",
    "evenement", "evenements", "incontro", "incontri", "rencontre", "rencontres",
    "conferenza", "conferenze", "conference", "conferences", "atelier", "ateliers",
    "laboratorio", "laboratori", "presentazione", "presentation", "lettura", "letture",
    "lecture", "lectures", "proiezione", "projection", "cinema", "musica", "musique",
    "musical", "musicale", "danza", "danse", "opera", "degustazione", "degustation",
    "mercatino", "mercatini", "marches", "brocante", "vernissage", "inaugurazione",
    "inauguration", "apertura", "ouverture", "chiusura", "cloture", "programma",
    "programme", "programmazione", "programmation", "serata", "serate", "soiree",
    "soirees", "giornate", "journees", "jours", "giorni", "giorno", "heures", "matin",
    "mattina", "pomeriggio", "weekend", "settimana", "semaine", "gratuit",
    "gratuito", "gratuita", "ingresso", "entree", "libero", "bambini", "enfants",
    "famiglia", "famille", "familles", "ragazzi", "jeunes", "annonce", "annonces",
    "annunciato", "svelati", "svelato", "devoile", "devoilee", "novita", "nouveautes",
    # Épithètes de gabarit
    "grande", "grandi", "grands", "grandes", "nuova", "nuovo", "nouveau", "nouvelle",
    "nouveaux", "nouvelles", "prima", "premiere", "ultima", "ultimo", "derniere", "dernier",
    # L'occasion n'est pas la chose : un bicentenaire donne dix événements distincts.
    "anniversario", "anniversaire", "bicentenario", "bicentenaire", "centenario",
    "centenaire", "annees", "edizioni", "editions",
    # Saisons, fêtes calendaires, mois, jours (≥ 5 lettres seulement — les autres ne
    # passent pas le plancher de longueur de toute façon)
    "estate", "inverno", "autunno", "primavera", "automne", "hiver", "printemps",
    "natale", "pasqua", "capodanno", "gennaio", "febbraio", "marzo", "aprile", "maggio",
    "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    "janvier", "fevrier", "avril", "juillet", "septembre", "octobre", "decembre",
    "lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica", "lundi",
    "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
    # Mots de lieu génériques et d'administration : ils disent OÙ, jamais QUOI
    "castello", "chateau", "palazzo", "palais", "chiesa", "eglise", "piazza", "place",
    "salle", "forte", "villa", "parco", "giardini", "giardino", "jardin", "jardins",
    "centro", "centre", "espace", "spazio", "auditorium", "arena", "stadio", "stade",
    "biblioteca", "bibliotheque", "mediatheque", "comune", "commune", "regione",
    "region", "provincia", "valle", "vallee", "cattedrale", "cathedrale", "duomo",
    "basilica", "basilique", "abbazia", "abbaye", "santuario", "sanctuaire", "fortezza",
    "forteresse", "borgo", "village", "paese", "quartier", "quartiere",
} | {mot for nom in _LIEUX_GENERIQUES for mot in nom.split()})

JETON_MIN_LETTRES = 5


def _jetons_distinctifs(title: str, exclure: frozenset[str] = frozenset()) -> set[str]:
    """Les mots d'un titre qui peuvent NOMMER un événement : ≥ 5 lettres, alphabétiques,
    hors mots vides, hors génériques du domaine, hors `exclure` (mots du lieu/ville)."""
    s = unicodedata.normalize("NFD", (title or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return {t for t in re.findall(r"[a-z]+", s)
            if len(t) >= JETON_MIN_LETTRES and t not in _NON_DISTINCTIFS and t not in exclure}


def paire_de_traduction(a: dict, b: dict) -> bool:
    """Ces deux fiches sont-elles les deux langues d'un même événement ?

    Trois formes de la même liaison : a traduit b, b traduit a, ou toutes deux traduisent
    le même original. Une paire pareille est NORMALE — deux pages Polylang — et ne doit
    jamais être appariée. Définie ICI et importée par verifier_doublons_publies : deux
    copies de la même question finiraient par se contredire (journal du 08/09, racine
    « deux détecteurs pour la même chose, un seul juste »)."""
    ta, tb = int(a.get("translation_of") or 0), int(b.get("translation_of") or 0)
    return ta == b["id"] or tb == a["id"] or bool(ta and ta == tb)


def _memes_dates(a: dict, b: dict) -> bool:
    """Intervalles [début, fin] IDENTIQUES, les deux fiches datées. Pas d'inclusion (cf.
    en-tête : une exposition contient ses visites guidées sans être leur doublon)."""
    sa, sb = _jour(a.get("date_event_start")), _jour(b.get("date_event_start"))
    if not sa or not sb or sa != sb:
        return False
    return (_jour(a.get("date_event_end")) or sa) == (_jour(b.get("date_event_end")) or sb)


def _lieu_commun(a: dict, b: dict) -> str:
    """« ville « bard » », « lieu « forte di bard » », ou "" si rien ne les réunit."""
    va, vb = _canon_ville(a.get("ville") or ""), _canon_ville(b.get("ville") or "")
    if va and va == vb:
        return f"ville « {va} »"
    la, lb = _plie(a.get("lieu") or ""), _plie(b.get("lieu") or "")
    if la and la == lb and not _lieu_generique(la):
        return f"lieu « {la} »"
    return ""


def coincidence_lieu_date(a: dict, b: dict) -> str:
    """Le MOTIF de coïncidence lieu + dates + jeton (« ville « bard », 2026-09-19→2026-09-20,
    jeton « pinocchio » »), ou "" si l'une des cinq conditions de l'en-tête manque.

    Renvoie une phrase et pas un booléen parce que ce motif est DIT à l'humain qui
    tranche (dry-run, verifier_doublons_publies, Slack) : une recommandation sans son
    critère se lit comme une certitude."""
    if paire_de_traduction(a, b):
        return ""
    if not _memes_dates(a, b):
        return ""
    ou = _lieu_commun(a, b)
    if not ou:
        return ""
    # Les mots du lieu et de la ville des DEUX fiches ne distinguent rien : deux
    # événements au Forte di Bard portent souvent « Forte » ou « Bard » dans leur titre.
    exclure = frozenset(m for e in (a, b) for champ in ("lieu", "ville")
                        for m in _plie(e.get(champ) or "").split())
    communs = _jetons_distinctifs(a.get("title", ""), exclure) & \
        _jetons_distinctifs(b.get("title", ""), exclure)
    if not communs:
        return ""
    debut = _jour(a.get("date_event_start"))
    fin = _jour(a.get("date_event_end")) or debut
    quand = debut if fin == debut else f"{debut}→{fin}"
    return f"{ou}, {quand}, jeton « {', '.join(sorted(communs))} »"


def _memes_titres(a: dict, b: dict, cross_lang: bool = False) -> bool:
    """Le chemin HISTORIQUE de _groups — ressemblance de titres, gardes années et dates —
    isolé pour que motif_groupe puisse dire par quel chemin une paire s'est formée."""
    if _dates_incompatible(a, b):
        return False
    ti, tj = a.get("title", ""), b.get("title", "")
    return (same_story(ti, tj) and not _years_incompatible(ti, tj)) \
        or (cross_lang and cross_lang_same(ti, tj))


def motif_groupe(group: list[dict], cross_lang: bool = False) -> str:
    """"" si le groupe tient par la ressemblance des TITRES (chemin historique) ; sinon le
    ou les motifs de coïncidence qui l'ont formé. Sert à l'affichage : un groupe formé
    par UN mot commun ne doit pas se présenter comme un groupe de titres jumeaux."""
    motifs: list[str] = []
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            if _memes_titres(group[i], group[j], cross_lang):
                continue
            m = coincidence_lieu_date(group[i], group[j])
            if m and m not in motifs:
                motifs.append(m)
    return " ; ".join(motifs)


def richness(ev: dict) -> int:
    """Score objectif de richesse d'un exemplaire (mesurable, sans LLM)."""
    s = 0
    if (ev.get("url_image") or "").strip():
        s += 25
    s += min(len(ev.get("description") or ""), 2000) // 50
    for f in _FIELDS:
        if (ev.get(f) or "").strip():
            s += 5
    url = ev.get("url_source") or ""
    if url and "news.google.com" not in url:
        s += 15
    return s


def score(ev: dict) -> tuple[int, int]:
    """(priorité de tier, richesse). Le tier prime ; la richesse départage."""
    return (TIER_RANK.get((ev.get("source_type") or "").lower(), 1), richness(ev))


def _groups(events: list[dict], cross_lang: bool = False,
            coincidence: bool = False) -> list[list[dict]]:
    """Regroupe par territoire + same_story (union-find simple).

    cross_lang=False (défaut) : on ne dédoublonne QU'EN MÊME LANGUE. Sur un site
    bilingue, les versions FR et IT d'un même événement ne sont PAS des doublons —
    ce sont deux traductions à lier via Polylang (+ hreflang), pas à fusionner. On
    n'active la fusion inter-langue (cross_lang_same) que si explicitement demandé.

    coincidence=False (défaut) : le troisième chemin — même lieu, mêmes dates, un jeton
    distinctif commun (cf. `coincidence_lieu_date`) — n'est PAS pris. `main` l'active pour LISTER
    des candidats sans les fusionner ; `verifier_doublons_publies` l'active pour les
    fiches publiées, où c'est un humain qui tranche."""
    parent = list(range(len(events)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    # ne comparer qu'à l'intérieur d'un même territoire (perf + sens)
    by_terr: dict[str, list[int]] = {}
    for idx, ev in enumerate(events):
        by_terr.setdefault(ev.get("territoire") or "", []).append(idx)
    for idxs in by_terr.values():
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                # même histoire (titres proches) — et, SI demandé, même événement
                # inter-langue FR/IT (désactivé par défaut : bilingue = à lier, pas
                # à fusionner).
                # Garde années : same_story compare les titres SANS regarder les
                # dates → deux éditions successives (« Festival X 2025 » vs « … 2026 »)
                # se ressemblent. On applique la MÊME règle que cross_lang_same :
                # années présentes des deux côtés et disjointes ⇒ pas de fusion.
                # (cross_lang_same porte déjà cette garde en interne.)
                # Garde DATES : s'applique aux DEUX chemins d'appariement (cf.
                # _dates_incompatible). Placée avant, elle coupe court sans dépendre de
                # la langue ni du vocabulaire — deux périodes séparées d'un mois ne sont
                # pas le même événement, quel que soit le degré de ressemblance des titres.
                # Les deux gardes et les deux chemins ci-dessus vivent dans
                # `_memes_titres` (une seule définition, réutilisée par motif_groupe).
                # Le troisième chemin, `coincidence_lieu_date`, ne s'ajoute que sur demande.
                if _memes_titres(events[i], events[j], cross_lang) \
                        or (coincidence and coincidence_lieu_date(events[i], events[j])):
                    union(i, j)

    buckets: dict[int, list[dict]] = {}
    for idx, ev in enumerate(events):
        buckets.setdefault(find(idx), []).append(ev)
    return list(buckets.values())


def ensure_unmerge_column(conn: sqlite3.Connection) -> None:
    """`unmerge_data` — ce que la fusion ÉCRASE, pour qu'elle puisse être défaite.

    AJOUTÉE LE 2026-08-03, au terme du recensement de docs/ETATS_TERMINAUX.md. La fusion
    était le SEUL cul-de-sac sans issue du dépôt : `statut='merged'` + `duplicate_of`, et
    aucun script ne les remet jamais à zéro. Mais le vrai problème est un cran plus
    profond que « personne ne rouvre » — c'est qu'il n'y avait **plus rien à rouvrir** :
    le statut d'avant de la perdante n'était conservé nulle part, et la description du
    gagnant, quand elle était remplacée, était perdue.

    On ne défait rien ici, et on ne défait rien rétroactivement : les 94 fusions suspectes
    déjà en base demandent un arbitrage éditorial (cf. ETATS_TERMINAUX.md). Ce correctif
    arrête l'hémorragie — à partir d'aujourd'hui, toute fusion est réversible.
    """
    try:
        conn.execute("ALTER TABLE events_raw ADD COLUMN unmerge_data TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def _empile(conn: sqlite3.Connection, event_id: int, entree: dict) -> None:
    """Ajoute une entrée à `unmerge_data`, qui est une LISTE.

    Une liste et pas un objet : une fiche peut absorber plusieurs groupes au fil des
    semaines. Écraser l'instantané précédent perdrait la première fusion — exactement le
    défaut qu'on répare. On empile, on n'écrase pas."""
    row = conn.execute("SELECT unmerge_data FROM events_raw WHERE id=?", (event_id,)).fetchone()
    try:
        pile = json.loads((row[0] if row else None) or "[]")
        if not isinstance(pile, list):
            pile = [pile]
    except (ValueError, TypeError):
        pile = []
    pile.append(entree)
    conn.execute("UPDATE events_raw SET unmerge_data=? WHERE id=?",
                 (json.dumps(pile, ensure_ascii=False), event_id))


def ensure_annulation_columns(conn: sqlite3.Connection) -> None:
    """Trace la suspicion d'annulation (docs/EVENEMENTS_ANNULES.md, canal 2)."""
    for col, decl in (("annulation_detectee_at", "TEXT"),
                      ("annulation_source_url", "TEXT"),
                      ("annulation_fiche_visee_id", "INTEGER"),
                      ("annulation_visee_etait_publiee", "INTEGER"),
                      # AJOUTÉE le 2026-08-08 : le texte EXACT matché par marqueur_
                      # annulation() au moment du signal — jusqu'ici calculé puis
                      # jeté (seulement utilisé pour le message Slack). Sans lui,
                      # scripts.audit_annulations ne pouvait vérifier la fraîcheur
                      # d'un marqueur qu'en re-scannant le TITRE de la fiche
                      # suspecte — correct pour ce canal 2 (le marqueur y est PAR
                      # CONSTRUCTION dans le titre de l'article), mais faux pour le
                      # canal 3 (scripts/dates.py, venues.py) : là, le marqueur
                      # vient du TEXTE DE LA PAGE, jamais copié dans la colonne
                      # `title` — le re-scan y échouait toujours, et CHAQUE
                      # suspicion du canal 3 se refermait donc automatiquement au
                      # premier passage d'audit_annulations, quel que soit l'état
                      # réel du marqueur dans la liste. Trouvé en relançant
                      # tests/test_annulation_canal3.py après un rebase.
                      ("annulation_marqueur", "TEXT")):
        try:
            conn.execute(f"ALTER TABLE events_raw ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()


def _porte_annulation(conn: sqlite3.Connection, group: list[dict], annulation_re) -> dict | None:
    """Si ce groupe cache une suspicion d'annulation, la traite et dit de NE PAS
    fusionner. Sinon renvoie None (fusion normale).

    S'applique QUEL QUE SOIT le statut du gagnant — pending, evaluated ou déjà
    publié. Vérifié dans crontab.txt : le dedupe quotidien tourne SANS --rescan,
    donc il ne compare QUE des fiches encore 'pending' entre elles. Le scénario du
    WP#6798 (fusion polluante) se produit déjà à CE stade, avant toute publication
    — restreindre la porte au seul cas « gagnant publié » l'aurait laissée inerte
    dans l'usage quotidien réel, une garde qui ne protège que le cas rare.
    Le marqueur est cherché dans les AUTRES membres du groupe (le scénario du doc :
    la presse annonce l'annulation d'un événement qui a déjà sa fiche).

    Réversible et non spammant : une fois signalée, la même suspicion n'alerte
    plus tant qu'elle n'est pas résolue — mais elle continue de BLOQUER la fusion.
    Deux rouvreurs, cf. `scripts.audit_annulations` : AUTOMATIQUE si la fiche visée
    était publiée et ne l'est plus (Franck l'a dépubliée) ; MANUEL sinon, via
    `--resolu <id>` — parce que rien ne peut deviner tout seul qu'un humain a
    vérifié une fiche encore pending."""
    winner = max(group, key=score)
    for e in group:
        if e["id"] == winner["id"]:
            continue
        marqueur = marqueur_annulation(e.get("title", ""), annulation_re)
        if not marqueur:
            continue
        deja_signale = bool(e.get("annulation_detectee_at"))
        if not deja_signale:
            # `annulation_fiche_visee_id` est la clé de résolution : scripts.
            # audit_annulations vérifie CETTE fiche (son wp_post_id_as), jamais le
            # statut de la fiche suspecte elle-même — celle-ci sera de toute façon
            # rejetée par l'évaluateur demain matin (c'est un article de presse, pas
            # un événement), que l'annulation soit confirmée ou non. Confondre les
            # deux aurait fabriqué une résolution FAUSSE dès le lendemain.
            conn.execute(
                "UPDATE events_raw SET annulation_detectee_at=datetime('now'), "
                "annulation_source_url=?, annulation_fiche_visee_id=?, "
                "annulation_visee_etait_publiee=?, annulation_marqueur=? WHERE id=?",
                (e.get("url_source", ""), winner["id"],
                 1 if winner.get("wp_post_id_as") else 0, marqueur, e["id"]))
            conn.commit()
            if winner.get("wp_post_id_as"):
                etat_fiche = f"déjà publiée (id {winner['id']}, WP#{winner['wp_post_id_as']})"
            else:
                etat_fiche = f"pas encore publiée (id {winner['id']}, statut {winner.get('statut')})"
            slack.notify(
                f"🔴 *Annulation suspectée* — « {(winner.get('title') or '')[:80]} »\n"
                f"Marqueur « {marqueur} » repéré dans un article apparié à cette fiche, "
                f"{etat_fiche}.\n"
                f"Source : {e.get('url_source', '?')}\n"
                f"Aucune fusion faite, aucun bandeau posé — à confirmer toi-même. Une "
                f"fois vérifié : `.venv/bin/python -m scripts.audit_annulations "
                f"--resolu {e['id']}` (docs/EVENEMENTS_ANNULES.md).")
            log.warning("[%s] annulation suspectée (marqueur « %s », source id=%s) — "
                        "fusion bloquée, alerte envoyée", winner["id"], marqueur, e["id"])
        else:
            log.info("[%s] annulation déjà signalée le %s — toujours en attente, "
                     "fusion toujours bloquée", winner["id"], e.get("annulation_detectee_at"))
        return {"winner": winner["id"], "suspect": e["id"], "marqueur": marqueur,
               "nouveau": not deja_signale}
    return None


def merge_group(conn: sqlite3.Connection, group: list[dict]) -> int:
    """Fusionne un groupe de doublons. Retourne le nb d'événements marqués 'merged'."""
    winner = max(group, key=score)
    losers = [e for e in group if e["id"] != winner["id"]]

    updates: dict[str, str] = {}
    # 1) compléter les champs STRUCTURÉS manquants du gagnant
    if not (winner.get("url_image") or "").strip():
        for e in sorted(losers, key=score, reverse=True):
            img = (e.get("url_image") or "").strip()
            if img and not is_logo_image(img):
                updates["url_image"] = img
                break
    for f in _FIELDS:
        if not (winner.get(f) or "").strip():
            for e in sorted(losers, key=score, reverse=True):
                if (e.get(f) or "").strip():
                    updates[f] = e[f]
                    break
    # 2) MATIÈRE : garder le texte le plus SUBSTANTIEL du groupe (même venu d'un radar
    # gratuit). On mesure le TEXTE VISIBLE, pas la longueur brute — bug corrigé le
    # 2026-08-02 : une description Google News RSS n'est qu'un `<a href="…">` dont l'URL
    # encodée fait plusieurs centaines de caractères sans un mot de contenu. Elle gagnait
    # donc systématiquement au « plus long » et écrasait la vraie description du gagnant,
    # y compris lors de fusions PARFAITEMENT CORRECTES (« Charlie Winston ■ 7 juillet »
    # fusionné dans « Charlie Winston » : bon appariement, description détruite). Cette
    # matière polluée alimentait ensuite la rédaction (enrich.py agrège les doublons) et
    # la traduction — d'où des articles écrits sur le mauvais sujet.
    richest = max(group, key=lambda e: _text_len(e.get("description")))
    if _text_len(richest.get("description")) > _text_len(winner.get("description")):
        updates["description"] = richest["description"]

    if updates:
        # AVANT d'écrire : on note ce qu'on remplace. `updates` ne contient que des champs
        # VIDES chez le gagnant — sauf `description`, qui est le seul cas où une valeur
        # existante est écrasée. C'est précisément celui qui a détruit des descriptions
        # légitimes (« Charlie Winston ■ 7 juillet » a écrasé « Charlie Winston ») et qui a
        # obligé à écrire scripts/repair_polluted_descriptions.py pour re-télécharger ce
        # qu'on avait soi-même effacé. Le noter coûte une ligne ; le reconstituer a coûté
        # un script entier.
        ecrases = {k: winner.get(k) for k in updates if (winner.get(k) or "").strip()}
        if ecrases:
            _empile(conn, winner["id"], {
                "role": "gagnant", "at": datetime.now().isoformat(timespec="seconds"),
                "perdants": [e["id"] for e in losers], "champs_ecrases": ecrases})
        cols = ", ".join(f"{k}=?" for k in updates)
        conn.execute(f"UPDATE events_raw SET {cols} WHERE id=?",
                     (*updates.values(), winner["id"]))
    merged_n = 0
    for e in losers:
        # Un doublon DÉJÀ poussé sur l'agenda : on ne le fusionne pas ici (ça
        # laisserait un brouillon WordPress orphelin) — le ménage WP s'en charge.
        if e.get("wp_post_id_as"):
            log.warning("id=%d déjà sur l'agenda (WP#%s) — non fusionné "
                        "(nettoie côté WP avec scripts.cleanup_as_dupes)",
                        e["id"], e["wp_post_id_as"])
            continue
        # Le statut d'AVANT est la seule chose qu'aucune autre source ne peut rendre :
        # 'pending', 'evaluated' ou 'published_sub' ne se devinent pas après coup. Sans
        # lui, défusionner obligerait à re-évaluer la fiche — donc à re-payer un appel LLM
        # et à risquer un verdict différent de celui qu'un humain avait déjà validé.
        _empile(conn, e["id"], {
            "role": "perdant", "at": datetime.now().isoformat(timespec="seconds"),
            "gagnant": winner["id"], "statut_avant": e.get("statut"),
            "duplicate_of_avant": e.get("duplicate_of")})
        conn.execute(
            "UPDATE events_raw SET statut='merged', duplicate_of=? WHERE id=?",
            (winner["id"], e["id"]))
        merged_n += 1
    log.info("Groupe « %s » : %d sources → garde id=%d (%s), %d fusionnée(s)",
             winner.get("title", "")[:50], len(group), winner["id"],
             winner.get("source_type"), merged_n)
    return merged_n


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Déduplication multi-sources (dont inter-langue FR/IT).")
    parser.add_argument("--rescan", action="store_true",
                        help="Inclure aussi les événements RETENUS (nettoie le stock "
                             "existant en MÊME LANGUE).")
    parser.add_argument("--cross-lang", action="store_true",
                        help="FUSIONNER aussi les paires FR/IT (⚠️ à éviter sur un site "
                             "bilingue : les traductions sont à LIER via Polylang, pas à "
                             "fusionner). Désactivé par défaut.")
    parser.add_argument("--dry-run", action="store_true",
                        help="N'écrit RIEN : imprime les groupes qui seraient fusionnés "
                             "(gagnant + perdants). À lire avant tout changement de critère.")
    parser.add_argument("--coincidence", action="store_true",
                        help="FUSIONNER aussi les groupes formés par coïncidence lieu + dates "
                             "+ jeton distinctif (règle du 2026-09-08, cas Pinocchio). Sans "
                             "cette option ils sont seulement LISTÉS (log, --dry-run) : un "
                             "seul mot commun mérite un regard avant la fusion.")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_unmerge_column(conn)      # ce que la fusion écrase, pour pouvoir la défaire
    ensure_annulation_columns(conn)  # suspicion d'annulation, docs/EVENEMENTS_ANNULES.md
    where = ("statut='pending' OR (statut IN ('evaluated','published_cs','published_sub') "
             "AND duplicate_of IS NULL)") if args.rescan else "statut='pending'"
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE {where}").fetchall()]
    log.info("%d événement(s) à dédupliquer%s", len(rows),
             " (rescan du stock retenu)" if args.rescan else "")

    annulation_re = load_annulation_filter()
    merged = suspectees = 0
    groups_titres = _groups(rows, cross_lang=args.cross_lang)
    groups_tous = _groups(rows, cross_lang=args.cross_lang, coincidence=True)
    # Un CANDIDAT est un groupe que seule la coïncidence lieu + dates + jeton a formé (ou
    # agrandi) : son ensemble d'ids n'est celui d'aucun groupe du chemin historique.
    ids_titres = {frozenset(e["id"] for e in g) for g in groups_titres}
    candidats = [g for g in groups_tous
                 if len(g) > 1 and frozenset(e["id"] for e in g) not in ids_titres]
    groups = groups_tous if args.coincidence else groups_titres
    dups = [g for g in groups if len(g) > 1]
    if args.dry_run:
        # Aperçu lisible par un humain : ce que le passage réel fusionnerait, et dans quel
        # sens. Rien n'est écrit — pas même la garde annulation (elle empile en base).
        print(f"DRY-RUN — {len(rows)} événement(s) examiné(s), "
              f"{len(dups)} groupe(s) de doublons (rien n'est écrit)")
        for g in dups:
            winner = max(g, key=score)
            print(f"\n▶ GAGNANT id={winner['id']} [{winner.get('statut')}] "
                  f"« {(winner.get('title') or '')[:70]} » — {winner.get('url_source') or '?'}")
            for e in sorted((e for e in g if e["id"] != winner["id"]), key=lambda e: e["id"]):
                print(f"   ↳ fusionné id={e['id']} [{e.get('statut')}] "
                      f"« {(e.get('title') or '')[:70]} » — {e.get('url_source') or '?'}")
            motif = motif_groupe(g, args.cross_lang)
            if motif:
                print(f"   ↔ formé par coïncidence : {motif}")
        if candidats and not args.coincidence:
            print(f"\nCANDIDATS par coïncidence lieu + dates + jeton — {len(candidats)} "
                  f"groupe(s), NON fusionnés (relancer avec --coincidence pour les fusionner) :")
            for g in candidats:
                print(f"   · ids {', '.join(str(e['id']) for e in sorted(g, key=lambda e: e['id']))}"
                      f" — {motif_groupe(g, args.cross_lang)}")
                for e in sorted(g, key=lambda e: e["id"]):
                    print(f"       [{e['id']}] [{e.get('statut')}] « {(e.get('title') or '')[:70]} »")
        conn.close()
        log.info("=== DRY-RUN : %d groupe(s) auraient été fusionnés, %d candidat(s) par "
                 "coïncidence %s, 0 écriture ===", len(dups), len(candidats),
                 "inclus" if args.coincidence else "non fusionnés")
        return 0
    if candidats and not args.coincidence:
        # Listés, jamais tus : ces fiches suivent leur chemin normal (évaluation,
        # publication) et c'est `verifier_doublons_publies --en-ligne` (9h50) qui les
        # rattrape une fois en ligne, avec la même règle. Le log dit ce qui l'attend.
        for g in candidats:
            log.info("CANDIDAT par coïncidence (non fusionné sans --coincidence) : ids %s — %s",
                     ", ".join(str(e["id"]) for e in sorted(g, key=lambda e: e["id"])),
                     motif_groupe(g, args.cross_lang))
    for g in dups:
        signal = _porte_annulation(conn, g, annulation_re)
        if signal:
            suspectees += 1
            continue  # groupe entier retenu tant que la suspicion n'est pas résolue
        merged += merge_group(conn, g)
    conn.commit()
    conn.close()
    # Le compteur de candidats est là même à zéro : un état qui sort une fiche d'une
    # file la sort aussi de tous les bilans (règle 6) — ici la fiche n'en sort pas, mais
    # le lecteur du log doit voir que la règle a tourné et combien de cas se sont présentés.
    log.info("=== Dédup terminée : %d groupe(s) de doublons, %d événement(s) fusionné(s), "
             "%d suspicion(s) d'annulation (fusion retenue), %d candidat(s) par coïncidence "
             "lieu+dates+jeton %s ===",
             len(dups), merged, suspectees, len(candidats),
             "fusionnés (--coincidence)" if args.coincidence else "listés, non fusionnés")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
