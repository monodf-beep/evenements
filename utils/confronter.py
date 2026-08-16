#!/usr/bin/env python3
"""CONFRONTER la fiche à la page officielle, au moment où la page est encore en mémoire.

Les trois derniers garde-fous du brief du 2026-08-12 (`docs/GARDE_FOUS_DATES_LIEUX_SOURCES.md`,
contrôles 2, 4 et 5) : ce sont les seuls qui exigent de RELIRE la source, donc les seuls qui
n'ont de sens qu'à l'enrichissement — `scripts/enrich.gather_material` vient de télécharger
la page, elle est là, il suffit de la regarder avant d'écrire.

  (a) `annee_dans_la_source`   — l'année de l'événement figure-t-elle dans le texte ?
  (b) `statut_source`          — l'URL répond-elle 200 au moment où on l'écrit ?
  (c) `bornes_contre_la_page`  — les quantièmes encadrant le nom du mois correspondent-ils
                                 aux bornes stockées ?

CE QUI A ÉTÉ APPRIS EN LES ÉCRIVANT, et qui change leur forme

Le brief attribuait 2289 et 2265 à une « borne de fin exclusive » dans `dates.py`. C'est
faux — `parse_dates` est strictement inclusif, `tests/test_bornes_inclusives.py` le prouve
sur les deux textes officiels cités. Le vrai mécanisme est que **la fiche n'a jamais été
datée depuis la page officielle** : la matière de 2289 est un extrait d'agrégateur qui écrit
lui-même « du 14 au 17 ». Le pipeline a transcrit fidèlement une source fausse.

D'où la forme de (c) : on ne cherche pas une erreur de calcul chez nous, on cherche un
DÉSACCORD entre deux textes. Et le désaccord qui compte a une signature très précise —
**même début, fin différente**. C'est celle de 2289 (14→18 contre 14→17) et de 2265 (4→8
contre 4→7). Un début commun prouve que les deux textes parlent du même événement ; c'est
ce qui rend la contradiction lisible au lieu d'être une coïncidence.

LA DOCTRINE, reprise de `scripts/verifier_dates.py` parce qu'elle a déjà été payée

**L'absence ne prouve rien.** Une page qui ne dit aucune date ne contredit aucune date. Le
2026-08-11, une file de 454 « points à contrôler » en comptait 315 qui n'étaient que les
silences de la source. Un texte muet est COMPTÉ, jamais LISTÉ — sinon on fabrique du travail
au lieu d'en désigner (CLAUDE.md règle 5), et le seul point qui compte se noie.

**Le désaccord flou ne prouve rien non plus.** Une page d'institution qui liste quinze
événements porte quinze plages ; qu'aucune ne soit la nôtre ne dit pas que la nôtre est
fausse, seulement que cette page ne parle pas que de nous. Compté, jamais listé.

**Aucun verdict n'est rendu sur un fait.** Le brief proposait aussi « aucun fait qui ne
figure pas dans la source ». Ce contrôle-là n'est PAS ici, et c'est délibéré : appliqué à la
fiche 2265, il aurait supprimé une foire équine, un défilé de carrosses et un feu
d'artifice — tous les trois écrits mot pour mot dans notre source, une newsletter de Turismo
Torino. Il aurait frappé en premier les fiches écrites depuis un dossier de presse, que la
charte §5 classe pourtant AU-DESSUS de la page officielle. On confronte des DATES, qui sont
comparables ; on ne confronte pas de la prose.

CE QUE ÇA NE FAIT PAS : ça n'écrit rien, ça ne corrige rien, ça ne rejette rien. Ça rend un
constat. Corriger d'office reviendrait à choisir entre deux sources sans savoir laquelle a
raison — et sur Terra Madre, c'est la source officielle qui se trompait, pas nous.

CE QUE LA MESURE SUR DONNÉES RÉELLES A CHANGÉ, le 2026-08-16

Passé sur la matière réellement collectée — 168 fiches publiées encore devant nous au sens
de la règle 5, description non vide, confrontées à leur PROPRE description stockée — (c)
rendait 36 `confirme`, 125 `muet` et **7 `contredit`**. Ces 7 lignes ne font que 4
événements (chaque fiche a son jumeau traduit), et **deux des quatre étaient faux** :

  • WP 14 / 3709 « Matisse – Yves Saint Laurent », 2026-06-17 → 09-28. La matière collectée
    est un item de newsletter qui parle du **Nice Classic Festival**, « du 21 juillet au
    09 août 2026 ». Une seule plage dans le texte, et elle n'a rien à voir avec la fiche ;
  • WP 6969 / 7193 « Achille Lauro », 2026-11-12. Le corps annonce les Nitto ATP Finals
    « dal 15 al 22 novembre » — le TOURNOI qui contient notre soirée, pas notre soirée. La
    fiche est juste : le texte écrit « giovedì 12 novembre alle ore 21 », noir sur blanc.

La règle fautive était « une seule plage dans le texte → aucune ambiguïté possible sur ce
dont il parle ». C'est faux, et pour une raison de fond : **notre matière n'est presque
jamais une page d'événement.** C'est un item de newsletter, un article de presse, un billet
d'agrégateur — des textes qui citent couramment la plage d'un ÉVÉNEMENT VOISIN, celui d'à
côté dans la lettre ou celui qui contient le nôtre. Le nombre de plages ne dit rien ; seul
un **ancrage** dit que deux textes parlent du même événement.

D'où la forme définitive de (c) : on ne nomme un désaccord que si les deux textes partagent
une BORNE — même début (2289, 2265, 6382) ou même fin (1856). Sans borne commune, la page
est comptée, jamais listée, quel que soit le nombre de plages qu'elle porte. Et un jour
isolé écrit hors de toute plage (« giovedì 12 novembre ») CONFIRME une fiche d'un seul
jour : c'est ce qui distingue 6969, qui est juste, de 6382, qui ne l'est pas.

Le seul vrai défaut du lot est d'ailleurs celui-là : **une plage annoncée dans le texte peut
s'effondrer sur son seul jour de début.** WP 6382, Earthink Festival — « Dal 27 agosto al
12 settembre 2026 » dans notre propre matière, `2026-08-27 → 2026-08-27` en base,
`date_source='manuel'`. Il a son verdict à lui, parce que le geste au bout n'est pas le même
qu'un désaccord de bornes : il n'y a pas à choisir entre deux dates, il y a une fin à aller
chercher.
"""
from __future__ import annotations

