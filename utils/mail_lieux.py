#!/usr/bin/env python3
"""Le LIEU et la VILLE d'une fiche venue d'un mail, lus dans le corps du mail — sans deviner.

D'OÙ ÇA VIENT (2026-09-08). Parmi les 108 fiches approuvées, à venir et incomplètes de la
file « À compléter », une vingtaine viennent d'une newsletter SANS AUCUN lien d'article :
leur adresse est « gmail:<message_id>#<rang> », et `gmail_relink` n'a rien trouvé à
rattacher. Pour elles il n'y a pas de page à lire : la seule matière est le mail. La date
est déjà servie par `scripts/dates_depuis_mail.py` ; il manque surtout l'IMAGE (toutes),
souvent la VILLE ou le LIEU. Franck : « les scripts travaillent au max » avant tout agent
payant.

CE MODULE NE DEVINE RIEN — c'est la doctrine d'`utils/lieux.py`, reprise mot pour mot : sur
un texte écrit pour des humains on ne peut pas EXTRAIRE, on ne peut que CONFIRMER à partir
d'un fait qu'on tient déjà. Trois faits sont tenus, et rien d'autre :

  ① LES LIEUX CONNUS — `utils.lieux.registre()` (notes de savoir + arbitrages de
    `config/lieux_villes.json`) et les lieux par défaut des sources officielles
    (`config/sources.txt`, colonnes lieu;ville — les mêmes que `venues.apply_source_venues`).
    Un lieu connu nommé dans le texte de l'annonce → lieu ET ville, puisque le registre
    déclare la ville. On écrit le nom TEL QUE LE MAIL L'ÉCRIT, pas la forme pliée.
  ② LES COMMUNES DU PÉRIMÈTRE — `utils.lieux.communes()` (784 noms, quatre territoires).
    Une commune nommée dans le texte de l'annonce → ville seule.
  ③ LES LIEUX DE NOTRE PROPRE BASE (fourni par l'appelant) — un lieu que nos fiches
    connaissent DANS LA VILLE que le texte nomme → lieu, en plus de la ville. Jamais
    l'inverse : on ne déduit pas la ville d'un nom de lieu lu en base, parce qu'un
    « Musée des Beaux-Arts » existe à Chambéry ET à Nice. La base sert à confirmer, pas
    à trancher.

CE QU'IL REFUSE, et pourquoi — chaque refus vient d'une mesure faite le jour même :

  • 26 des 784 noms de communes sont aussi des MOTS COURANTS : « la salle », « verres »,
    « contes », « la chapelle », « la table », « saint pierre »… « la salle des fêtes »
    donnerait La Salle (Vallée d'Aoste), « Contes pour enfants » donnerait Contes (06).
    Donc la commune doit être écrite avec sa MAJUSCULE dans le texte d'origine — un nom
    propre — et les mots-pièges les plus courts ou les plus fréquents exigent en plus un
    marqueur de lieu devant eux (« à », « in », une virgule, un code postal…) ;
  • un nom de commune qui fait partie d'un NOM DE BÂTIMENT n'est pas une adresse :
    « église Saint-Pierre » n'est pas à Saint-Pierre, « Café de Turin » est à Nice (le
    cas fondateur d'`utils/lieux.py`). Refusé quand un mot de bâtiment le précède,
    directement ou via « de/di/della » ;
  • DEUX communes différentes dans la même annonce → rien. « Entre Colmars et
    Saint-Martin-d'Entraunes » ne se départage pas ici ;
  • le texte lu est celui de L'ANNONCE, pas du mail : la fenêtre part du titre de la
    fiche et s'arrête au titre de l'annonce voisine (les autres fiches du même mail,
    quel que soit leur statut) — c'est la borne de `utils/mail_dates.py`, réutilisée et
    non réécrite. Sans elle, l'annonce d'à côté prête sa ville, en silence ;
  • les adresses web du corps sont retirées avant lecture : « https://www.nice.fr/… »
    contient « nice » en mot entier.

Un texte muet rend un dict vide, et c'est le résultat qu'on préfère : une fiche sans ville
reste réparable, une fiche avec la ville du voisin envoie quelqu'un au mauvais endroit.
"""
from __future__ import annotations

import re
import unicodedata

from utils import lieux as _lieux
from utils.mail_dates import _FENETRE, _TITRE_MIN, _norm, _positions

