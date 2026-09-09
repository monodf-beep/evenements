#!/usr/bin/env python3
"""Fixture : lieu, ville et image relus dans le mail — et surtout ce qui ne doit PAS s'écrire.

Un mail HTML de six annonces (calqué sur la lettre des musées de Chambéry et sur les fiches
5103, 5106, 5090, 5111, 5265 de la file du 2026-09-08), un mail « à plat » sans blocs, un mail
introuvable. Base jetable (scripts.scraper_events.init_db), aucun réseau : le téléchargement
Gmail et la mesure des images sont remplacés.

CE QUE LA FIXTURE PROTÈGE, dans l'ordre d'importance :
  • qu'aucune fiche ne reçoive la VILLE de l'annonce voisine (le titre d'une fiche rejetée
    borne aussi) ;
  • que RIEN ne s'écrive quand le mail ne nomme ni lieu connu ni commune du périmètre —
    c'est le cas frontière qui doit PASSER (règle 3, fixture du 06/08) : « salle des fêtes »,
    « église Saint-Pierre », « Contes pour enfants », deux communes dans la même annonce ;
  • qu'un pixel de suivi, un logo et une image trop petite soient refusés, et qu'une vraie
    image du bloc de l'annonce soit acceptée ;
  • qu'en simulation RIEN ne soit écrit, et qu'après --apply le bilan soit celui de la base.

Lancer : .venv/bin/python -m tests.test_completer_depuis_mail
"""
import base64
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db  # noqa: E402
from scripts import gmail_collect as gc  # noqa: E402
import scripts.completer_depuis_mail as cdm  # noqa: E402
from utils import mail_html, mail_lieux  # noqa: E402
from utils.mail_dates import _norm  # noqa: E402

cdm.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# ──────────────────────────── les mails ────────────────────────────
MID_A, MID_B, MID_C = "19fa0000000000a1", "19fa0000000000b2", "19fa0000000000c3"

MAIL_A = """<html><head><title>Lettre</title><style>td{color:red}</style></head><body>
<table><tr><td><img src="https://esp.example/img/header-logo.png" width="600" height="120" alt="Newsletter"></td></tr>
<tr><td><h1>Musées de Chambéry &mdash; la lettre du 3 septembre 2026</h1><p>Nos musées sont ouverts du mardi au dimanche.</p></td></tr>
<tr><td>
  <img src="https://img.example/2026/visite-meditative.jpg" width="600">
  <h2>Visite <b>méditative</b> au Musée des Arts Asiatiques</h2>
  <p>Le samedi 12 septembre à 15h, au Musée des Arts Asiatiques, 405 promenade des Anglais, Nice.
  <a href="https://www.chambery.fr/agenda">Sur inscription</a></p>
</td></tr>
<tr><td>
  <img src="https://img.example/2026/pinocchio.jpg">
  <h2>Le avventure di Pinocchio</h2>
  <p>Domenica 20 settembre, ore 16, al Teatro Giacosa, Aosta. Ingresso libero.</p>
</td></tr>
<tr><td>
  <h2>Rencontre As de Chœur</h2>
  <p>Le vendredi 2 octobre à 20h, à la salle des fêtes. Entrée libre. Verre offert à l'église Saint-Pierre ensuite.</p>
</td></tr>
<tr><td>
  <img src="https://img.example/2026/charmettes.jpg">
  <h2>Balade gourmande aux Charmettes</h2>
  <p>Le dimanche 4 octobre à 11h, aux Charmettes, Chambéry.</p>
</td></tr>
<tr><td>
  <img src="https://img.example/2026/rousseau.jpg">
  <h2>George Sand et Jean-Jacques Rousseau : la nature en partage</h2>
  <p>Le jeudi 15 octobre à 18h30, au Théâtre Charles Dullin. Gratuit.</p>
</td></tr>
<tr><td>
  <h2>Cols Connectés 2026 - Ascension du Col des Champs</h2>
  <p>Dimanche 27 septembre, entre Guillaumes et Saint-Martin-d'Entraunes. Départ 8h.</p>
</td></tr>
<tr><td>
  <h2>Contes pour enfants et grands</h2>
  <p>Le mercredi 7 octobre à 16h, à la médiathèque. Vers 18h, goûter.</p>
</td></tr>
<tr><td><img src="https://cdn.example/social/facebook-icon.png" width="32" height="32">
<img src="https://t.sendibm1.com/open/abc" width="1" height="1"></td></tr>
</table></body></html>"""

