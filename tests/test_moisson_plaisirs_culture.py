#!/usr/bin/env python3
"""Fixture de scripts/moisson_plaisirs_culture.py — sur la VRAIE brochure 2026.

LA MATIÈRE. `tests/fixtures/plaisirs_culture_2026_brochure.json` est la couche texte de
la brochure officielle (valledaostaheritage.com, téléchargée le 22/09/2026 ; adresse et
empreinte sha256 du PDF dans le fichier), relevée par `fragments_pdf` : chaque fragment
avec sa position, sa taille et sa police. Le PDF lui-même (6,4 Mo, images comprises)
n'est pas versionné. Cette fixture tourne donc SANS pypdf.

LE COMPTE, FAIT À LA MAIN sur le relevé ligne à ligne de la brochure (une ligne = un
fragment de gras corps 10 à la marge, lu page imprimée par page imprimée) :

    inauguration       p. 5                                     1
    visite             p. 8, 9, 12-15, 18-28 : deux par page ;
                       p. 10, 11, 16, 17 : une par page          38
    incontri           p. 34-39 : deux par page ; p. 40 : une    13
    eventi             p. 42, 43, 44 : deux par page              6
    bambini e famiglie p. 46, 47, 48, 49 : deux par page          8
                                                               ----
    rendez-vous publics                                          66
    + a scuola (p. 52 : un, p. 53 : deux)                         3
    + luoghi (intertitres CASTELLI, SITI ARCHEOLOGICI, MOSTRE,
      MUSEI, MUSEI A TARIFFA RIDOTTA)                             5
    + 4e de couverture « Regione autonoma Valle d'Aosta »         1
                                                               ----
    fiches lues par le parseur                                   75

Les neuf dernières DOIVENT être lues puis écartées avec leur motif : c'est ce qui prouve
que le compte « écartées » dit d'où il vient.

LES CAS FRONTIÈRE, choisis là où la mise en page piège :
  • « Il tesoro della cattedrale » est sous l'en-tête courant « LUNEDÌ 21 | MARTEDÌ 22 »,
    avant le grand en-tête du 22 : elle est du 21 SEULEMENT (le calendrier le dit) ;
  • « Tissus d'histoire » sort, dans l'ordre du flux PDF, AVANT l'en-tête de sa page :
    seul l'ordre par position la met au 26 ;
  • « ConneXions » a un X en corps 13 dans un titre en corps 10 ;
  • « Le lunette del Castello di Issogne » court du 19 au 26 (« da … a … ») : au 23, elle
    est EN COURS et doit être gardée, du 23 au 26.

LA CONTRE-ÉPREUVE du calendrier : la brochure porte son propre calendrier récapitulatif ;
chacune de ses 89 lignes doit retrouver une fiche (même page, même jour). On casse
ensuite une fiche exprès, et le contrôle DOIT le voir — sinon un « 0 écart » ne prouve
rien.

LE ZÉRO QUI PARLE : une brochure vide ou d'une autre forme doit rendre 0 fiche ET une
alerte qui dit que ce zéro n'est pas une absence de rendez-vous.

L'ÉCRITURE : sur une base JETABLE créée par `scripts.scraper_events.init_db`, jamais
`data/events.db`.

Lancer : python3 -m tests.test_moisson_plaisirs_culture
"""
import copy
import json
import sqlite3
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.moisson_plaisirs_culture import (  # noqa: E402
    SOURCE_NAME, TERRITOIRE, confronter, dates_repliques, ecrire, parse_brochure,
    selectionner)
from scripts.publisher_as import _map_territoire  # noqa: E402
from scripts.scraper_events import init_db  # noqa: E402
from utils.moments_forts import etiquettes  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "plaisirs_culture_2026_brochure.json"

echecs = []


def verifie(cond, ok, ko):
    if cond:
        print("  ok  " + ok)
    else:
        echecs.append(ko)
        print("  ÉCHEC " + ko)


def fiche(entrees, bout):
    return next((e for e in entrees if bout in (e.get("titre_calendrier") or e["titre"]).lower()), None)


