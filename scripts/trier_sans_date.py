#!/usr/bin/env python3
"""Les fiches sans date, RANGÉES pour être décidées — pas décidées à ta place.

Mesuré le 2026-08-11 : 79 fiches encore devant nous n'ont pas de date, et la soirée a
établi que ce n'est ni un problème de plafond API, ni d'extraction trop étroite, ni de
pages officielles mal lues. La page de « Per Olivia » a été récupérée à la main : elle ne
porte AUCUNE date, parce que le spectacle appartient à une saison et que ses dates vivent
dans la billetterie. Le diagnostic de la moisson a confirmé à l'échelle : 29 pages muettes
portent bien du JSON-LD, mais qui décrit l'organisation, pas l'événement.

Ces fiches n'ont donc pas de date parce qu'il n'y en a pas à trouver. Elles ne relèvent
plus du code, elles relèvent d'un CLASSEMENT — et ce classement est éditorial, donc il
appartient à Franck. Ce que ce script fait, c'est lui éviter d'ouvrir 79 pages pour
découvrir de quoi il s'agit.

⚠️ LE REGROUPEMENT EST UN ORDRE DE LECTURE, PAS UN VERDICT. Il repose sur des mots du
titre, et la charte éditoriale dit exactement l'inverse pour décider : « Le partage se
fait sur À QUI ÇA S'ADRESSE, jamais sur le mot du titre. » Un « salon du livre » est dans
le catalogue, un « salon des entrepreneurs » n'y est pas, et aucun mot ne les sépare. Le
script met donc côte à côte ce qui se ressemble pour que la décision soit rapide ; il
n'en prend aucune, et il n'écrit RIEN.

CE QUI SORT DE LA FILE, ET COMMENT
  • RÉCURRENT — une saison, un programme annuel, une activité permanente : le
    back-office a un bouton « récurrent » qui remplace la date par un renvoi à la source.
    La fiche devient publiable, elle quitte « À compléter ».
  • REJET — une offre commerciale, un événement professionnel, une fiche vide : bouton
    « rejeté ». Réversible, la fiche reste en base.
  • RIEN — un vrai événement dont la date n'est pas publiée : on la laisse attendre. Elle
    repassera si sa page change (dates.py surveille l'empreinte de sa matière).

LECTURE SEULE : base ouverte en `mode=ro`, aucun réseau, aucun appel de modèle.

Exemples :
  .venv/bin/python -m scripts.trier_sans_date
  .venv/bin/python -m scripts.trier_sans_date --groupe saison
"""
from __future__ import annotations

import argparse
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

# Indices, pas preuves. Chaque famille dit ce qu'elle SUGGÈRE et ce qu'elle ne prouve pas.
#
# ⚠️ TOUS CES INDICES PORTENT SUR LA FORME, JAMAIS SUR LE PUBLIC — sauf le dernier, qui
# est marqué comme tel. La distinction n'est pas cosmétique : la charte interdit de
# trancher l'appartenance au catalogue sur un mot du titre (« le partage se fait sur à
# qui ça s'adresse »), mais elle ne dit rien contre le fait de repérer qu'une chose n'a
# PAS de date unique. « Exposition », « visites du soir », « été 2026 » ne disent rien du
# public : ils disent que l'objet s'étale dans le temps. C'est une question de forme, et
# c'est exactement celle que « récurrent » résout.
#
# ÉLARGI le 2026-08-11 après le premier passage : la version d'origine ne rangeait que
# 2 fiches sur 75 en « saison » et en laissait 70 dans « événement » — inutilisable.
# En lisant la liste, la moitié sautait aux yeux : « Sere d'Estate alla Reggia »,
# « Aperture serali della Basilica di Superga », « AGOSTO AI MUSEI REALI », « Percorsi
# enogastronomici », quatre expositions de la Venaria. Un tri qui range 93 % des fiches
# dans « je ne sais pas » ne trie rien.
_INDICES = (
    ("vide", None,
     "Titre absent ou dérisoire — il n'y a rien à publier, quelle que soit la date.",
     "rejeter"),
    ("exposition", (
        r"\bexposition\b", r"\bexpositions\b", r"\bmostra\b", r"\bmostre\b",
        r"\besposizion", r"\bexpo\b", r"\bretrospective\b", r"\bcollezione\b"),
     "Une exposition court sur des semaines ou des mois. Si ses dates ne sont pas "
     "publiées, « récurrent » (renvoi à la source) vaut mieux qu'une fiche bloquée.",
     "récurrent"),
    ("saison", (
        r"\bsaison\b", r"\bstagione\b", r"\bprogramm[ae]\b", r"\bcartellone\b",
        r"\brassegna\b", r"\bciclo\b", r"\babbonament", r"\babonnement",
        r"\b20\d{2}\s*[-/–]\s*20\d{2}\b", r"\bà l'année\b", r"\btoute l'année\b",
        r"\bpermanent", r"\bser[ei] d'estate\b", r"\bagosto ai\b", r"\bun été\b",
        r"\bestate\b", r"\bd'été\b", r"\bmusica nelle\b"),
     "Une saison, un programme ou une série sur tout un été : ça n'a pas de date "
     "unique, c'est normal.", "récurrent"),
    ("activité", (
        r"\bpasseggiate\b", r"\bpercorsi\b", r"\bvisites? guidées?\b",
        r"\bvisit[ae] serale?\b", r"\bvisite serali\b", r"\baperture serali\b",
        r"\bnocturnes?\b", r"\bateliers?\b", r"\blaboratori\b", r"\bbalade",
        r"\brandonnées?\b", r"\banimations? nature\b", r"\bdégustation",
        r"\bosservazione del cielo\b", r"\bsieste musicale\b",
        # Second élargissement, sur la liste du 2026-08-11 au matin : « visite
        # commentée » manquait alors que « visite guidée » y était (même chose, autre
        # mot), et les séances d'été qui reviennent chaque semaine — cinéma en plein
        # air, dimanche au musée, cours de bien-être — sont des rendez-vous réguliers,
        # pas des événements datés.
        r"\bvisites? comment", r"\bbien-etre\b", r"\bdomenica al museo\b",
        r"\bcinema sotto le stelle\b", r"\bcinema nel\b", r"\bcinéma en plein air\b"),
     "Une activité qui se répète (visites, ateliers, balades) : elle a des horaires, "
     "pas une date d'événement.", "récurrent"),
    ("professionnel", (
        r"\boffre vip\b", r"\bvip\b", r"\bb2b\b", r"\bcongrès\b", r"\bcongresso\b",
        r"\bcolloque\b", r"\bséminaire\b", r"\bseminario\b", r"\bnetworking\b",
        r"\bsalon des\b", r"\brecrutement\b", r"\bin tech\b",
        r"\bworkshop pro", r"\bassemblée générale\b", r"\bconférence de presse\b"),
     "⚠️ SEUL INDICE QUI TOUCHE AU PUBLIC, donc le seul à ne jamais appliquer sans "
     "ouvrir la fiche : peut viser un public PROFESSIONNEL, ce qui serait hors charte. "
     "À vérifier sur le contenu, jamais sur ce mot.", "rejeter (si public pro)"),
)


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "")
                if not unicodedata.combining(c))
    return s.lower()


