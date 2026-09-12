#!/usr/bin/env python3
"""Le calendrier des catégories — laquelle est DE SAISON, et donc laquelle mérite une
tuile dans le bloc « Explorer d'autres catégories » de la page d'accueil.

D'OÙ ÇA VIENT. Franck, 05/09/2026, devant la tuile « Cinéma » encore affichée en
septembre : « le cinéma en plein air c'est terminé maintenant […] les festivals sont
terminés aussi, c'est en été festivals et cinéma en plein air. à partir de septembre
il y a d'autres catégories peut être. Il faut un calendrier où à partir de telle date
on valorise telle catégorie, puis telle autre et etc, d'autres s'enlèvent à partir
d'une date. » Et, quand j'ai proposé de trancher au nombre de fiches : « le comptage
n'est pas forcément le point, mais la saisonnalité ».

DONC, DEUX PRINCIPES :
  - la SAISON ordonne — une catégorie « forte » passe devant une « moyenne », qui
    passe devant une « de base », quel que soit le nombre de fiches ;
  - le NOMBRE ne fait que retirer — une tuile qui mène à une page vide est pire
    qu'une tuile absente (`seuil_fiches`, 1 par défaut : on refuse seulement le vide).

La SOURCE UNIQUE est `config/calendrier_categories.json` : fenêtres par catégorie
(bornes MM-JJ incluses, chevauchement du Nouvel An permis), niveau fort/moyen, ce que
vaut la catégorie hors fenêtre (« base » = éligible en dernier, « exclu » = retirée,
c'est le « s'enlève à partir d'une date » de Franck), et pour chaque fenêtre la RAISON
et des ancres vérifiées. Ce module ne fait que le LIRE : aucune date en dur ici.

Ne pas confondre avec `utils/saison.py` (temps forts nommés → fenêtre de PUBLICATION
d'une fiche) : ici on décide ce que la home MET EN AVANT, pas ce qui se publie.

Où ça se voit : le back-office, page « Calendrier des catégories »
(`/calendrier-categories`), qui montre le calendrier de l'année, la sélection du
jour avec ses raisons, le nombre réel de fiches devant nous par catégorie, et les
prochains changements. Aujourd'hui (05/09) le bloc de la home est SIX TUILES FIXES en
HTML (pages WP 928 FR / 1717 IT) ; la page montre l'écart entre ce que le calendrier
dit et ce qui est en ligne. Le pilotage du bloc par ce calendrier est l'étape suivante.
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FICHIER = ROOT / "config" / "calendrier_categories.json"

# Ordre de priorité : plus le rang est PETIT, plus la catégorie passe devant.
NIVEAUX = ("fort", "moyen", "base", "exclu")
_RANG = {n: i for i, n in enumerate(NIVEAUX)}


def charger(path: Path | None = None) -> dict:
    """Lit la configuration. Lève si le fichier manque ou est invalide : un
    calendrier absent n'est pas « aucune saison », c'est une panne à voir."""
    p = path or FICHIER
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("categories"):
        raise ValueError(f"{p} : pas de clé 'categories'")
    for cat in data["categories"]:
        for f in cat.get("fenetres", []):
            _md(f["debut"]), _md(f["fin"])           # valide le format tôt, pas au 1er usage
            if f.get("niveau") not in ("fort", "moyen"):
                raise ValueError(f"{cat['nom']} : niveau {f.get('niveau')!r} inconnu")
        if cat.get("hors_fenetre", "base") not in ("base", "exclu"):
            raise ValueError(f"{cat['nom']} : hors_fenetre {cat.get('hors_fenetre')!r} inconnu")
    return data


def _md(s: str) -> tuple[int, int]:
    """'MM-JJ' → (mois, jour), validé."""
    mois, jour = s.split("-")
    mois, jour = int(mois), int(jour)
    if not (1 <= mois <= 12 and 1 <= jour <= 31):
        raise ValueError(f"borne invalide : {s!r}")
    return mois, jour


def dans_fenetre(jour: date, debut: str, fin: str) -> bool:
    """Vrai si `jour` est dans [debut, fin], bornes INCLUSES, année ignorée. Une
    fenêtre qui chevauche le Nouvel An (debut > fin, ex. 11-15 → 01-06) est
    l'union « ≥ debut » ∪ « ≤ fin »."""
    md = (jour.month, jour.day)
    d, f = _md(debut), _md(fin)
    if d <= f:
        return d <= md <= f
    return md >= d or md <= f


def etat_categorie(cat: dict, jour: date) -> dict:
    """Ce que vaut UNE catégorie un jour donné : son niveau (fort / moyen / base /
    exclu), la fenêtre active la plus forte, et sa raison — pour que la page puisse
    écrire POURQUOI, jamais un niveau nu."""
    actives = [f for f in cat.get("fenetres", []) if dans_fenetre(jour, f["debut"], f["fin"])]
    if actives:
        f = min(actives, key=lambda x: _RANG[x["niveau"]])
        return {"nom": cat["nom"], "niveau": f["niveau"], "fenetre": f,
                "raison": f.get("raison", "")}
    hors = cat.get("hors_fenetre", "base")
    raison = ("hors saison — retirée (arbitrage : voir le fichier de configuration)"
              if hors == "exclu" else "hors de toute fenêtre — éligible, en dernier")
    return {"nom": cat["nom"], "niveau": hors, "fenetre": None, "raison": raison}