import re
from datetime import date

from scripts.dates import _MONTH_RE, _MONTHS, _iso, _strip, _year

# Les verdicts qui se LISENT (il y a un geste au bout) et ceux qui se COMPTENT.
CONTREDIT = "contredit"      # deux textes, deux dates, et une borne commune prouve qu'ils
                             # parlent du même événement
EFFONDREE = "effondree"      # le texte annonce une plage, la fiche ne garde que son premier
                             # jour. Séparé de CONTREDIT parce que le geste diffère : rien à
                             # arbitrer, une fin à aller chercher (WP 6382, Earthink)
ABSENTE = "absente"          # la page date d'autres années, jamais la nôtre
CONFIRME = "confirme"        # la page dit ce que nous disons
MUET = "muet"                # la page ne dit rien là-dessus → ne prouve rien
AMBIGU = "ambigu"            # la page porte des dates, mais AUCUNE borne commune avec la
                             # fiche : rien ne prouve qu'elle parle de notre événement
                             # (l'item de newsletter d'à côté, le tournoi qui nous contient)

A_LIRE = (CONTREDIT, EFFONDREE, ABSENTE)


# ─────────────────────────────────────────────────────────────────────────────
# (c) LES BORNES
# ─────────────────────────────────────────────────────────────────────────────

# Plage dans un SEUL mois : « du 14 au 18 juillet 2026 », « Dal 4 all'8 luglio », « 5 e 6
# luglio ». Un mot toléré après le lien (« du samedi 5 au dimanche 6 juillet »).
_PLAGE_1MOIS = re.compile(
    rf"(?:du|dal|dall'|dall’|da)?\s*(?<!\d)(\d{{1,2}})(?!\d)\s*"
    rf"(?:au|al|all'|all’|et|e|&|[-–—à])\s*(?:[a-zà-ÿ]+\s+)?(?<!\d)(\d{{1,2}})(?!\d)\s+"
    rf"({_MONTH_RE})\.?\s*(\d{{4}})?")