def main() -> int:
    pages = json.loads(FIXTURE.read_text(encoding="utf-8"))["pages"]

    print("— le compte")
    r = parse_brochure(pages)
    ent = r["entrees"]
    verifie(r["alerte"] is None, "pas d'alerte sur la vraie brochure", f"alerte inattendue : {r['alerte']}")
    verifie(len(ent) == 75, "75 fiches lues (compte manuel ci-dessus)", f"75 fiches attendues, {len(ent)} lues")
    par_section = Counter(e["section"] for e in ent if e["page"] is not None)
    attendu = {"inaugurazione": 1, "visite": 38, "incontri": 13, "eventi": 6, "famiglie": 8,
               "scuola": 3, "luoghi": 5}
    verifie(dict(par_section) == attendu, f"par section : {dict(par_section)}",
            f"par section : attendu {attendu}, obtenu {dict(par_section)}")

    print("— la contre-épreuve du calendrier")
    ctl = confronter(ent, r["calendrier"])
    verifie(len(r["calendrier"]) == 89, "89 lignes de calendrier lues",
            f"89 lignes de calendrier attendues, {len(r['calendrier'])}")
    verifie(not ctl["sans_fiche"] and not ctl["jour_absent"] and not ctl["jour_en_trop"],
            "chaque ligne du calendrier retrouve sa fiche au bon jour, et aucune fiche n'a de jour en trop",
            f"{len(ctl['sans_fiche'])} ligne(s) sans fiche, {len(ctl['jour_absent'])} jour(s) absent(s), "
            f"{len(ctl['jour_en_trop'])} jour(s) en trop")
    # … et le contrôle voit une fiche cassée exprès (sinon « 0 écart » ne prouve rien)
    casse = copy.deepcopy(ent)
    lun = fiche(casse, "le lunette")
    lun["jours"].pop("2026-09-19", None)
    casse = [e for e in casse if "tesoro della cattedrale" not in e["titre"].lower()]
    # le cas de la version fautive essayée le 22/09 : un jour que le calendrier ne donne pas
    fiche(casse, "ad memoriam")["jours"]["2026-09-22"] = "17:00"
    ctl2 = confronter(casse, r["calendrier"])
    verifie(len(ctl2["jour_absent"]) == 1 and len(ctl2["sans_fiche"]) == 1
            and len(ctl2["jour_en_trop"]) == 1,
            "contre-épreuve : un jour retiré, une fiche retirée et un jour ajouté sont vus",
            f"fiche cassée non vue : {len(ctl2['jour_absent'])} jour absent, "
            f"{len(ctl2['sans_fiche'])} sans fiche, {len(ctl2['jour_en_trop'])} en trop (attendu 1, 1, 1)")

    print("— les cas frontière")
    tes = fiche(ent, "tesoro della cattedrale")
    verifie(tes and list(tes["jours"]) == ["2026-09-21"],
            "Il tesoro della cattedrale : le 21 seulement (l'en-tête courant 21|22 ne décide pas)",
            f"Il tesoro : {tes and list(tes['jours'])}")
    tis = fiche(ent, "tissus d")
    verifie(tis and list(tis["jours"]) == ["2026-09-26"] and tis["ville"] == "Sarre",
            "Tissus d'histoire : le 26, à Sarre (ordre par position, pas par flux)",
            f"Tissus : {tis and (list(tis['jours']), tis['ville'])}")
    con = fiche(ent, "connexions")
    verifie(con and list(con["jours"]) == ["2026-09-25"] and con["jours"]["2026-09-25"] == "16:00",
            "ConneXions : titre reconnu malgré le X en corps 13, le 25 à 16:00",
            f"ConneXions : {con and con['jours']}")
    lun = fiche(ent, "le lunette")
    verifie(lun and list(lun["jours"]) == [f"2026-09-{j}" for j in range(19, 27)]
            and lun["ville"] == "Issogne" and lun["organisateur"].startswith("Comune di Issogne"),
            "Le lunette : du 19 au 26 (plage « da … a … »), Issogne, Comune di Issogne",
            f"Le lunette : {lun and (list(lun['jours']), lun['ville'], lun['organisateur'])}")
    cer = fiche(ent, "cercami tra il bianco")
    verifie(cer and cer["section"] == "famiglie" and list(cer["jours"]) == ["2026-09-26"]
            and cer["ville"] == "Saint-Pierre",
            "Cercami tra il bianco della neve! : section famiglie (absente du calendrier), 26, Saint-Pierre",
            f"Cercami : {cer and (cer['section'], list(cer['jours']), cer['ville'])}")

    print("— les répliques")
    verifie(len(dates_repliques("da sabato 19 settembre a sabato 26 settembre dalle ore 13.00")) == 8,
            "« da sabato 19 a sabato 26 » → 8 jours", "plage mal lue")
    rep = dates_repliques("domenica 20 settembre, sabato 26 settembre e domenica 27 settembre ore 10.15")
    verifie(rep == [("2026-09-20", "10:15"), ("2026-09-26", "10:15"), ("2026-09-27", "10:15")],
            "trois dates, l'heure écrite après la dernière vaut pour les trois", f"répliques : {rep}")

    print("— la sélection au 23/09 (règle 5 : à venir ou en cours)")
    garder, ecartes = selectionner(ent, "2026-09-23")
    motifs = Counter(m.split(" :")[0].split(" «")[0] for _, m in ecartes)
    verifie(len(garder) == 42 and len(ecartes) == 33,
            "42 gardées, 33 écartées", f"attendu 42/33, obtenu {len(garder)}/{len(ecartes)}")
    verifie(dict(motifs) == {"passée": 24, "section": 8, "hors programme": 1},
            f"motifs : {dict(motifs)}", f"motifs inattendus : {dict(motifs)}")
    g_lun = next((g for g in garder if "le lunette" in g["titre"].lower()), None)
    verifie(g_lun and (g_lun["date_start"], g_lun["date_end"], g_lun["time_start"])
            == ("2026-09-23", "2026-09-26", "13:00"),
            "Le lunette, en cours : gardée du 23 au 26, 13:00",
            f"Le lunette : {g_lun and (g_lun['date_start'], g_lun['date_end'], g_lun['time_start'])}")
    verifie(not any("tesoro della cattedrale" in g["titre"].lower() for g in garder),
            "Il tesoro (21/09) est écarté comme passé", "Il tesoro a été gardé")
    verifie(len({g["url"] for g in garder}) == len(garder), "une url_source distincte par fiche",
            "deux fiches partagent une url_source : la seconde serait perdue à l'insertion")
    g22, _ = selectionner(ent, "2026-09-22")
    verifie(len(g22) == 49, "au 22/09 : 49 gardées (7 de plus, celles du 22)",
            f"au 22/09 : 49 attendues, {len(g22)}")

    print("— le zéro qui parle")
    for nom, pp in (("brochure vide", []),
                    ("mise en page changée (plus aucun gras)",
                     [dict(p, frags=[dict(f, f="Roboto-Regular") for f in p["frags"]]) for p in pages])):
        rv = parse_brochure(pp)
        verifie(not rv["entrees"] and rv["alerte"] and "PAS une absence" in rv["alerte"],
                f"{nom} → 0 fiche ET une alerte qui le dit",
                f"{nom} : {len(rv['entrees'])} fiche(s), alerte={rv['alerte']!r}")

    # Le 22/09 au soir, sur le VPS : 75 fiches, 0 ligne de calendrier, 35 fiches sans folio,
    # et une contre-épreuve qui affichait « 0 écart ». Les deux zéros doivent ARRÊTER.
    from scripts.moisson_plaisirs_culture import demi_pages, _est_calendrier
    cal_pdf = {dp["page_pdf"] for dp in demi_pages(pages) if _est_calendrier(dp)}
    sans_cal = [p for n, p in enumerate(pages, 1) if n not in cal_pdf]
    rv = parse_brochure(sans_cal)
    verifie(rv["entrees"] and not rv["calendrier"] and rv["alerte"] and "AUCUNE ligne de calendrier" in rv["alerte"],
            f"calendrier illisible ({len(cal_pdf)} page(s) retirée(s)) → fiches lues MAIS alerte, rien d'écrit",
            f"calendrier illisible : alerte={rv['alerte']!r}")
    sans_folios = [dict(p, frags=[f for f in p["frags"] if not (f["y"] < 30 and f["t"].strip().isdigit())])
                   for p in pages]
    rv = parse_brochure(sans_folios)
    verifie(rv["alerte"] and "SANS FOLIO" in rv["alerte"],
            "folios illisibles → alerte, rien d'écrit",
            f"folios illisibles : alerte={rv['alerte']!r}")
    rv = parse_brochure(pages)
    verifie(rv["alerte"] is None,
            "contre-épreuve : la brochure intacte ne déclenche aucune alerte",
            f"contre-épreuve : alerte inattendue {rv['alerte']!r}")

    print("— l'écriture, sur base jetable")
    with tempfile.TemporaryDirectory() as d:
        conn = sqlite3.connect(Path(d) / "jetable.db")
        init_db(conn)
        pose = ecrire(conn, garder)
        n = conn.execute("SELECT COUNT(*) FROM events_raw WHERE source_name=?", (SOURCE_NAME,)).fetchone()[0]
        verifie(pose == n == 42, "42 lignes posées, 42 recomptées en base",
                f"posées {pose}, en base {n}, attendu 42")
        verifie(ecrire(conn, garder) == 0, "rejouer n'insère rien (url_source UNIQUE)",
                "le second passage a inséré des doublons")
        row = conn.execute("""SELECT territoire, date_start, date_event_start, date_event_end,
                                     time_start, ville, organisateur, source_type
                              FROM events_raw WHERE title LIKE 'Le lunette%'""").fetchone()
        verifie(row == (TERRITOIRE, "2026-09-23", "2026-09-23", "2026-09-26", "13:00", "Issogne",
                        row[6], "institutionnel") and row[6],
                f"ligne écrite : {row[:6]}", f"ligne écrite inattendue : {row}")
        # de bout en bout : la ligne écrite reçoit l'étiquette du moment fort
        terr = _map_territoire(row[0])
        verifie(terr == "vallee-d-aoste"
                and etiquettes(terr, row[2], SOURCE_NAME, "fr") == ["Journées européennes du patrimoine"],
                "la ligne écrite, lue par _map_territoire + moments_forts, reçoit l'étiquette",
                f"étiquette non posée : territoire {terr!r}")
        conn.close()

    print()
    if echecs:
        print(f"ÉCHEC — {len(echecs)} problème(s).")
        return 1
    print("SUCCÈS — 0 problème(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