def saisons(jour: date, cfg: dict | None = None) -> list[dict]:
    """L'état de TOUTES les catégories pour `jour`, dans l'ordre du fichier."""
    cfg = cfg or charger()
    out = []
    for cat in cfg["categories"]:
        e = etat_categorie(cat, jour)
        e.update({"slug_fr": cat.get("slug_fr", ""), "slug_it": cat.get("slug_it", ""),
                  "tuile": cat.get("tuile", "secondaire")})
        out.append(e)
    return out


def tuiles(jour: date, comptes: dict[str, int], cfg: dict | None = None,
           n: int | None = None, seuil: int | None = None) -> dict:
    """La sélection des tuiles secondaires pour `jour`.

    `comptes` : nombre de fiches PUBLIÉES et ENCORE DEVANT NOUS par catégorie (règle
    5 : à venir, en cours, ou récurrentes) — c'est l'appelant qui mesure, ce module
    n'ouvre pas la base. Une catégorie absente du dict compte 0.

    Renvoie {"retenues": [...], "ecartees": [...]} ; chaque entrée porte son niveau,
    son compte et sa raison — la raison d'être retenue OU d'être écartée. Les
    catégories à tuile « principale » (bloc dédié sur la home) ne concourent pas.
    Ordre : niveau (fort > moyen > base), puis compte décroissant, puis le nom — le
    nom en dernier pour qu'un même jour donne toujours le même ordre.
    """
    cfg = cfg or charger()
    n = n if n is not None else int(cfg.get("n_tuiles", 6))
    seuil = seuil if seuil is not None else int(cfg.get("seuil_fiches", 1))
    candidates, ecartees = [], []
    for e in saisons(jour, cfg):
        e = dict(e, compte=int(comptes.get(e["nom"], 0)))
        if e["tuile"] == "principale":
            e["motif"] = "bloc principal sur la home — ne concourt pas pour une tuile"
            ecartees.append(e)
        elif e["niveau"] == "exclu":
            e["motif"] = "hors saison — retirée par le calendrier"
            ecartees.append(e)
        elif e["compte"] < seuil:
            e["motif"] = (f"{e['compte']} fiche(s) devant nous, seuil {seuil} — "
                          "une tuile vers une page vide est pire qu'une tuile absente")
            ecartees.append(e)
        else:
            candidates.append(e)
    candidates.sort(key=lambda e: (_RANG[e["niveau"]], -e["compte"], e["nom"]))
    retenues = candidates[:n]
    for e in candidates[n:]:
        e["motif"] = f"éligible mais au-delà des {n} tuiles (niveau {e['niveau']})"
        ecartees.append(e)
    for e in retenues:
        e["motif"] = {"fort": "de saison, à mettre en avant",
                      "moyen": "de saison",
                      "base": "hors fenêtre, retenue faute de mieux"}[e["niveau"]]
    return {"retenues": retenues, "ecartees": ecartees, "n": n, "seuil": seuil}


def prochains_changements(jour: date, cfg: dict | None = None, horizon: int = 120) -> list[dict]:
    """Les dates, dans les `horizon` prochains jours, où le NIVEAU d'une catégorie
    change — c'est le « à partir de telle date » de Franck, rendu lisible. Chaque
    entrée : date, catégorie, niveau avant → après, raison de la fenêtre entrante."""
    cfg = cfg or charger()
    out = []
    etat = {c["nom"]: etat_categorie(c, jour)["niveau"] for c in cfg["categories"]}
    for k in range(1, horizon + 1):
        d = jour + timedelta(days=k)
        for c in cfg["categories"]:
            e = etat_categorie(c, d)
            if e["niveau"] != etat[c["nom"]]:
                out.append({"date": d, "nom": c["nom"], "avant": etat[c["nom"]],
                            "apres": e["niveau"], "raison": e["raison"]})
                etat[c["nom"]] = e["niveau"]
    return out


def grille_annee(annee: int, cfg: dict | None = None) -> list[dict]:
    """Pour la page : par catégorie, la liste des SEGMENTS (debut, fin, niveau, raison)
    couvrant toute l'année civile, jour par jour, en positions relatives (0–1) pour
    dessiner une barre. Le calcul est bête et sûr : un état par jour, puis on fusionne
    les jours consécutifs de même niveau."""
    cfg = cfg or charger()
    j1 = date(annee, 1, 1)
    nb = (date(annee + 1, 1, 1) - j1).days
    lignes = []
    for c in cfg["categories"]:
        segs = []
        for k in range(nb):
            e = etat_categorie(c, j1 + timedelta(days=k))
            if segs and segs[-1]["niveau"] == e["niveau"] and segs[-1]["raison"] == e["raison"]:
                segs[-1]["fin_k"] = k
            else:
                segs.append({"niveau": e["niveau"], "raison": e["raison"],
                             "debut_k": k, "fin_k": k})
        for s in segs:
            s["debut"] = j1 + timedelta(days=s["debut_k"])
            s["fin"] = j1 + timedelta(days=s["fin_k"])
            s["gauche"] = s["debut_k"] / nb
            s["largeur"] = (s["fin_k"] - s["debut_k"] + 1) / nb
        lignes.append({"nom": c["nom"], "tuile": c.get("tuile", "secondaire"),
                       "hors_fenetre": c.get("hors_fenetre", "base"), "segments": segs})
    return lignes
