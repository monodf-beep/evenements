#!/usr/bin/env python3
"""LE NOM D'UN LIEU CONTIENT SOUVENT SA VILLE — et personne ne le lisait.

Écrit le 2026-08-11, après qu'une autre session a trouvé la fiche lieu WordPress 208 :
`_VenueCity = Aosta` pour le **Forte di Bard**, qui est à Bard, cinquante kilomètres plus
bas dans la vallée. Trois événements pointaient sur cette fiche et affichaient donc au
public une ville fausse — un visiteur qui suit l'indication se trompe de commune, pas de
rue.

Le plus dur à avaler : **la bonne réponse était déjà dans le dépôt**. `docs/savoir/forte-
di-bard.md`, écrit par Franck, déclare en tête `villes: Bard`. Rien ne comparait ce qu'on
savait à ce qu'on publiait.

CE MODULE NE DEVINE RIEN. C'est la leçon de la journée, la même que `verifier_dates` :
sur une donnée écrite pour des humains on ne peut pas EXTRAIRE, seulement CONFIRMER à
partir d'un fait qu'on tient déjà. D'où trois confrontations, et aucune extraction :

  ① LE REGISTRE — une note de `docs/savoir/` (ou `config/lieux_villes.json`) nomme ce
    lieu et déclare sa ville. C'est Franck qui l'a écrite : elle fait foi, point final.
  ② LE TOPONYME — le NOM du lieu contient une commune que nous connaissons, et le champ
    `ville` en nomme une AUTRE que nous connaissons aussi. Les deux côtés viennent du même
    registre : on ne compare pas un fait à une intuition, on compare deux faits.
  ③ (dans `scripts/verifier_lieux.py`, parce qu'il faut la base) LE DÉSACCORD INTERNE —
    le même lieu porte deux villes différentes sur deux de nos fiches. Aucune connaissance
    extérieure requise : nos deux affirmations ne peuvent pas être vraies ensemble.

CE QU'IL NE SIGNALE JAMAIS

  • l'ABSENCE. Une ville vide, un lieu inconnu du registre, une commune hors de nos
    listes : silence. Une liste incomplète ne prouve rien contre une donnée — c'est la
    règle 6, et c'est ce qui a fait des 454 « points à contrôler » du matin une file que
    personne ne pouvait traiter.
  • le HORS PÉRIMÈTRE. `config/communes_italiennes.json` est explicitement partielle ;
    s'en servir pour dire « cette ville n'existe pas » serait transformer notre ignorance
    en verdict.

Les noms ambigus (« Nus », « Quart », « Sarre », « Alba »…) sont écartés du balayage des
NOMS de lieux mais gardés pour reconnaître une VILLE : « Théâtre des Nus » ne parle pas de
la commune de Nus, alors que `ville = "Nus"` en parle forcément.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
REGISTRE_JSON = CONFIG / "lieux_villes.json"

# Deux noms pour une même ville. Sans ça, « Aoste » et « Aosta » se contrediraient l'un
# l'autre et le contrôle crierait sur des fiches justes — un vérificateur qui produit du
# faux positif se fait désactiver au bout d'une semaine, et c'est le pire des sorts.
_ALIAS = {
    "aosta": "aoste",
    "torino": "turin",
    "chatillon": "chatillon",
}


def plie(s: str) -> str:
    """Casse, accents et séparateurs neutralisés — « Aix-les-Bains » = « aix les bains ».

    Les tirets deviennent des espaces pour que les listes en SLUG (`communes_savoie_dept`)
    et celles en NOM D'AFFICHAGE (`communes_comte_de_nice`) se comparent sans conversion."""
    n = unicodedata.normalize("NFD", s or "")
    n = "".join(c for c in n if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", n)).strip()


def canon(ville: str) -> str:
    """Forme canonique d'un nom de ville, alias compris."""
    p = plie(ville)
    return _ALIAS.get(p, p)


def _charge(nom: str) -> dict:
    f = CONFIG / nom
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


_communes_cache: tuple[dict, set] | None = None


def communes() -> tuple[dict[str, str], set[str]]:
    """({forme pliée : nom affichable}, {formes pliées ambiguës}).

    Réunit les quatre territoires depuis `config/` : Savoie + Haute-Savoie (slugs),
    arrondissement de Nice, Vallée d'Aoste et la part connue du Piémont. Toute clé
    commençant par « _ » est un commentaire du fichier, pas une donnée."""
    global _communes_cache
    if _communes_cache is not None:
        return _communes_cache

    noms: dict[str, str] = {}
    ambigus: set[str] = set()

    for slug in _charge("communes_savoie_dept.json"):
        if not slug.startswith("_"):
            noms.setdefault(plie(slug), slug.replace("-", " ").title())

    nice = _charge("communes_comte_de_nice.json")
    for cle, val in nice.items():
        # SEULEMENT l'arrondissement de Nice : celui de Grasse est hors périmètre
        # éditorial (CLAUDE.md), et le fichier le stocke à côté pour mémoire.
        if cle == "arrondissement_de_nice" and isinstance(val, list):
            for c in val:
                noms.setdefault(plie(c), c)

    ita = _charge("communes_italiennes.json")
    for cle in ("vallee_d_aoste", "piemont"):
        for c in ita.get(cle) or []:
            noms.setdefault(plie(c), c)
    for c in ita.get("ambigus") or []:
        ambigus.add(plie(c))

    _communes_cache = (noms, ambigus)
    return _communes_cache


_registre_cache: dict | None = None


def registre() -> dict[str, dict]:
    """{lieu plié : {"ville": …, "provenance": …}} — ce que NOUS savons de ce lieu.

    Deux gisements, et le second existe parce que le premier ne se remplit qu'à la main :

      • `docs/savoir/*.md` — les notes de Franck, dont l'en-tête `lieux:` / `villes:`
        décrit déjà exactement ce couple. Elles ont été écrites pour enrichir les
        articles ; elles servent ici de registre d'autorité, gratuitement ;
      • `config/lieux_villes.json` — le dépôt des arbitrages rendus en vérifiant un
        signalement. C'est LUI le rouvreur/fermeur de la règle 3 : un lieu tranché une
        fois cesse de se signaler, et il corrige les fiches suivantes au lieu de
        simplement se taire.
    """
    global _registre_cache
    if _registre_cache is not None:
        return _registre_cache

    out: dict[str, dict] = {}
    noms, _ = communes()
    try:
        from utils import savoir as _savoir
        for note in _savoir.notes_disponibles():
            cles = note.get("cles") or {}
            # `savoir` rend les valeurs DÉJÀ pliées (même normalisation que `plie` ici) :
            # on les réaffiche via la liste des communes quand elle les connaît, sinon en
            # capitales initiales. Une ville qui s'écrit « bard » dans un signalement
            # sabote la lecture, et c'est la lecture qui décide.
            villes = [v for v in cles.get("villes") or [] if v]
            if not villes:
                continue
            ville = noms.get(villes[0], villes[0].title())
            for lieu in cles.get("lieux") or []:
                if lieu:
                    out.setdefault(lieu, {
                        "ville": ville,
                        "provenance": f"note de savoir « {note.get('nom', '?')} »",
                    })
    except Exception:  # noqa: BLE001 — le registre est un CONFORT, jamais un prérequis
        pass

    for lieu, val in (_charge("lieux_villes.json") or {}).items():
        if lieu.startswith("_"):
            continue
        ville = val.get("ville") if isinstance(val, dict) else val
        if not str(ville or "").strip():
            continue
        out[plie(lieu)] = {
            "ville": str(ville).strip(),
            "provenance": (val.get("motif") if isinstance(val, dict) else "")
                          or "arbitrage consigné dans config/lieux_villes.json",
        }

    _registre_cache = out
    return out


# CES NOMS NE DÉSIGNENT PAS UN LIEU, ILS EN DÉSIGNENT CENT. Chaque village a sa salle des
# fêtes ; « Salle des Fêtes » ne distingue donc rien. Ça n'aurait aucune importance si
# WordPress ne retrouvait pas ses fiches lieu PAR LEUR TITRE (`get_page_by_title`, dans
# cs-publish.php) : deux salles des fêtes de deux communes s'écrasent alors sur une seule
# fiche, avec une seule ville, et l'une des deux affiche la commune de l'autre.
#
# Trouvé le 2026-08-12 au premier passage en production : « Salle des Fêtes » à Margencel
# (fiche 926) et à Draillant (fiche 925), toutes deux PUBLIÉES. Le contrôle les avait
# rangées en « désaccord interne » et disait « les deux ne peuvent pas être vraies » —
# c'était faux, les deux sont vraies, et le vrai défaut était ailleurs.
#
# ÉGALITÉ STRICTE, jamais « commence par ». « Salle des fêtes de Margencel » distingue
# parfaitement, et le signaler serait fabriquer du bruit. C'est l'ABSENCE de tout élément
# distinctif qui pose problème, pas la présence des mots.
GENERIQUES = {
    "salle des fetes", "salle polyvalente", "salle communale", "salle municipale",
    "salle des associations", "salle d animation", "salle de spectacle",
    "maison des associations", "foyer rural", "centre culturel", "espace culturel",
    "centre socioculturel", "mediatheque", "bibliotheque", "mairie", "eglise",
    "chapelle", "temple", "gymnase", "place du village", "place de l eglise",
    "office de tourisme", "parc municipal", "theatre municipal", "cinema",
    "chateau", "halle", "esplanade", "salle des sports",
    "piazza", "chiesa", "biblioteca", "municipio", "palazzo comunale",
    "teatro comunale", "sala consiliare", "oratorio", "centro culturale",
    "casa del popolo", "palazzetto dello sport",
}


def est_generique(lieu: str) -> bool:
    """« Salle des Fêtes » : un nom que cent communes partagent, donc qui n'identifie rien."""
    return plie(lieu) in GENERIQUES


def toponyme_du_lieu(lieu: str) -> str:
    """La commune nommée DANS le nom du lieu (« Forte di Bard » → « Bard »). "" sinon.

    Recherche par mots entiers sur la forme pliée : « Bardonecchia » ne contient donc PAS
    « Bard ». La plus longue correspondance gagne — « Casale Monferrato » avant « Casale »
    si les deux existaient un jour."""
    noms, ambigus = communes()
    hay = f" {plie(lieu)} "
    trouve = ""
    for p, affiche in noms.items():
        if len(p) < 4 or p in ambigus:
            continue
        if f" {p} " in hay and len(p) > len(plie(trouve)):
            trouve = affiche
    return trouve


def confronte(lieu: str, ville: str) -> tuple[str, str, str]:
    """(verdict, phrase lisible, ville attendue). Verdict "" = rien à dire.

    Une PHRASE, pas un booléen : elle finira sous les yeux de quelqu'un qui doit trancher,
    et « le nom du lieu dit Bard, la fiche dit Aoste » se juge en une seconde là où
    « True » ne se juge pas du tout. Même choix que `utils/jours.contredit`."""
    lieu, ville = (lieu or "").strip(), (ville or "").strip()
    if not lieu or not ville:
        return ("", "", "")          # l'absence ne contredit rien (règle 6)

    reg = registre().get(plie(lieu))
    if reg:
        # LE REGISTRE TRANCHE, DANS LES DEUX SENS. S'il désigne une autre ville, on
        # signale ; s'il désigne la nôtre, on s'ARRÊTE LÀ — sans ce retour, le toponyme
        # reprenait la parole derrière lui et « Castello di Rivoli, à Turin », pourtant
        # arbitré et consigné, se signalait quand même tous les jours. C'est très
        # exactement le refus qui se rejoue sur la même entrée que la règle 3 interdit :
        # le fichier existait pour l'éteindre, il ne l'éteignait pas.
        if canon(reg["ville"]) != canon(ville):
            return ("registre",
                    f"nous savons ce lieu à {reg['ville']} — {reg['provenance']} — "
                    f"et la fiche dit {ville}",
                    reg["ville"])
        return ("", "", "")

    top = toponyme_du_lieu(lieu)
    if top and canon(top) != canon(ville):
        noms, _ = communes()
        # LES DEUX CÔTÉS DOIVENT ÊTRE CONNUS. Sans cette exigence, « Café de Turin » à
        # Nice deviendrait une anomalie : le nom d'un établissement n'est pas une adresse.
        # En n'ouvrant la bouche que quand la ville est elle aussi une commune de nos
        # listes, on compare deux faits du même registre au lieu d'un fait à une intuition.
        if canon(ville) in {canon(n) for n in noms.values()} or plie(ville) in noms:
            return ("toponyme",
                    f"le nom du lieu contient la commune de {top}, la fiche dit {ville}",
                    top)
    return ("", "", "")
