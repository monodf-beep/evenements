#!/usr/bin/env python3
"""Fixture : une page officielle lue UNE fois remplit tous les champs vides d'un coup —
et n'écrase jamais rien.

Franck, 2026-08-11 : « la complétion des informations grâce aux infos officielles devrait
se faire, alors qu'actuellement ce n'est pas le cas ». Trois crons savent lire une page
officielle et chacun n'y prend qu'un champ, chacun avec son propre délai de carence :
il suffit que l'horloge des dates soit fermée pour que le lieu et l'image, pourtant dans
la même page, ne soient pas récoltés. Constaté le soir même : « 0 page(s) à lire » côté
dates ET côté lieux, avec 79 fiches sans date et 31 sans lieu.

Ce que la fixture vérifie, en particulier ce qui doit NE PAS bouger :
  • les champs vides sont remplis depuis le JSON-LD et l'og:image ;
  • un champ DÉJÀ renseigné n'est jamais écrasé — c'est la leçon du 2026-08-09, quand le
    pipeline a remplacé une vraie photo posée à la main par une image de repli ;
  • une page muette ne pose AUCUN verdict : la fiche reste candidate pour dates.py, on
    ne lui consomme pas un délai de carence pour un essai qui n'a rien coûté ;
  • une fiche sans page téléchargeable (« gmail:… ») est ignorée, pas tentée ;
  • le passé est écarté (règle 5) ;
  • en simulation, RIEN n'est écrit.

Aucun réseau : le téléchargement est monkey-patché.

Lancer : .venv/bin/python -m tests.test_moisson_officielle
"""
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
import scripts.moisson_officielle as mo  # noqa: E402

mo.DB_PATH = tmp
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


PAGE_RICHE = '''<html><head>
<meta property="og:image" content="https://officiel.fr/affiche.jpg">
<script type="application/ld+json">{"@type":"Event","name":"Concert",
"startDate":"2026-12-05","endDate":"2026-12-06",
"location":{"@type":"Place","name":"Théâtre Charles Dullin",
"address":{"addressLocality":"Chambéry"}}}</script>
</head><body>Concert</body></html>'''
PAGE_MUETTE = "<html><head><title>Rien</title></head><body>Aucune donnée.</body></html>"


class _Rep:
    def __init__(self, text, url=""):
        self.text = text
        # `url` = adresse d'ARRIVÉE après redirections, comme le fait requests. C'est
        # elle qui décide si l'on a le droit de récolter (2026-08-11) : un lien de
        # traçage de newsletter n'est pas un éditeur, il renvoie vers un.
        self.url = url


AUJOURDHUI = "2026-08-11"
PAGES = {
    "https://officiel.fr/riche": PAGE_RICHE,
    "https://officiel.fr/muette": PAGE_MUETTE,
    "https://officiel.fr/deja": PAGE_RICHE,
    "https://officiel.fr/riche2": PAGE_RICHE,
}
REDIRECTIONS = {}   # traqueur -> destination réelle
mo._robust_get = lambda url: (
    _Rep(PAGES[REDIRECTIONS.get(url, url)], REDIRECTIONS.get(url, url))
    if REDIRECTIONS.get(url, url) in PAGES else None)
mo.fetch_og_image = lambda url, timeout=8: (
    "https://officiel.fr/affiche.jpg" if PAGES.get(url) == PAGE_RICHE else "")
# Page d'événement SANS og:image mais avec l'affiche en pleine page (Montmélian, 08/09).
PAGE_AFFICHE_SANS_OG = """<html><head><title>Festival</title></head><body>
<img src="/wp-content/uploads/06.13-Festival-Photo.png" alt="affiche"></body></html>"""
PAGES["https://officiel.fr/festival-photo/"] = PAGE_AFFICHE_SANS_OG
mo.remote_dims = lambda u, *a, **k: (774, 1000)   # pas de réseau : l'affiche mesure 774×1000

conn = sqlite3.connect(tmp)
init_db(conn)
# (id, url_source, date_start, lieu, ville, image, date_end)
CAS = [
    (1, "https://officiel.fr/riche",  "", "", "", "", "2026-12-31"),
    (2, "https://officiel.fr/muette", "", "", "", "", "2026-12-31"),
    (3, "https://officiel.fr/deja",   "2026-11-11", "Ma salle", "Ma ville",
     "https://vraie-photo-posee-a-la-main.jpg", "2026-11-11"),
    (4, "gmail:abc#1",                "", "", "", "", "2026-12-31"),
    (5, "https://officiel.fr/riche2", "", "", "", "", "2026-05-01"),   # PASSÉE
]
for eid, url, ds, lieu, ville, img, fin in CAS:
    conn.execute(
        "INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,ville,"
        "url_image,date_event_end) VALUES (?,?,?, 'evaluated', ?,?,?,?,?)",
        (eid, f"Fiche {eid}", url, ds, lieu, ville, img, fin))
