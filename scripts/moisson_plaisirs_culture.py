#!/usr/bin/env python3
"""« Plaisirs de Culture en Vallée d'Aoste » : le volet valdôtain des journées du patrimoine.

D'OÙ ÇA VIENT. `scripts/moisson_gep.py` (22/09/2026) a fait entrer le programme
ministériel des Giornate Europee del Patrimonio pour le Piémont — et a constaté que la
Vallée d'Aoste n'y figure pas : région autonome, elle publie son propre rendez-vous.
Quatorzième édition, du 19 au 27 septembre 2026, thème « Patrimonio a rischio.
Rinnovare, resistere, reinventare ». Ce script en est le pendant.

LA SOURCE, ET POURQUOI ELLE. `valledaostaheritage.com` est le site de la Région
autonome elle-même : son pied de page porte « Regione autonoma Valle d'Aosta —
Dipartimento Soprintendenza per i beni e le attività culturali », le Palais Roncas et
le code fiscal de la Région (80002270074). La page de l'événement renvoie, pour le
programme, à une BROCHURE PDF et à un CALENDRIER PDF. Vérifié le 22/09/2026 :

  • la page HTML ne contient AUCUN rendez-vous — seulement la présentation ;
  • l'agenda du site (plugin Events Manager) n'en publie que quatre, isolément, et son
    API REST répond 401 ;
  • donc le programme, c'est le PDF. Pas de JSON, pas de liste HTML.

LA BROCHURE, PAS LE CALENDRIER SEUL. La brochure (31 pages PDF, des doubles pages)
contient deux choses : les fiches détaillées (titre, horaires, lieu, répliques,
description, infos pratiques, organisateur) et, pages 29-32 imprimées, un calendrier
récapitulatif jour par jour qui renvoie à la page de chaque fiche. Le calendrier seul ne
suffit pas : il ne couvre PAS la section « Attività per bambini e famiglie » (mesuré :
ses renvois s'arrêtent à la page 44, la section occupe les pages 45-49). On lit donc
les fiches, et le calendrier sert de CONTRE-ÉPREUVE : chaque ligne du calendrier doit
retrouver une fiche à la même page et au même jour. Ce qui ne se retrouve pas est
AFFICHÉ, jamais avalé.

POURQUOI LA POSITION ET PAS LE TEXTE BRUT. `extract_text()` de pypdf rend les
fragments dans l'ordre du flux PDF, pas de la lecture : sur la page de « Tissus
d'histoire », le titre sort AVANT l'en-tête du jour, et la mention « A cura di » avant
les infos pratiques. On relève donc chaque fragment avec sa position, sa taille et sa
police, et on reconstruit la page moitié par moitié, de haut en bas. La mise en page
est régulière : titre en gras corps 10 à la marge, horaire en gras corps 8 en retrait,
lieu en maigre corps 8 en retrait, description en maigre à la marge, en-tête de jour en
corps 13-20.

LE JOUR se lit sur le dernier GRAND en-tête rencontré (« SABATO 19 SETTEMBRE » en
corps 13-20), et il se reporte d'une demi-page à l'autre. Les petits en-têtes courants
en haut de page (corps 8) ne décident de rien : ils résument la plage de la page
(« LUNEDÌ 21 | MARTEDÌ 22 »), et une fiche placée sous « LUNEDÌ 21 | MARTEDÌ 22 » avant
le grand en-tête du 22 appartient au 21 — le calendrier le confirme (Il tesoro della
cattedrale, lundi 21 seulement).

CE QU'IL NE PREND PAS, et il le dit :
  • la section « Plaisirs de Culture a scuola » — des visites pour les CLASSES, sur
    rendez-vous avec les enseignants : public non visé (docs/CHARTE_EDITORIALE.md) ;
  • la section « Luoghi, musei e siti culturali » — la liste des lieux en entrée
    gratuite pendant la période : des ouvertures, pas des rendez-vous ;
  • ce qui est passé (règle 5 du CLAUDE.md) : une initiative dont TOUTES les dates sont
    antérieures à `--depuis` (aujourd'hui par défaut) est écartée et comptée.

UNE FICHE PAR INITIATIVE, pas une par jour. Une visite répétée le 19, le 20, le 26 et
le 27 est un seul rendez-vous ; en faire quatre fiches fabriquerait quatre quasi-doublons
que `dedupe.py` devrait ensuite fusionner. `date_event_start` / `date_event_end`
encadrent les dates ENCORE DEVANT NOUS : lire « du 26 au 27 » un 22 septembre est juste,
« du 19 au 27 » ne l'est plus. Toutes les dates, passées comprises, restent écrites
dans la description (horaires et répliques recopiés de la brochure).

`url_source` : il n'existe pas de page par rendez-vous. On prend la page officielle de
l'événement suivie d'une ancre propre à l'initiative
(`…/plaisirs-de-culture-2026/#<titre-en-slug>`) — même principe que `gmail:<id>#<n>`
dans gmail_collect. La colonne étant UNIQUE, le script est rejouable sans doublon.

CE QU'IL NE FAIT PAS. Aucun appel à un modèle de langue ni à une API payante : pure
extraction. Il n'écrit que dans `events_raw` ; la suite du pipeline ne change pas.

USAGE
    python -m scripts.moisson_plaisirs_culture                  # DRY-RUN : lit, trie, affiche
    python -m scripts.moisson_plaisirs_culture --apply          # insère dans events_raw
    python -m scripts.moisson_plaisirs_culture --pdf brochure.pdf --depuis 2026-09-23
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sqlite3
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# La page officielle et le PDF qu'elle désigne. Le millésime est dans les deux adresses :
# c'est le seul endroit à changer l'an prochain.
URL_PAGE = "https://valledaostaheritage.com/events/plaisirs-de-culture-2026/"
URL_BROCHURE = ("https://valledaostaheritage.com/wp-content/uploads/2026/08/"
                "VDA-HERITAGE-Plaisirs-de-culture-brochure.pdf")
ANNEE = 2026

SOURCE_NAME = "Regione Valle d'Aosta — Plaisirs de Culture"
# Valeur de `territoire` en base, telle que l'écrit config/sources.txt (« Vallee-Aoste ») ;
# publisher_as._map_territoire la lit comme le slug `vallee-d-aoste`.
TERRITOIRE = "Vallee-Aoste"

MOIS_IT = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
           "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11,
           "dicembre": 12}
_MOIS = "|".join(MOIS_IT)
JOURS = r"(?:LUNED[IÌ]|MARTED[IÌ]|MERCOLED[IÌ]|GIOVED[IÌ]|VENERD[IÌ]|SABATO|DOMENICA)"

# Sections de la brochure, lues sur l'onglet vertical (texte de corps ~1, police Black).
# L'ordre compte : « ATTIVITÀ PER BAMBINI E FAMIGLIE » contient aussi « E ».
SECTIONS = (("BAMBINI", "famiglie"), ("SCUOLA", "scuola"), ("LUOGHI", "luoghi"),
            ("SITI CULTURALI", "luoghi"), ("INCONTRI", "incontri"), ("EVENTI", "eventi"),
            ("VISITE", "visite"))
ECARTEES = {
    "scuola": "section « a scuola » : visites pour les classes, public non visé",
    "luoghi": "section « luoghi » : liste des lieux en entrée libre, pas un rendez-vous",
}

# Géométrie mesurée sur la brochure 2026, RELATIVE au bord gauche de la demi-page.
MARGE = 35       # titres, descriptions, « A cura di »
RETRAIT = 47     # horaire, lieu, répliques, infos pratiques


# ─────────────────────────────── extraction PDF ───────────────────────────────

def fragments_pdf(donnees: bytes) -> list[dict]:
    """Chaque page du PDF → {"w": largeur, "frags": [{x, y, s, f, t}]}.

    pypdf est déjà dans requirements.txt (scripts/press_kits.py s'en sert). Importé ici
    seulement : le parseur, lui, travaille sur ces fragments et n'en a pas besoin — c'est
    ce qui permet à la fixture de tourner sans pypdf.
    """
    import io
    from pypdf import PdfReader

    pages = []
    for p in PdfReader(io.BytesIO(donnees)).pages:
        frags = []

        def visiteur(texte, cm, tm, fd, fs):
            if not texte.strip():
                return
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            if x == 0 and y == 0:            # fragment sans position : artefact de pypdf
                return
            taille = fs * (tm[3] or 1) * (cm[3] or 1)
            police = ((fd or {}).get("/BaseFont", "") if fd else "").split("+")[-1]
            frags.append({"x": round(x, 1), "y": round(y, 1), "s": round(taille, 1),
                          "f": police, "t": texte})

        p.extract_text(visitor_text=visiteur)
        pages.append({"w": round(float(p.mediabox.width), 1), "frags": frags})
    return pages


# ─────────────────────────────── mise en lignes ───────────────────────────────

def _gras(f: str) -> bool:
    return "Bold" in f or "Black" in f


def demi_pages(pages: list[dict]) -> list[dict]:
    """Découpe chaque double page en deux moitiés, et chaque moitié en LIGNES.

    Une ligne = les fragments de même ordonnée (à 1,5 pt près), de gauche à droite.
    Les coordonnées x sont rendues relatives au bord de la demi-page.
    """
    out = []
    for n, p in enumerate(pages, 1):
        w = p["w"]
        moities = [(0.0, w / 2), (w / 2, w)] if w > 400 else [(0.0, w)]
        for i, (a, b) in enumerate(moities):
            frs = sorted((f for f in p["frags"] if a <= f["x"] < b),
                         key=lambda f: (-f["y"], f["x"]))
            lignes, cour = [], []
            for f in frs:
                if cour and abs(f["y"] - cour[-1]["y"]) > 1.5:
                    lignes.append(cour)
                    cour = []
                cour.append(f)
            if cour:
                lignes.append(cour)
            out.append({
                "page_pdf": n, "moitie": i,
                "lignes": [{
                    "y": l[0]["y"], "x": min(f["x"] for f in l) - a,
                    "s": max(f["s"] for f in l), "s0": l[0]["s"], "f": l[0]["f"],
                    "gras": _gras(l[0]["f"]), "italique": "Italic" in l[0]["f"],
                    "t": re.sub(r"\s+", " ", "".join(f["t"] for f in sorted(l, key=lambda f: f["x"]))).strip(),
                    "frags": [dict(f, x=f["x"] - a) for f in l],
                } for l in lignes],
            })
    return out


def _page_imprimee(dp: dict) -> int | None:
    """Le folio imprimé en bas de la demi-page (corps 8, y ≈ 21)."""
    for l in dp["lignes"]:
        if l["y"] < 30 and re.fullmatch(r"\d{1,3}", l["t"]):
            return int(l["t"])
    return None


def _section(dp: dict) -> str | None:
    """La section désignée par l'onglet vertical de la demi-page, None s'il n'y en a pas."""
    for l in dp["lignes"]:
        for f in l["frags"]:
            if f["s"] <= 1.5 and "Black" in f["f"]:
                t = f["t"].upper()
                for cle, nom in SECTIONS:
                    if cle in t:
                        return nom
    return None


def _est_calendrier(dp: dict) -> bool:
    return any("ORARIO" in l["t"] and "PAGINA" in l["t"] for l in dp["lignes"])


def _jours_entete(texte: str) -> list[int]:
    """« SABATO 26 SETTEMBRE | DOMENICA 27 SETTEMBRE » → [26, 27]."""
    return [int(m.group(1)) for m in
            re.finditer(r"(\d{1,2})\s*SETTEMBRE", unicodedata.normalize("NFC", texte).upper())]


# ─────────────────────────────── dates des répliques ───────────────────────────────

_RE_HEURE = re.compile(r"\b(\d{1,2})[.:](\d{2})\b")


def dates_repliques(texte: str, annee: int = ANNEE) -> list[tuple[str, str]]:
    """« REPLICHE: da sabato 19 settembre a sabato 26 settembre dalle 13.00… »
    → [(date ISO, heure du premier créneau), …] — chaque jour de la plage.

    L'heure d'une date est la PREMIÈRE heure écrite après sa mention (ou après la fin de
    sa plage) : « domenica 20, sabato 26 e domenica 27 settembre ore 10.15 » donne 10.15
    aux trois. C'est ainsi que la brochure les écrit, sans exception relevée en 2026.
    """
    t = texte.lower()
    ancres: list[tuple[int, int, int]] = []   # (position, mois, jour)
    plages = list(re.finditer(
        rf"\bda\s+\w+\s+(\d{{1,2}})\s+({_MOIS})\s+a\s+\w+\s+(\d{{1,2}})\s+({_MOIS})", t))
    dans_plage = set()
    for m in plages:
        d1 = dt.date(annee, MOIS_IT[m.group(2)], int(m.group(1)))
        d2 = dt.date(annee, MOIS_IT[m.group(4)], int(m.group(3)))
        d = d1
        while d <= d2:
            ancres.append((m.end(), d.month, d.day))
            d += dt.timedelta(days=1)
        dans_plage.update(range(m.start(), m.end()))
    for m in re.finditer(rf"(\d{{1,2}})\s+({_MOIS})", t):
        if m.start() in dans_plage:
            continue
        ancres.append((m.end(), MOIS_IT[m.group(2)], int(m.group(1))))
    out = {}
    for pos, mois, jour in ancres:
        h = _RE_HEURE.search(t, pos)
        iso = f"{annee}-{mois:02d}-{jour:02d}"
        out.setdefault(iso, f"{int(h.group(1)):02d}:{h.group(2)}" if h else "")
    return sorted(out.items())


def _premiere_heure(texte: str) -> str:
    h = _RE_HEURE.search(texte or "")
    return f"{int(h.group(1)):02d}:{h.group(2)}" if h else ""


# ─────────────────────────────── les fiches ───────────────────────────────

def parse_brochure(pages: list[dict], annee: int = ANNEE) -> dict:
    """Les fiches de la brochure, et de quoi dire d'où vient un éventuel zéro.

    Rend {"entrees": [...], "demi_pages": n, "calendrier": [...], "alerte": str|None}.
    Chaque entrée : titre, section, page (folio imprimé), jours (ISO → heure), horaire,
    lieu, ville, description, repliques, pratique, organisateur.
    """
    dps = demi_pages(pages)
    entrees, calendrier = [], []
    section, jours_courants = None, []
    cour = None

    def clore():
        nonlocal cour
        if cour:
            entrees.append(cour)
        cour = None

    for dp in dps:
        if _est_calendrier(dp):
            clore()
            calendrier.extend(_parse_calendrier(dp, annee))
            continue
        s = _section(dp)
        if s and s != section:
            section = s
            jours_courants = []      # chaque section rouvre sur son propre en-tête de jour
        folio = _page_imprimee(dp)
        etat = None
        for l in dp["lignes"]:
            t = l["t"]
            if l["y"] < 30 and re.fullmatch(r"\d{1,3}", t):
                continue                                   # folio
            if l["s"] <= 1.5:
                continue                                   # onglet de section
            # GRAND en-tête de jour : il décide. Le petit (corps 8, haut de page) résume.
            if l["s"] >= 12 and re.search(JOURS, unicodedata.normalize("NFC", t).upper()) \
                    and _jours_entete(t):
                clore()
                jours_courants = _jours_entete(t)
                continue
            if l["y"] > 580 and l["s"] <= 8.5 and _jours_entete(t):
                continue                                   # en-tête courant
            # TITRE : gras corps 10 à la marge. Une ligne de titre qui suit une autre
            # ligne de titre la prolonge (titres sur deux ou trois lignes).
            # (« CONNE|X|IONS » : le X est en corps 13, d'où la taille du PREMIER fragment)
            if l["gras"] and 9.5 <= l["s0"] <= 11 and abs(l["x"] - MARGE) < 4:
                if cour and etat == "titre":
                    cour["titre"] += " " + t
                    continue
                clore()
                cour = {"titre": t, "section": section or "inaugurazione", "page": folio,
                        "page_pdf": dp["page_pdf"],
                        "jour_entete": [f"{annee}-09-{j:02d}" for j in jours_courants],
                        "horaire": "", "lieu_brut": "", "repliques": "", "description": "",
                        "pratique": "", "organisateur": ""}
                etat = "titre"
                continue
            if not cour or l["s"] < 7:
                continue                                   # exposants, décor
            retrait = abs(l["x"] - RETRAIT) < 4
            marge = abs(l["x"] - MARGE) < 4
            if retrait and l["gras"] and not cour["horaire"] and etat in ("titre", "sous"):
                cour["horaire"] = t
                etat = "horaire"
            elif marge and l["gras"] and etat in ("titre", "sous"):
                cour["description"] += t + " "             # sous-titre (distribution…)
                etat = "sous"
            elif retrait and etat in ("horaire", "lieu") and not l["gras"] \
                    and not t.upper().startswith(("REPLIC", "INFO")) and "Light" in l["f"]:
                cour["lieu_brut"] += t + " "
                etat = "lieu"
            elif retrait and t.upper().startswith("REPLIC"):
                cour["repliques"] = t
                etat = "repliques"
            elif retrait and etat == "repliques":
                cour["repliques"] += " " + t
            elif marge and l["italique"] and t.startswith("A cura"):
                cour["organisateur"] = t
                etat = "cura"
            elif marge and etat == "cura":
                cour["organisateur"] += " " + t
            elif marge:
                cour["description"] += t + " "
                etat = "description"
            elif retrait:
                cour["pratique"] += t + " "
                etat = "pratique"
        # une fiche ne déborde pas sur la demi-page suivante dans cette brochure
        clore()

    for e in entrees:
        _finaliser(e, annee)

    alerte = None
    if not entrees:
        alerte = (f"AUCUNE fiche reconnue sur {len(dps)} demi-page(s) lue(s) : la mise en "
                  "page a changé (ou ce n'est pas la brochure). Ce zéro n'est PAS une "
                  "absence de rendez-vous.")
    return {"entrees": entrees, "demi_pages": len(dps), "calendrier": calendrier,
            "alerte": alerte}


def _propre(t: str) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    return re.sub(r"(\w) ?(['’]) ?(\w)", r"\1\2\3", t)       # « D 'AOSTA » → « D'AOSTA »


def _finaliser(e: dict, annee: int) -> None:
    e["titre"] = _propre(e["titre"])
    e["description"] = _propre(e["description"])
    e["pratique"] = _propre(e["pratique"])
    e["repliques"] = _propre(e["repliques"])
    org = _propre(e["organisateur"])
    e["organisateur"] = re.sub(r"^A cura (?:dall['’]|dalla|dal|dell['’]|della|dello|delle|degli|dei|del|di)\s*",
                               "", org, flags=re.I).strip()
    lieu = _propre(e["lieu_brut"]).rstrip(", ")
    e["lieu_complet"] = lieu
    ville, _, reste = lieu.partition(",")
    e["ville"] = ville.strip().title() if ville.isupper() or ville.strip().isupper() else ville.strip()
    e["lieu"] = reste.strip()
    # jours : ceux de l'en-tête, plus les répliques ; l'heure vient de l'horaire du jour
    jours = {d: _premiere_heure(e["horaire"]) for d in e["jour_entete"]}
    for iso, h in dates_repliques(e["repliques"].split(":", 1)[-1], annee):
        jours.setdefault(iso, h)
    e["jours"] = dict(sorted(jours.items()))


# ─────────────────────────────── le calendrier (contre-épreuve) ───────────────────────────────

def _parse_calendrier(dp: dict, annee: int) -> list[dict]:
    """Les lignes du calendrier récapitulatif : jour, horaire, titre, lieu, folio.

    Tableau à quatre colonnes (ORARIO · TITOLO · LUOGO · PAGINA). Une ligne s'ancre sur
    son numéro de page ; chaque fragment de corps 6 est rattaché à l'ancre la plus
    proche verticalement. Le jour est le dernier en-tête gras (corps 8) au-dessus.
    """
    frags = [f for l in dp["lignes"] for f in l["frags"]]
    entetes = sorted(((f["y"], _jours_entete(f["t"])) for f in frags
                      if f["s"] >= 7.5 and "Bold" in f["f"] and _jours_entete(f["t"])
                      and re.search(JOURS, f["t"].upper())), reverse=True)
    ancres = [f for f in frags if 5 <= f["s"] <= 7 and f["x"] > 285
              and re.fullmatch(r"\s*\d{1,3}\s*", f["t"]) and f["y"] < 560]
    cellules = [f for f in frags if 5 <= f["s"] <= 7 and f["x"] <= 285 and 25 < f["y"] < 560]
    lignes = []
    for a in ancres:
        mien = [c for c in cellules
                if min(ancres, key=lambda b: abs(b["y"] - c["y"])) is a and abs(c["y"] - a["y"]) <= 9]
        dessus = [j for y, j in entetes if y > a["y"]]
        jour = dessus[-1][0] if dessus else None

        def colonne(x0, x1):
            parts = sorted((c for c in mien if x0 <= c["x"] < x1), key=lambda c: (-c["y"], c["x"]))
            txt, y_prec = "", None
            for c in parts:
                sep = " " if (y_prec is not None and abs(c["y"] - y_prec) > 1.5) else ""
                txt += sep + c["t"]
                y_prec = c["y"]
            return re.sub(r"\s+", " ", txt).strip()

        lignes.append({"jour": f"{annee}-09-{jour:02d}" if jour else "",
                       "horaire": colonne(0, 80), "titre": colonne(80, 185),
                       "lieu": colonne(185, 286), "page": int(a["t"])})
    return lignes


def _cle(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"[^a-z0-9]", "", t.encode("ascii", "ignore").decode())


def _proche(a: str, b: str) -> float:
    ka, kb = _cle(a), _cle(b)
    if not ka or not kb:
        return 0.0
    if ka in kb or kb in ka:
        return 1.0
    return SequenceMatcher(None, ka, kb).ratio()


def confronter(entrees: list[dict], calendrier: list[dict]) -> dict:
    """Fiches et calendrier se contrôlent l'un l'autre, DANS LES DEUX SENS.

    • chaque ligne du calendrier doit retrouver une fiche (même folio, titre voisin) qui
      porte son jour → sinon `sans_fiche` ou `jour_absent` ;
    • chaque jour d'une fiche que le calendrier couvre doit y figurer → sinon
      `jour_en_trop`. Seule exception, mesurée : le calendrier écrit une plage en une
      ligne (« 13.00 - 18.00 fino al 26 settembre », deux cas en 2026), et les jours de
      cette plage ne sont pas en trop.

    Le second sens n'est pas décoratif. Sans lui, une version fautive qui laissait
    l'en-tête courant « LUNEDÌ 21 | MARTEDÌ 22 » décider du jour donnait à « Il tesoro
    della cattedrale » NEUF jours au lieu d'un — et le contrôle affichait « 0 écart ».

    Sert aussi à reprendre le titre du calendrier, en casse normale là où la brochure
    met des capitales.
    """
    sans_fiche, jour_absent, jour_en_trop = [], [], []
    lignes_de: dict[int, list[dict]] = {}
    for c in calendrier:
        cands = [e for e in entrees if e["page"] == c["page"]]
        best = max(cands, key=lambda e: _proche(e["titre"], c["titre"]), default=None)
        if not best or _proche(best["titre"], c["titre"]) < 0.6:
            sans_fiche.append(c)
            continue
        best.setdefault("titre_calendrier", c["titre"])
        lignes_de.setdefault(id(best), []).append(c)
        if c["jour"] and c["jour"] not in best["jours"]:
            jour_absent.append((c, best))
    for e in entrees:
        lignes = lignes_de.get(id(e))
        if not lignes:
            continue                      # hors calendrier (famiglie, scuola…) : rien à confronter
        couverts = set()
        for c in lignes:
            couverts.add(c["jour"])
            m = re.search(r"fino al (\d{1,2}) settembre", c["horaire"])
            if m and c["jour"]:
                d0 = int(c["jour"][-2:])
                couverts.update(f"{c['jour'][:8]}{j:02d}" for j in range(d0, int(m.group(1)) + 1))
        for d in e["jours"]:
            if d not in couverts:
                jour_en_trop.append((d, e))
    return {"sans_fiche": sans_fiche, "jour_absent": jour_absent, "jour_en_trop": jour_en_trop}


# ─────────────────────────────── sélection ───────────────────────────────

def _slug(t: str) -> str:
    t = re.sub(r"['’]", " ", t.lower())                         # « dall’arca » → dall-arca
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:80]


