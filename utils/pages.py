#!/usr/bin/env python3
"""Qu'est-ce qu'une PAGE D'ÉVÉNEMENT — et ce qu'on a le droit d'en tirer.

Un seul endroit pour une question que trois modules se posaient séparément : la page
que la base a mémorisée parle-t-elle de CET événement, ou est-ce une page d'accueil,
une rubrique presse, une page « nos artistes » ? De la réponse dépendent le lien
« source » montré au lecteur (`scripts/affiner_source.py`) et le droit d'y prendre une
image (`scripts/visuals.py`, `scripts/moisson_officielle.py`, `scripts/images_wide.py`).

Ce module existe parce que la réponse vivait dans UN module et manquait aux voisins —
la racine du 08/09, « deux détecteurs pour la même chose, un seul juste »
(docs/ERREURS_2026-09-08.md). La liste des rubriques était née dans `affiner_source`
(premier dry-run du 08/09 : sur 37 propositions, une douzaine étaient des pages presse
ou actualités) ; la chaîne d'images ne l'a jamais lue.

CE QUI A ÉTÉ MESURÉ LE 2026-09-21, sur les 22 pages RACINE servant de source à des
fiches publiées encore devant nous : NEUF portaient un og:image, et pas une seule ne
montrait l'événement. On y trouvait le fond de la page de connexion admin du musée du
Risorgimento (`backend-login-bg-01.jpg`), l'affiche de saison 25-26 de la MAL de Thonon
— périmée d'un an —, le logo du Conservatoire de Turin, l'image de partage Facebook de
Bonlieu, la façade de Palazzo Madama. Et trois mois plus tôt, la même balise du musée du
Risorgimento portait l'affiche d'une exposition de MARS : c'est le fond du problème, une
page d'accueil illustre la programmation du moment, donc au mieux un AUTRE événement.
Aucun de ces 22 sites n'était lui-même l'événement.

Pas dans `utils/sources.py` : ce fichier-là est synchronisé avec
observatoire-business-sabaudo et ses divergences se paient à chaque reprise.
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

# Chemins qui ne sont JAMAIS la page d'un événement : rubrique presse, actualités, appel
# aux dons, galerie, contact.
RUBRIQUES_NON_EVENEMENT = (
    "press", "presse", "stampa", "comunicat", "news", "notizie", "actualit",
    "attualita", "blog", "soutenir", "soutien", "sostieni", "sostenere", "donazion",
    "mecenat", "newsletter", "contact", "gallery", "galleria", "/pro/",
    # Ajouté le 2026-09-21 sur mesure : mal-thonon.org/scolaires est la source de QUATRE
    # fiches publiées à venir (Charlie Winston, Mathias Lévy, James Carter, Thomas
    # Bernhard). C'est la page « séances scolaires » du théâtre, pas celle du spectacle.
    "scolaire", "scuole")

# Mots de titre trop généraux pour reconnaître un domaine (même liste qu'enrich).
_TITRE_STOP = frozenset((
    "festival", "concert", "spectacle", "exposition", "salon", "foire", "fete",
    "edition", "saison", "rencontres", "journees"))


def _fold(s: str) -> str:
    """Minuscule sans accents — pour comparer un mot de titre à un domaine désaccentué."""
    return "".join(c for c in unicodedata.normalize("NFKD", (s or "").lower())
                   if not unicodedata.combining(c))


def est_racine(url: str) -> bool:
    """Vrai si l'URL est la racine d'un site (chemin vide ou « / »)."""
    u = (url or "").strip()
    return u.startswith("http") and not urlparse(u).path.strip("/")


def est_page_generique(url: str) -> bool:
    """Vrai si l'URL ne peut pas être la page d'un événement : racine, ou rubrique.

    Le test des rubriques porte sur la SOUS-CHAÎNE du chemin : c'est ce qu'exige
    « /it/cartellastampa-comunicatistampa/ » (Torino Film Festival), où « stampa » n'est
    pas un segment. Un slug d'événement qui contiendrait « presse » ou « news » serait
    donc pris pour une rubrique — limite connue, bornée par les appelants : le rouvreur
    de sources ne remplace rien sans meilleure page, et la chaîne d'images se contente de
    descendre d'un étage."""
    u = (url or "").strip()
    if not u.startswith("http"):
        return False
    return est_racine(u) or any(sk in _fold(urlparse(u).path)
                                for sk in RUBRIQUES_NON_EVENEMENT)