conn.commit()

print("──── sélection ────")
conn.row_factory = sqlite3.Row
cibles = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
_check("la fiche incomplète avec page est retenue", 1 in cibles, str(sorted(cibles)))
_check("la fiche « gmail: » est ignorée (rien à télécharger)", 4 not in cibles,
       str(sorted(cibles)))
_check("la fiche PASSÉE est écartée (règle 5)", 5 not in cibles, str(sorted(cibles)))
# CHANGEMENT DE CONTRAT (2026-08-11) : une fiche « complète » est désormais retenue si
# elle n'a pas encore ses INFOS PRATIQUES. C'est la demande de Franck — « il faut que le
# script aille chercher les informations dans les ressources officielles » — et c'est ce
# qui tarit la file « À vérifier » remplie de tarifs et d'horaires : ces faits sont sur la
# page de l'organisateur, il suffit de les lire. Ses champs obligatoires, eux, restent
# intouchés (vérifié plus bas).
_check("une fiche complète MAIS sans infos pratiques est retenue", 3 in cibles,
       str(sorted(cibles)))
conn.close()

print("\n──── simulation : rien n'est écrit ────")
mo.main([])
conn = sqlite3.connect(tmp)
avant = conn.execute("SELECT date_event_start, lieu FROM events_raw WHERE id=1").fetchone()
conn.close()
_check("la fiche 1 est toujours vide après simulation", avant == ("", ""), str(avant))

print("\n──── --apply : la page riche remplit tout d'un coup ────")
mo.main(["--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f1 = dict(conn.execute("SELECT * FROM events_raw WHERE id=1").fetchone())
f2 = dict(conn.execute("SELECT * FROM events_raw WHERE id=2").fetchone())
f3 = dict(conn.execute("SELECT * FROM events_raw WHERE id=3").fetchone())
conn.close()

_check("date de début récoltée", f1["date_event_start"] == "2026-12-05", str(f1["date_event_start"]))
# La fin SUIT le début : la fiche portait « 2026-12-31 » (une borne venue d'ailleurs),
# et comme le début vient d'être posé depuis cette page, la fin est reprise avec lui.
# Garder les deux bornes de sources différentes fabriquerait un intervalle faux.
_check("date de fin récoltée, et elle suit son début",
       f1["date_event_end"] == "2026-12-06", str(f1["date_event_end"]))
_check("lieu récolté", f1["lieu"] == "Théâtre Charles Dullin", str(f1["lieu"]))
_check("ville récoltée", f1["ville"] == "Chambéry", str(f1["ville"]))
_check("image récoltée", f1["url_image"] == "https://officiel.fr/affiche.jpg",
       str(f1["url_image"]))
_check("date_source='page' posée quand on a TROUVÉ", f1["date_source"] == "page",
       str(f1["date_source"]))

# Le cas qui compte le plus : ne rien trouver ne doit RIEN fermer.
_check("page muette : aucun verdict de date posé (la fiche reste candidate)",
       not (f2["date_source"] or ""), repr(f2["date_source"]))
_check("page muette : aucun verdict de lieu posé",
       not (f2["venue_source"] or ""), repr(f2["venue_source"]))

# Et celui qui a déjà coûté cher en production : ne JAMAIS écraser.
_check("la vraie photo posée à la main n'est PAS écrasée",
       f3["url_image"] == "https://vraie-photo-posee-a-la-main.jpg", str(f3["url_image"]))
_check("le lieu saisi à la main n'est PAS écrasé", f3["lieu"] == "Ma salle", str(f3["lieu"]))
_check("la date saisie à la main n'est PAS écrasée",
       f3["date_event_start"] == "2026-11-11", str(f3["date_event_start"]))

# ── La bannière est une place vide, la vraie photo ne l'est pas ─────────────────
# Mesuré le 2026-08-11 avec --diagnostic : 36 des 53 pages « muettes » portaient un
# og:image que la moisson n'a PAS pris, parce qu'elle ne regardait que « url_image est
# vide ». La veille, un run sans-API avait posé une bannière générique sur 40 fiches :
# le pis-aller bloquait l'accès à la vraie affiche.
print("\n──── bannière : une place vide, pas une image ────")
conn = sqlite3.connect(tmp)
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,"
             "ville,url_image,image_source,date_event_end) VALUES "
             "(6,'Sur bannière','https://officiel.fr/banniere','evaluated','2026-12-01',"
             "'Salle','Ville','https://banniere-generique.png','banner','2026-12-01')")
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,lieu,"
             "ville,url_image,image_source,date_event_end) VALUES "
             "(7,'Vraie photo','https://officiel.fr/photo','evaluated','2026-12-01',"
             "'Salle','Ville','https://sa-vraie-affiche.jpg','og','2026-12-01')")
