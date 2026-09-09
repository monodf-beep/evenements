#!/usr/bin/env python3
"""UNE page officielle téléchargée UNE fois, et TOUS ses champs récoltés d'un coup.

Franck, 2026-08-11 : « je comprends que la génération du texte soit obligatoire avec
l'api mais la complétion des informations grâce aux infos officielles devrait se faire,
alors qu'actuellement ce n'est pas le cas ». C'est exact, et c'est un défaut de
construction, pas un manque de moyens.

CE QUI NE VA PAS AUJOURD'HUI
Trois crons savent lire une page officielle, et chacun n'y prend qu'un seul champ :
  • dates.py       → `dates_from_page`  : JSON-LD startDate/endDate ;
  • venues.py      → `venue_from_page`  : JSON-LD location (name + addressLocality) ;
  • visuals.py     → `fetch_og_image`   : og:image.
Ils tournent à des heures différentes, téléchargent la MÊME page séparément, et surtout
chacun porte SON PROPRE délai de carence. Une fiche qui a épuisé son quota côté date
n'est plus téléchargée par dates.py — donc son lieu et son image, qui sont dans la même
page et qui n'ont rien demandé à personne, ne sont pas récoltés non plus. Trois horloges
indépendantes sur une seule ressource : il suffit que l'une soit fermée pour que le reste
attende.

Vérifié en production le 2026-08-11 : un run complet du mode sans-API a affiché
« Passe page : 0 page(s) à lire » côté dates ET côté lieux, alors que 79 fiches
attendaient une date et 31 un lieu. Aucune page n'a été lue de la soirée.

CE QUE FAIT CE SCRIPT
Un seul téléchargement par fiche, et on en tire tout ce qui s'y trouve : date de début,
date de fin, lieu, ville, image de partage. Aucun modèle — du JSON-LD et des balises
meta, c'est-à-dire de l'analyse syntaxique. Les fonctions d'extraction sont celles qui
existent déjà (dates.dates_from_page, venues.venue_from_page, images.fetch_og_image) :
rien n'est réécrit, on cesse seulement de les appeler chacune dans son coin.

CE QU'IL NE FAIT JAMAIS
  • il n'écrase RIEN : seuls les champs VIDES sont remplis. Une date posée à la main, un
    lieu corrigé au back-office, une image que Franck a remplacée par une vraie — tout
    cela est intouchable. C'est la leçon du 2026-08-09 (« pourquoi ça a retouché à
    l'image alors que je venais de la changer pour une vraie ? ») ;
  • il ne pose pas de verdict d'échec : ne rien trouver ne ferme aucune porte, ne
    consomme aucun délai de carence, et n'empêche pas dates.py ou venues.py de faire
    leur propre travail plus tard. Ce script AJOUTE, il ne décide pas ;
  • il ne touche pas aux fiches dont l'URL n'est pas une page (« gmail:… », Google News) :
    il n'y a rien à télécharger.

CE QUE ÇA RAPPORTE VRAIMENT (mesuré le 2026-08-11, et rectifié le même jour)
68 pages lues → 4 dates, 1 lieu, 5 images. C'est peu, et il faut le dire tel quel.
J'avais d'abord annoncé « 36 vraies affiches attendent derrière une bannière », en lisant
le compteur --diagnostic avant d'avoir posé le filtre des domaines : sur ces 36 og:image,
la plupart venaient de pages de PRESSE, qu'on n'a pas le droit de récolter. Après filtre :
cinq. Le gain de ce script n'est donc pas dans le volume, il est dans le fait qu'une page
officielle n'est plus lue trois fois pour un champ chacune.

RÈGLE 5 : uniquement ce qui est encore devant nous. RÈGLE 4 : dry-run par défaut.
RÈGLE 6 : le bilan est recompté en base, champ par champ, après écriture.

Exemples :
  .venv/bin/python -m scripts.moisson_officielle                 # simulation
  .venv/bin/python -m scripts.moisson_officielle --apply --cap 100
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.logger import get_logger  # noqa: E402
from utils.images import fetch_og_image, page_image_candidates, remote_dims, looks_like_banner_shape  # noqa: E402
from utils.sources import is_logo_image, is_blocked_image, load_blocked_image_domains  # noqa: E402
from utils.radar import source_officielle  # noqa: E402
from utils.traqueurs import est_traqueur, sans_parametres_de_suivi  # noqa: E402
from utils import jsonld  # noqa: E402
from utils import infos_pratiques  # noqa: E402
import json  # noqa: E402
from scripts.dates import (dates_from_page, debut_depuis_page, ensure_columns,  # noqa: E402
                           _robust_get)
from scripts.venues import venue_from_page  # noqa: E402

log = get_logger("moisson")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

CHAMPS = ("date_event_start", "date_event_end", "lieu", "ville", "url_image")
# INFOS PRATIQUES (2026-08-11) — Franck : « il faut que le script aille chercher les
# informations dans les ressources officielles ». Sur 81 colonnes, aucune ne stockait un
# tarif, un horaire ou une condition d'accès : ces faits ne vivaient que dans l'article,
# donc quand ils manquaient la seule issue prévue était d'ouvrir une tâche. Ils sont
# pourtant écrits sur la page de l'organisateur — il suffisait d'aller les lire.
# Stockés en JSON : ce sont des EXTRAITS de la page, pas des valeurs interprétées.
_COL_INFOS = "infos_pratiques"
# Écrit UNE fois : la sélection et le recompte final doivent porter sur le même
# critère, sinon le bilan diverge de ce qui a été tenté.
_MANQUE = (" OR ".join(f"COALESCE({c},'')=''" for c in CHAMPS)
           # Une bannière n'est pas une image : la fiche a beau avoir tous
           # ses champs remplis, il lui manque une vraie affiche.
           + " OR COALESCE(image_source,'')='banner'"
           # Une fiche complète mais sans infos pratiques mérite la lecture : c'est
           # justement ce qui remplissait la file « À vérifier » de tarifs et d'horaires.
           + f" OR COALESCE({_COL_INFOS},'')=''")


# Marqueurs qu'on sait lire aujourd'hui, et ceux qu'on ne lit PAS encore. Le mode
# --diagnostic les compte sur les pages qui n'ont rien donné : 53 pages muettes sur 58
# au premier run, et il faut savoir si c'est parce que la donnée est ABSENTE ou parce
# qu'elle est écrite dans une forme que l'extracteur ignore. Étendre l'extraction sans
# cette mesure, ce serait coder à l'aveugle contre une hypothèse.
_MARQUEURS = (
    ("json-ld startDate", r'"startDate"\s*:\s*"'),
    ("json-ld aux guillemets échappés", r'\\"startDate\\"'),
    ("balise <time datetime>", r'<time[^>]+datetime='),
    ("microdata itemprop=startDate", r'itemprop=["\']startDate'),
    ("meta event:start_time", r'event:start_time'),
    ("json-ld location", r'"location"\s*:'),
    ("microdata itemprop=location", r'itemprop=["\']location'),
    ("og:image", r'property=["\']og:image'),
    ("un bloc JSON-LD est bien présent", r'application/ld\+json'),
)


def _diagnostic(html: str) -> list[str]:
    import re as _re
    return [nom for nom, motif in _MARQUEURS if _re.search(motif, html, _re.I)]


# Services de traçage de lien employés par les newsletters. Ce ne sont pas des sources :
# ils ne publient rien, ils comptent les clics et renvoient ailleurs. Les juger sur leur
# domaine revient à juger une enveloppe au lieu de la lettre.
#
# LA LISTE A QUITTÉ CE FICHIER LE 2026-09-08. Elle vivait ici en double de
# scripts/publisher_as._TRACKING_HOSTS, et les deux divergeaient : celle-ci ignorait le
# motif MailUp `/e/tr` (donc tr.comune.torino.it et go.fondazionetorinomusei.it, des
# routeurs posés sur le domaine du client), l'autre ignorait sendibm1, emailsp, awstrack.
# Mesuré ce soir-là sur les fiches approuvées et incomplètes : une vingtaine avaient pour
# seule adresse un lien de traçage, et la moitié des routeurs rencontrés (Brevo en marque
# blanche, Postmark, OpenEMM, Sequar, le compteur du département 06) n'étaient reconnus
# par AUCUNE des deux listes. Un seul détecteur désormais : utils/traqueurs.py.
_est_traqueur = est_traqueur

# Un lien de traçage ne redirige pas toujours en HTTP : certains rendent une PAGE DE
# REBOND (meta refresh, `location.href` en JavaScript, ou une page « cliquez ici si vous
# n'êtes pas redirigé » avec un seul lien). requests ne suit que les redirections HTTP,
# donc `r.url` valait l'adresse de départ et la moisson concluait « traqueur mort ».
# On suit ces rebonds, à trois conditions : profondeur bornée, jamais la même adresse deux
# fois, et — pour le JavaScript et le lien unique, qui existent aussi sur de vraies pages
# (sélecteur de langue, bandeau cookies) — seulement sur une page qui n'a presque rien
# d'autre à dire. Une page riche qui contient `location.href` dans un script est une page
# à moissonner, pas un rebond : c'est le cas frontière de la fixture.
_PROFONDEUR_REBONDS = 3
_REBOND_TEXTE_MAX = 400      # caractères de texte visible au-delà desquels ce n'est plus un rebond
_META_REFRESH = re.compile(r"<meta\b[^>]*http-equiv\s*=\s*[\"']?refresh[\"']?[^>]*>", re.I)
_JS_LOCATION = re.compile(
    r"(?:window\.|document\.|top\.|self\.)?location(?:\.href|\.replace|\.assign)?"
    r"\s*(?:=|\()\s*[\"']([^\"']+)[\"']", re.I)
_HREFS = re.compile(r"<a\b[^>]+href\s*=\s*[\"']([^\"'#]+)", re.I)


def _destination_rebond(html: str, url: str) -> str:
    """L'adresse vers laquelle une PAGE DE REBOND envoie le navigateur, '' si la page n'en
    est pas une. Adresse absolue, résolue par rapport à `url`."""
    h = html or ""
    m = _META_REFRESH.search(h)
    if m:
        c = re.search(r"content\s*=\s*[\"']([^\"']*)", m.group(0), re.I)
        u = re.search(r"url\s*=\s*[\"']?([^\"'>;\s]+)", c.group(1), re.I) if c else None
        if u:
            cible = urljoin(url, unescape(u.group(1)))
            if cible.startswith(("http://", "https://")) and cible != url:
                return cible
    # Le reste ne se lit que sur une page qui n'a RIEN d'autre à dire.
    if len(infos_pratiques._texte_visible(h)) > _REBOND_TEXTE_MAX:
        return ""
    m = _JS_LOCATION.search(h)
    if m:
        cible = urljoin(url, unescape(m.group(1)))
        if cible.startswith(("http://", "https://")) and cible != url:
            return cible
    hote = urlparse(url).netloc.lower()
    sortants = {urljoin(url, unescape(l)) for l in _HREFS.findall(h)}
    sortants = {l for l in sortants
                if l.startswith(("http://", "https://")) and urlparse(l).netloc.lower() != hote}
    if len(sortants) == 1:
        return sortants.pop()
    return ""


def _telecharger(url: str):
    """(réponse, adresse finale, nombre de rebonds non-HTTP suivis). Réponse None si rien
    n'a répondu. Les redirections HTTP sont suivies par `_robust_get` ; ici on ajoute les
    rebonds que le protocole ne voit pas, dans la limite de `_PROFONDEUR_REBONDS`.
    Un rebond vers une adresse qui ne répond pas laisse la page de rebond en main : c'est
    l'appelant qui la jugera (même hôte qu'au départ → traqueur sans destination)."""
    r = _robust_get(url)
    courante = url
    sauts = 0
    vues = {url}
    while r is not None and sauts < _PROFONDEUR_REBONDS:
        courante = getattr(r, "url", courante) or courante
        vues.add(courante)
        suite = _destination_rebond(r.text, courante)
        if not suite or suite in vues:
            break
        r2 = _robust_get(suite)
        sauts += 1
        if r2 is None:
            break
        r, courante = r2, suite
    if r is not None:
        courante = getattr(r, "url", courante) or courante
    return r, courante, sauts


def _plie(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").lower())
                   if not unicodedata.combining(c))


def _parle_du_titre(html: str, titre: str, url: str = "") -> bool:
    """La page mentionne-t-elle au moins un mot significatif du titre (≥ 4 lettres,
    accents pliés, ABSENT du nom d'hôte) ? Vrai aussi quand le titre n'a aucun mot de ce
    genre — on ne refuse pas sur une absence de critère.

    Pourquoi ce test, et seulement à l'ARRIVÉE d'un traqueur : mesuré le 2026-09-08,
    `enteturismolmr.sequar.com/r/6pf/m/<n'importe quoi>` redirige en 301 vers la page de
    repli de la campagne (comune.asti.it/vivere-comune/eventi) — un hôte officiel, un
    chemin non vide, aucun rapport avec la fiche. Sans ce test, un jeton périmé ferait
    mémoriser la page de repli comme page officielle de l'événement, et `_url_telechargeable`
    la lirait en premier à chaque passage : un cul-de-sac (règle 3).

    Les mots déjà présents dans l'HÔTE ne comptent pas : « Palio di Asti » sur comune.asti.it,
    c'est « asti » partout et « palio » nulle part — passé sur la page réelle le 08/09, le
    test sans cette clause acceptait la liste des événements d'Asti. Même discipline que
    scripts/enrich.py:_page_evenement, non importé ici parce que ce module tire anthropic."""
    hote = _plie(urlparse(url).netloc)
    mots = [w for w in re.findall(r"[a-z0-9]+", _plie(titre))
            if len(w) >= 4 and not w.isdigit() and w not in hote]
    if not mots:
        return True
    texte = _plie(infos_pratiques._texte_visible(html))
    return any(w in texte for w in mots)


def _jeton_brouille(url: str) -> str:
    """La même adresse avec son DERNIER groupe de lettres/chiffres remplacé par des zéros
    (ou des uns s'il n'y avait que des zéros) : un jeton qui ne peut pas être le bon."""
    m = None
    for m in re.finditer(r"[A-Za-z0-9]+", url):
        pass
    if not m or m.end() <= len("https://"):
        return url
    faux = ("1" if set(m.group(0)) == {"0"} else "0") * len(m.group(0))
    return url[:m.start()] + faux + url[m.end():]


def _page_de_repli(depart: str, finale: str) -> bool:
    """L'arrivée dépend-elle du jeton ? Si la MÊME adresse finale répond à un jeton
    brouillé, le routeur n'a pas résolu notre lien : il a servi la page de repli de la
    campagne, quelle que soit la fiche.

    C'est une MESURE, pas une heuristique — et elle tranche là où le titre ne peut pas :
    vu le 08/09, la liste des événements d'Asti mentionnait bien le Palio, et la moisson y
    a pris les horaires d'un spectacle de théâtre du 8 novembre pour une course de chevaux
    de septembre. Une requête de plus, seulement quand un traqueur a abouti quelque part."""
    brouille = _jeton_brouille(depart)
    if brouille == depart:
        return False
    r2, finale2, _ = _telecharger(brouille)
    if r2 is None:
        return False
    return sans_parametres_de_suivi(finale2) == sans_parametres_de_suivi(finale)


def _url_telechargeable(ev: dict) -> str:
    """L'adresse à lire. `url_officiel` d'abord — c'est la page de l'événement chez
    l'organisateur, la plus riche en données structurées ; `url_source` sinon. Les
    pseudo-adresses (« gmail:… ») et Google News ne sont pas des pages."""
    for cle in ("url_officiel", "url_source"):
        u = (ev.get(cle) or "").strip()
        if not u.startswith(("http://", "https://")) or "news.google.com" in u:
            continue
        # LE DOMAINE DOIT POUVOIR SERVIR DE SOURCE OFFICIELLE (2026-08-11). Sans ce
        # test, la moisson récoltait l'og:image de la page d'origine quelle qu'elle
        # soit — Franck a vu passer guidatorino.com, quotidianopiemontese.it et
        # aostaoggi.it, c'est-à-dire de la presse. Le contrat radar est explicite :
        # « DÉTECTER, jamais créditer ni lier ». Et une photo de presse appartient au
        # journal, pas à nous.
        # On ne récolte RIEN de ces pages, pas même la date : un article de presse est
        # souvent un « que faire ce week-end » qui parle de dix événements, et une date
        # prise là-dedans risque d'être celle d'un autre — c'est ainsi que WP#6798 a
        # porté la date d'un voisin. Le chemin de sortie de ces fiches reste la
        # résolution de leur page officielle, qui est le travail de l'enrichissement.
        # UN TRAQUEUR N'EST PAS UN ÉDITEUR (2026-08-11, Franck : « pourquoi ça tourne
        # pas seul pour trouver les informations manquantes ? »). Six expositions de la
        # Reggia di Venaria n'étaient JAMAIS lues : leur adresse est un lien de traçage
        # de newsletter (sendibm1.com), qui échoue au test du domaine officiel — alors
        # qu'il redirige vers lavenaria.it. Le portillon jugeait l'adresse ÉCRITE, pas
        # celle où l'on arrive.
        #
        # On les laisse donc passer la sélection, et c'est `_recolte` qui vérifie le
        # domaine d'ARRIVÉE, après redirection : juger le domaine sur lequel on a
        # atterri, pas celui qu'on nous a donné. Le contrat radar est intact — rien
        # n'est récolté si la destination n'est pas officielle.
        if not source_officielle(u) and not _est_traqueur(u):
            continue
        return u
    return ""


def _ensure_colonne_infos(conn) -> None:
    """Crée `infos_pratiques` si besoin. Appelée par TOUTE fonction qui l'interroge, et
    pas seulement par main() : la leçon d'audit_annulations le 2026-08-09 (« no such
    column »), c'est qu'un module ne doit pas supposer qu'un autre chemin a déjà migré."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    if _COL_INFOS not in cols:
        conn.execute(f"ALTER TABLE events_raw ADD COLUMN {_COL_INFOS} TEXT")
        conn.commit()