# Plage à cheval sur deux mois : « du 30 juin au 3 juillet 2026 ».
_PLAGE_2MOIS = re.compile(
    rf"(?:du|dal|dall'|dall’|da)\s*(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?\s*"
    rf"(?:au|al|all'|all’)\s*(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?")

# Un jour ÉCRIT SEUL : « giovedì 12 novembre alle ore 21 ». Même motif que la 5ᵉ passe de
# `dates.parse_dates`, à une condition près qui fait tout : on ne le retient que s'il tombe
# HORS de toute plage déjà lue — sinon le « 12 settembre » de « dal 27 agosto al 12
# settembre » compterait comme une date isolée, et l'effondrement de 6382 passerait pour
# une fiche corroborée.
_JOUR_SEUL = re.compile(rf"(?<!\d)(\d{{1,2}})(?!\d)\s+({_MONTH_RE})\.?\s*(\d{{4}})?")


def plages_du_texte(texte: str, ref: date) -> set[tuple[str, str]]:
    """TOUTES les plages (début, fin) lisibles dans un texte, en ISO.

    Volontairement différent de `dates.parse_dates`, qui rend LA date — la première qui
    accroche un motif. Ici on veut l'inventaire, parce que la question n'est pas « quelle
    plage ? » mais « la nôtre y est-elle ? ».

    ⚠️ Le NOMBRE de plages ne dit rien de la valeur de preuve du texte — c'était l'erreur
    du 2026-08-13, corrigée le 16 sur mesure (cf. l'en-tête du module) : un texte qui n'en
    porte qu'une seule peut parfaitement parler d'un autre événement que le nôtre. Le
    nombre ne sert plus qu'à une chose, dire combien de cas se sont présentés.

    Même choix que `verifier_dates.dates_du_texte`, et pour la même raison : `ref` est la
    date de COLLECTE de la fiche, pas aujourd'hui — c'est le fait connu auquel on accroche
    l'année sous-entendue.
    """
    return _plages_et_spans(texte, ref)[0]


def _plages_et_spans(texte: str, ref: date) -> tuple[set[tuple[str, str]], list[tuple[int, int]]]:
    """Les plages, ET l'empan de texte que chacune occupe — c'est l'empan qui permet
    ensuite de reconnaître un jour écrit SEUL (`jours_isoles`)."""
    t = _strip(texte or "")
    trouvees: set[tuple[str, str]] = set()
    spans: list[tuple[int, int]] = []

    for m in _PLAGE_2MOIS.finditer(t):
        d1, mon1, y1, d2, mon2, y2 = (int(m[1]), _MONTHS[m[2]], m[3],
                                      int(m[4]), _MONTHS[m[5]], m[6])
        # Même propagation d'année que dates.py : si UNE SEULE borne la porte, on la
        # propage plutôt que de la deviner — sinon on fabrique une plage de deux ans.
        if y1 and y2:
            yy1, yy2 = int(y1), int(y2)
        elif y2 and not y1:
            yy2 = int(y2)
            yy1 = yy2 if mon1 <= mon2 else yy2 - 1
        elif y1 and not y2:
            yy1 = int(y1)
            yy2 = yy1 if mon2 >= mon1 else yy1 + 1
        else:
            yy1 = _year(d1, mon1, ref)
            yy2 = yy1 if mon2 >= mon1 else yy1 + 1
        s, e = _iso(yy1, mon1, d1), _iso(yy2, mon2, d2)
        if s and e:
            trouvees.add((min(s, e), max(s, e)))
            spans.append(m.span())

    for m in _PLAGE_1MOIS.finditer(t):
        d1, d2, mon, yr = int(m[1]), int(m[2]), _MONTHS[m[3]], m[4]
        y = int(yr) if yr else _year(min(d1, d2), mon, ref)
        s, e = _iso(y, mon, d1), _iso(y, mon, d2)
        if s and e:
            trouvees.add((min(s, e), max(s, e)))
            spans.append(m.span())

    return trouvees, spans