# Mots du texte qui ne sont pas des noms propres même dans un nom de commune : on
# n'exige pas leur majuscule (« Saint-Martin-de-Belleville » s'écrit avec « de »).
_PARTICULES = frozenset((
    "de", "du", "des", "d", "la", "le", "les", "l", "sur", "sous", "en", "et", "aux", "au",
    "di", "del", "della", "dei", "degli", "delle", "da", "in", "san", "sant", "santa",
    "santo", "saint", "sainte", "st", "ste", "a", "e", "lo", "gli", "i",
))

# Ce qui précède un nom de commune quand celui-ci est en fait un morceau de NOM DE
# BÂTIMENT : « église Saint-Pierre », « Théâtre de Nice », « Forte di Bard ». Le premier
# n'est pas à Saint-Pierre ; les deux autres sont bien à Nice et à Bard, mais « Café de
# Turin » est à Nice — on ne sait pas les distinguer ici, donc on ne tranche pas, et la
# ville viendra d'une AUTRE mention du texte (« à Nice ») ou ne viendra pas.
_BATIMENTS = frozenset((
    "eglise", "chapelle", "cathedrale", "basilique", "abbaye", "prieure", "monastere",
    "collegiale", "temple", "rue", "avenue", "place", "boulevard", "chemin", "quai",
    "route", "allee", "impasse", "square", "college", "ecole", "lycee", "hopital", "gare",
    "quartier", "pont", "fort", "chateau", "musee", "theatre", "salle", "hotel", "cafe",
    "cinema", "stade", "parc", "jardin", "domaine", "tour", "porte", "cours", "esplanade",
    "chiesa", "via", "piazza", "corso", "basilica", "cattedrale", "duomo", "santuario",
    "abbazia", "castello", "forte", "museo", "teatro", "sala", "palazzo", "villa", "torre",
    "porta", "ponte", "stazione", "ospedale", "scuola", "liceo", "parco", "giardino",
    "viale", "largo", "vicolo", "strada", "borgo", "cascina",
))
_LIENS_BATIMENT = frozenset(("de", "du", "des", "d", "di", "del", "della", "dei", "degli",
                             "delle", "da", "la", "le", "l"))

# Mots courants qui sont AUSSI des communes du périmètre (mesuré le 2026-09-08 : 26 sur
# 784, liste ci-dessous non exhaustive mais couvrant les plus fréquents dans une
# newsletter culturelle). Pour eux la majuscule ne suffit pas — « Contes pour enfants »,
# « Vers 18h », « La Salle est ouverte » portent la majuscule en début de titre ou de
# phrase — on exige en plus un MARQUEUR DE LIEU juste devant.
_PIEGES = frozenset((
    "contes", "vers", "drap", "tende", "verres", "la salle", "la table", "la tour",
    "la chapelle", "les marches", "la motte", "le noyer", "le bois", "les deserts",
    "la compote", "le bourget", "la baume", "la balme", "la cote", "les clefs", "la penne",
    "la trinite", "le pontet", "le reposoir", "la chambre", "les echelles", "saint pierre",
    "saint jean", "saint martin", "saint paul", "saint andre", "saint michel", "saint marcel",
    "saint nicolas", "saint vincent", "saint clair", "saint maurice", "saint christophe",
    "none", "monte", "riva", "castello", "villar", "torre", "fontaine", "bourg", "roure",
    "moye", "hone", "eze", "ayn", "alex", "mery", "seez", "susa", "asti", "ceva", "cusy",
    "giez", "motz", "viry", "ayse", "bard",
))
_MARQUEURS_AVANT = frozenset(("a", "in", "ad", "au", "aux", "de", "di", "da", "sur", "pres",
                              "vers", "direction", "commune", "comune", "ville", "citta",
                              "mairie", "municipio", "village", "villaggio", "cp"))
_MIN_VILLE = 3          # « Èze » (Comté de Nice) fait trois lettres, et c'est une commune


def carte_norm(texte: str) -> tuple[str, list[int]]:
    """La forme normalisée de `utils.mail_dates._norm`, PLUS l'index d'origine de chacun
    de ses caractères — pour revenir du texte plié au texte écrit (majuscules, accents).

    Reproduit `_norm` pas à pas (NFKD, sans accents, minuscules, un seul espace pour toute
    suite de non-alphanumériques, sans bords) : la fixture vérifie l'ÉGALITÉ des deux
    sorties sur chaque mail d'essai. Un seul localisateur de titre (`_positions`) pour la
    date et pour le lieu, donc une seule normalisation."""
    texte = texte or ""
    chars: list[str] = []
    orig: list[int] = []
    for i, c in enumerate(texte):
        for d in unicodedata.normalize("NFKD", c):
            if unicodedata.combining(d):
                continue
            for e in d.lower():
                chars.append(e)
                orig.append(i)
    out: list[str] = []
    out_idx: list[int] = []
    dans_run = False
    for ch, o in zip(chars, orig):
        if re.fullmatch(r"[a-z0-9]", ch):
            out.append(ch)
            out_idx.append(o)
            dans_run = False
        elif not dans_run:
            out.append(" ")
            out_idx.append(o)
            dans_run = True
    # strip()
    debut = 0
    while debut < len(out) and out[debut] == " ":
        debut += 1
    fin = len(out)
    while fin > debut and out[fin - 1] == " ":
        fin -= 1
    return "".join(out[debut:fin]), out_idx[debut:fin]