def _titre_affiche(e: dict) -> str:
    t = _propre(e.get("titre_calendrier") or "")
    if t:
        return re.sub(r"^Inaugurazione:\s*", "", t)
    # hors calendrier (section famiglie) : la brochure n'a que des capitales
    t = e["titre"]
    return t[:1] + t[1:].lower() if t.isupper() else t


def selectionner(entrees: list[dict], depuis: str) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(fiches à écrire, [(entrée écartée, motif)]). Rien n'est écarté sans motif."""
    garder, ecartes = [], []
    vus = set()
    for e in entrees:
        if e["page"] is None:
            # la 4e de couverture (« Regione autonoma Valle d'Aosta », en gras corps 10)
            # a la forme d'un titre ; elle n'a pas de folio, aucune fiche n'en manque.
            ecartes.append((e, "hors programme : couverture ou colophon, sans folio"))
            continue
        if e["section"] in ECARTEES:
            ecartes.append((e, ECARTEES[e["section"]]))
            continue
        if not e["titre"] or not e["jours"]:
            ecartes.append((e, "incomplète : sans titre ou sans date lisible"))
            continue
        a_venir = [d for d in e["jours"] if d >= depuis]
        if not a_venir:
            ecartes.append((e, f"passée : dernière date {max(e['jours'])} < {depuis}"))
            continue
        titre = _titre_affiche(e)
        ancre = _slug(titre)
        if ancre in vus:                         # deux fiches de même titre : on distingue
            ancre = f"{ancre}-p{e['page']}"
        vus.add(ancre)
        debut, fin = min(a_venir), max(a_venir)
        garder.append({
            "titre": titre,
            "date_start": debut, "date_end": fin,
            "time_start": e["jours"][debut],
            "lieu": e["lieu"], "ville": e["ville"],
            "organisateur": e["organisateur"],
            "url": f"{URL_PAGE}#{ancre}",
            "section": e["section"], "page": e["page"],
            "tous_jours": list(e["jours"]),
            "description": _description(e),
        })
    return garder, ecartes