def site_est_evenement(url: str, titre: str) -> bool:
    """Vrai si le SITE est l'événement — TOUS les mots significatifs du titre sont dans le
    nom de domaine (doujador.it ↔ « Douja d'Or », beercult.it ↔ « BeerCult 2026 »). Sa
    page d'accueil est alors la page de l'événement, et son og:image la bonne affiche.
    Les millésimes et ordinaux ne comptent pas : un domaine ne les porte presque jamais
    (même écartement que `scripts/affiner_source.page_evenement_depuis_racine`).

    EXIGEANTE EXPRÈS, et la limite est connue : un titre RÉDIGÉ — « BeerCult 2026 à Aoste :
    trois jours entre bière alpine et Marché européen » — n'a aucune chance de tenir dans
    un domaine, donc l'exception ne joue pas pour lui et l'image de la page d'accueil est
    refusée comme pour n'importe quel site. Deux raisons de l'assumer plutôt que d'assouplir
    (mesuré le 2026-09-21) : sur les 22 racines du catalogue à venir, AUCUNE n'était un
    site-événement et les neuf og:image trouvées étaient toutes de l'habillage — le coût
    réel du refus était donc nul ce jour-là ; et un critère plus large (« un mot long du
    titre dans le domaine ») réautorise précisément les cas qu'on veut bloquer, parce que
    le domaine porte le nom du LIEU ou de la VILLE : « Risorgimento » dans
    museorisorgimentotorino.it, « Thonon » dans mal-thonon.org — dont l'og:image est
    l'affiche de la saison 25-26, périmée d'un an. Un lieu n'est pas un événement.

    Le chemin propre pour ces fiches n'est pas d'assouplir ce test : c'est de préciser
    leur source (`scripts/affiner_source.py`), et la chaîne reprend alors l'og:image de la
    vraie page de l'événement."""
    host = _fold(urlparse((url or "").strip()).netloc)
    if not host:
        return False
    toks = [w for w in re.findall(r"[a-z0-9]+", _fold(titre))
            if len(w) > 3 and w not in _TITRE_STOP
            and not re.fullmatch(r"\d+[a-z]{0,4}|[xivl]+e", w)]
    return bool(toks) and all(t in host for t in toks)


def peut_illustrer(url: str, titre: str) -> bool:
    """L'image trouvée sur cette page se suffit-elle à elle-même pour illustrer CET
    événement ? Non pour une page générique — sauf si le site EST l'événement.

    CE QUE « NON » VEUT DIRE, ET CE QU'IL NE VEUT PAS DIRE (corrigé le 2026-09-21, dans
    la journée). La première version de cette fonction servait à REFUSER ces pages. En
    regardant ensuite les cinq fiches publiées que ce refus visait, trois avaient une
    BONNE image : l'affiche exacte de l'exposition, prise sur la page d'accueil de la
    mairie de Villefranche-sur-Mer, et la chapelle des Scrovegni pour un cours sur
    « huit lieux qui ont changé l'histoire de l'art », prise sur celle de Palazzo Madama.

    Les deux mesures du jour sont vraies, et c'est ce qui rend le cas intéressant : un
    INSTANTANÉ des og:image de ces racines n'en montrait aucune de bonne (fond de page
    admin, affiche de saison périmée d'un an, logo, façade), parce qu'une page d'accueil
    montre la programmation DU MOMENT — donc elle illustre bien l'événement en cours, et
    mal tous les autres. Mesurer l'instant ne pouvait pas le dire ; il fallait regarder
    les fiches.

    D'où la répartition, selon que l'appelant a un JUGE ou non :
      • `scripts/visuals.py` a l'agent vision → il lit ces pages quand même, et l'agent
        tranche (c'est précisément son travail : « cette image montre-t-elle CET
        événement ? ») ;
      • `scripts/moisson_officielle.py` n'a aucune vérification vision → il s'abstient ;
      • `scripts/images_wide.py` en a une, mais elle a validé le même jour une brochure de
        saison comme « affiche portrait » et un plan de salle comme « affiche paysage » →
        il s'abstient aussi, tant qu'elle n'est pas plus sûre.

    Un « non » n'est donc jamais un cul-de-sac (règle 3) : l'appelant descend d'un étage —
    Commons, agent web, puis la bannière territoire, neutre. Et le jour où la source est
    précisée (`scripts/affiner_source.py` remplace la racine par la page du spectacle), la
    même chaîne reprend l'og:image, cette fois la bonne."""
    return not est_page_generique(url) or site_est_evenement(url, titre)