# Mise en page À PLAT : une seule cellule, des <br>. Le « bloc » du titre est la lettre
# entière — seul l'attribut alt permet encore d'attribuer une image.
MAIL_B = """<html><body><table><tr><td>
<img src="https://esp.example/img/logo-mao.png" width="600" height="100"><br>
Fondazione Torino Musei — newsletter<br><br>
<img src="https://img.example/mao/apertura.jpg" alt="Apertura straordinaria MAO Museo d'Arte Orientale" width="600"><br>
<b>Apertura straordinaria MAO Museo d'Arte Orientale</b><br>
Sabato 10 ottobre, ore 20-24, Torino. Ingresso ridotto.<br><br>
<img src="https://img.example/mao/altra.jpg" width="600"><br>
<b>Song Dong. Soul Out</b><br>
Dal 25 settembre, Torino.<br>
</td></tr></table></body></html>"""

FAUX_GMAIL = {
    MID_B: {"html": MAIL_B, "texte": gc._linkify_html(MAIL_B)},
}
DIMS = {
    "https://img.example/2026/visite-meditative.jpg": (800, 600),
    "https://img.example/2026/pinocchio.jpg": (300, 200),          # trop petite
    "https://img.example/2026/charmettes.jpg": (900, 600),
    "https://img.example/2026/rousseau.jpg": (1500, 480),          # 3,1:1 → bandeau
    "https://img.example/mao/apertura.jpg": (1000, 700),
    "https://img.example/mao/altra.jpg": (1000, 700),
    "https://mcusercontent.com/abc/images/photo-concert.jpg": (480, 270),   # CDN Mailchimp, 16:9 de newsletter
    "https://img.example/2026/juste-sous.jpg": (479, 269),                 # frontière : un pixel sous les deux seuils
    "https://img.example/2026/haute-etroite.jpg": (300, 400),              # petit côté ok, grand côté trop court
}
telechargements = []


def _faux_telecharger(mid):
    telechargements.append(mid)
    return FAUX_GMAIL.get(mid)


cdm._telecharger = _faux_telecharger
cdm._dims = lambda url: DIMS.get(url, (0, 0))

# ──────────────────────────── la base ────────────────────────────
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
init_db(conn)
gc.ensure_colonne_corps(conn)
gc.ensure_table_html(conn)


def _fiche(idx, mid, titre, statut="evaluated", **champs):
    cols = {"title": titre, "url_source": f"gmail:{mid}#{idx}", "statut": statut,
            "date_event_start": "2027-03-01", "date_event_end": "2027-03-01",
            "territoire": "Savoie", "llm_categorie": "Visites", "source_name": "lettre"}
    cols.update(champs)
    cur = conn.execute(
        f"INSERT INTO events_raw ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
        list(cols.values()))
    return cur.lastrowid


# Le HTML du mail A est déjà en mémoire (collecté après le 08/09) ; son corps texte aussi.
gc.memoriser_html(conn, MID_A, MAIL_A)
CORPS_A = gc._linkify_html(MAIL_A)
F_VISITE = _fiche(0, MID_A, "Visite méditative au Musée des Arts Asiatiques", mail_corps=CORPS_A)
F_PINOCCHIO = _fiche(1, MID_A, "Le avventure di Pinocchio", mail_corps=CORPS_A)
F_CHOEUR = _fiche(2, MID_A, "Rencontre As de Chœur", mail_corps=CORPS_A)
# REJETÉE — mais son titre borne l'annonce précédente. Sans elle, « Rencontre As de Chœur »
# recevrait « Chambéry », lu 90 caractères plus loin dans SON annonce à elle.
F_BALADE = _fiche(3, MID_A, "Balade gourmande aux Charmettes", statut="rejected", mail_corps=CORPS_A)
F_ROUSSEAU = _fiche(4, MID_A, "George Sand et Jean-Jacques Rousseau : la nature en partage",
                    mail_corps=CORPS_A)
F_COLS = _fiche(5, MID_A, "Cols Connectés 2026 - Ascension du Col des Champs", mail_corps=CORPS_A)
F_CONTES = _fiche(6, MID_A, "Contes pour enfants et grands", mail_corps=CORPS_A)
# Mail B : collecté AVANT le 08/09 — ni HTML ni corps en base, il faut Gmail.
F_MAO = _fiche(0, MID_B, "Apertura straordinaria MAO Museo d'Arte Orientale")
F_SONG = _fiche(1, MID_B, "Song Dong. Soul Out")
# Mail C : introuvable dans Gmail.
F_PERDU = _fiche(0, MID_C, "Ricordare Giorgio Balmas, concerto")
# PASSÉE : hors périmètre (règle 5), ne doit même pas être examinée.
F_PASSEE = _fiche(7, MID_A, "Sieste musicale aux Charmettes - OudéBach",
                  date_event_start="2026-08-21", date_event_end="2026-08-21", mail_corps=CORPS_A)