def _description(e: dict) -> str:
    """Le texte source, tel que la brochure le donne — c'est la matière de l'enrichissement.

    La page officielle ne dit rien de chaque rendez-vous : sans ce texte-ci, `enrich.py`
    n'aurait à lire que la présentation générale de la manifestation.
    """
    morceaux = [f"{e['lieu_complet']} — {e['description']}".strip(" —")]
    jours = ", ".join(dt.date.fromisoformat(d).strftime("%d/%m") for d in e["jours"])
    morceaux.append(f"Plaisirs de Culture en Vallée d'Aoste 2026 (Giornate Europee del "
                    f"Patrimonio). Date: {jours}. Orario: {e['horaire']}.")
    if e["repliques"]:
        morceaux.append(e["repliques"])
    if e["pratique"]:
        morceaux.append(e["pratique"])
    if e["organisateur"]:
        morceaux.append(f"A cura di: {e['organisateur']}")
    return "\n\n".join(m for m in morceaux if m)


# ─────────────────────────────── écriture ───────────────────────────────

def ecrire(conn: sqlite3.Connection, fiches: list[dict]) -> int:
    """INSERT OR IGNORE dans events_raw. Rend le nombre de lignes réellement posées.

    La date va dans `date_start` ET dans `date_event_start`/`date_event_end` : c'est la
    leçon de moisson_gep du 22/09 (`publish_batch_as` exige `date_event_start`, la
    règle 5 juge sur `date_event_end`, et `dates.py` ne touche qu'aux fiches sans date).
    """
    pose = 0
    for f in fiches:
        cur = conn.execute("""
            INSERT OR IGNORE INTO events_raw
                (title, description, date_start, date_event_start, date_event_end, time_start,
                 lieu, ville, territoire, url_source, organisateur, source_name, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (f["titre"], f["description"], f["date_start"], f["date_start"], f["date_end"],
              f["time_start"], f["lieu"], f["ville"], TERRITOIRE, f["url"],
              f["organisateur"], SOURCE_NAME, "institutionnel"))
        pose += cur.rowcount
    conn.commit()
    return pose


def _telecharge(url: str, essais: int = 4) -> bytes:
    """Trois nouvelles tentatives, chacune annoncée.

    Mesuré le 22/09 : valledaostaheritage.com a coupé 5 requêtes sur 16 (« Connection
    reset by peer », curl comme urllib), et chaque fois la suivante est passée. Un seul
    essai ferait donc échouer la moisson environ une fois sur trois, pour une raison qui
    n'a rien à voir avec le programme.
    """
    import time
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    })
    for n in range(1, essais + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except OSError as e:
            if n == essais:
                raise
            print(f"  … essai {n}/{essais} coupé ({e}), nouvel essai dans {3 * n} s")
            time.sleep(3 * n)
    raise RuntimeError("inatteignable")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit en base (sinon : dry-run)")
    ap.add_argument("--db", default=str(RACINE / "data" / "events.db"))
    ap.add_argument("--pdf", help="brochure déjà téléchargée (sinon : URL officielle)")
    ap.add_argument("--depuis", default=dt.date.today().isoformat(),
                    help="première date encore utile, AAAA-MM-JJ (défaut : aujourd'hui)")
    args = ap.parse_args()

    try:
        donnees = Path(args.pdf).read_bytes() if args.pdf else _telecharge(URL_BROCHURE)
    except Exception as e:  # le zéro doit dire d'où il vient
        print(f"  ⚠ brochure illisible ({args.pdf or URL_BROCHURE}) : {e}")
        print("\nAUCUNE page lue — c'est un échec de lecture, pas une absence d'événements.")
        return 1

    r = parse_brochure(fragments_pdf(donnees))
    print(f"  {r['demi_pages']} demi-pages lues · {len(r['entrees'])} fiche(s) reconnue(s) · "
          f"{len(r['calendrier'])} ligne(s) de calendrier")
    if r["alerte"]:
        print(f"\n{r['alerte']}")
        return 2

    ctl = confronter(r["entrees"], r["calendrier"])
    print(f"  contre-épreuve calendrier : {len(r['calendrier']) - len(ctl['sans_fiche'])} ligne(s) "
          f"retrouvée(s), {len(ctl['sans_fiche'])} sans fiche, "
          f"{len(ctl['jour_absent'])} jour(s) du calendrier absent(s) de la fiche, "
          f"{len(ctl['jour_en_trop'])} jour(s) de fiche absent(s) du calendrier")
    for c in ctl["sans_fiche"]:
        print(f"    ⚠ sans fiche : {c['jour']} p.{c['page']} {c['titre'][:60]}")
    for c, e in ctl["jour_absent"]:
        print(f"    ⚠ jour absent : {c['jour']} p.{c['page']} {c['titre'][:50]} "
              f"(fiche : {', '.join(e['jours'])})")
    for d, e in ctl["jour_en_trop"]:
        print(f"    ⚠ jour en trop : {d} p.{e['page']} {e['titre'][:50]} (absent du calendrier)")

    fiches, ecartes = selectionner(r["entrees"], args.depuis)
    motifs: dict[str, int] = {}
    for _, m in ecartes:
        cle = m.split(":")[0].strip()
        motifs[cle] = motifs.get(cle, 0) + 1
    print(f"\n{len(r['entrees'])} initiative(s) lue(s) → {len(fiches)} retenue(s), "
          f"{len(ecartes)} écartée(s)" + (" : " + ", ".join(f"{n} {k}" for k, n in motifs.items())
                                          if motifs else ""))
    for e, m in ecartes:
        print(f"    écartée p.{e['page']} [{e['section']}] {e['titre'][:55]} — {m}")

    if not Path(args.db).exists():
        print(f"\nbase introuvable : {args.db}")
        return 1
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA busy_timeout=30000")
    deja = {row[0] for row in conn.execute(
        "SELECT url_source FROM events_raw WHERE url_source IN (%s)" % ",".join("?" * len(fiches)),
        [f["url"] for f in fiches]).fetchall()} if fiches else set()
    neufs = [f for f in fiches if f["url"] not in deja]

    print(f"\ndéjà en base : {len(deja)} · à insérer : {len(neufs)} (à partir du {args.depuis})\n")
    for f in neufs:
        plage = f["date_start"] if f["date_start"] == f["date_end"] else f"{f['date_start']}→{f['date_end'][5:]}"
        print(f"  {plage:<16} {f['time_start'] or '--:--'} [{f['section'][:4]}] "
              f"{f['ville'][:20]:<20} {f['titre'][:62]}")

    if not args.apply:
        print(f"\nDRY-RUN — rien n'a été écrit. Relancer avec --apply pour insérer ces {len(neufs)}.")
        conn.close()
        return 0

    pose = ecrire(conn, neufs)
    # Règle 6 : on recompte en base, on n'annonce pas la longueur d'une liste.
    verif = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE source_name = ?", (SOURCE_NAME,)).fetchone()[0]
    conn.close()
    print(f"\n{pose} insérée(s). En base pour « {SOURCE_NAME} » : {verif} fiche(s) au total.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