def sans_urls(texte: str) -> str:
    """Retire les adresses web du corps — celles que `gmail_collect._linkify_html` a
    gardées entre parenthèses, et les nues. Leur slug contient des noms de communes."""
    t = re.sub(r"\(\s*https?://[^\s)]+\s*\)", " ", texte or "")
    return re.sub(r"https?://\S+", " ", t)


def zones_du_titre(texte: str, titre: str, autres_titres: list[str] | None = None,
                   fenetre: int = _FENETRE) -> list[tuple[int, int]]:
    """Les portions du TEXTE D'ORIGINE qui parlent de cette annonce : du titre jusqu'au
    titre voisin le plus proche, ou jusqu'à `fenetre` caractères pliés après le titre.
    Une entrée par occurrence du titre ; [] si le titre est introuvable.

    Contrairement à la date (qui SUIT le titre), le lieu est souvent DANS le titre —
    « Visite méditative au Musée des Arts Asiatiques » — donc la zone l'inclut."""
    norm, carte = carte_norm(texte)
    titre_norm = _norm(titre)
    if not norm or not titre_norm:
        return []
    bornes = [_norm(t) for t in (autres_titres or [])]
    bornes = [b for b in bornes if len(b) >= _TITRE_MIN and b != titre_norm]
    zones: list[tuple[int, int]] = []
    for pos in _positions(norm, titre_norm):
        # `_positions` peut avoir retenu un BOUT du titre : la longueur utile est celle du
        # motif trouvé, pas celle du titre entier. On la relit sur place.
        longueur = len(titre_norm) if norm.startswith(titre_norm, pos) else 0
        if not longueur:
            mots = [m for m in titre_norm.split() if len(m) > 3]
            for n in range(min(4, len(mots)), 1, -1):
                bout = " ".join(mots[:n])
                if len(bout) >= _TITRE_MIN and norm.startswith(bout, pos):
                    longueur = len(bout)
                    break
        apres = pos + longueur
        fin = min(apres + fenetre, len(norm))
        for b in bornes:
            suivant = norm.find(b, apres)
            if suivant != -1:
                fin = min(fin, suivant)
        if fin <= pos:
            continue
        d_orig = carte[pos]
        f_orig = carte[fin - 1] + 1 if fin - 1 < len(carte) else len(texte)
        zones.append((d_orig, f_orig))
    return zones


def _mots_avant(texte: str, debut: int, n: int = 2) -> list[str]:
    """Les `n` mots pliés qui précèdent la position `debut` du texte d'origine."""
    avant = _norm(texte[max(0, debut - 80):debut])
    return avant.split()[-n:] if avant else []


def _majuscule_ok(extrait: str, cle: str) -> bool:
    """Le nom tel qu'écrit porte-t-il ses majuscules de nom propre ?

    « La Salle » oui ; « la salle », « La salle » non. Les particules (de, sur, di…) sont
    libres ; le PREMIER mot doit être en capitale — sauf élision (« l'Escarène »), où
    c'est le mot suivant qui compte."""
    mots = [m for m in re.split(r"[^\w']+", extrait) if m]
    if not mots:
        return False
    plats = [_norm(m) for m in mots]
    premier = mots[0]
    if premier[0].isupper():
        pass
    elif plats[0] in ("l", "d") and len(mots) > 1 and mots[1][0].isupper():
        pass
    elif "'" in premier and premier.split("'", 1)[1][:1].isupper():
        pass
    else:
        return False
    for m, p in zip(mots, plats):
        if p in _PARTICULES or not p or p.isdigit():
            continue
        lettre = m.lstrip("'")[:1]
        if lettre and lettre.isalpha() and not lettre.isupper():
            return False
    return True


def _precede_par_batiment(texte: str, debut: int) -> bool:
    mots = _mots_avant(texte, debut, 2)
    if not mots:
        return False
    if mots[-1] in _BATIMENTS:
        return True
    return len(mots) == 2 and mots[-1] in _LIENS_BATIMENT and mots[-2] in _BATIMENTS


