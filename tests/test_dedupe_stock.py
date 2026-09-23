#!/usr/bin/env python3
"""Fixture : une nouvelle fiche se compare AUSSI au stock déjà retenu (2026-09-23).

⚠️ BASE JETABLE (init_db sur un fichier temporaire). Aucun réseau, aucun appel LLM,
Slack intercepté.

D'OÙ ÇA VIENT. Franck, 23/09 : « comment c'est possible d'avoir deux articles identiques ?
Il n'y a pas, dans le process, le fait de regarder si on n'a pas déjà écrit quelque chose
sur le sujet ? » Terra Madre Salone del Gusto (Turin, 24-27/09) : fiche 2190 en ligne
depuis le 20/07 (WP#2190/8132), puis 5534 publiée le 15/09 (WP#9388/9503), puis 5639
créée le 22/09 (WP#10303). Le cron de 8h30 ne comparait que les fiches 'pending' entre
elles : 5534 n'a jamais rencontré 2190.

LES TITRES. 5534 et 5639 : tels que le digest Slack les a imprimés (« Terra Madre 2026
celebra la biodiversità e porta i suoi… », « Terra Madre Salone del Gusto »), le premier
complété par l'adresse de sa source torinoclick. 2190 : RECONSTITUÉ depuis l'adresse de
sa source (…/dal-24-al-27-settembre-terra-madre-salone-del-gusto-porta-la-biodiversita-
nel-centro-storico-di-torino/) — le titre exact en base n'a pas été lu.

QUEL TITRE EST COMPARÉ — appris en écrivant cette fixture. La colonne `title` garde le
titre de la SOURCE ; le texte rédigé en français va dans `article_title`
(scripts/enrich.py, l'UPDATE qui écrit enrich_data). Une première version du §2 mettait le
titre FR publié (« …quitte le Lingotto pour investir le centre historique de Turin ») dans
`title` : la source italienne ne s'y appariait plus — deux mots communs sur trois requis.
Ce n'était pas la base réelle. Le §2 pose donc les deux colonnes comme elles le sont.

CE QUE LA FIXTURE VÉRIFIE :

  1. LE TÉMOIN ROUGE : le chemin d'avant (`_groups` sur les seules 'pending') ne met
     JAMAIS la nouvelle en face de la fiche du stock — c'est le défaut constaté.
  2. `dedupe.main()` (le cron, sans option) absorbe 5534 et 5639 dans 2190 : statut
     'merged', duplicate_of=2190, entrée `unmerge_data` lisible par scripts.unmerge ;
     la fiche du stock n'est PAS modifiée ; un message Slack dit ce qui a été fait et
     comment le défaire.
  3. ⚠️ CE QUI DOIT PASSER (règle 3 de CLAUDE.md), pris près de la frontière :
       a. « In cucina con… Roberto Alajmo », même ville, mêmes dates — le faux positif
          RÉEL du rapport de 9h50 du 23/09 : la coïncidence ne suffit pas à absorber ;
       b. la même fiche Terra Madre, mais celle du stock est TERMINÉE : l'édition
          suivante se publie (règle 5) ;
       c. titre du stock avec « 2026 », nouvelle avec « 2028 » : deux éditions ;
       d. une fiche du stock sans date : ne retient rien (donnée manquante) ;
       e. la jumelle italienne du stock (translation_of) n'est jamais la cible ;
       f. une nouvelle « Terra Madre … annullato » : PAS absorbée — ce serait taire
          l'annulation ; la porte d'annulation la retient et la signale ;
       g. un autre territoire : pas comparé.
  4. Le dry-run montre l'absorption et n'écrit rien.

Lancer : .venv/bin/python -m tests.test_dedupe_stock
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db   # noqa: E402
import scripts.dedupe as dd                   # noqa: E402

dd.DB_PATH = tmp
SLACK = []
dd.slack.notify = lambda texte, *a, **k: SLACK.append(texte) or True
echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


AUJ = date.today()
DEBUT = (AUJ + timedelta(days=1)).isoformat()
FIN = (AUJ + timedelta(days=4)).isoformat()
PASSE_D = (AUJ - timedelta(days=30)).isoformat()
PASSE_F = (AUJ - timedelta(days=27)).isoformat()

T_2190_SOURCE = ("Dal 24 al 27 settembre Terra Madre Salone del Gusto porta la biodiversità "
                 "nel centro storico di Torino")
T_2190_PUBLIE = ("Terra Madre Salone del Gusto quitte le Lingotto pour investir le centre "
                 "historique de Turin")
T_5534 = "Terra Madre 2026 celebra la biodiversità e porta i suoi custodi nel cuore di Torino"
T_5639 = "Terra Madre Salone del Gusto"
T_CUCINA = "In cucina con... la Sicilia di Roberto Alajmo apre un nuovo ciclo a Torino"


def _base():
    if tmp.exists():
        tmp.unlink()
    conn = sqlite3.connect(tmp)
    init_db(conn)
    dd.ensure_unmerge_column(conn)
    dd.ensure_annulation_columns(conn)
    return conn


def _ins(conn, id_, titre, statut, debut=DEBUT, fin=FIN, terr="piemonte", ville="Torino",
         lieu="Centro storico di Torino", wp=None, trad=None, desc="Texte de la source."):
    conn.execute(
        "INSERT INTO events_raw (id, title, statut, date_event_start, date_event_end, "
        "territoire, ville, lieu, wp_post_id_as, translation_of, description, url_source, "
        "source_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (id_, titre, statut, debut, fin, terr, ville, lieu, wp, trad, desc,
         f"https://exemple.test/{id_}", "radar"))
    conn.commit()


def _ligne(conn, id_):
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM events_raw WHERE id=?", (id_,)).fetchone()
    conn.row_factory = None
    return dict(r)


def _cron():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        dd.main([])
    return buf.getvalue()


# ════════════════════════════════════════════════════════════════════════════════════════
# 1. LE TÉMOIN ROUGE — le chemin d'avant ne les met jamais face à face
# ════════════════════════════════════════════════════════════════════════════════════════
print("──── 1. témoin rouge : les 'pending' seules ne voient pas le stock ────")
conn = _base()
_ins(conn, 2190, T_2190_SOURCE, "published_cs", wp=2190)
_ins(conn, 5534, T_5534, "pending")
pending = [dict(zip([c[0] for c in conn.execute("SELECT * FROM events_raw").description], r))
           for r in conn.execute("SELECT * FROM events_raw WHERE statut='pending'")]
_check("le chemin d'avant (statut='pending' seul) n'a qu'une fiche en main — rien à apparier",
       [len(g) for g in dd._groups(pending)] == [1])
tous = [_ligne(conn, 2190), _ligne(conn, 5534)]
_check("   alors que le critère, lui, les apparie (le défaut n'était PAS la ressemblance)",
       dd._memes_titres(tous[0], tous[1]))
conn.close()

# ════════════════════════════════════════════════════════════════════════════════════════
# 2. LE CAS TERRA MADRE — absorbé par le cron, sans toucher la fiche en ligne
# ════════════════════════════════════════════════════════════════════════════════════════
for _ in (1,):
    print("\n──── 2. Terra Madre : 2190 en ligne (titre source + article FR), 5534 et 5639 "
          "arrivent ────")
    conn = _base()
    _ins(conn, 2190, T_2190_SOURCE, "published_cs", wp=2190, desc="Matière d'origine.")
    conn.execute("UPDATE events_raw SET article_title=? WHERE id=2190", (T_2190_PUBLIE,))
    conn.commit()
    _ins(conn, 8132, "Terra Madre Salone del Gusto lascia il Lingotto per il centro storico",
         "published_cs", wp=8132, trad=2190)
    _ins(conn, 5534, T_5534, "pending", desc="Matière bien plus longue " * 40)
    _ins(conn, 5639, T_5639, "pending")
    avant_2190 = _ligne(conn, 2190)
    SLACK.clear()
    _cron()
    for id_ in (5534, 5639):
        l = _ligne(conn, id_)
        _check(f"[{id_}] absorbée dans 2190 (statut merged, duplicate_of=2190)",
               l["statut"] == "merged" and l["duplicate_of"] == 2190,
               f"statut={l['statut']} duplicate_of={l['duplicate_of']}")
        pile = json.loads(l["unmerge_data"] or "[]")
        _check(f"   [{id_}] unmerge_data : statut d'avant 'pending', gagnant 2190",
               pile and pile[-1].get("statut_avant") == "pending"
               and pile[-1].get("gagnant") == 2190, pile)
    _check("la fiche en ligne n'est PAS modifiée (description, statut)",
           _ligne(conn, 2190) == avant_2190)
    _check("   et jamais la jumelle italienne 8132 comme cible",
           _ligne(conn, 5534)["duplicate_of"] != 8132)
    _check("un message Slack nomme les absorptions et la commande qui les défait",
           len(SLACK) == 1 and "[5534]" in SLACK[0] and "WP#2190" in SLACK[0]
           and "scripts.unmerge 5534 5639" in SLACK[0], SLACK)
    conn.close()

# ════════════════════════════════════════════════════════════════════════════════════════
# 3. CE QUI DOIT PASSER — pris près de la frontière
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 3. cas frontière : ce qui NE doit PAS être absorbé ────")


def _reste_pending(label, prepare, id_nouvelle=5534):
    conn = _base()
    prepare(conn)
    SLACK.clear()
    _cron()
    l = _ligne(conn, id_nouvelle)
    _check(label, l["statut"] == "pending" and not l["duplicate_of"],
           f"statut={l['statut']} duplicate_of={l['duplicate_of']}")
    conn.close()
    return l


_reste_pending("a. « In cucina con… », même ville et mêmes dates : pas absorbée "
               "(la coïncidence seule n'absorbe pas)",
               lambda c: (_ins(c, 2190, T_2190_SOURCE, "published_cs", wp=2190),
                          _ins(c, 5534, T_CUCINA, "pending", lieu="Mercato Centrale Torino")))
_reste_pending("b. la fiche du stock est TERMINÉE : la nouvelle édition se publie",
               lambda c: (_ins(c, 2190, T_2190_SOURCE, "published_cs", wp=2190,
                               debut=PASSE_D, fin=PASSE_F),
                          _ins(c, 5534, T_5534, "pending", debut="", fin="")))
_reste_pending("c. « … 2026 » au stock, « … 2028 » en arrivée : deux éditions",
               lambda c: (_ins(c, 2190, "Terra Madre Salone del Gusto 2026 porta la "
                               "biodiversità a Torino", "published_cs", wp=2190),
                          _ins(c, 5534, "Terra Madre Salone del Gusto 2028 porta la "
                               "biodiversità a Torino", "pending", debut="", fin="")))
_reste_pending("d. fiche du stock SANS date : elle ne retient rien",
               lambda c: (_ins(c, 2190, T_2190_SOURCE, "published_cs", wp=2190,
                               debut="", fin=""),
                          _ins(c, 5534, T_5534, "pending")))
l = _reste_pending("f. « Terra Madre … annullato » : pas absorbée, l'annulation est retenue",
                   lambda c: (_ins(c, 2190, T_2190_SOURCE, "published_cs", wp=2190),
                              _ins(c, 5534, "Terra Madre Salone del Gusto annullato: la "
                                   "biodiversità non arriva nel centro di Torino", "pending")))
_check("   et elle est SIGNALÉE (porte d'annulation, fiche visée = celle du stock)",
       bool(l.get("annulation_detectee_at")) and l.get("annulation_fiche_visee_id") == 2190,
       {k: l.get(k) for k in ("annulation_detectee_at", "annulation_fiche_visee_id")})
_reste_pending("g. même titre dans un AUTRE territoire : pas comparé",
               lambda c: (_ins(c, 2190, T_2190_SOURCE, "published_cs", wp=2190),
                          _ins(c, 5534, T_5534, "pending", terr="savoie")))

print("\n──── 3 bis. la jumelle traduite n'est jamais une cible ────")
conn = _base()
_ins(conn, 8132, T_2190_SOURCE, "published_cs", wp=8132, trad=9999)
_ins(conn, 5534, T_5534, "pending")
_cron()
_check("e. seule la traduction couvre le sujet : pas d'absorption (on absorbe dans "
       "l'original, jamais dans sa jumelle)", _ligne(conn, 5534)["statut"] == "pending")
conn.close()

# ════════════════════════════════════════════════════════════════════════════════════════
# 4. LE DRY-RUN — il montre, il n'écrit pas
# ════════════════════════════════════════════════════════════════════════════════════════
print("\n──── 4. dry-run ────")
conn = _base()
_ins(conn, 2190, T_2190_SOURCE, "published_cs", wp=2190)
_ins(conn, 5534, T_5534, "pending")
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    dd.main(["--dry-run"])
sortie = buf.getvalue()
_check("le dry-run annonce l'absorption et nomme la fiche du stock",
       "id=5534" in sortie and "id=2190 WP#2190" in sortie, sortie[-600:])
_check("   et n'écrit rien", _ligne(conn, 5534)["statut"] == "pending")
conn.close()

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