def _a_moissonner(conn, today: str, cap: int) -> list[dict]:
    """Fiches encore devant nous à qui il manque au moins un champ récoltable."""
    _ensure_colonne_infos(conn)
    rows = [dict(r) for r in conn.execute(
        f"SELECT * FROM events_raw WHERE "
        "statut IN ('evaluated','published_cs','published_sub') "
        "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
        "AND (COALESCE(recurring,0)=1 OR COALESCE(NULLIF(date_event_end,''), "
        "     NULLIF(date_event_start,''), '9999') >= ?) "
        f"AND ({_MANQUE}) "
        "ORDER BY COALESCE(llm_score,0) DESC LIMIT ?", (today, cap * 3))]
    return [ev for ev in rows if _url_telechargeable(ev)][:cap]


def _recolte(ev: dict, marqueurs=None, morts: list | None = None) -> dict:
    """Champs VIDES que la page permet de remplir. {} si la page est illisible.
    `marqueurs` (Counter, optionnel) : reçoit ce que porte une page qui n'a rien donné.
    `morts` (liste, optionnelle) : reçoit (id, adresse) des liens de traçage SANS
    destination — ils sortent de la récolte, ils doivent donc entrer dans le bilan."""
    depart = _url_telechargeable(ev)
    depart_traqueur = _est_traqueur(depart)
    r, finale, _sauts = _telecharger(depart)
    if r is None:
        if marqueurs is not None:
            marqueurs["PAGE INJOIGNABLE"] += 1
        if depart_traqueur and morts is not None:
            morts.append((ev.get("id"), depart))
        return {}
    # LE DOMAINE D'ARRIVÉE FAIT FOI. Pour un lien de traçage, c'est ici — et seulement
    # ici — qu'on sait où il menait. Si la destination n'est pas une source officielle,
    # on ne récolte RIEN : ni date, ni image, ni tarif. Le contrat radar tient.
    #
    # UN TRAQUEUR RESTE UN TRAQUEUR, MÊME À L'ARRIVÉE. Vérifié en production quinze
    # minutes après avoir posé ce contrôle (11/08) : il laissait passer 8 fiches sur 12 et
    # allait inscrire « https://lql1t.r.a.d.sendibm1.com/… » comme page officielle de la
    # Reggia di Venaria. ET L'HÔTE DOIT AVOIR CHANGÉ — invariant qui ne dépend d'aucune
    # liste : si l'on atterrit sur le même hôte qu'au départ, aucune résolution n'a eu
    # lieu. Ça rattrape les routeurs que utils/traqueurs.py ne connaît pas encore, tant
    # qu'ils ne renvoient pas vers un confrère.
    #
    # Ces deux cas — arrivée sur un traqueur, ou sur l'hôte de départ — sont comptés À
    # PART, avec l'identifiant de la fiche : mesuré le 2026-09-08, dix liens sur douze
    # rendaient la même page qu'un jeton volontairement faux (Brevo « Page not found »,
    # MailUp « Oops! », MailUp court 200 vide, departement06 « Lien invalide »). Ce ne sont
    # pas des pages muettes, ce sont des adresses mortes ; les fondre dans « sans donnée
    # exploitable » cachait vingt fiches que rien ne pouvait plus moissonner.
    change_d_hote = urlparse(depart).netloc.lower() != urlparse(finale).netloc.lower()
    if depart_traqueur and (_est_traqueur(finale) or not change_d_hote):
        if marqueurs is not None:
            marqueurs["TRAQUEUR SANS DESTINATION (périmé, tronqué ou rebond non résolu)"] += 1
        if morts is not None:
            morts.append((ev.get("id"), depart))
        return {}
    # `source_officielle` est une liste de REFUS : un domaine INCONNU est accepté. Le refus
    # d'un traqueur à l'arrivée doit donc rester EXPLICITE (cas du départ non traqueur).
    if _est_traqueur(finale) or not source_officielle(finale):
        if marqueurs is not None:
            marqueurs["DESTINATION NON OFFICIELLE"] += 1
        return {}
    html = r.text
    # LA DESTINATION D'UN TRAQUEUR DOIT PARLER DE L'ÉVÉNEMENT. Sequar renvoie la page de
    # repli de la campagne pour n'importe quel jeton (mesuré le 08/09 : un identifiant
    # bidon arrive sur comune.asti.it/vivere-comune/eventi, hôte officiel, chemin non vide).
    # Une page qui ne mentionne aucun mot du titre n'est pas la page de la fiche : on n'en
    # récolte rien et surtout on ne la mémorise pas — sinon `_url_telechargeable` la lirait
    # en premier à chaque passage, pour toujours.
    if depart_traqueur and not _parle_du_titre(html, ev.get("title") or "", finale):
        if marqueurs is not None:
            marqueurs["DESTINATION SANS RAPPORT AVEC LE TITRE (page de repli de la campagne)"] += 1
        if morts is not None:
            morts.append((ev.get("id"), depart))
        return {}
    # Et quand la page PARLE de l'événement, il reste à savoir si c'est NOTRE lien qui y a
    # mené, ou si le routeur y envoie tout le monde : un jeton brouillé qui arrive au même
    # endroit répond non. Une requête de plus, une page de liste évitée en url_officiel et
    # des infos pratiques d'un autre événement évitées sur la fiche.
    if depart_traqueur and _page_de_repli(depart, finale):
        if marqueurs is not None:
            marqueurs["PAGE DE REPLI DE LA CAMPAGNE (même arrivée avec un jeton brouillé)"] += 1
        if morts is not None:
            morts.append((ev.get("id"), depart))
        return {}
    trouve: dict = {}
    # La vraie adresse, une fois connue, mérite d'être gardée : la prochaine passe n'aura
    # plus à traverser le traqueur, et l'enrichissement disposera enfin d'une page. Sans ses
    # paramètres de campagne (?utm_source=…), qui changent à chaque lettre.
    if depart_traqueur and not (ev.get("url_officiel") or "").strip():
        trouve["url_officiel"] = sans_parametres_de_suivi(finale)
    # Tout ce qui suit — image, hôte, page d'événement — se juge sur la page où l'on EST,
    # pas sur l'adresse du routeur : `fetch_og_image(depart)` retéléchargeait le traqueur,
    # et ne pouvait pas traverser une page de rebond.
    url = finale

    # ── 1. LES DONNÉES STRUCTURÉES, LUES POUR DE BON ────────────────────────────
    # « Implacable au niveau de la collecte des informations officielles AVANT de passer
    # par les LLM » (Franck, 2026-08-11). Jusqu'ici on cherchait la chaîne
    # `"startDate":"…"` dans le HTML — donc on ignorait le bloc `@graph` de Yoast et de
    # Rank Math (la forme de la majorité des sites WordPress), les tableaux de plusieurs
    # objets, les guillemets échappés et les microdata. utils/jsonld.py PARSE le
    # document que le site publie pour être lu par des machines, au lieu d'y chercher
    # un motif. Une seule lecture donne date, lieu, ville et image.
    struct = jsonld.champs(html)
    for cle, val in struct.items():
        if not (ev.get(cle) or "").strip():
            trouve[cle] = val
    # SEULE EXCEPTION AU « ON N'ÉCRASE RIEN » : la date de FIN suit sa date de DÉBUT.
    # Si le début vient d'être posé depuis cette page, garder une fin venue d'ailleurs
    # fabriquerait un intervalle à deux sources — le genre de fiche qui se termine avant
    # de commencer. Les deux bornes décrivent un seul fait, elles se remplacent ensemble.
    if "date_event_start" in trouve and struct.get("date_event_end"):
        trouve["date_event_end"] = struct["date_event_end"]

    # ── 2. Les extracteurs historiques, en complément de ce qui manque encore ────
    if not (ev.get("date_event_start") or "").strip() and "date_event_start" not in trouve:
        debut, fin, _src = dates_from_page(html)
        if debut:
            trouve["date_event_start"] = debut
            # La date de fin ne se pose QUE si le début vient d'être trouvé ici : poser
            # une fin sur un début venu d'ailleurs mélangerait deux sources sur un même
            # intervalle, et c'est ainsi qu'on obtient des fiches qui se terminent avant
            # de commencer.
            if fin:
                trouve["date_event_end"] = fin
    # ── 2 bis. Le DÉBUT corroboré par une FIN déjà connue ───────────────────────
    # Franck, 2026-08-11 : « date de début, date de fin ! » Après trois passages de
    # scripts/dates.py, 54 fiches n'avaient toujours qu'une fin — un « jusqu'au 20
    # septembre » qui ne dit rien du début, et dont la page SOURCE (souvent un article de
    # presse) n'a rien donné de plus. Mais la page lue ICI est la page OFFICIELLE, celle
    # de l'organisateur : c'est elle qui écrit « du 12 juin au 20 septembre ».
    #
    # On ne cherche pas « une date » dans son texte — une page en porte toujours plusieurs
    # (l'article, les autres événements, les horaires, le copyright). On cherche une PLAGE
    # QUI SE TERMINE à la date déjà connue : c'est une confirmation, pas une devinette, et
    # deux débuts possibles pour la même fin ne rendent rien du tout
    # (scripts.dates.debut_depuis_page).
    fin_connue = (ev.get("date_event_end") or "").strip()
    if (not (ev.get("date_event_start") or "").strip()
            and "date_event_start" not in trouve and fin_connue):
        debut = debut_depuis_page(infos_pratiques._texte_visible(html), fin_connue)
        if debut:
            # La fin n'est PAS réécrite : c'est elle qui a servi de preuve, la toucher
            # reviendrait à valider le début avec lui-même.
            trouve["date_event_start"] = debut

    if not (ev.get("lieu") or "").strip() and "lieu" not in trouve:
        lieu, ville, _src = venue_from_page(html)
        if lieu:
            trouve["lieu"] = lieu
        if ville and not (ev.get("ville") or "").strip() and "ville" not in trouve:
            trouve["ville"] = ville

    # ── 3. Microdata, la seconde forme que schema.org autorise ──────────────────
    if not trouve.get("date_event_start") and not (ev.get("date_event_start") or "").strip():
        for cle, val in jsonld.champs_microdata(html).items():
            if not (ev.get(cle) or "").strip() and cle not in trouve:
                trouve[cle] = val
    # UNE BANNIÈRE COMPTE COMME UNE PLACE VIDE (2026-08-11, mesuré). Le premier
    # --diagnostic a donné le chiffre qui décide : 36 des 53 pages « muettes » portent un
    # og:image — mais aucune n'a été récoltée, parce que la condition testait seulement
    # « url_image est vide ». Or la veille au soir, un run sans-API avait posé une
    # bannière générique sur 40 fiches : leur champ n'était plus vide, donc la vraie
    # affiche de leur page officielle restait inatteignable. Le pis-aller bloquait
    # l'accès à la vraie chose.
    # On ne remplace QUE la bannière — jamais une photo (og/page/commons), jamais une
    # image posée à la main : celles-là valent mieux que ce qu'on retrouverait.
    # LA PAGE DE L'ÉVÉNEMENT FAIT FOI POUR L'IMAGE (2026-09-08, Franck : « je trouve qu'il y
    # a encore trop de vignettes générées ! le script n'arrive pas à trouver dans les pages
    # des sites officiels ? »). Mesuré le soir même sur les 18 fiches dont la source venait
    # d'être précisée : 10 pages sur 12 portaient un og:image propre, les 2 autres affichaient
    # l'affiche en pleine page — et la moisson n'en a repris qu'UNE. Deux raisons :
    #   1. elle ne lisait que la balise og:image, jamais les images de la page ;
    #   2. elle ne remplaçait qu'une image vide ou une bannière — jamais une image FAUSSE
    #      déjà en place : une vue de Nice prise sur Wikimedia (Levitation), la photo
    #      d'accueil du TNN (Bernard Stasi), un pixel de traçage (Manara).
    # Désormais une image de PROVENANCE NON OFFICIELLE (bannière, Commons, recherche web,
    # Europeana, ou photo de page prise sur un AUTRE site) cède à l'og:image de la page
    # officielle ; à défaut d'og:image, sur une PAGE d'événement (pas une racine), à sa
    # première image de contenu assez grande. Jamais une image posée à la main, jamais une
    # image de provenance inconnue ni déjà prise en og : la fixture de cette moisson les
    # protège depuis le 11/08 (« ne JAMAIS dégrader une image déjà valide », docs/IMAGES.md).
    from urllib.parse import urlparse as _up
    _img = (ev.get("url_image") or "").strip()
    _src = (ev.get("image_source") or "")
    _banniere = _src == "banner"
    _hote = _up(url).netloc.lower().removeprefix("www.")
    _hote_img = _up(_img).netloc.lower().removeprefix("www.") if _img.startswith("http") else ""
    _ailleurs = bool(_hote_img) and _hote not in _hote_img and _hote_img not in _hote
    _page_evt = bool(_up(url).path.strip("/"))
    _bloques = load_blocked_image_domains()

    def _acceptable(u: str) -> bool:
        return bool(u) and u != _img and not is_logo_image(u) and not is_blocked_image(u, _bloques)

    # Un lien de traçage (sendibm1, mailchimp…) posé comme image n'est jamais une image :
    # c'est le pixel d'ouverture d'une newsletter (Manara à la Venaria, 08/09). Il cède
    # quelle que soit sa provenance.
    _remplacable = (not _img or _banniere or _src in ("commons", "web", "europeana")
                    or (_src == "page" and _ailleurs) or _est_traqueur(_img))
    if _src != "manual" and _remplacable:
        og = fetch_og_image(url)
        if _acceptable(og):
            trouve["url_image"] = og
        elif not og and _page_evt:
            for cand in page_image_candidates(html, url)[:3]:
                if not _acceptable(cand):
                    continue
                w, h = remote_dims(cand)
                if min(w, h) >= 400 and not looks_like_banner_shape(w, h):
                    trouve["url_image"] = cand
                    break
    # Les infos pratiques ne sont pas dans CHAMPS : elles ne conditionnent pas la
    # publication (la porte qualité n'en demande pas), elles la RENSEIGNENT. On les
    # récolte donc même quand tout le reste est déjà rempli.
    if not (ev.get(_COL_INFOS) or "").strip():
        pratiques = infos_pratiques.extraire(html)
        if pratiques:
            trouve[_COL_INFOS] = json.dumps(pratiques, ensure_ascii=False)

    if not trouve and marqueurs is not None:
        for nom in _diagnostic(html) or ["AUCUN marqueur connu"]:
            marqueurs[nom] += 1
        # LA QUESTION À LAQUELLE LE PREMIER DIAGNOSTIC NE RÉPONDAIT PAS. Il comptait la
        # PRÉSENCE d'un bloc JSON-LD, et j'en ai conclu devant Franck que « ces pages
        # décrivent l'organisation, pas l'événement ». Le marqueur ne testait pas ça.
        # Ici on lit les @type réellement déclarés : s'il y a des Event qu'on rate
        # encore, ils apparaissent noir sur blanc.
        for t in jsonld.types_presents(html):
            marqueurs[f"  @type déclaré : {t}"] += 1
    return trouve


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Récolte date, lieu, ville et image sur la page officielle (sans LLM).")
    p.add_argument("--apply", action="store_true", help="Exécute (sinon simulation).")
    p.add_argument("--cap", type=int, default=100, help="Nb max de pages lues (défaut 100).")
    p.add_argument("--diagnostic", action="store_true",
                   help="Sur les pages qui ne donnent RIEN, dire quels marqueurs elles "
                        "portent — pour savoir si la donnée est absente ou seulement "
                        "écrite dans une forme qu'on ne lit pas encore.")
    p.add_argument("ids", nargs="*", type=int, help="Se limiter à ces fiches.")
    args = p.parse_args(argv)

    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # NE PAS SUPPOSER QU'UN AUTRE SCRIPT A DÉJÀ CRÉÉ SES COLONNES. Même famille de panne
    # que audit_annulations le 2026-08-09 (« no such column: annulation_marqueur ») :
    # ce script écrit date_source et date_checked_at, qui appartiennent à dates.py. Sur
    # une base neuve — ou si moisson tourne avant dates.py — la colonne n'existe pas.
    ensure_columns(conn)
    _ensure_colonne_infos(conn)
    if args.ids:
        ph = ",".join("?" * len(args.ids))
        cibles = [dict(r) for r in conn.execute(
            f"SELECT * FROM events_raw WHERE id IN ({ph})", args.ids)]
        cibles = [ev for ev in cibles if _url_telechargeable(ev)]
    else:
        cibles = _a_moissonner(conn, today, args.cap)

    print(f"═══ {len(cibles)} page(s) officielle(s) à lire ═══\n")
    if not cibles:
        print("Aucune fiche incomplète ne dispose d'une page téléchargeable.")
        conn.close()
        return 0

    from collections import Counter
    # Compteur TOLÉRANT aux champs neufs : `url_officiel` s'y est ajouté le 2026-08-11
    # (résolution des liens de traçage) et un dict figé sur CHAMPS levait un KeyError.
    # Un bilan ne doit pas tomber parce qu'on a récolté une chose de plus.
    gagnes = Counter({c: 0 for c in (*CHAMPS, _COL_INFOS)})
    lues = vides = 0
    # « 0 date_event_start » ne dit RIEN tant qu'on ignore si le cas s'est
    # présenté (règle 6 : un compteur doit dire ce qu'il compte). Le run du
    # 2026-08-11 a affiché 0 date sur 70 pages, et il était impossible de
    # savoir si le chemin « début corroboré par la fin » avait échoué ou n'avait
    # simplement jamais eu de candidat : aucune des 70 fiches n'avait peut-être
    # de date de fin sans début. Un zéro qui ne distingue pas « rien trouvé » de
    # « rien tenté » envoie chercher un bug là où il n'y a que du vide.
    candidats_debut = trouves_debut = 0
    marqueurs_vides = Counter()
    # Les liens de traçage SANS destination, toujours comptés — pas seulement en
    # --diagnostic : un état qui sort une fiche de la récolte doit entrer dans le bilan
    # (règle 6), sinon on le découvre des semaines plus tard. Vingt fiches, le 08/09.
    morts: list[tuple] = []
    for ev in cibles:
        # Le cas s'est-il seulement présenté ? Compté AVANT la récolte, sur l'état de la
        # fiche : une fin connue, pas de début. C'est la seule façon de lire le zéro.
        candidat = (not (ev.get("date_event_start") or "").strip()
                    and bool((ev.get("date_event_end") or "").strip()))
        candidats_debut += candidat
        trouve = _recolte(ev, marqueurs_vides if args.diagnostic else None, morts)
        trouves_debut += candidat and "date_event_start" in trouve
        lues += 1
        if not trouve:
            vides += 1
            continue
        for c in trouve:
            gagnes[c] += 1
        detail = " · ".join(
            (f"{c}=" + ", ".join(json.loads(v))) [:70] if c == _COL_INFOS
            else f"{c.replace('date_event_', '')}={v}"[:46]
            for c, v in trouve.items())
        print(f"  [{ev['id']:>5}] {detail}")
        if args.apply:
            sets = ", ".join(f"{c}=?" for c in trouve)
            conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?",
                         (*trouve.values(), ev["id"]))
            # date_source/venue_source renseignés SEULEMENT quand on a trouvé : un
            # échec ici ne doit poser aucun verdict, sinon on garerait la fiche pour
            # un délai de carence alors qu'on n'a même pas essayé le LLM (règle 3).
            if "date_event_start" in trouve:
                conn.execute("UPDATE events_raw SET date_source='page', "
                             "date_checked_at=datetime('now') WHERE id=?", (ev["id"],))
            if "lieu" in trouve or "ville" in trouve:
                conn.execute("UPDATE events_raw SET venue_source='page' WHERE id=?",
                             (ev["id"],))
            if "url_image" in trouve:
                # La provenance suit l'image : sans ça une affiche récoltée resterait
                # marquée « banner » et serait reprise indéfiniment.
                conn.execute("UPDATE events_raw SET image_source='og' WHERE id=?",
                             (ev["id"],))
            conn.commit()

    print(f"\n{lues} page(s) lue(s), dont {vides} sans aucune donnée exploitable.")
    print(f"Début corroboré par une fin déjà connue : {candidats_debut} fiche(s) "
          f"étaient dans ce cas, {trouves_debut} y ont gagné une date de début.")
    if morts:
        # Périmètre écrit à côté du nombre : ces fiches sont COMPRISES dans « sans aucune
        # donnée exploitable » ci-dessus. La longueur de l'adresse est affichée exprès :
        # le 08/09, les douze adresses examinées faisaient toutes 80 caractères — une
        # coupe, quelque part, et personne ne l'aurait vue sans la mesure.
        print(f"\nDont {len(morts)} lien(s) de traçage SANS destination propre — jeton périmé, "
              f"adresse tronquée, rebond non résolu, ou page de repli de la campagne. Rien à "
              f"moissonner tant que la fiche n'a pas d'autre adresse (Site officiel au "
              f"back-office, ou résolution par l'enrichissement) :")
        for eid, adresse in morts:
            print(f"  [{eid:>5}] {len(adresse):3} car.  {adresse[:90]}")
    print()
    if args.diagnostic and marqueurs_vides:
        print("Ce que portent les pages MUETTES (une page peut compter plusieurs fois) :")
        for nom, n in marqueurs_vides.most_common():
            print(f"  {n:4} {nom}")
        print()
    for c in (*CHAMPS, _COL_INFOS):
        print(f"  {gagnes[c]:4} {c}")
    for c, n in sorted(gagnes.items()):
        if c not in (*CHAMPS, _COL_INFOS) and n:
            print(f"  {n:4} {c}")

    if not args.apply:
        print("\nSimulation — RIEN n'a été écrit. Ajouter --apply pour enregistrer.")
        conn.close()
        return 0

    # RÈGLE 6 : recompter en base plutôt que faire confiance à la boucle ci-dessus.
    reste = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE "
        "statut IN ('evaluated','published_cs','published_sub') AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 "
        "AND (COALESCE(recurring,0)=1 OR COALESCE(NULLIF(date_event_end,''), "
        "     NULLIF(date_event_start,''), '9999') >= ?) "
        f"AND ({_MANQUE})",
        (today,)).fetchone()[0]
    conn.close()
    # LIBELLÉ PRÉCIS, sinon deux compteurs se contredisent (2026-08-11, vu le soir même) :
    # ce nombre inclut les fiches dont l'image n'est qu'une BANNIÈRE, ce que
    # scripts/audit_incomplets.py ne compte pas — lui s'en tient aux champs vides de la
    # porte qualité. Le premier run a donc affiché 109 là où l'audit disait 95, sans que
    # rien n'ait empiré. Un compteur qui n'annonce pas ce qu'il compte fabrique une
    # fausse alerte, ce qui est exactement ce qu'on reproche aux files du back-office.
    print(f"\nIl reste {reste} fiche(s) à qui il manque un champ RÉCOLTABLE — bannière "
          f"comprise (une bannière compte comme une image manquante ici, pas dans "
          f"scripts/audit_incomplets.py, qui ne regarde que la porte qualité).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