def _precede_par_marqueur(texte: str, debut: int) -> bool:
    """Un marqueur de lieu juste devant : « à Nice », « in Aosta », « , Chambéry »,
    « 73000 Chambéry », « — Nice ». Exigé pour les mots-pièges seulement."""
    brut = texte[max(0, debut - 40):debut]
    if re.search(r"[,;:—–\-|(/]\s*$", brut) or re.search(r"\b\d{5}\s*$", brut):
        return True
    mots = _mots_avant(texte, debut, 1)
    return bool(mots) and mots[0] in _MARQUEURS_AVANT


def _occurrences(zone_norm: str, cle: str) -> list[int]:
    """Positions (dans la zone pliée) de `cle` en MOTS ENTIERS."""
    return [m.start() for m in re.finditer(rf"(?<![a-z0-9]){re.escape(cle)}(?![a-z0-9])",
                                           zone_norm)]


def villes_dans(texte: str, zone: tuple[int, int]) -> list[tuple[str, str]]:
    """Les communes du périmètre nommées dans cette zone : [(canon, tel qu'écrit)],
    dédoublonnées par canon, la plus longue correspondance d'abord à chaque endroit.

    Filtre, dans l'ordre : mot entier ; longueur ≥ 3 ; pas dans les ambigus du registre ;
    majuscule de nom propre dans le texte d'origine ; pas un morceau de nom de bâtiment ;
    marqueur de lieu devant pour les mots-pièges ; une commune contenue dans une plus
    longue au même endroit ne compte pas (« Saint-Martin » dans « Saint-Martin-Vésubie »)."""
    noms, ambigus = _lieux.communes()
    d, f = zone
    portion = texte[d:f]
    zone_norm, carte = carte_norm(portion)
    if not zone_norm:
        return []
    trouvees: list[tuple[int, int, str, str]] = []      # (début, fin, canon, écrit)
    for cle in noms:
        if len(cle) < _MIN_VILLE or cle in ambigus:
            continue
        for pos in _occurrences(zone_norm, cle):
            fin = pos + len(cle)
            o_d = carte[pos]
            o_f = carte[fin - 1] + 1
            ecrit = portion[o_d:o_f]
            if not _majuscule_ok(ecrit, cle):
                continue
            if _precede_par_batiment(portion, o_d):
                continue
            if cle in _PIEGES and not _precede_par_marqueur(portion, o_d):
                continue
            trouvees.append((pos, fin, _lieux.canon(cle), ecrit))
    # La plus longue gagne à chaque endroit : on écarte toute trouvaille contenue dans
    # une autre.
    retenues = [t for t in trouvees
                if not any(a[0] <= t[0] and t[1] <= a[1] and (a[1] - a[0]) > (t[1] - t[0])
                           for a in trouvees)]
    vues: dict[str, str] = {}
    for _, _, canon, ecrit in sorted(retenues):
        vues.setdefault(canon, ecrit)
    return list(vues.items())


_lieux_connus_cache: dict | None = None


def lieux_connus() -> dict[str, dict]:
    """{lieu plié : {"ville": …, "provenance": …}} — le registre d'`utils.lieux`, complété
    des lieux par défaut des sources officielles (`config/sources.txt`), qui sont la même
    connaissance sous une autre forme : « les fiches de flowersfestival.it sont au Flowers
    Festival, à Collegno » veut aussi dire « le Flowers Festival est à Collegno ». Les
    noms génériques (« Salle des Fêtes ») sont écartés : ils désignent cent lieux."""
    global _lieux_connus_cache
    if _lieux_connus_cache is not None:
        return _lieux_connus_cache
    out = dict(_lieux.registre())
    try:
        from scripts.scraper_events import load_sources
        for s in load_sources():
            lieu, ville = (s.get("lieu") or "").strip(), (s.get("ville") or "").strip()
            if lieu and ville and not _lieux.est_generique(lieu):
                out.setdefault(_lieux.plie(lieu), {
                    "ville": ville,
                    "provenance": f"lieu par défaut de la source « {s.get('name', '?')} » "
                                  f"(config/sources.txt)",
                })
        # Un lieu qui, dans une autre source, porte une AUTRE ville n'est pas un fait :
        # deux sources ne peuvent pas avoir raison ensemble, on le retire.
        par_lieu: dict[str, set[str]] = {}
        for s in load_sources():
            lieu, ville = (s.get("lieu") or "").strip(), (s.get("ville") or "").strip()
            if lieu and ville:
                par_lieu.setdefault(_lieux.plie(lieu), set()).add(_lieux.canon(ville))
        for lieu, villes in par_lieu.items():
            if len(villes) > 1 and lieu in out and "sources.txt" in out[lieu]["provenance"]:
                del out[lieu]
    except Exception:  # noqa: BLE001 — sources.txt est un confort, jamais un prérequis
        pass
    _lieux_connus_cache = {k: v for k, v in out.items() if len(k) >= 6}
    return _lieux_connus_cache