# Déjà complète : rien à faire.
F_COMPLETE = _fiche(8, MID_A, "Atelier complet des Charmettes", lieu="Les Charmettes",
                    ville="Chambéry", url_image="https://x/y.jpg", image_source="og")
# Ce que NOTRE base sait déjà : un Musée des Arts Asiatiques à Nice (fiche approuvée d'une
# autre source), et un homonyme de nom générique qui ne doit pas servir.
_fiche(0, "autre", "Expo permanente", url_source="https://arts-asiatiques.example/expo",
       lieu="Musée des Arts Asiatiques", ville="Nice", url_image="https://x/z.jpg")
_fiche(0, "autre2", "Loto", url_source="https://mairie.example/loto",
       lieu="Salle des Fêtes", ville="Aoste", url_image="https://x/w.jpg")
conn.commit()


def _lire(eid):
    return dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())


def _etat():
    return [tuple(r) for r in conn.execute(
        "SELECT id, lieu, ville, venue_source, url_image, image_source, mail_corps "
        "FROM events_raw ORDER BY id")]


# ──────────────────────────── 1. la normalisation ────────────────────────────
print("──── carte_norm reproduit _norm à l'identique ────")
for texte in (CORPS_A, gc._strip_html(MAIL_B), "Èze — L'Escarène, Saint-Martin-d'Entraunes",
              "  déjà   « plié »  ", ""):
    n, carte = mail_lieux.carte_norm(texte)
    _check(f"« {texte[:30]!r} » : même texte plié, même longueur",
           n == _norm(texte) and len(n) == len(carte), f"{n!r} vs {_norm(texte)!r}")

# ──────────────────────────── 2. le bloc d'une annonce ────────────────────────────
print("\n──── images_du_titre : le bloc, pas la première image ────")
TITRES_A = [r[0] for r in conn.execute("SELECT title FROM events_raw WHERE url_source LIKE ?",
                                        (f"gmail:{MID_A}%",))]
cands, motif = mail_html.images_du_titre(MAIL_A, "Visite méditative au Musée des Arts Asiatiques",
                                         TITRES_A)
_check("l'annonce « Visite méditative » n'a qu'une image, la sienne (titre coupé par <b>)",
       [c["src"] for c in cands] == ["https://img.example/2026/visite-meditative.jpg"],
       f"{[c['src'] for c in cands]} {motif}")
cands, motif = mail_html.images_du_titre(MAIL_A, "Rencontre As de Chœur", TITRES_A)
_check("une annonce sans image ne reçoit pas celle du voisin", cands == [], f"{cands} {motif}")
_check("…et le motif le dit", "aucune image propre" in motif, motif)
cands, motif = mail_html.images_du_titre(MAIL_B, "Song Dong. Soul Out", [])
_check("annonce seule connue d'un mail à plat → le bloc est la lettre entière → rien",
       cands == [] and "lettre entière" in motif, f"{cands} {motif}")
cands, motif = mail_html.images_du_titre(MAIL_A, "Concert de jazz au Manège", TITRES_A)
_check("titre absent du mail → rien, motif « introuvable »",
       cands == [] and "introuvable" in motif, motif)
cands, motif = mail_html.images_du_titre(MAIL_B, "Song Dong. Soul Out",
                                         ["Apertura straordinaria MAO Museo d'Arte Orientale"])
_check("mise en page à plat sans alt → rien (bloc = la lettre entière)",
       cands == [] and ("lettre entière" in motif or "partagé" in motif), f"{cands} {motif}")
cands, motif = mail_html.images_du_titre(MAIL_B, "Apertura straordinaria MAO Museo d'Arte Orientale",
                                         ["Song Dong. Soul Out"])
_check("mise en page à plat AVEC alt = titre → l'image désignée par l'expéditeur, et elle seule",
       [c["src"] for c in cands] == ["https://img.example/mao/apertura.jpg"],
       f"{[c['src'] for c in cands]} {motif}")

# ──────────────────────────── 3. les filtres d'image ────────────────────────────
print("\n──── filtres : pixel, logo, icône, trop petite, bandeau ────")
_check("pixel de suivi 1×1 sur hôte de traçage → refusé",
       cdm._refus_statique({"src": "https://t.sendibm1.com/open/abc", "largeur": "1", "hauteur": "1"}) != "")