def jours_isoles(texte: str, ref: date) -> set[str]:
    """Les jours écrits SEULS, hors de toute plage — « giovedì 12 novembre alle ore 21 ».

    LE CAS QUI L'A DICTÉ, WP 6969 « Achille Lauro » : le corps annonce les Nitto ATP Finals
    « dal 15 al 22 novembre », et notre soirée le 12. Sans cette lecture, la plage du
    tournoi qui nous contient ressemble à une contradiction ; avec elle, le texte dit
    lui-même que la fiche a raison.

    L'empan compte plus que le motif : un jour PRIS DANS une plage n'est pas un jour isolé,
    sinon « dal 27 agosto al 12 settembre » corroborerait n'importe quelle fiche datée du
    12 septembre — et couvrirait l'effondrement de 6382, qu'on cherche précisément à voir.

    CE QUE ÇA NE PROUVE PAS : que l'événement tient en un jour. Ça prouve que la source
    nomme NOTRE jour. WP 915 en donne la limite, vue à la mesure du 16/08 : « du 12 jun au
    26 septembre 2026 » — « jun » n'est pas un mois lisible, la plage n'est donc pas lue, le
    « 26 septembre » passe pour un jour isolé et la fiche d'un jour est confirmée à tort.
    C'est un raté, pas un faux signalement, et c'est l'arbitrage assumé ici : mieux vaut
    laisser passer que fabriquer du travail (CLAUDE.md règle 6).
    """
    t = _strip(texte or "")
    spans = _plages_et_spans(texte, ref)[1]
    jours: set[str] = set()
    for m in _JOUR_SEUL.finditer(t):
        if any(a <= m.start() and m.end() <= b for a, b in spans):
            continue
        if any(a < m.end() and m.start() < b for a, b in spans):
            continue          # chevauchement partiel : on ne tranche pas, on s'abstient
        d, mon, yr = int(m[1]), _MONTHS[m[2]], m[3]
        y = int(yr) if yr else _year(d, mon, ref)
        iso = _iso(y, mon, d)
        if iso:
            jours.add(iso)
    return jours


def bornes_contre_la_page(debut: str, fin: str, texte: str, ref: date) -> dict:
    """(c) Nos bornes tiennent-elles devant le texte de la page ?

    Rend {"verdict", "motif", "plages"} — `plages` est le nombre de plages lues, pour que
    le compteur d'en face puisse dire si un zéro vient d'une page muette ou d'une requête
    vide (CLAUDE.md, journal des erreurs : « un zéro ne dit pas s'il vient d'un échec ou
    d'une absence de cas »).

    L'ORDRE DES TESTS EST LE FOND DU SUJET, pas un détail d'implémentation. Il ne tient
    qu'à une question : **qu'est-ce qui prouve que ce texte parle de NOTRE événement ?**
    Une borne commune le prouve ; le fait qu'il ne porte qu'une date, non (mesuré le
    2026-08-16 sur 168 fiches, deux faux signalements sur quatre — voir l'en-tête).

      1. la page porte NOTRE plage → confirmé, on ne cherche pas plus loin ;
      2. la fiche tient sur UN SEUL jour et la page écrit ce jour-là SEUL, hors de toute
         plage → confirmé. La plage voisine qu'elle porte par ailleurs est celle d'un autre
         événement, souvent celui qui contient le nôtre (6969, les ATP Finals) ;
      3. la page porte une plage de MÊME DÉBUT, et notre fin est notre début → effondrée.
         Il n'y a pas deux dates à départager : notre fin manque (6382) ;
      4. la page porte une plage de MÊME DÉBUT et une autre fin → contredit. Le début
         commun prouve que les deux textes parlent du même événement, la fin diffère, il
         faut aller lire. 2289 et 2265 ;
      5. symétriquement, MÊME FIN et un autre début → contredit (1856 « Jazz Art », que
         notre matière date du 16 juillet et la fiche du 13 mai) ;
      6. des plages, mais aucune borne commune → ambigu. Rien ne dit que ce texte parle de
         nous : compté, jamais listé ;
      7. aucune plage → muet.
    """
    debut, fin = (debut or "").strip()[:10], (fin or "").strip()[:10]
    if not debut:
        return {"verdict": MUET, "motif": "", "plages": 0}
    fin = fin or debut
    plages, _ = _plages_et_spans(texte, ref)
    n = len(plages)

    if (debut, fin) in plages:
        return {"verdict": CONFIRME, "motif": "", "plages": n}

    if debut == fin and debut in jours_isoles(texte, ref):
        return {"verdict": CONFIRME, "motif": "", "plages": n}

    memes_debuts = sorted(e for s, e in plages if s == debut and e != fin)
    if memes_debuts and debut == fin:
        return {"verdict": EFFONDREE, "plages": n,
                "motif": (f"la source annonce {debut} → {memes_debuts[0]}, la fiche "
                          f"s'arrête à son seul jour de début ({debut}) : la fin manque")}
    if memes_debuts:
        return {"verdict": CONTREDIT, "plages": n,
                "motif": (f"la source annonce {debut} → {memes_debuts[0]}, "
                          f"la fiche dit {debut} → {fin} (même début, fin différente)")}

    memes_fins = sorted(s for s, e in plages if e == fin and s != debut)
    if memes_fins:
        return {"verdict": CONTREDIT, "plages": n,
                "motif": (f"la source annonce {memes_fins[0]} → {fin}, "
                          f"la fiche dit {debut} → {fin} (même fin, début différent)")}

    if n:
        return {"verdict": AMBIGU, "motif": "", "plages": n}
    return {"verdict": MUET, "motif": "", "plages": 0}


