#!/usr/bin/env python3
"""Signale les fiches datées AVANT leur propre collecte — le bon jour, la mauvaise année.

TROUVÉ PAR L'AGENT QUOTIDIEN (2026-08-11, premier run réel) : « trois fiches portent le
bon jour mais une année périmée — 4440 en 2025, 4691 et 4434 en 2024. » Il proposait de
comparer l'année stockée à l'année de collecte. C'est exactement la bonne idée, et voici
pourquoi elle marche.

POURQUOI CE DÉFAUT EST LE PIRE DE TOUS. Une fiche datée dans le passé disparaît de TOUT :
la règle 5 l'écarte des files, des audits et des bilans — à juste titre, puisqu'un
événement terminé ne sert personne. Mais si la date est FAUSSE, l'événement, lui, est
peut-être devant nous. La fiche n'est pas morte : elle est enterrée vivante, et aucun
compteur ne la réclamera jamais. C'est un état terminal sans rouvreur (règle 3), et c'est
ce script qui le rouvre.

⚠️ Ce script REGARDE DONC LE PASSÉ, ce que la règle 5 interdit partout ailleurs. C'est
délibéré et c'est le seul endroit où ça se justifie : on ne cherche pas à réparer des
événements terminés, on cherche des événements À VENIR qui portent une date morte. La
liste doit rester COURTE — si elle enfle, c'est que le filtre ci-dessous est trop large.

CE QUI REND LE SIGNAL SÛR — et c'est `dates.py` lui-même qui le fournit. Quand le texte
ne porte pas d'année, `_year()` en invente une avec une grâce de SOIXANTE JOURS : une
date qui serait plus vieille que ça bascule à l'année suivante. Donc `parse_dates` ne
peut PAS produire une date antérieure de plus de 60 jours à la collecte.

Une telle date vient forcément d'ailleurs :
  • d'une année ÉCRITE en toutes lettres dans le texte (« l'édition du 5 juillet 2024 »,
    une rétrospective, un rappel d'édition précédente) ;
  • du JSON-LD d'une page qui n'a pas été remis à jour depuis l'édition passée ;
  • d'une balise `<time datetime>` qui datait l'ARTICLE et non l'événement.

Aucune source n'annonce un événement fini depuis plus de deux mois au moment où elle
publie. Le seuil n'est donc pas un réglage de confort : c'est le miroir exact de la
grâce de `_year()`. Le baisser ferait remonter des événements légitimement passés (une
page de saison lue en août mentionne le 12 mars) ; le monter raterait les décalages
d'un an de peu.

CE QU'IL NE FAIT PAS : il ne corrige rien. La date affichée est peut-être juste — la
fiche peut être une archive assumée. Corriger d'office reviendrait à INVENTER une année,
ce qui est précisément la faute qu'on traque (et l'erreur 14 du 2026-08-11 : j'ai déclaré
deux dates fausses alors qu'elles étaient bonnes, sur la foi d'un affichage tronqué).
Donc il montre LA PHRASE d'où vient la date, et le geste reste humain — ou revient à
l'agent quotidien, qui sait ouvrir la page et déposer la correction par
`completer_verifie --depuis` avec sa clause « remplace ».

  .venv/bin/python -m scripts.audit_annee_date
  .venv/bin/python -m scripts.audit_annee_date --tout   # sans le plafond d'affichage
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Miroir exact de la grâce de `dates._year()`. Les deux doivent bouger ensemble : si la
# grâce passait à 90 jours, ce seuil laisserait passer un mois de faux positifs.
GRACE_JOURS = 60

_MOIS = ("janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|"
         "octobre|novembre|décembre|decembre|"
         "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|"
         "ottobre|novembre|dicembre")


def _norm(s: str) -> str:
    n = unicodedata.normalize("NFKD", (s or ""))
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


def phrase_de_l_annee(materiau: str, iso: str) -> str:
    """La phrase du texte source où l'année suspecte est écrite, ou "".

    C'EST LE GARDE-FOU DE L'ERREUR 14 (2026-08-11) : j'avais déclaré deux dates fausses
    parce que mon extrait montrait le mauvais bout du texte. Elles étaient justes. Une
    date qu'on accuse doit être présentée AVEC la phrase qui l'a produite, sinon le
    lecteur arbitre à l'aveugle — et il tranchera dans le sens de celui qui affiche.

    On cherche l'année sous ses trois écritures possibles : ISO (2024-07-05), en toutes
    lettres (5 juillet 2024) et numérique (05/07/2024)."""
    if not materiau or not iso:
        return ""
    an, mois, jour = iso.split("-")
    t = _norm(materiau)
    motifs = (
        rf"\b{an}-{mois}-{jour}\b",
        rf"\b0?{int(jour)}\s+(?:{_MOIS})\.?\s*{an}\b",
        rf"\b(?:{_MOIS})\s+{an}\b",
        rf"\b0?{int(jour)}[/.]0?{int(mois)}[/.]{an}\b",
        rf"\b{an}\b",                       # dernier recours : l'année seule
    )
    for motif in motifs:
        m = re.search(motif, t)
        if not m:
            continue
        # La phrase, bornée par la ponctuation forte de part et d'autre.
        debut = max((t.rfind(c, 0, m.start()) for c in ".;!?\n"), default=-1)
        fin = min((p for p in (t.find(c, m.end()) for c in ".;!?\n") if p != -1),
                  default=len(t))
        return " ".join(materiau[debut + 1:fin + 1].split())[:220].strip()
    return ""


def _materiau(row: sqlite3.Row) -> str:
    """Le texte SOURCE, jamais l'article rédigé : on cherche d'où vient la date, pas ce
    que le modèle en a fait ensuite."""
    bouts = []
    for col in ("title", "description", "date_start"):
        try:
            v = row[col]
        except (IndexError, KeyError):
            v = None
        if v:
            bouts.append(str(v))
    try:
        if row["mail_corps"]:
            bouts.append(str(row["mail_corps"]))
    except (IndexError, KeyError):
        pass
    return "\n".join(bouts)


def _colonnes(conn: sqlite3.Connection) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}


def _explique(conn: sqlite3.Connection, ids: list[int], jours: int) -> int:
    """Pourquoi CETTE fiche est-elle retenue, ou pas ? Une réponse par étage.

    NÉ D'UN ZÉRO DE PRODUCTION. L'audit annonçait « 240 examinées, aucune suspecte » le
    soir même où l'agent en avait nommé trois. Les deux affirmations ne pouvaient pas être
    vraies ensemble, et rien dans la sortie ne permettait de trancher : il fallait ouvrir
    SQLite à la main pour savoir laquelle des six conditions avait mangé les fiches.

    C'est le défaut de tous les compteurs qui filtrent : ils disent ce qui reste, jamais ce
    qui est tombé. Un filtre qui ne sait pas s'expliquer se croit — et on le croit d'autant
    plus qu'il donne le chiffre qui arrange."""
    for eid in ids:
        r = conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone()
        print(f"\n═══ Fiche {eid} ═══")
        if r is None:
            print("  INTROUVABLE en base — elle n'existe pas (ou plus) sous ce numéro.")
            continue
        print(f"  {(r['title'] or '')[:76]}")
        cles = ("statut", "duplicate_of", "recurring", "date_event_start",
                "date_event_end", "date_source", "scrape_date", "wp_post_id_as")
        for c in cles:
            try:
                print(f"    {c:<18} = {r[c]!r}")
            except (IndexError, KeyError):
                print(f"    {c:<18} = (colonne absente)")

        motifs = []
        if r["duplicate_of"]:
            motifs.append(f"doublon de {r['duplicate_of']} — traitée sur l'original")
        if (r["statut"] or "") in ("merged", "rejected"):
            motifs.append(f"statut « {r['statut']} » : hors des files")
        if r["recurring"]:
            motifs.append("récurrente : pas de date unique, donc pas de date fausse")
        if not (r["date_event_start"] or "").strip():
            motifs.append("SANS date de début : c'est un TROU, pas une date fausse — "
                          "elle relève de scripts.dates, pas de cet audit")
        if not (r["scrape_date"] or "").strip():
            motifs.append("sans date de collecte : rien à quoi comparer")
        if motifs:
            print("  ÉCARTÉE du périmètre :")
            for m in motifs:
                print(f"    • {m}")
            continue

        try:
            collecte = date.fromisoformat((r["scrape_date"] or "")[:10])
            fin = date.fromisoformat(
                (r["date_event_end"] or r["date_event_start"] or "")[:10])
        except ValueError:
            print("  ÉCARTÉE : date illisible (ni ISO ni horodatage reconnu).")
            continue
        ecart = (collecte - fin).days
        if ecart > jours:
            print(f"  RETENUE : dernière date {fin}, collectée le {collecte} — "
                  f"{ecart} jours AVANT (seuil {jours}).")
        else:
            print(f"  DANS LE PÉRIMÈTRE mais NON suspecte : dernière date {fin}, "
                  f"collectée le {collecte} — écart {ecart} j, sous le seuil de {jours}. "
                  f"C'est le cas normal.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tout", action="store_true",
                    help="affiche toutes les fiches (défaut : les 40 plus récentes)")
    ap.add_argument("--jours", type=int, default=GRACE_JOURS,
                    help=f"écart minimal en jours (défaut {GRACE_JOURS}, "
                         f"= la grâce de dates._year)")
    ap.add_argument("--fiche", nargs="+", type=int, metavar="ID",
                    help="explique, fiche par fiche, POURQUOI elle est retenue ou écartée "
                         "du périmètre — la réponse à « pourquoi celle-là n'y est pas ? »")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cols = _colonnes(conn)
    corps = "mail_corps" if "mail_corps" in cols else "'' AS mail_corps"

    if args.fiche:
        code = _explique(conn, args.fiche, args.jours)
        conn.close()
        return code

    # L'ENTONNOIR, ÉTAGE PAR ÉTAGE — écrit après un « 0 » de production (2026-08-11 au
    # soir). L'audit annonçait « 240 fiches examinées, aucune suspecte » alors que l'agent
    # en avait nommé trois. 240 sur près de cinq mille : le nombre criait que la sélection
    # perdait quelque chose, et il n'y avait AUCUN moyen de savoir où.
    #
    # C'est mot pour mot la faute que CLAUDE.md décrit — « un zéro ne dit pas s'il vient
    # d'un échec ou d'une absence de cas » — et je venais de l'écrire dans ce fichier, dans
    # le commentaire d'à côté, en croyant qu'annoncer le total suffisait. Il ne suffit pas :
    # un dénominateur sans sa décomposition ne se vérifie pas, il se croit.
    print("═══ Fiches datées avant leur propre collecte ═══\n")
    print("Entonnoir de sélection (chaque ligne retire des fiches de la précédente) :")
    for libelle, clause in (
            ("fiches en base", "1=1"),
            ("  – dont doublons fusionnés",
             "COALESCE(duplicate_of,0)<>0 OR COALESCE(statut,'') = 'merged'"),
            ("  – dont écartées (rejected)", "COALESCE(statut,'') = 'rejected'"),
            ("  – dont récurrentes (pas de date unique)", "COALESCE(recurring,0)=1"),
            ("  – dont SANS date de début", "COALESCE(date_event_start,'')=''"),
            ("  – dont sans date de collecte", "COALESCE(scrape_date,'')=''")):
        n = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE {clause}").fetchone()[0]
        print(f"  {n:>6}  {libelle}")

    # PÉRIMÈTRE, écrit ici et répété à l'écran (règle 6) : les fiches DATÉES, non
    # dédoublonnées, non écartées, dont la dernière date connue précède la collecte de
    # plus de `--jours`. Les récurrentes sont exclues : elles n'ont pas de date unique et
    # ne peuvent donc pas en avoir une de fausse.
    lignes = conn.execute(
        f"SELECT id, title, description, date_start, {corps}, statut, "
        "       date_event_start, date_event_end, date_source, scrape_date, "
        "       wp_post_id_as, source_name "
        "FROM events_raw "
        "WHERE COALESCE(duplicate_of,0)=0 "
        "  AND COALESCE(statut,'') NOT IN ('merged','rejected') "
        "  AND COALESCE(recurring,0)=0 "
        "  AND COALESCE(date_event_start,'') <> '' "
        "  AND COALESCE(scrape_date,'') <> '' "
        "ORDER BY id DESC").fetchall()

    suspects, examinees, illisibles = [], 0, []
    for r in lignes:
        try:
            collecte = date.fromisoformat((r["scrape_date"] or "")[:10])
            fin = date.fromisoformat(
                (r["date_event_end"] or r["date_event_start"] or "")[:10])
        except ValueError:
            # ON NE JETTE PLUS EN SILENCE. Une date illisible sortait du décompte sans
            # laisser de trace : le total affiché était donc faux, et faux vers le bas —
            # la direction qui rassure.
            illisibles.append(r["id"])
            continue
        examinees += 1
        if fin >= collecte - timedelta(days=args.jours):
            continue
        suspects.append((r, collecte, fin, (collecte - fin).days))

    # UN ZÉRO DOIT DIRE D'OÙ IL VIENT (leçon du 2026-08-11 : trois fois un « 0 » a semblé
    # désigner une source pauvre, trois fois c'était la requête). On annonce donc toujours
    # combien de fiches ont été EXAMINÉES avant d'annoncer combien sont suspectes.
    print(f"\nPérimètre retenu : {examinees} fiche(s) datées, actives, non récurrentes, "
          f"examinées ; écart retenu > {args.jours} jours.")
    if illisibles:
        print(f"⚠ {len(illisibles)} fiche(s) à date ILLISIBLE, hors décompte — "
              f"{', '.join(str(i) for i in illisibles[:12])}"
              f"{'…' if len(illisibles) > 12 else ''}")
    print()

    if not suspects:
        print("Aucune suspecte dans ce périmètre.")
        print("Si une fiche que vous attendiez n'y est pas, demandez-lui pourquoi :")
        print("  .venv/bin/python -m scripts.audit_annee_date --fiche 4440 4691 4434")
        conn.close()
        return 0

    montrees = suspects if args.tout else suspects[:40]
    for r, collecte, fin, ecart in montrees:
        etat = "EN LIGNE" if r["wp_post_id_as"] else (r["statut"] or "?")
        print(f"  [{r['id']:>5}] {(r['title'] or '')[:66]}")
        print(f"          {r['date_event_start']} → {r['date_event_end'] or '—'}   "
              f"collectée le {collecte}   soit {ecart} j AVANT   "
              f"(date_source={r['date_source'] or '?'}, {etat})")
        # Ce que la MÊME date donnerait à l'année de la collecte : si l'événement existe
        # encore, c'est presque toujours là qu'il tombe. Proposé, jamais écrit.
        try:
            replacee = fin.replace(year=collecte.year)
            if replacee < collecte:
                replacee = fin.replace(year=collecte.year + 1)
            print(f"          même jour à l'année de collecte → {replacee} "
                  f"(hypothèse à VÉRIFIER sur la page, pas à appliquer)")
        except ValueError:
            pass                          # 29 février : pas de report automatique
        phrase = phrase_de_l_annee(_materiau(r), r["date_event_end"]
                                   or r["date_event_start"])
        if phrase:
            print(f"          « {phrase} »")
        else:
            print(f"          (l'année n'apparaît pas dans le texte collecté — elle vient "
                  f"donc de la PAGE ou du modèle, pas du flux)")
        print()

    reste = len(suspects) - len(montrees)
    print(f"{len(suspects)} fiche(s) suspecte(s) sur {examinees} examinée(s)"
          + (f", {reste} non affichée(s) (--tout pour les voir)." if reste else "."))
    print("SIGNALEMENT, PAS UN VERDICT : certaines sont des archives assumées, dont la "
          "date est juste. La correction se fait page en main, par "
          "`completer_verifie --depuis` avec sa clause « remplace ».")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
