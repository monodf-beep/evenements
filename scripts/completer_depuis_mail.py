#!/usr/bin/env python3
"""Lieu, ville et image des fiches venues d'un mail — relus dans le mail, sans modèle.

MESURÉ LE 2026-09-08 EN PRODUCTION. Parmi 108 fiches approuvées, à venir et incomplètes, une
vingtaine viennent d'une newsletter SANS AUCUN lien d'article : `url_source` vaut
« gmail:<message_id>#<rang> » et `gmail_relink` n'a rien trouvé à rattacher. 5103 « Visite
méditative au Musée des Arts Asiatiques » (manque date, ville, image), 5109 « Les Charmettes
s'éveillent en famille », 5263 « 43° Raduno Internazionale dello Spazzacamino », 5312 « La
Filarmonica della Scala a Torino »… Il leur manque l'IMAGE (toutes), souvent la VILLE ou le
LIEU. La date est déjà servie par `dates_depuis_mail` (cron 08:47). Pour le reste il n'y a
PAS de page à lire : la seule matière est le mail. Franck : « les scripts travaillent au
max » avant tout agent payant.

CE QUE FAIT CE SCRIPT, et rien d'autre :

  1. LIEU et VILLE — `utils/mail_lieux.py` : un lieu CONNU (registre d'`utils.lieux`, lieux
     par défaut de `config/sources.txt`) nommé dans l'annonce → lieu + ville ; sinon une
     COMMUNE DU PÉRIMÈTRE nommée dans l'annonce → ville, et le lieu en plus si nos propres
     fiches connaissent ce lieu DANS CETTE VILLE. L'annonce, pas le mail : la fenêtre part
     du titre de la fiche et s'arrête au titre de l'annonce voisine — les autres fiches du
     même mail, tous statuts confondus (c'est plus que `dates_depuis_mail`, qui ne borne
     qu'avec les fiches encore sans date : une voisine rejetée borne aussi bien).
  2. IMAGE — `utils/mail_html.py` : les <img> du BLOC de l'annonce dans le HTML du mail,
     jamais la première image du mail (l'incident des 40 fiches au même en-tête Mailinblue,
     cf. gmail_collect.parse_message). Puis les filtres qui existent déjà : hôte de traçage
     (`moisson_officielle._est_traqueur`), logo/icône (`utils.sources.is_logo_image`),
     habillage (`utils.images._is_chrome`), pixel déclaré 1×1, et la mesure réelle
     (`utils.images.remote_dims`, petit côté ≥ 400 px, pas une forme de bandeau).
     Écrit `url_image` + `image_source='mail'`.

D'OÙ VIENT LE HTML. `gmail_collect` ne gardait que le TEXTE du mail (`mail_corps`, liens
compris, images exclues). Depuis le 08/09 il garde aussi le HTML, une fois par message
(`gmail_html`). Pour les fiches déjà en base, le mail est retéléchargé dans Gmail par son
identifiant — le chemin de `dates_depuis_mail` — et mémorisé : la fois suivante ne coûte
plus rien.

CE QU'IL NE FAIT JAMAIS : deviner. Pas de lieu connu ni de commune dans l'annonce → rien.
Deux communes → rien. Bloc HTML partagé avec une autre annonce → rien. Chaque zéro est
affiché avec le nombre de cas qui se sont présentés, et chaque écriture avec la phrase
d'où elle vient.

CE QU'IL NE POSE PAS : aucun état. Une fiche que le mail ne renseigne pas reste dans la
file « À compléter », et repasse ici chaque matin. Ce n'est pas le refus qui se rejoue à
l'identique (règle 3) : ce qui change d'un jour à l'autre, c'est le REGISTRE — un lieu
tranché dans config/lieux_villes.json, une note de savoir, une ligne de sources.txt, une
fiche voisine désormais pourvue d'un lieu — et le passage suivant le lit. Le HTML, lui, ne
change pas : les images d'une fiche refusée hier seront refusées demain, au prix d'une
mesure réseau par candidate ; c'est assumé, pour l'instant, et compté.

RÈGLE 4 : dry-run par défaut. RÈGLE 5 : seulement ce qui est devant nous. RÈGLE 6 : le
bilan est recompté en base, sur le périmètre de la pastille.

  .venv/bin/python -m scripts.completer_depuis_mail              # simulation
  .venv/bin/python -m scripts.completer_depuis_mail 5103 5109    # ces fiches seulement
  .venv/bin/python -m scripts.completer_depuis_mail --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.logger import get_logger  # noqa: E402
from utils import images as _images  # noqa: E402
from utils import lieux as _lieux  # noqa: E402
from utils import mail_html, mail_lieux  # noqa: E402
from utils.mail_dates import message_id_de  # noqa: E402
from utils.sources import is_logo_image  # noqa: E402

log = get_logger("completer_mail")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

APPROUVES = ("evaluated", "published_cs", "published_sub")
# Petit côté minimal, en pixels : le seuil de la moisson officielle pour une image de page
# (`moisson_officielle`, « min(w, h) >= 400 »), repris tel quel.
MIN_COTE = 400
# Candidates MESURÉES (téléchargées) par fiche, au plus : au-delà, on brûle du réseau sur
# des vignettes de pied de page.
MAX_MESURES = 3


# ─────────────────────────────── sélection ───────────────────────────────────

def _a_traiter(conn: sqlite3.Connection, today: str, ids: list[int]) -> list[dict]:
    """Fiches issues d'un mail, approuvées, encore devant nous (à venir, en cours,
    récurrentes ou pas encore datées — règle 5), à qui il manque lieu, ville ou image."""
    sql = ("SELECT * FROM events_raw WHERE url_source LIKE 'gmail:%' "
           "AND statut IN ('evaluated','published_cs','published_sub') "
           "AND duplicate_of IS NULL AND COALESCE(translation_of,0)=0 "
           "AND (COALESCE(recurring,0)=1 OR COALESCE(date_event_end, date_event_start, '')='' "
           "     OR COALESCE(date_event_end, date_event_start) >= ?)")
    params: list = [today]
    if ids:
        sql += f" AND id IN ({','.join('?' * len(ids))})"
        params.extend(ids)
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]
    return [ev for ev in rows if _besoins(ev)]


def _besoins(ev: dict) -> list[str]:
    """Ce que ce script peut remplir sur cette fiche : 'lieu', 'ville', 'image'.

    Une bannière générique compte comme une place vide pour l'image — même règle que la
    moisson officielle (« UNE BANNIÈRE COMPTE COMME UNE PLACE VIDE », 2026-08-11)."""
    out = []
    if not ev.get("multi_lieux"):
        if not (ev.get("lieu") or "").strip():
            out.append("lieu")
        if not (ev.get("ville") or "").strip():
            out.append("ville")
    if not (ev.get("url_image") or "").strip() or (ev.get("image_source") or "") == "banner":
        out.append("image")
    return out


def _titres_du_mail(conn: sqlite3.Connection, mid: str) -> list[str]:
    """TOUS les titres nés de ce mail, quel que soit leur statut : chacun borne l'annonce
    de ses voisins."""
    return [r[0] or "" for r in conn.execute(
        "SELECT title FROM events_raw WHERE url_source LIKE ?", (f"gmail:{mid}%",))]


def _lieux_de_la_base(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
    """{lieu plié : {canon ville : lieu tel qu'écrit}} — les lieux que NOS fiches approuvées
    connaissent, avec leur ville. Ne sert qu'à confirmer un lieu dans une ville que le
    texte nomme (utils.mail_lieux, gisement ③). Les noms génériques sont écartés."""
    out: dict[str, dict[str, str]] = {}
    for lieu, ville in conn.execute(
            "SELECT lieu, ville FROM events_raw WHERE COALESCE(lieu,'')<>'' "
            "AND COALESCE(ville,'')<>'' AND statut IN ('evaluated','published_cs','published_sub') "
            "AND duplicate_of IS NULL"):
        cle = _lieux.plie(lieu)
        if len(cle) < 8 or _lieux.est_generique(lieu):
            continue
        out.setdefault(cle, {}).setdefault(_lieux.canon(ville), lieu.strip())
    return out


# ─────────────────────────────── matière ─────────────────────────────────────

def _telecharger(mid: str) -> dict | None:
    """Le mail dans Gmail : {"html": …, "texte": …} ou None s'il est illisible. Isolé pour
    que la fixture le remplace — aucun réseau dans les tests."""
    from scripts.gmail_collect import build_service, html_du_message, parse_message
    service = build_service()
    raw = service.users().messages().get(userId="me", id=mid, format="full").execute()
    return {"html": html_du_message(raw), "texte": parse_message(raw).get("body", "")}


def _dims(url: str) -> tuple[int, int]:
    return _images.remote_dims(url)


def _texte_depuis(html: str, corps: str) -> str:
    """Le texte à lire pour le lieu : celui du HTML entier quand on l'a (le `mail_corps`
    est tronqué à 6 000 caractères, et la huitième annonce d'une lettre est au-delà),
    sinon le corps gardé. Sans les adresses web, dans les deux cas."""
    if html:
        from scripts.gmail_collect import _strip_html
        return mail_lieux.sans_urls(_strip_html(html))
    return mail_lieux.sans_urls(corps or "")


# ─────────────────────────────── images ──────────────────────────────────────

def _refus_statique(c: dict) -> str:
    """Motif de refus lisible SANS réseau, "" si la candidate mérite d'être mesurée."""
    src = c["src"]
    low = src.lower()
    if not low.startswith("http"):
        return "pas une adresse web (cid:/data:)"
    if re.search(r"\.(gif|svg)(\?|#|$)", low):
        return "format gif/svg (animation, pictogramme ou pixel)"
    from scripts.moisson_officielle import _est_traqueur
    if _est_traqueur(src):
        return "hôte de traçage"
    if is_logo_image(src):
        return "logo/icône d'après le nom de fichier"
    if _images._is_chrome(src):
        return "habillage de gabarit"
    def _px(v: str) -> int:
        m = re.match(r"\s*(\d+)", v or "")
        return int(m.group(1)) if m else 0
    w, h = _px(c.get("largeur", "")), _px(c.get("hauteur", ""))
    if (w and w <= 2) or (h and h <= 2):
        return f"pixel déclaré {w or '?'}×{h or '?'}"
    if (w and w < 100) or (h and h < 100):
        return f"icône déclarée {w or '?'}×{h or '?'} px"
    return ""


def _choisir_image(candidats: list[dict], min_cote: int) -> tuple[str, str, list[str]]:
    """(url retenue, pourquoi, refus) — la première candidate qui passe tout, dans l'ordre
    de confiance de `mail_html.images_du_titre` ; chaque refus garde son motif."""
    refus: list[str] = []
    mesures = 0
    for c in candidats:
        motif = _refus_statique(c)
        if motif:
            refus.append(f"{motif} — {c['src'][:70]}")
            continue
        if mesures >= MAX_MESURES:
            refus.append(f"non mesurée (plafond {MAX_MESURES}) — {c['src'][:70]}")
            continue
        mesures += 1
        w, h = _dims(c["src"])
        if not w or not h:
            refus.append(f"injoignable ou illisible — {c['src'][:70]}")
            continue
        if min(w, h) < min_cote:
            refus.append(f"trop petite {w}×{h} (petit côté < {min_cote}) — {c['src'][:70]}")
            continue
        if _images.looks_like_banner_shape(w, h):
            refus.append(f"forme de bandeau ou carré {w}×{h} — {c['src'][:70]}")
            continue
        return c["src"], f"{c['pourquoi']}, {w}×{h}", refus
    return "", "", refus


# ─────────────────────────────── main ────────────────────────────────────────

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", type=int, help="fiches à traiter (défaut : toutes)")
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    ap.add_argument("--cap", type=int, default=50, help="nombre max de mails téléchargés")
    ap.add_argument("--min-cote", type=int, default=MIN_COTE,
                    help=f"petit côté minimal d'une image, en px (défaut {MIN_COTE})")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        log.error("Base introuvable : %s", DB_PATH)
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    from scripts.gmail_collect import ensure_colonne_corps, ensure_table_html, html_memorise
    ensure_colonne_corps(conn)
    ensure_table_html(conn)
    today = date.today().isoformat()

    approuvees_gmail = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE url_source LIKE 'gmail:%' AND statut IN "
        "('evaluated','published_cs','published_sub') AND duplicate_of IS NULL").fetchone()[0]
    cibles = _a_traiter(conn, today, args.ids)
    print(f"═══ {len(cibles)} fiche(s) « gmail: » approuvées, encore devant nous, à qui il "
          f"manque lieu, ville ou image (sur {approuvees_gmail} fiches gmail approuvées, "
          f"tous horizons) ═══\n")
    if not cibles:
        print("Rien à faire : 0 cas présenté.")
        conn.close()
        return 0

    lieux_base = _lieux_de_la_base(conn)
    # Un mail porte souvent plusieurs fiches : on le lit UNE fois.
    matiere: dict[str, dict] = {}          # mid -> {"html", "texte", "origine"}
    titres_par_mail: dict[str, list[str]] = {}
    telecharges = 0
    ecritures: list[tuple[int, dict, str]] = []     # (id, champs, phrase)
    compte = Counter()
    refus_images = Counter()

    for ev in cibles:
        eid, titre = ev["id"], (ev.get("title") or "")
        mid = message_id_de(ev["url_source"])
        besoins = _besoins(ev)
        compte["fiches"] += 1
        for b in besoins:
            compte[f"besoin {b}"] += 1
        if not mid:
            compte["adresse gmail: sans identifiant"] += 1
            print(f"  [{eid:>5}] adresse « {ev['url_source'][:40]} » sans identifiant de mail")
            continue
        if mid not in titres_par_mail:
            titres_par_mail[mid] = _titres_du_mail(conn, mid)
        if mid not in matiere:
            html = html_memorise(conn, mid)
            corps = (ev.get("mail_corps") or "").strip()
            origine = "mémoire" if (html or corps) else ""
            if not html and telecharges < args.cap:
                telecharges += 1
                try:
                    dl = _telecharger(mid)
                except Exception as exc:                   # message supprimé, droits…
                    log.warning("[%s] mail %s illisible : %s", eid, mid, exc)
                    dl = None
                if dl:
                    html = dl.get("html") or ""
                    corps = corps or (dl.get("texte") or "")
                    origine = "Gmail"
            matiere[mid] = {"html": html, "texte": _texte_depuis(html, corps),
                            "corps": corps, "origine": origine, "neuf": origine == "Gmail"}
        m = matiere[mid]
        voisins = [t for t in titres_par_mail[mid] if t and t != titre]
        champs: dict = {}
        phrases: list[str] = []

        # ── lieu / ville ──
        if ("lieu" in besoins or "ville" in besoins):
            if not m["texte"]:
                compte["lieu/ville : pas de texte de mail disponible"] += 1
                phrases.append("lieu/ville : aucun texte de mail disponible")
            else:
                res = mail_lieux.completer(m["texte"], titre, voisins, lieux_base)
                if not res:
                    compte["lieu/ville : le mail ne nomme rien de connu près du titre"] += 1
                    phrases.append("lieu/ville : rien de connu près du titre")
                else:
                    lieu_actuel = (ev.get("lieu") or "").strip()
                    verdict, _, _ = _lieux.confronte(lieu_actuel, res["ville"]) \
                        if lieu_actuel else ("", "", "")
                    if verdict:
                        compte["ville refusée : contredit le lieu déjà en base"] += 1
                        phrases.append(f"ville « {res['ville']} » refusée : le lieu en base "
                                       f"« {lieu_actuel} » est connu ailleurs")
                    else:
                        if "ville" in besoins:
                            champs["ville"] = res["ville"]
                            compte["villes trouvées"] += 1
                        if "lieu" in besoins and res.get("lieu"):
                            champs["lieu"] = res["lieu"]
                            champs["venue_source"] = "mail"
                            compte["lieux trouvés"] += 1
                        elif "lieu" in besoins:
                            compte["lieu : ville trouvée mais aucun lieu connu nommé"] += 1
                        phrases.append("lu : " + res["motif"][:160])

        # ── image ──
        if "image" in besoins:
            if not m["html"]:
                compte["image : pas de HTML disponible (mail non mémorisé, non téléchargé)"] += 1
                phrases.append("image : pas de HTML de mail disponible")
            else:
                cands, motif = mail_html.images_du_titre(m["html"], titre, voisins)
                if not cands:
                    compte[f"image : {motif}"] += 1
                    phrases.append(f"image : {motif}")
                else:
                    url, pourquoi, refus = _choisir_image(cands, args.min_cote)
                    for r in refus:
                        refus_images[r.split(" — ")[0]] += 1
                    if url:
                        champs["url_image"] = url
                        champs["image_source"] = "mail"
                        compte["images trouvées"] += 1
                        phrases.append(f"image : {url[:80]} ({pourquoi})")
                    else:
                        compte["image : toutes les candidates refusées"] += 1
                        phrases.append(f"image : {len(cands)} candidate(s), toutes refusées")
                    for r in refus[:4]:
                        phrases.append(f"   ✗ {r}")

        marque = "✎" if champs else "·"
        print(f"  {marque} [{eid:>5}] {titre[:56]}   (manque : {', '.join(besoins)}"
              f" · mail {m['origine'] or 'indisponible'})")
        for p in phrases:
            print(f"          ↳ {p}")
        if champs:
            ecritures.append((eid, champs, "; ".join(phrases)))

    # ── bilan, avec le périmètre à côté de chaque nombre ──
    print(f"\n{compte['fiches']} fiche(s) examinée(s) · {len(matiere)} mail(s) distincts, "
          f"dont {telecharges} téléchargé(s) dans Gmail "
          f"({sum(1 for m in matiere.values() if m['origine'] == 'mémoire')} en mémoire, "
          f"{sum(1 for m in matiere.values() if not m['origine'])} indisponible(s)).")
    for cle, libelle in (("ville", "villes trouvées"), ("lieu", "lieux trouvés"),
                         ("image", "images trouvées")):
        print(f"  {cle:<6} {compte[libelle]} trouvé(e)s sur {compte[f'besoin {cle}']} "
              f"fiche(s) qui en manquent")
    autres = {k: v for k, v in compte.items()
              if not k.startswith("besoin ") and k not in ("fiches",)
              and not k.endswith("trouvées") and not k.endswith("trouvés")}
    if autres:
        print("  Pourquoi le reste n'a rien donné :")
        for k, v in sorted(autres.items(), key=lambda kv: -kv[1]):
            print(f"    {v:>3}  {k}")
    if refus_images:
        print("  Images candidates refusées, par motif :")
        for k, v in refus_images.most_common():
            print(f"    {v:>3}  {k}")

    if not args.apply:
        print(f"\nSimulation — RIEN n'a été écrit ({len(ecritures)} fiche(s) recevraient "
              f"quelque chose). Ajouter --apply pour enregistrer.")
        conn.close()
        return 0

    # ── écriture ──
    from scripts.gmail_collect import memoriser_html
    for eid, champs, _ in ecritures:
        sets = ", ".join(f"{k}=?" for k in champs)
        conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?", [*champs.values(), eid])
    html_gardes = 0
    for mid, m in matiere.items():
        if m["neuf"] and m["html"]:
            html_gardes += int(memoriser_html(conn, mid, m["html"]))
        if m["corps"]:
            conn.execute("UPDATE events_raw SET mail_corps=? WHERE url_source LIKE ? "
                         "AND COALESCE(mail_corps,'')=''", (m["corps"][:6000], f"gmail:{mid}%"))
    conn.commit()

    # RECOMPTÉ EN BASE (règle 6) : ce qui est écrit, pas ce qui était prévu.
    ids_ecrits = [eid for eid, _, _ in ecritures]
    def _n(cond: str) -> int:
        if not ids_ecrits:
            return 0
        return conn.execute(
            f"SELECT COUNT(*) FROM events_raw WHERE id IN ({','.join('?' * len(ids_ecrits))}) "
            f"AND {cond}", ids_ecrits).fetchone()[0]
    n_ville = _n("COALESCE(ville,'')<>''")
    n_lieu = _n("venue_source='mail'")
    n_img = _n("image_source='mail'")
    # `multi_lieux` est créée par le back-office (app/app.py), pas par init_db : un module
    # ne suppose pas qu'un autre chemin a déjà migré (leçon d'audit_annulations, 09/08).
    try:
        conn.execute("ALTER TABLE events_raw ADD COLUMN multi_lieux INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    from scripts.lister_a_completer import _clause
    where, params = _clause(today)
    reste = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE {where}", params).fetchone()[0]
    reste_gmail = conn.execute(
        f"SELECT COUNT(*) FROM events_raw WHERE url_source LIKE 'gmail:%' AND {where}",
        params).fetchone()[0]
    conn.close()
    print(f"\n✅ Écrit puis recompté en base sur les {len(ids_ecrits)} fiche(s) touchées : "
          f"{n_ville} ont une ville, {n_lieu} un lieu venu du mail, {n_img} une image venue "
          f"du mail.")
    print(f"   {html_gardes} HTML de mail mémorisé(s) : la prochaine relecture n'ira plus "
          f"dans Gmail pour eux.")
    print(f"   La file « À compléter » contient maintenant {reste} fiche(s) — même périmètre "
          f"que la pastille du back-office — dont {reste_gmail} venue(s) d'un mail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