conn.commit()
PAGES["https://officiel.fr/banniere"] = PAGE_RICHE
PAGES["https://officiel.fr/photo"] = PAGE_RICHE

conn.row_factory = sqlite3.Row
cibles2 = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
_check("la fiche sur BANNIÈRE est reprise (il lui manque une vraie affiche)",
       6 in cibles2, str(sorted(cibles2)))
# Elle est reprise, mais pour ses INFOS PRATIQUES seulement — sa photo, elle, ne sera pas
# touchée : c'est ce que vérifie l'assertion suivante sur url_image.
_check("la fiche à VRAIE photo est reprise pour ses infos pratiques, pas pour son image",
       7 in cibles2, str(sorted(cibles2)))
conn.close()

mo.main(["--apply", "6", "7"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f6 = dict(conn.execute("SELECT * FROM events_raw WHERE id=6").fetchone())
f7 = dict(conn.execute("SELECT * FROM events_raw WHERE id=7").fetchone())
conn.close()
_check("la bannière est remplacée par l'og:image de la page officielle",
       f6["url_image"] == "https://officiel.fr/affiche.jpg", str(f6["url_image"]))
_check("… et sa provenance suit (plus jamais reprise pour ce motif)",
       f6["image_source"] == "og", str(f6["image_source"]))
_check("la vraie photo existante n'est PAS remplacée",
       f7["url_image"] == "https://sa-vraie-affiche.jpg", str(f7["url_image"]))

# ── Aucune récolte sur un domaine de presse ────────────────────────────────────
# Franck, 2026-08-11, en lisant la sortie : « il semble encore y avoir du radar ! » —
# la moisson proposait l'og:image de guidatorino.com, quotidianopiemontese.it et
# aostaoggi.it. Le contrat radar dit « DÉTECTER, jamais créditer ni lier », et une photo
# de presse appartient au journal. On ne prend RIEN de ces pages, pas même la date : un
# article « que faire ce week-end » parle de dix événements, et la date qu'on y lirait
# risque d'être celle d'un autre (c'est ainsi que WP#6798 a porté la date d'un voisin).
print("\n──── presse : rien n'est récolté ────")
PRESSE = [
    (10, "https://www.guidatorino.com/evenement-x"),
    (11, "https://www.quotidianopiemontese.it/evenement-y"),
    (12, "https://www.aostaoggi.it/evenement-z"),
]
conn = sqlite3.connect(tmp)
for eid, url in PRESSE:
    PAGES[url] = PAGE_RICHE          # la page EST riche : seul le domaine la disqualifie
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,"
                 "lieu,ville,url_image,date_event_end) VALUES (?,?,?, 'evaluated', "
                 "'','','','', '2026-12-31')", (eid, f"Presse {eid}", url))
conn.commit()
conn.row_factory = sqlite3.Row
cibles3 = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
for eid, url in PRESSE:
    _check(f"écarté — {url.split('/')[2]}", eid not in cibles3, str(sorted(cibles3)))
_check("une page officielle riche reste, elle, récoltable",
       any(mo._url_telechargeable(dict(r)) for r in
           conn.execute("SELECT * FROM events_raw WHERE id=1")))
conn.close()

print("\n──── le DÉBUT corroboré par une FIN déjà connue ────")
# Franck, 2026-08-11 : « date de début, date de fin ! ». Après trois passages de dates.py,
# 54 fiches n'avaient toujours qu'une fin, tirée d'un « jusqu'au 20 septembre » dont la
# page SOURCE ne disait pas le début. La page lue ici est l'OFFICIELLE : c'est elle qui
# écrit « du 12 juin au 20 septembre ». On n'y cherche pas une date — une page en porte
# toujours plusieurs — mais une PLAGE QUI FINIT à la date connue.
PAGE_PROSE = ("<html><body><p>Publié le 3 mars 2026 par la rédaction.</p>"
              "<p>L'exposition est visible du 12 juin au 20 septembre 2026.</p>"
              "<p>Prochainement : concert du 5 octobre 2026.</p></body></html>")
PAGE_PROSE_AUTRE_FIN = ("<html><body><p>Rendez-vous du 1 juillet au 3 août 2026.</p>"
                        "</body></html>")
PAGES["https://officiel.fr/prose"] = PAGE_PROSE
PAGES["https://officiel.fr/prose-sans-rapport"] = PAGE_PROSE_AUTRE_FIN
conn = sqlite3.connect(tmp)
for eid, url, fin in ((20, "https://officiel.fr/prose", "2026-09-20"),
                      (21, "https://officiel.fr/prose-sans-rapport", "2026-09-20")):
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,"
                 "lieu,ville,url_image,date_event_end) VALUES (?,?,?, 'evaluated', "
                 "'','','','', ?)", (eid, f"Fin seule {eid}", url, fin))