_check("pixel 1×1 sur hôte inconnu → refusé quand même (dimensions déclarées)",
       "pixel" in cdm._refus_statique({"src": "https://x.example/o.png", "largeur": "1", "hauteur": "1"}))
_check("logo d'en-tête → refusé (is_logo_image)",
       "logo" in cdm._refus_statique({"src": "https://esp.example/img/header-logo.png", "largeur": "600", "hauteur": "120"}))
_check("icône de réseau social 32×32 → refusée",
       cdm._refus_statique({"src": "https://cdn.example/social/facebook-icon.png", "largeur": "32", "hauteur": "32"}) != "")
_check("un FICHIER image sur le CDN d'un routeur (mcusercontent.com/….jpg) n'est PAS un traqueur",
       cdm._refus_statique({"src": "https://mcusercontent.com/abc/images/photo-concert.jpg", "largeur": "600", "hauteur": ""}) == "")
_check("…mais un lien sans extension sur le même genre d'hôte reste un traqueur",
       "traçage" in cdm._refus_statique({"src": "https://mcusercontent.com/abc/track/xyz", "largeur": "", "hauteur": ""}))
url, pourquoi, refus = cdm._choisir_image(
    [{"src": "https://mcusercontent.com/abc/images/photo-concert.jpg", "alt": "", "largeur": "", "hauteur": "", "pourquoi": "bloc"}], cdm.MIN_COTE)
_check("480×270 (le format réel des newsletters mesuré le 09/09) → ACCEPTÉE au seuil par défaut (cas frontière qui doit passer)",
       url.endswith("photo-concert.jpg"), str(refus))
url, pourquoi, refus = cdm._choisir_image(
    [{"src": "https://img.example/2026/juste-sous.jpg", "alt": "", "largeur": "", "hauteur": "", "pourquoi": "bloc"}], cdm.MIN_COTE)
_check("479×269 → refusée : un pixel sous le seuil", url == "" and any("trop petite" in r for r in refus), str(refus))
url, pourquoi, refus = cdm._choisir_image(
    [{"src": "https://img.example/2026/haute-etroite.jpg", "alt": "", "largeur": "", "hauteur": "", "pourquoi": "bloc"}], cdm.MIN_COTE)
_check("300×400 → refusée : grand côté < 480 (le petit côté seul ne suffit pas)", url == "" and any("trop étroite" in r for r in refus), str(refus))
_check("une photo de contenu passe le filtre statique",
       cdm._refus_statique({"src": "https://img.example/2026/visite-meditative.jpg", "largeur": "600", "hauteur": ""}) == "")
url, pourquoi, refus = cdm._choisir_image(
    [{"src": "https://img.example/2026/pinocchio.jpg", "alt": "", "largeur": "", "hauteur": "", "pourquoi": "bloc"}], 400)
_check("300×200 → refusée, trop petite, motif chiffré", url == "" and any("trop petite 300×200" in r for r in refus), str(refus))
url, pourquoi, refus = cdm._choisir_image(
    [{"src": "https://img.example/2026/rousseau.jpg", "alt": "", "largeur": "", "hauteur": "", "pourquoi": "bloc"}], 400)
_check("1500×480 → refusée, forme de bandeau", url == "" and any("bandeau" in r for r in refus), str(refus))
url, pourquoi, refus = cdm._choisir_image(
    [{"src": "https://img.example/2026/visite-meditative.jpg", "alt": "", "largeur": "", "hauteur": "", "pourquoi": "bloc"}], 400)
_check("800×600 → acceptée", url == "https://img.example/2026/visite-meditative.jpg" and "800×600" in pourquoi)

# ──────────────────────────── 4. simulation : rien n'est écrit ────────────────────────────
print("\n──── dry-run ────")
avant = _etat()
rc = cdm.main([])
_check("le dry-run rend 0", rc == 0)
_check("le dry-run n'écrit RIEN", _etat() == avant)
_check("le dry-run n'a pas mémorisé le HTML téléchargé",
       gc.html_memorise(conn, MID_B) == "")
_check("le mail B a été demandé à Gmail, le mail A (en mémoire) non, le mail C une fois",
       telechargements.count(MID_B) == 1 and MID_A not in telechargements
       and telechargements.count(MID_C) == 1, str(telechargements))