def lieux_dans(texte: str, zone: tuple[int, int],
               connus: dict[str, dict] | None = None) -> list[tuple[str, dict, str]]:
    """Les lieux CONNUS nommés dans la zone : [(lieu plié, fiche du registre, tel qu'écrit)],
    la plus longue correspondance à chaque endroit, dédoublonnés."""
    connus = lieux_connus() if connus is None else connus
    d, f = zone
    portion = texte[d:f]
    zone_norm, carte = carte_norm(portion)
    if not zone_norm:
        return []
    trouves: list[tuple[int, int, str, str]] = []
    for cle in connus:
        for pos in _occurrences(zone_norm, cle):
            fin = pos + len(cle)
            trouves.append((pos, fin, cle, portion[carte[pos]:carte[fin - 1] + 1]))
    retenus = [t for t in trouves
               if not any(a[0] <= t[0] and t[1] <= a[1] and (a[1] - a[0]) > (t[1] - t[0])
                          for a in trouves)]
    vus: dict[str, tuple[dict, str]] = {}
    for _, _, cle, ecrit in sorted(retenus):
        vus.setdefault(cle, (connus[cle], ecrit))
    return [(cle, fiche, ecrit) for cle, (fiche, ecrit) in vus.items()]


def completer(texte: str, titre: str, autres_titres: list[str] | None = None,
              lieux_base: dict[str, dict[str, str]] | None = None) -> dict:
    """Ce que le mail permet d'affirmer sur cette annonce : {} ou un dict avec
    « ville » (toujours), « lieu » (si un lieu connu est nommé), « motif » (la phrase
    lisible qui dit d'où ça vient — elle finit sous les yeux de quelqu'un).

    `lieux_base` : {lieu plié : {canon ville : lieu tel qu'écrit en base}} — les lieux de
    NOS fiches, qui ne servent que si le texte nomme aussi leur ville (gisement ③)."""
    texte = sans_urls(texte or "")
    zones = zones_du_titre(texte, titre, autres_titres)
    if not zones:
        return {}
    resultats: set[tuple[str, str, str, str]] = set()   # (lieu, ville, canon ville, motif)
    for zone in zones:
        lieux = lieux_dans(texte, zone)
        if len(lieux) > 1:
            return {}          # deux lieux connus dans la même annonce : on ne tranche pas
        if lieux:
            cle, fiche, ecrit = lieux[0]
            resultats.add((ecrit, fiche["ville"], _lieux.canon(fiche["ville"]),
                           f"lieu connu « {ecrit} » → {fiche['ville']} — "
                           f"{fiche['provenance'][:100]}"))
            continue
        villes = villes_dans(texte, zone)
        if len(villes) != 1:
            if len(villes) > 1:
                return {}      # deux communes différentes : idem
            continue
        canon, ecrit_ville = villes[0]
        lieu, motif = "", f"commune du périmètre nommée dans l'annonce : « {ecrit_ville} »"
        if lieux_base:
            zone_norm, _ = carte_norm(texte[zone[0]:zone[1]])
            candidats = [(cle, formes[canon]) for cle, formes in lieux_base.items()
                         if canon in formes and _occurrences(zone_norm, cle)]
            candidats.sort(key=lambda c: -len(c[0]))
            if candidats and not (len(candidats) > 1
                                  and not candidats[0][0].startswith(candidats[1][0])
                                  and candidats[1][0] not in candidats[0][0]):
                lieu = candidats[0][1]
                motif += f" ; lieu « {lieu} » connu de nos fiches dans cette ville"
        resultats.add((lieu, ecrit_ville, canon, motif))
    # Une seule réponse, ou rien : deux occurrences du titre qui mènent à deux villes,
    # c'est la fenêtre qui a mordu sur l'annonce voisine.
    if len({r[2] for r in resultats}) != 1:
        return {}
    avec_lieu = [r for r in resultats if r[0]] or list(resultats)
    lieu, ville, _, motif = sorted(avec_lieu)[0]
    out = {"ville": ville, "motif": motif}
    if lieu:
        out["lieu"] = lieu
    return out