conn.commit()
conn.close()
mo.main(["--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f20 = dict(conn.execute("SELECT * FROM events_raw WHERE id=20").fetchone())
f21 = dict(conn.execute("SELECT * FROM events_raw WHERE id=21").fetchone())
conn.close()
_check("la plage qui finit à la date connue donne le début",
       f20["date_event_start"] == "2026-06-12", str(f20["date_event_start"]))
_check("… et la fin, qui a servi de preuve, n'est pas réécrite",
       f20["date_event_end"] == "2026-09-20", str(f20["date_event_end"]))
_check("une plage SANS rapport avec la fin connue ne donne rien — surtout pas sa "
       "première date", f21["date_event_start"] == "", str(f21["date_event_start"]))
_check("… et la fiche garde sa date de fin intacte",
       f21["date_event_end"] == "2026-09-20", str(f21["date_event_end"]))

print("\n──── un lien de TRAÇAGE se juge sur sa destination ────")
# Franck, 2026-08-11 : « pourquoi ça tourne pas seul pour trouver les informations
# manquantes ? » Six expositions de la Reggia di Venaria n'étaient JAMAIS lues : leur
# adresse est un lien sendibm1.com, qui échoue au test du domaine officiel — alors qu'il
# redirige vers lavenaria.it. Le portillon jugeait l'adresse écrite, pas celle où l'on
# arrive.
# Domaine de PRESSE réel du fichier de configuration : « presse-quelconque.fr » ne
# marchait pas comme cas de test, et c'est instructif — source_officielle est une liste
# de REFUS, donc un domaine inconnu passe. Le test doit donc employer un domaine que le
# dépôt reconnaît vraiment comme presse, sinon il vérifie une frontière imaginaire.
PAGES["https://www.guidatorino.com/article"] = PAGE_RICHE
REDIRECTIONS["https://lql1t.r.a.d.sendibm1.com/mk/cl/f/vers-officiel"] = \
    "https://officiel.fr/riche"
REDIRECTIONS["https://lql1t.r.a.d.sendibm1.com/mk/cl/f/vers-presse"] = \
    "https://www.guidatorino.com/article"
conn = sqlite3.connect(tmp)
# Le TITRE doit être celui de la page d'arrivée (« Concert ») : depuis le 2026-09-08 la
# destination d'un traqueur doit parler de l'événement, sinon c'est la page de repli de la
# campagne (Sequar renvoie la même page pour n'importe quel jeton — mesuré). Voir plus bas.
for eid, url in ((30, "https://lql1t.r.a.d.sendibm1.com/mk/cl/f/vers-officiel"),
                 (31, "https://lql1t.r.a.d.sendibm1.com/mk/cl/f/vers-presse")):
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,"
                 "lieu,ville,url_image,date_event_end) VALUES (?,?,?, 'evaluated', "
                 "'','','','', '2026-12-31')", (eid, f"Concert au théâtre {eid}", url))
conn.commit()
conn.row_factory = sqlite3.Row
cibles4 = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
conn.close()
_check("un lien de traçage n'est plus écarté d'emblée", 30 in cibles4, str(sorted(cibles4)))
mo.main(["--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f30 = dict(conn.execute("SELECT * FROM events_raw WHERE id=30").fetchone())
f31 = dict(conn.execute("SELECT * FROM events_raw WHERE id=31").fetchone())
conn.close()
_check("destination OFFICIELLE → la page est récoltée",
       (f30.get("date_event_start") or "") != "", str(f30.get("date_event_start")))
_check("… et la vraie adresse est enregistrée, pour ne plus repasser par le traqueur",
       (f30.get("url_officiel") or "") == "https://officiel.fr/riche",
       str(f30.get("url_officiel")))
# LE CAS QUI A FAILLI PASSER EN PRODUCTION : le lien de traçage ne redirige pas (page de
# rebond, ou lien périmé), donc l'adresse d'arrivée EST le traqueur. source_officielle ne
# l'arrête pas — c'est une liste de refus, un domaine inconnu est accepté — et on allait
# inscrire sendibm1.com comme page officielle de la Reggia di Venaria.
REDIRECTIONS["https://lql1t.r.a.d.sendibm1.com/mk/cl/f/sans-redirection"] = \
    "https://lql1t.r.a.d.sendibm1.com/mk/cl/f/sans-redirection"
PAGES["https://lql1t.r.a.d.sendibm1.com/mk/cl/f/sans-redirection"] = PAGE_RICHE
conn = sqlite3.connect(tmp)
conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,"
             "lieu,ville,url_image,date_event_end) VALUES (32,'Traqueur mort',"
             "'https://lql1t.r.a.d.sendibm1.com/mk/cl/f/sans-redirection','evaluated',"
             "'','','','', '2026-12-31')")
conn.commit(); conn.close()
mo.main(["--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f32 = dict(conn.execute("SELECT * FROM events_raw WHERE id=32").fetchone())
conn.close()
_check("un traqueur qui ne redirige pas n'est JAMAIS inscrit comme page officielle",
       not (f32.get("url_officiel") or ""), str(f32.get("url_officiel")))
_check("… et rien n'est récolté de sa page de rebond",
       (f32.get("date_event_start") or "") == "", str(f32.get("date_event_start")))

_check("destination PRESSE → RIEN n'est récolté, le contrat radar tient",
       (f31.get("date_event_start") or "") == "" and not (f31.get("url_image") or ""),
       str({k: f31.get(k) for k in ("date_event_start", "url_image")}))

# ── 2026-09-08 : les REBONDS que HTTP ne voit pas, et les traqueurs SANS destination ───
# Mesuré ce soir-là sur les fiches approuvées, à venir et incomplètes : une vingtaine
# n'avaient pour seule adresse qu'un lien de traçage, et rien n'en avait jamais été
# récolté. Téléchargées une à une comme le fait _robust_get : dix rendaient la MÊME page
# qu'un jeton volontairement faux (Brevo « Page not found », MailUp « Oops! », musvc3 200
# vide, departement06 « Lien invalide ») — des adresses mortes, fondues jusqu'ici dans
# « sans donnée exploitable ». Et la moitié des routeurs (Brevo en marque blanche
# arenametrix.fr / sp1-brevo.net, MailUp sur le domaine du client tr.comune.torino.it,
# Sequar, Postmark, OpenEMM) n'étaient pas reconnus comme traqueurs du tout.
print("\n──── rebonds non-HTTP, traqueurs morts, et la page qui ne parle pas de la fiche ────")
PAGE_REBOND_META = ('<html><head><meta http-equiv="refresh" content="0; url={dest}">'
                    '</head><body>Redirection…</body></html>')
PAGE_REBOND_JS = ('<html><head><script>window.location.href = "{dest}";</script></head>'
                  '<body></body></html>')
PAGE_REBOND_LIEN = ('<html><body><p>Si vous n\'êtes pas redirigé, '
                    '<a href="{dest}">cliquez ici</a>.</p></body></html>')
PAGE_OOPS = ('<html><head><title></title></head><body><div id="msg">Oops! It looks like '
             'something went really wrong.</div></body></html>')
# LE CAS FRONTIÈRE QUI DOIT PASSER : une vraie page, riche, dont un script porte un
# `location.href` (sélecteur de langue vers un site tiers) et une meta refresh SANS url
# (rechargement toutes les 300 s). Ce n'est pas un rebond : on la moissonne ELLE.
PAGE_RICHE_AVEC_JS = PAGE_RICHE.replace(
    "</head>",
    '<meta http-equiv="refresh" content="300">'
    '<script>function lang(){ window.location.href = "https://www.guidatorino.com/x"; }'
    '</script></head>').replace(
    "<body>Concert</body>",
    "<body><h1>Concert</h1><p>Le Théâtre Charles Dullin accueille ce concert le 5 décembre "
    "à 20 h 30, dans la grande salle. Billetterie sur place et en ligne. Tarifs de 12 à 28 "
    "euros. Ouverture des portes une heure avant le début de la représentation. Placement "
    "numéroté. Accès par la rue Jean-Pierre Veyrat, parking à proximité.</p></body>")

T_META = "https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/meta"
T_JS = "https://tr.comune.torino.it/e/tr?q=js"
T_LIEN = "https://enteturismolmr.sequar.com/r/6pf/m/1"
T_PRESSE = "https://lql1t.r.sp1-brevo.net/mk/cl/f/sh/jeton/presse"
T_MORT_404 = "https://7cxp.r.a.d.sendibm1.com/mk/cl/f/sh/jeton/mort"       # absent de PAGES → None
T_OOPS = "https://go.fondazionetorinomusei.it/e/tr?q=oops"              # 200, même hôte
T_REPLI = "https://enteturismolmr.sequar.com/r/6pf/m/2"                 # 301 vers la page de repli
T_UTM = "https://track.pstmrk.it/3s/jeton-utm"
T_CHAINE4 = "https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/c0"     # 4 sauts : trop
T_CHAINE2 = "https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/d0"     # 2 sauts : passe
# LE CAS QUE LE TITRE NE PEUT PAS TRANCHER : la page de repli PARLE de l'événement (la
# liste des événements d'Asti mentionne le Palio), mais un jeton BROUILLÉ y mène aussi —
# donc ce n'est pas notre lien qui a été résolu. Mesuré le 08/09 sur sequar.com :
# `/r/6pf/m/999999999` arrive au même endroit que `/r/6pf/m/651314`.
T_REPLI_MEME_TITRE = "https://enteturismolmr.sequar.com/r/6pf/m/77"
OFFICIEL_UTM = "https://officiel.fr/riche?utm_source=lettre+de+septembre&utm_medium=email"

PAGES[T_META] = PAGE_REBOND_META.format(dest="https://officiel.fr/riche")
PAGES[T_JS] = PAGE_REBOND_JS.format(dest="https://officiel.fr/riche")
PAGES[T_LIEN] = PAGE_REBOND_LIEN.format(dest="https://officiel.fr/riche")
PAGES[T_PRESSE] = PAGE_REBOND_META.format(dest="https://www.guidatorino.com/article")
PAGES[T_OOPS] = PAGE_OOPS
REDIRECTIONS[T_REPLI] = "https://officiel.fr/riche"        # hôte officiel, mais pas la fiche
REDIRECTIONS[T_REPLI_MEME_TITRE] = "https://officiel.fr/riche"
REDIRECTIONS[mo._jeton_brouille(T_REPLI_MEME_TITRE)] = "https://officiel.fr/riche"   # jeton bidon : même arrivée
REDIRECTIONS[T_UTM] = OFFICIEL_UTM
_check("le jeton brouillé change bien le dernier groupe de caractères",
       mo._jeton_brouille(T_REPLI_MEME_TITRE) == "https://enteturismolmr.sequar.com/r/6pf/m/00",
       mo._jeton_brouille(T_REPLI_MEME_TITRE))
PAGES[OFFICIEL_UTM] = PAGE_RICHE
PAGES["https://officiel.fr/riche-js"] = PAGE_RICHE_AVEC_JS
for i in range(4):
    PAGES[f"https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/c{i}"] = PAGE_REBOND_META.format(
        dest=f"https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/c{i + 1}")
PAGES["https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/c4"] = PAGE_RICHE   # jamais atteinte
PAGES["https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/d0"] = PAGE_REBOND_META.format(
    dest="https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/d1")
PAGES["https://r.routage2.arenametrix.fr/mk/cl/f/sh/jeton/d1"] = PAGE_REBOND_JS.format(
    dest="https://officiel.fr/riche")

for t in (T_META, T_JS, T_LIEN, T_PRESSE, T_MORT_404, T_OOPS, T_REPLI, T_UTM, T_CHAINE4,
          T_CHAINE2):
    _check(f"reconnu comme traqueur : {t.split('/')[2]}{'/' + t.split('/')[3] if '/e/' in t else ''}",
           mo._est_traqueur(t))
_check("… et bct.comune.torino.it (source à conserver, décision de Franck) ne l'est pas",
       not mo._est_traqueur("https://bct.comune.torino.it/eventi/lavoriamo-a-maglia"))

REBONDS = [
    # (id, adresse, titre)
    (50, T_META, "Concert de rentrée"),
    (51, T_JS, "Concert de rentrée"),
    (52, T_LIEN, "Concert de rentrée"),
    (53, T_PRESSE, "Concert de rentrée"),
    (54, T_MORT_404, "Julien Clerc en concert"),
    (55, T_OOPS, "Concert au Conservatorio"),
    (56, T_REPLI, "Palio di Asti"),
    (57, T_UTM, "Concert de rentrée"),
    (58, "https://officiel.fr/riche-js", "Concert"),
    (59, T_CHAINE4, "Concert de rentrée"),
    (60, T_CHAINE2, "Concert de rentrée"),
    (61, T_REPLI_MEME_TITRE, "Concert de rentrée"),
]
conn = sqlite3.connect(tmp)
for eid, url, titre in REBONDS:
    conn.execute("INSERT INTO events_raw (id,title,url_source,statut,date_event_start,"
                 "lieu,ville,url_image,date_event_end) VALUES (?,?,?, 'evaluated', "
                 "'','','','', '2026-12-31')", (eid, titre, url))
conn.commit()
conn.row_factory = sqlite3.Row
cibles5 = {e["id"] for e in mo._a_moissonner(conn, AUJOURDHUI, 50)}
_check("tous les traqueurs sont retenus pour lecture (on juge l'arrivée, pas l'adresse)",
       {50, 51, 52, 53, 54, 55, 56, 57, 59, 60} <= cibles5, str(sorted(cibles5)))
conn.close()

# Les traqueurs SANS destination sont comptés, avec l'identifiant de la fiche : c'est ce
# qui manquait au bilan — vingt fiches invisibles dans « sans donnée exploitable ».
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
morts: list = []
for eid in (54, 55, 59, 50):
    ev = dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
    mo._recolte(ev, None, morts)
conn.close()
_check("traqueur 404 (Brevo « Page not found ») → compté SANS destination",
       54 in {m[0] for m in morts}, str(morts))
_check("traqueur 200 sur son propre hôte (MailUp « Oops! ») → compté SANS destination",
       55 in {m[0] for m in morts}, str(morts))
_check("chaîne de 4 rebonds → arrêt à 3, compté SANS destination (pas de boucle infinie)",
       59 in {m[0] for m in morts}, str(morts))
_check("un rebond qui aboutit n'est PAS compté mort", 50 not in {m[0] for m in morts}, str(morts))

mo.main(["--apply", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
F = {eid: dict(conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone())
     for eid, _u, _t in REBONDS}
conn.close()


def _recolte_ok(eid):
    return (F[eid]["date_event_start"] == "2026-12-05"
            and F[eid]["lieu"] == "Théâtre Charles Dullin")


_check("meta refresh → site officiel : la page d'arrivée est récoltée", _recolte_ok(50),
       str({k: F[50][k] for k in ("date_event_start", "lieu")}))
_check("… et la vraie adresse est mémorisée",
       F[50]["url_officiel"] == "https://officiel.fr/riche", str(F[50]["url_officiel"]))
_check("… et l'image vient de la page d'ARRIVÉE, plus du traqueur",
       F[50]["url_image"] == "https://officiel.fr/affiche.jpg", str(F[50]["url_image"]))
_check("rebond JavaScript (MailUp sur le domaine du client) → récolté", _recolte_ok(51),
       str({k: F[51][k] for k in ("date_event_start", "lieu")}))
_check("… mémorisé — l'hôte a changé (tr.comune.torino.it → officiel.fr)",
       F[51]["url_officiel"] == "https://officiel.fr/riche", str(F[51]["url_officiel"]))
_check("page « cliquez ici » à lien unique → récolté", _recolte_ok(52),
       str({k: F[52][k] for k in ("date_event_start", "lieu")}))
_check("meta refresh vers la PRESSE → rien, et rien de mémorisé",
       F[53]["date_event_start"] == "" and not F[53]["url_officiel"] and not F[53]["url_image"],
       str({k: F[53][k] for k in ("date_event_start", "url_officiel", "url_image")}))
_check("traqueur mort (404) → rien, rien de mémorisé, aucun verdict",
       F[54]["date_event_start"] == "" and not F[54]["url_officiel"] and not F[54]["date_source"],
       str({k: F[54][k] for k in ("date_event_start", "url_officiel", "date_source")}))
_check("MailUp « Oops! » sur un hôte officiel (go.fondazionetorinomusei.it) → rien de mémorisé",
       F[55]["date_event_start"] == "" and not F[55]["url_officiel"],
       str({k: F[55][k] for k in ("date_event_start", "url_officiel")}))
_check("page de REPLI (hôte officiel, mais pas un mot du titre « Palio di Asti ») → rien, "
       "et surtout pas mémorisée", F[56]["date_event_start"] == "" and not F[56]["url_officiel"],
       str({k: F[56][k] for k in ("date_event_start", "url_officiel")}))
_check("les paramètres de campagne (?utm_…) ne sont pas mémorisés",
       F[57]["url_officiel"] == "https://officiel.fr/riche", str(F[57]["url_officiel"]))
_check("FRONTIÈRE : une vraie page avec `location.href` dans un script et une meta refresh "
       "sans url est moissonnée ELLE-MÊME, pas suivie vers la presse", _recolte_ok(58),
       str({k: F[58][k] for k in ("date_event_start", "lieu")}))
_check("… et une page qui n'était pas un traqueur n'écrit pas d'url_officiel",
       not F[58]["url_officiel"], str(F[58]["url_officiel"]))
_check("chaîne de 4 rebonds → rien (borne de profondeur)",
       F[59]["date_event_start"] == "" and not F[59]["url_officiel"],
       str({k: F[59][k] for k in ("date_event_start", "url_officiel")}))
_check("chaîne de 2 rebonds (meta puis JS) → récolté et mémorisé",
       _recolte_ok(60) and F[60]["url_officiel"] == "https://officiel.fr/riche",
       str({k: F[60][k] for k in ("date_event_start", "url_officiel")}))
_check("page de repli qui PARLE de l'événement mais qu'un jeton brouillé atteint aussi → "
       "rien récolté, rien mémorisé (la mesure tranche là où le titre ne peut pas)",
       F[61]["date_event_start"] == "" and not F[61]["url_officiel"] and not F[61]["infos_pratiques"],
       str({k: F[61][k] for k in ("date_event_start", "url_officiel", "infos_pratiques")}))
_check("… et la même page atteinte par un lien dont le jeton COMPTE reste récoltée (cas 50)",
       _recolte_ok(50))

# ── 2026-09-08 : la page de l'événement fait foi pour une image de provenance non officielle
# Une image prise ailleurs (Wikimedia) cède à l'og:image ; une image posée à la main jamais ;
# une page sans og:image mais avec l'affiche en <img> la fournit quand la fiche est vide.
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
for eid, url, img, src in (
    (41, "https://officiel.fr/riche", "https://upload.wikimedia.org/nuit-de-nice.jpg", "commons"),
    (42, "https://officiel.fr/riche", "https://ailleurs.org/choix-de-franck.jpg", "manual"),
    (43, "https://officiel.fr/festival-photo/", "", ""),
):
    # url_source est UNIQUE en base : on la distingue par un suffixe, url_officiel (lue
    # d'abord par la moisson) reste la page officielle commune.
    conn.execute("INSERT INTO events_raw (id,title,url_source,url_officiel,statut,date_event_start,lieu,"
                 "ville,url_image,image_source,date_event_end) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 (eid, "Fiche %d" % eid, f"{url}?fiche={eid}", url, "evaluated", "2026-11-11", "Salle", "Ville",
                  img, src, "2026-12-01"))
conn.commit()
conn.close()
mo.main(["41", "42", "43", "--apply"])
conn = sqlite3.connect(tmp)
conn.row_factory = sqlite3.Row
f41, f42, f43 = (dict(conn.execute("SELECT url_image FROM events_raw WHERE id=?", (i,)).fetchone()) for i in (41, 42, 43))
conn.close()
_check("une image prise AILLEURS (Wikimedia) cède à l'og:image de la page de l'événement",
       f41["url_image"] == "https://officiel.fr/affiche.jpg", str(f41["url_image"]))
_check("une image posée À LA MAIN n'est jamais remplacée",
       f42["url_image"] == "https://ailleurs.org/choix-de-franck.jpg", str(f42["url_image"]))
_check("page sans og:image : l'affiche en <img> est prise quand la fiche est vide",
       f43["url_image"] == "https://officiel.fr/wp-content/uploads/06.13-Festival-Photo.png", str(f43["url_image"]))

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