# ─────────────────────────────────────────────────────────────────────────────
# (a) L'ANNÉE
# ─────────────────────────────────────────────────────────────────────────────

_ANNEE = re.compile(r"\b(19|20)\d{2}\b")


def annee_dans_la_source(debut: str, texte: str) -> dict:
    """(a) L'année de l'événement figure-t-elle dans le texte de la source ?

    LE CAS QUI L'A DICTÉ, 2319 « Ah ! La Belle Saison » : la page du Théâtre des Collines
    ne mentionne QUE 2025 (« belle saison 2025, 7ème édition »), et la fiche annonçait
    juin-juillet 2026. L'année n'avait pas été lue, elle avait été supposée.

    ⚠️ CE CONTRÔLE NE PEUT PAS ÊTRE UN VERDICT, et le brief le dit lui-même : trois fiches
    sourcées sur `visitmondovi.it` décrivent des événements récurrents sur des pages
    permanentes qui ne portent AUCUNE année. La source est parfaitement légitime, elle ne
    confirme simplement pas la date.

    D'où la séparation, qui est tout l'intérêt de la fonction :
      • la page porte d'autres années mais pas la nôtre → `absente`, il y a un geste au bout ;
      • la page ne porte aucune année → `muet`, il n'y a rien à faire et rien à afficher.
    Confondre les deux, c'est refabriquer la file de 454 points dont 315 étaient des silences.
    """
    debut = (debut or "").strip()
    if len(debut) < 4:
        return {"verdict": MUET, "motif": "", "annees": []}
    notre = debut[:4]
    annees = sorted({m.group() for m in _ANNEE.finditer(texte or "")})
    if not annees:
        return {"verdict": MUET, "motif": "", "annees": []}
    if notre in annees:
        return {"verdict": CONFIRME, "motif": "", "annees": annees}
    return {"verdict": ABSENTE, "annees": annees,
            "motif": (f"la source ne cite jamais {notre} ; elle porte "
                      f"{', '.join(annees[:4])}")}


# ─────────────────────────────────────────────────────────────────────────────
# (b) L'URL
# ─────────────────────────────────────────────────────────────────────────────

# Ces schémas ne SONT pas des pages : les interroger en HTTP n'a aucun sens, et compter
# leur « échec » ferait un compteur qui ment sur son périmètre (CLAUDE.md règle 6).
_PAS_UNE_PAGE = ("gmail:", "translated:", "mailto:")