# ──────────────────────────── 5. --apply ────────────────────────────
print("\n──── --apply ────")
telechargements.clear()
rc = cdm.main(["--apply"])
_check("--apply rend 0", rc == 0)
v = _lire(F_VISITE)
_check("Visite méditative : ville Nice (commune nommée dans l'annonce)", v["ville"] == "Nice", str(v["ville"]))
_check("Visite méditative : lieu confirmé par la base DANS cette ville, venue_source='mail'",
       v["lieu"] == "Musée des Arts Asiatiques" and v["venue_source"] == "mail",
       f"{v['lieu']!r} {v['venue_source']!r}")
_check("Visite méditative : l'image de SON bloc, image_source='mail'",
       v["url_image"] == "https://img.example/2026/visite-meditative.jpg" and v["image_source"] == "mail",
       f"{v['url_image']!r} {v['image_source']!r}")
p = _lire(F_PINOCCHIO)
_check("Pinocchio : ville Aosta, seule", p["ville"] == "Aosta" and not p["lieu"], f"{p['ville']!r} {p['lieu']!r}")
_check("Pinocchio : image trop petite → aucune image écrite", not p["url_image"], str(p["url_image"]))
c = _lire(F_CHOEUR)
_check("As de Chœur : « salle des fêtes » et « église Saint-Pierre » ne donnent RIEN, "
       "et « Chambéry » de l'annonce voisine (rejetée) non plus",
       not c["ville"] and not c["lieu"] and not c["url_image"],
       f"{c['ville']!r} {c['lieu']!r} {c['url_image']!r}")
r = _lire(F_ROUSSEAU)
_check("Rousseau : lieu connu du registre → Théâtre Charles Dullin + Chambéry",
       r["lieu"] == "Théâtre Charles Dullin" and r["ville"] == "Chambéry" and r["venue_source"] == "mail",
       f"{r['lieu']!r} {r['ville']!r}")
_check("Rousseau : image 1500×480 refusée (bandeau) → rien", not r["url_image"], str(r["url_image"]))
k = _lire(F_COLS)
_check("Cols Connectés : deux communes dans l'annonce → rien", not k["ville"] and not k["lieu"], f"{k['ville']!r}")
t = _lire(F_CONTES)
_check("« Contes pour enfants » : mot-piège sans marqueur de lieu → rien", not t["ville"], f"{t['ville']!r}")
m = _lire(F_MAO)
_check("MAO (mail relu dans Gmail) : ville Torino", m["ville"] == "Torino", f"{m['ville']!r}")
_check("MAO : image désignée par son alt, malgré la mise en page à plat",
       m["url_image"] == "https://img.example/mao/apertura.jpg" and m["image_source"] == "mail",
       f"{m['url_image']!r}")
s = _lire(F_SONG)
_check("Song Dong : ville Torino, mais AUCUNE image (bloc = la lettre entière, pas d'alt)",
       s["ville"] == "Torino" and not s["url_image"], f"{s['ville']!r} {s['url_image']!r}")
_check("le HTML du mail B est maintenant mémorisé", gc.html_memorise(conn, MID_B) == MAIL_B)
_check("le corps texte du mail B est posé sur ses fiches",
       bool(m["mail_corps"]) and bool(s["mail_corps"]))
perdu = _lire(F_PERDU)
_check("mail introuvable : rien d'écrit, rien de mémorisé",
       not perdu["ville"] and not perdu["url_image"] and gc.html_memorise(conn, MID_C) == "")
passee = _lire(F_PASSEE)
_check("la fiche PASSÉE n'a pas été touchée (règle 5)", not passee["ville"] and not passee["url_image"])
rej = _lire(F_BALADE)
_check("la fiche REJETÉE n'a pas été touchée (elle a seulement servi de borne)",
       not rej["ville"] and not rej["url_image"])
comp = _lire(F_COMPLETE)
_check("la fiche déjà complète est intacte", comp["ville"] == "Chambéry" and comp["image_source"] == "og")

# ──────────────────────────── 6. ids positionnels et second passage ────────────────────────────
print("\n──── ids positionnels, idempotence, mémoire ────")
avant = _etat()
telechargements.clear()
rc = cdm.main([str(F_CHOEUR), "--apply"])
_check("un second --apply sur une fiche muette n'écrit rien", _etat() == avant)
rc = cdm.main(["--apply"])
_check("un second --apply général n'écrit rien de plus (idempotent)", _etat() == avant)
_check("le mail B, mémorisé au premier --apply, n'est plus demandé à Gmail ; le mail C "
       "introuvable l'est encore (une fois par passage)",
       MID_B not in telechargements and telechargements.count(MID_C) == 1, str(telechargements))

conn.close()
print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