def _groupe(ev: dict) -> str:
    titre = (ev.get("title") or "").strip()
    if len(titre) < 4:
        return "vide"
    bas = _norm(titre)
    for nom, motifs, _quoi, _action in _INDICES:
        if motifs and any(re.search(_norm(m), bas) for m in motifs):
            return nom
    return "événement"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Range les fiches sans date par cas (lecture seule, aucune décision).")
    p.add_argument("--groupe", default="", help="N'afficher qu'un groupe.")
    p.add_argument("--limite", type=int, default=40, help="Lignes par groupe (défaut 40).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    today = date.today().isoformat()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(date_event_start,'')='' "
        "AND COALESCE(recurring,0)=0 AND duplicate_of IS NULL "
        "AND COALESCE(translation_of,0)=0 "
        "AND statut IN ('evaluated','published_cs','published_sub') "
        # Règle 5 : une fiche sans date n'est PAS passée — c'est une donnée manquante.
        # Elle reste donc dans la file, c'est tout l'objet de ce tri.
        "ORDER BY COALESCE(llm_score,0) DESC")]
    conn.close()

    if not rows:
        print("Aucune fiche sans date. 🎉")
        return 0

    paniers: dict[str, list[dict]] = {}
    for ev in rows:
        paniers.setdefault(_groupe(ev), []).append(ev)

    print(f"═══ {len(rows)} fiche(s) sans date, rangées par cas ═══\n")
    print("Le regroupement est un ORDRE DE LECTURE, pas un verdict : il repose sur des")
    print("mots du titre, alors que la charte tranche sur À QUI ÇA S'ADRESSE. Un « salon")
    print("du livre » est dans le catalogue, un « salon des entrepreneurs » non, et aucun")
    print("mot ne les sépare.\n")

    ordre = [("vide", "rejeter"), ("exposition", "récurrent"), ("saison", "récurrent"),
             ("activité", "récurrent"), ("professionnel", "rejeter (si public pro)"),
             ("événement", "laisser attendre")]
    quoi = {nom: (txt, act) for nom, _m, txt, act in _INDICES}
    quoi["événement"] = ("Un vrai événement dont la date n'est pas publiée. Elle "
                         "repassera toute seule si sa page change.", "laisser attendre")

    for nom, _action in ordre:
        lot = paniers.get(nom, [])
        if not lot or (args.groupe and args.groupe != nom):
            continue
        texte, action = quoi[nom]
        print(f"── {nom.upper()} · {len(lot)} fiche(s) · suggestion : {action} ──")
        print(f"   {texte}\n")
        for ev in lot[:args.limite]:
            titre = (ev.get("title") or "(sans titre)").strip()[:56]
            src = (ev.get("source_name") or "?")[:22]
            print(f"   [{ev['id']:>5}] {titre:56} · {src}")
        if len(lot) > args.limite:
            print(f"   … et {len(lot) - args.limite} autre(s) "
                  f"(--groupe {nom} --limite 200)")
        print()

    print("POUR AGIR — dans le back-office, fiche par fiche : le bouton « récurrent »")
    print("remplace la date par un renvoi à la source (la fiche redevient publiable), le")
    print("bouton « rejeté » la sort du catalogue. Les deux se défont.")
    print("\nRIEN N'A ÉTÉ MODIFIÉ par ce script.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