def statut_source(url: str, get=None, timeout: int = 8) -> dict:
    """(b) L'URL de source répond-elle, au moment même où on l'écrit ?

    LE CAS QUI L'A DICTÉ, 909 « Chopin » à l'Opéra de Nice : l'URL a la forme
    `/agenda/chopin/20260918-1800/`, c'est-à-dire entièrement dérivable des données de
    l'événement lui-même. Tout indique qu'elle a été construite par motif plutôt que
    relevée ; elle répond 404 et n'a, semble-t-il, jamais été ouverte.

    TROIS ÉTATS, PAS DEUX, et c'est la seule chose qui compte ici :
      • `absente`     — le serveur a répondu, et il a répondu 4xx. La page n'existe pas.
      • `injoignable` — rien n'a répondu (DNS, réseau, délai). On ne sait RIEN : ça peut
        être notre VPS, un pare-feu, une coupure d'une minute. Ne jamais retirer une source
        là-dessus ;
      • `non_page`    — `gmail:`, `translated:` … il n'y a pas d'URL à interroger.

    Les confondre produirait exactement la faute de la règle 1 transposée aux sources :
    conclure à la mort d'une chose qu'on n'a pas su joindre.
    """
    url = (url or "").strip()
    if not url or url.startswith(_PAS_UNE_PAGE) or "news.google.com" in url:
        return {"verdict": "non_page", "code": None, "motif": ""}
    if get is None:
        import requests
        def get(u):  # noqa: E306
            return requests.get(u, timeout=timeout, allow_redirects=True,
                                headers={"User-Agent": "Mozilla/5.0 (compatible; AgendaSabauda/1.0)"})
    try:
        r = get(url)
    except Exception as exc:  # noqa: BLE001 — toute panne réseau vaut « on ne sait pas »
        return {"verdict": "injoignable", "code": None,
                "motif": f"aucune réponse ({type(exc).__name__})"}
    code = getattr(r, "status_code", None)
    if code == 200:
        return {"verdict": CONFIRME, "code": 200, "motif": ""}
    if code and 400 <= code < 500:
        return {"verdict": ABSENTE, "code": code,
                "motif": f"la source répond {code} au moment de l'écriture"}
    return {"verdict": "injoignable", "code": code,
            "motif": f"la source répond {code}" if code else "aucune réponse"}


# ─────────────────────────────────────────────────────────────────────────────
# L'AGRÉGAT
# ─────────────────────────────────────────────────────────────────────────────

def confronter(ev: dict, texte_source: str, ref: date | None = None,
               verifier_url: bool = True, get=None) -> dict:
    """Les trois contrôles d'un coup, sur la page DÉJÀ en mémoire.

    Rend un constat sérialisable, destiné à `enrich_data['confrontation']` :

        {"a_lire": bool,          # au moins un verdict qui demande une lecture humaine
         "motifs": [str, ...],    # ce qu'on dirait à Franck, en français
         "bornes": {...}, "annee": {...}, "source": {...}}

    `a_lire` est FAUX quand tout est confirmé ET quand tout est muet : dans les deux cas il
    n'y a pas de geste au bout. Les verdicts muets et ambigus restent dans le constat pour
    que le compteur puisse dire combien de cas se sont présentés — un « 0 contradiction »
    doit pouvoir se distinguer d'un « 0 page lue ».
    """
    ref = ref or _ref_de_collecte(ev)
    texte = texte_source or ""
    bornes = bornes_contre_la_page(ev.get("date_event_start", ""),
                                   ev.get("date_event_end", ""), texte, ref)
    annee = annee_dans_la_source(ev.get("date_event_start", ""), texte)
    source = ({"verdict": "non_verifie", "code": None, "motif": ""} if not verifier_url
              else statut_source(ev.get("url_source", ""), get=get))
    motifs = [c["motif"] for c in (bornes, annee, source)
              if c.get("verdict") in A_LIRE and c.get("motif")]
    return {"a_lire": bool(motifs), "motifs": motifs,
            "bornes": bornes, "annee": annee, "source": source}


def _ref_de_collecte(ev: dict) -> date:
    """La date de COLLECTE de la fiche, ou aujourd'hui à défaut. Jamais « aujourd'hui »
    par commodité : c'est elle qui sert à deviner l'année sous-entendue d'un texte, et
    une page lue six mois après la collecte ne se lit pas avec l'horloge d'aujourd'hui."""
    brut = (ev.get("scrape_date") or "").strip()[:10]
    try:
        return date.fromisoformat(brut)
    except ValueError:
        return date.today()
