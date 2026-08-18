#!/usr/bin/env python3
"""Combien des lieux PAYÉS au modèle étaient trouvables GRATUITEMENT ? — mesure, sans rien changer.

D'OÙ ÇA VIENT — Franck, 2026-08-18 : « toutes les sources donnent les informations. Toutes
les informations, on les trouve. C'est juste que des fois c'est mal cherché, c'est mal
trouvé », puis « il faudra qu'on travaille en amont, qu'il n'y ait pas ces erreurs ».

CE QUE LA MESURE DU JOUR A MONTRÉ. Sur les fiches encore devant nous, la provenance des
champs RÉSOLUS se répartit ainsi :

    dates  : 220 par le code, 114 par le modèle, 36 à la main   → 59 % gratuit
    lieux  :  79 par le code, 454 par le modèle                 → 15 % gratuit

Les dates, le code sait les lire. Les lieux, presque pas — et pourtant une adresse n'est
pas une question de jugement : elle est écrite sur la page, ou dans le titre. `venues.py`
n'a qu'UN seul chemin gratuit, le JSON-LD schema.org ; tout ce qui n'en a pas tombe
directement sur un appel de modèle. D'où 454 appels là où il devrait y en avoir une
fraction.

POURQUOI CE SCRIPT NE CORRIGE RIEN. Parce que quatre hypothèses ont été fausses le
2026-08-18 avant que la mesure ne tranche, et que la leçon du dépôt est écrite :
« conclure sur un indice de SURFACE, au lieu d'aller lire la chose ». « On lit mal les
pages » est encore un indice de surface. Ce script le transforme en nombre AVANT qu'une
ligne d'extraction soit écrite.

CE QU'IL MESURE, ET COMMENT IL SE CONTRÔLE. Pour chaque fiche dont le lieu a été payé
(`venue_source` = 'llm' ou 'web'), il demande à des signaux GRATUITS s'ils auraient trouvé
la même ville. La réponse du modèle sert d'étalon : on ne cherche pas à savoir si un signal
propose quelque chose — n'importe quel signal bavard le fait — mais s'il propose LA MÊME
CHOSE. Un signal qui couvre 300 fiches en se trompant sur la moitié coûterait plus cher que
les appels qu'il économise, en fiches fausses publiées.

Chaque signal est donc rendu avec trois nombres : proposés, d'accord, EN DÉSACCORD. Le
troisième décide, pas le premier.

LES SIGNAUX ÉPROUVÉS ICI ne demandent NI réseau NI API — ils n'utilisent que ce qui est
déjà en base :

    titre       une commune connue apparaît dans le titre de la fiche
    url         une commune connue apparaît dans l'adresse de la page source
    repertoire  le nom du lieu est déjà tranché dans config/lieux_villes.json
    soeur       une autre fiche au titre très proche a déjà une ville, trouvée gratuitement

C'est volontaire : un signal qui exige de retélécharger la page ne peut pas être mesuré
pendant que le VPS est coupé du réseau, et surtout ces quatre-là sont les moins chers de
tous. S'ils suffisent, il n'y a rien d'autre à écrire.

LE RÉSULTAT DU 2026-08-18 EST DANS docs/MESURE_LIEUX_GRATUITS_2026-08-18.md, ET IL DIT
NON. Au moins un signal tombe juste sur 67 fiches sur 454 — 15 %. Les deux signaux qui
marchent un peu marchent mal, et pour des raisons structurelles : l'adresse de la page donne
la ville de l'ÉDITEUR (l'office de tourisme du Grand Annecy publie dans tout son
territoire), et un dictionnaire de communes appliqué à du texte libre ramasse « La
Saint-Ours » et « l'école Montessori » comme des noms de communes.

Conclusion consignée : ces signaux ne sont PAS branchés, et le modèle gagne ses 454 appels
sur ce champ — il fait ce que le code ne sait pas faire, distinguer le lieu de l'événement
de la ville de celui qui l'annonce. Relire le document avant de rouvrir la question.

Usage :
    .venv/bin/python -m scripts.audit_lieux_gratuits            # mesure et rapport
    .venv/bin/python -m scripts.audit_lieux_gratuits --exemples 15
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
CONFIG = ROOT / "config"

# Les provenances qui ont COÛTÉ quelque chose. Ce sont elles qu'on cherche à remplacer.
PAYANTES = ("llm", "web")
# Celles qui n'ont rien coûté : elles servent de vivier au signal « fiche sœur », qui ne
# doit jamais propager une ville venue d'un appel payant — ce serait recycler la dépense,
# pas l'éviter.
GRATUITES = ("page", "page_corroboree", "parsed", "source", "registre", "moisson",
             "jsonld", "mail", "manuel")


def _norm(s: str) -> str:
    """Minuscules, sans accent, sans ponctuation : la forme qui sert à COMPARER.

    Les listes de communes sont écrites en slug (`aix-les-bains`) et les titres en clair
    (« Aix-les-Bains ») : sans une forme commune, tout le comptage vaut zéro.
    """
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def charger_communes() -> dict[str, str]:
    """Toutes les communes du périmètre, en forme normalisée → nom d'affichage.

    Les trois fichiers font foi (`CLAUDE.md`, « Périmètre éditorial ») ; on ne devine
    aucune commune hors de cette liste, sinon le signal « titre » attraperait n'importe
    quel nom propre.
    """
    out: dict[str, str] = {}
    for nom in ("communes_savoie_dept.json", "communes_italiennes.json",
                "communes_comte_de_nice.json"):
        chemin = CONFIG / nom
        if not chemin.exists():
            continue
        try:
            brut = json.loads(chemin.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        cles = brut if isinstance(brut, dict) else {k: "" for k in brut}
        for slug in cles:
            if slug.startswith("_"):
                continue
            forme = _norm(slug)
            # Un nom d'une seule syllabe courte ferait des faux positifs partout
            # (« Rive », « Sale »). On garde le seuil bas mais non nul, et on le DIT
            # plutôt que de laisser croire à une couverture totale.
            if len(forme) >= 5:
                out[forme] = slug.replace("-", " ").title()
    return out


def charger_repertoire() -> dict[str, str]:
    """`config/lieux_villes.json` : les arbitrages déjà tranchés, lieu → ville."""
    chemin = CONFIG / "lieux_villes.json"
    if not chemin.exists():
        return {}
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    out = {}
    for cle, val in (brut or {}).items():
        if cle.startswith("_"):
            continue
        ville = val.get("ville") if isinstance(val, dict) else val
        if isinstance(ville, str) and ville.strip():
            out[_norm(cle)] = ville.strip()
    return out


def commune_dans(texte: str, communes: dict[str, str]) -> str:
    """La première commune connue trouvée dans ce texte, en tant que MOT entier.

    « en tant que mot entier » n'est pas un détail : sans ça, « Nice » se déclencherait sur
    « Venice » et « Ars » sur « Arsenal ». La forme normalisée est encadrée d'espaces.
    """
    t = f" {_norm(texte)} "
    for forme, affiche in communes.items():
        if f" {forme} " in t:
            return affiche
    return ""


def _signaux(ligne: dict, communes: dict[str, str], repertoire: dict[str, str],
             par_titre: dict[str, str]) -> dict[str, str]:
    """Ce que chaque signal GRATUIT proposerait comme ville pour cette fiche."""
    titre = ligne.get("title") or ""
    return {
        "titre": commune_dans(titre, communes),
        "url": commune_dans(ligne.get("url_source") or "", communes),
        "repertoire": repertoire.get(_norm(ligne.get("lieu") or ""), ""),
        "soeur": par_titre.get(_norm(titre), ""),
    }


def mesurer(conn: sqlite3.Connection) -> dict:
    """Le comptage. Ne modifie RIEN — aucune écriture, aucun appel réseau, aucun jeton."""
    conn.row_factory = sqlite3.Row
    auj = date.today().isoformat()
    # LE PÉRIMÈTRE, ET IL EST LE MÊME QUE CELUI DU RELEVÉ DE PROVENANCE (règle 6) : deux
    # compteurs qui portent sur des ensembles différents finiront par se contredire.
    devant = ("COALESCE(duplicate_of,0)=0 AND COALESCE(translation_of,0)=0 "
              "AND (COALESCE(date_event_end, date_event_start, '')='' "
              "     OR COALESCE(date_event_end, date_event_start) >= ?)")

    communes = charger_communes()
    repertoire = charger_repertoire()

    # Le vivier des fiches sœurs : uniquement des villes obtenues GRATUITEMENT. Propager
    # une ville venue d'un appel payant reviendrait à recycler la dépense au lieu de
    # l'éviter, et gonflerait artificiellement le résultat de ce signal.
    par_titre: dict[str, str] = {}
    q_libres = ",".join("?" * len(GRATUITES))
    for r in conn.execute(
            f"SELECT title, ville FROM events_raw WHERE {devant} "
            f"AND venue_source IN ({q_libres}) AND COALESCE(ville,'')<>''",
            (auj, *GRATUITES)):
        par_titre.setdefault(_norm(r["title"]), r["ville"])

    q_pay = ",".join("?" * len(PAYANTES))
    lignes = [dict(r) for r in conn.execute(
        f"SELECT id, title, url_source, lieu, ville, venue_source FROM events_raw "
        f"WHERE {devant} AND venue_source IN ({q_pay}) AND COALESCE(ville,'')<>''",
        (auj, *PAYANTES))]

    noms = ("titre", "url", "repertoire", "soeur")
    stats = {n: {"propose": 0, "accord": 0, "desaccord": 0} for n in noms}
    desaccords: list[dict] = []
    couverts_accord = 0

    for ligne in lignes:
        props = _signaux(ligne, communes, repertoire, par_titre)
        attendu = _norm(ligne.get("ville") or "")
        un_accord = False
        for n in noms:
            propose = props[n]
            if not propose:
                continue
            stats[n]["propose"] += 1
            if _norm(propose) == attendu:
                stats[n]["accord"] += 1
                un_accord = True
            else:
                stats[n]["desaccord"] += 1
                desaccords.append({"id": ligne["id"], "signal": n,
                                   "propose": propose, "modele": ligne.get("ville"),
                                   "titre": (ligne.get("title") or "")[:70]})
        if un_accord:
            couverts_accord += 1

    return {
        "communes_connues": len(communes),
        "repertoire_entrees": len(repertoire),
        "soeurs_disponibles": len(par_titre),
        "fiches_payees": len(lignes),
        "couverts_par_au_moins_un_signal": couverts_accord,
        "signaux": stats,
        "desaccords": desaccords,
    }


def rapport(m: dict, exemples: int = 8) -> str:
    n = m["fiches_payees"]
    L = ["LIEUX PAYÉS AU MODÈLE : combien étaient trouvables sans rien dépenser ?",
         "",
         f"Périmètre : {n} fiches encore devant nous (ou sans date), non doublons, non "
         f"traductions, dont le LIEU vient d'un appel payant ('llm' ou 'web') et dont la "
         f"ville est renseignée.",
         f"Matière de référence : {m['communes_connues']} communes du périmètre, "
         f"{m['repertoire_entrees']} arbitrages de lieux, "
         f"{m['soeurs_disponibles']} fiches sœurs à ville gratuite.",
         ""]
    if not n:
        # UN ZÉRO DOIT DIRE D'OÙ IL VIENT (leçon du 11/08) : ici, aucune fiche ne s'est
        # présentée — ce n'est pas « aucun signal ne marche ».
        L.append("AUCUNE fiche ne correspond à ce périmètre : il n'y a rien à mesurer, ce "
                 "qui n'est pas la même chose qu'un signal inefficace.")
        return "\n".join(L)

    L.append(f"{'signal':12s} {'propose':>8s} {'d accord':>9s} "
             f"{'EN DÉSACCORD':>13s}   gain net")
    for nom, s in m["signaux"].items():
        gain = s["accord"] - s["desaccord"]
        L.append(f"{nom:12s} {s['propose']:8d} {s['accord']:9d} {s['desaccord']:13d}   "
                 f"{gain:+d}")
    couv = m["couverts_par_au_moins_un_signal"]
    L += ["",
          f"Au moins un signal gratuit tombe juste sur {couv} fiches sur {n} "
          f"({round(100 * couv / n)} %).",
          "",
          "COMMENT LIRE CE TABLEAU. « propose » ne vaut rien tout seul : un signal bavard "
          "propose toujours. C'est « en désaccord » qui décide, parce qu'une ville fausse "
          "publiée coûte plus cher que l'appel qu'elle économise. Un signal n'est bon à "
          "brancher que si son désaccord est proche de zéro.",
          "",
          "Et une précaution sur l'étalon : la colonne « d'accord » compare au lieu trouvé "
          "PAR LE MODÈLE, qui n'est pas la vérité — c'est seulement ce qu'on a. Un "
          "désaccord peut donc être le signal qui a raison. Les exemples ci-dessous sont "
          "là pour être LUS, pas comptés."]
    if m["desaccords"]:
        L += ["", f"DÉSACCORDS ({len(m['desaccords'])} au total, "
                  f"{min(exemples, len(m['desaccords']))} montrés) :"]
        for d in m["desaccords"][:exemples]:
            L.append(f"  [{d['id']}] {d['signal']:10s} propose « {d['propose']} » "
                     f"vs modèle « {d['modele']} » — {d['titre']}")
    return "\n".join(L)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Mesure ce que des signaux gratuits auraient trouvé à la place du "
                    "modèle, sur les lieux. N'écrit rien.")
    p.add_argument("--exemples", type=int, default=8,
                   help="Nombre de désaccords montrés (ils servent à être lus).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base absente : {DB_PATH}")
        return 1
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        print(rapport(mesurer(conn), args.exemples))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
