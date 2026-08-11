#!/usr/bin/env python3
"""LA SOURCE DIT-ELLE LA MÊME DATE QUE NOUS ? — contradiction, pas extraction.

Franck, 2026-08-11 : « est-ce qu'on a des loops de script jusqu'à obtenir des résultats ?
plus vérificateur ? concernant la véracité des informations ».

Deux questions, et il faut y répondre séparément parce qu'elles ne vont pas ensemble.

SUR LES BOUCLES : on en a, et CLAUDE.md interdit celle qu'on croit vouloir. Rejouer un
refus sur la MÊME matière n'est pas un rouvreur (règle 3) — le modèle produit un résultat
équivalent, le portillon refuse à l'identique, tous les jours, en brûlant deux appels à
chaque passage. Constaté en vrai sur la fiche 3588. Nos vraies boucles ne se rejouent donc
que si QUELQUE CHOSE A CHANGÉ : `_rearme_matiere_changee` (l'empreinte du texte a bougé),
les cooldowns web (une page peut avoir été mise à jour), `purge_bylines --restaurer` (le
vocabulaire s'est amélioré). Une boucle « jusqu'à obtenir un résultat » sur une matière
figée ne converge pas : elle facture.

SUR LA VÉRACITÉ : là, il manquait vraiment quelque chose, et c'est ce script.

Tout le pipeline EXTRAIT. Personne ne CONTREDIT. Or on sait depuis le 2026-08-11, cinq
fois dans la même journée, que sur un texte écrit pour des humains on ne peut pas
extraire — seulement confirmer à partir d'un fait déjà connu. Ce script fait l'inverse du
reste de la chaîne : il part de ce qu'on a écrit et cherche à le REFUTER avec la matière
qu'on détient.

CE QU'IL SIGNALE, ET RIEN D'AUTRE

  ① CONTREDIT — le texte source ne contient QU'UNE SEULE date, et ce n'est pas la nôtre.
    Aucune ambiguïté possible sur « de quelle date parle ce texte » : il n'y en a qu'une.
  ② ANNÉE — le texte porte notre jour et notre mois, mais une autre année.
  ③ JOUR DE SEMAINE — le texte annonce « samedi 7 mai » et notre 7 mai tombe un vendredi.
    Le plus fort des trois, et le seul qui attrape une faute de PLUSIEURS années : c'est
    lui qui a démasqué la fiche 1069, en ligne le 2026-08-11 pour le 7 mai 2027 alors que
    la page Paratissima disait « sabato 7 maggio » et « 4 anni fa » — le 7 mai ne tombe un
    samedi qu'en 2022. Un jour de semaine est écrit par un humain qui savait de quoi il
    parlait, et il contraint l'année à une sur sept. C'est gratuit et personne ne le lisait.

CE QU'IL NE SIGNALE PAS, ET C'EST LE PLUS IMPORTANT

  • l'ABSENCE. Un texte qui ne dit aucune date ne contredit rien. Le 2026-08-11, une file
    de 454 « points à contrôler » en comptait 315 qui n'étaient pas des faits douteux mais
    des informations que la source ne publie pas — personne ne peut vérifier la capacité
    d'accueil d'une sortie au lac, ni Franck ni le modèle. Une file pareille n'est pas un
    garde-fou, c'est l'inventaire des silences de la source, et elle noie le seul point qui
    comptait sous trois cents « tarifs non publiés » ;
  • le DÉSACCORD FLOU. Un texte qui contient cinq dates et pas la nôtre ne prouve rien :
    notre date vient peut-être de la page officielle, que ce texte ne contient pas. Compté,
    jamais listé.

Autrement dit : on ne liste que ce qui a un GESTE au bout (règle 6). Le compte des muets
et des indécis est affiché — sans lui, un « 0 contradiction » ne dirait pas s'il vient
d'une base saine ou d'une requête vide.

Déterministe, zéro appel LLM — donc utilisable pendant le plafond d'API.

  .venv/bin/python -m scripts.verifier_dates
  .venv/bin/python -m scripts.verifier_dates --en-ligne   # d'abord ce que le public voit
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.audit_annee_date import phrase_de_l_annee  # noqa: E402
from scripts.dates import _MONTHS, _MONTH_RE, _iso, _strip, _year  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def dates_du_texte(texte: str, ref: date) -> set[str]:
    """TOUTES les dates lisibles d'un texte, en ISO. Volontairement différent de
    `dates.parse_dates`, qui rend LA date (la première qui accroche un motif).

    Ici on veut l'inventaire complet, parce que la question n'est pas « quelle date ? »
    mais « combien y en a-t-il ? ». C'est le nombre qui décide si le texte est sans
    ambiguïté (une seule date → il parle d'elle) ou muet sur le sujet (plusieurs dates →
    il faudrait comprendre, et comprendre est justement ce qu'on ne sait pas faire).

    `ref` sert à l'année sous-entendue et vaut la date de COLLECTE de la fiche, pas
    aujourd'hui : c'est le fait connu auquel on accroche le reste."""
    t = _strip(texte or "")
    trouvees: set[str] = set()

    for y, m, d in re.findall(r"\b(\d{4})-(\d{2})-(\d{2})\b", t):
        v = _iso(int(y), int(m), int(d))
        if v:
            trouvees.add(v)

    for d1, mon, yr in re.findall(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\.?\s*(\d{{4}})?", t):
        mois = _MONTHS[mon]
        annee = int(yr) if yr else _year(int(d1), mois, ref)
        v = _iso(annee, mois, int(d1))
        if v:
            trouvees.add(v)

    for d1, mon, y in re.findall(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b", t):
        v = _iso(int(y), int(mon), int(d1))
        if v:
            trouvees.add(v)

    return trouvees


_BALISES = re.compile(r"<[^>]{1,200}>")

# Le jour de la semaine, en français et en italien. Lundi = 0, comme `date.weekday()`.
_JOURS = {
    "lundi": 0, "lunedi": 0, "mardi": 1, "martedi": 1, "mercredi": 2, "mercoledi": 2,
    "jeudi": 3, "giovedi": 3, "vendredi": 4, "venerdi": 4, "samedi": 5, "sabato": 5,
    "dimanche": 6, "domenica": 6,
}
_JOUR_RE = "|".join(_JOURS)
_NOM_DU_JOUR = {v: k for k, v in (("lundi", 0), ("mardi", 1), ("mercredi", 2),
                                  ("jeudi", 3), ("vendredi", 4), ("samedi", 5),
                                  ("dimanche", 6))}


def jours_nommes(texte: str) -> dict[tuple[int, int], int]:
    """{(mois, jour) : indice du jour de semaine annoncé}, lu dans le texte.

    LE SIGNAL LE PLUS SOUS-EXPLOITÉ DE TOUTE LA CHAÎNE, trouvé le 2026-08-11 au soir en
    lisant l'extrait de la fiche 1069 : « ti basterà venire a trovarci sabato 7 maggio
    dalle 16 ». Notre base annonçait le 7 mai 2027. Or le 7 mai ne tombe un SAMEDI ni en
    2025, ni en 2026, ni en 2027 — il le fait en 2022, et la page Paratissima porte la
    mention « 4 anni fa ». La fiche était en ligne, annonçant pour dans un an un événement
    vieux de quatre.

    Un texte français ou italien nomme presque toujours le jour de la semaine. C'est une
    donnée GRATUITE, écrite par un humain qui savait de quoi il parlait, et qui contraint
    l'année à une sur sept. Rien d'autre dans le texte ne fait ça.

    C'est encore la même forme que les cinq trouvailles de la journée : on ne peut pas
    EXTRAIRE une année d'un texte, mais on peut CONFIRMER celle qu'on a — ici en la
    confrontant à un fait que l'auteur a écrit sans y penser."""
    t = _strip(texte or "")
    trouves: dict[tuple[int, int], int] = {}
    for j, d, mon in re.findall(rf"\b({_JOUR_RE})\s+(\d{{1,2}})\s+({_MONTH_RE})", t):
        trouves[(_MONTHS[mon], int(d))] = _JOURS[j]
    return trouves


def _materiau(row: sqlite3.Row) -> str:
    """Le TEXTE écrit pour des humains — et rien d'autre.

    DEUX EXCLUSIONS, toutes deux apprises en production.

    `article_md` d'abord : c'est notre propre écriture, rédigée À PARTIR de la date qu'on
    veut vérifier. La confronter à elle ne prouverait qu'une chose, que la rédaction a bien
    recopié la base — le témoin qui se cite lui-même.

    `date_start` ensuite, et celle-là m'a coûté deux faux signalements le 2026-08-11 au
    soir. Cette colonne reçoit `entry.get("published")`, c'est-à-dire l'horodatage de
    PUBLICATION du flux RSS, jamais la date de l'événement. La fiche 923 (Charlie Winston)
    a donc été annoncée « contredite » parce que son unique date était
    « Wed, 24 Jun 2026 13:44:10 +0000 » — la date à laquelle la Maison des Arts du Léman a
    poussé son billet.

    Le dépôt le savait déjà : `dates.dates_from_page` écarte explicitement
    `article:published_time` avec le commentaire « n'EST PAS la date d'événement ». Je l'ai
    refait un étage plus haut, sur une autre colonne. **Une métadonnée n'est pas un texte
    écrit pour des humains, et tout ce script repose sur le fait qu'elle en soit un.**

    Les balises sont retirées : `description` contient parfois du HTML brut (la fiche 473
    portait « <time>20/05/2026</time> </span> »), et un extrait truffé de balises ne se lit
    pas — or c'est un humain qui doit trancher."""
    bouts = []
    for col in ("title", "description"):
        try:
            if row[col]:
                bouts.append(str(row[col]))
        except (IndexError, KeyError):
            pass
    try:
        if row["mail_corps"]:
            bouts.append(str(row["mail_corps"]))
    except (IndexError, KeyError):
        pass
    return _BALISES.sub(" ", "\n".join(bouts))


def verdict_jour(stockees: set[str], jours: dict[tuple[int, int], int]) -> str:
    """Le jour de semaine annoncé colle-t-il à notre date ? "" si rien à dire.

    On ne juge que les dates dont le texte nomme le jour POUR LE MÊME quantième et le
    même mois : sans ça on comparerait le samedi d'un autre événement au nôtre.

    En prime, on cherche l'année qui, elle, collerait — sur une fenêtre large. Quand elle
    est loin derrière, ce n'est plus une faute d'un an : c'est une annonce ancienne
    remontée telle quelle, et le geste n'est pas de corriger la date mais d'écarter la
    fiche."""
    for iso in sorted(stockees):
        d = date.fromisoformat(iso)
        annonce = jours.get((d.month, d.day))
        if annonce is None or annonce == d.weekday():
            continue
        candidates = [a for a in range(d.year - 6, d.year + 3)
                      if _iso(a, d.month, d.day)
                      and date(a, d.month, d.day).weekday() == annonce]
        detail = (f"la dernière année où le {d.day:02d}/{d.month:02d} tombe un "
                  f"{_NOM_DU_JOUR[annonce]} est {max(candidates)}"
                  if candidates else
                  f"aucune année proche ne place le {d.day:02d}/{d.month:02d} un "
                  f"{_NOM_DU_JOUR[annonce]}")
        return (f"le texte annonce un {_NOM_DU_JOUR[annonce]}, notre {iso} est un "
                f"{_NOM_DU_JOUR[d.weekday()]} — {detail}")
    return ""


def verdict(stockees: set[str], du_texte: set[str]) -> tuple[str, str, str]:
    """(verdict, motif, date_du_texte). Verdicts : 'confirme' | 'contredit' | 'annee' |
    'muet' | 'indecis'. La troisième valeur est la date du TEXTE qui a déclenché le
    signalement — c'est elle qu'on ira montrer dans sa phrase.

    L'ordre des tests compte. « confirmé » passe en premier : un texte qui contient NOTRE
    date ne la contredit pas, même s'il en contient dix autres (une page de saison cite ses
    voisines, un mail cite la date d'envoi)."""
    if not du_texte:
        return ("muet", "le texte source ne porte aucune date", "")
    if stockees & du_texte:
        return ("confirme", "la date figure telle quelle dans le texte source", "")

    # ② L'année : même jour, même mois, autre millésime. Reconnaissable sans rien
    #    comprendre — c'est tout l'intérêt.
    for s in sorted(stockees):
        for d in sorted(du_texte):
            if s[5:] == d[5:] and s[:4] != d[:4]:
                return ("annee", f"le texte dit {d}, la base dit {s} — même jour, "
                                 f"autre année", d)

    # ① Une seule date dans le texte, et ce n'est pas la nôtre. Aucune ambiguïté sur ce
    #    dont le texte parle : il n'a qu'un candidat.
    if len(du_texte) == 1:
        seule = next(iter(du_texte))
        return ("contredit", f"le texte ne dit qu'UNE date, {seule} ; la base dit "
                             f"{' / '.join(sorted(stockees))}", seule)

    return ("indecis", f"{len(du_texte)} dates dans le texte, aucune n'est la nôtre — "
                       f"notre date vient peut-être de la page officielle", "")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--en-ligne", action="store_true",
                    help="ne regarde que les fiches PUBLIÉES — un fait faux y coûte le "
                         "plus cher, puisqu'un visiteur le lit")
    ap.add_argument("--tout", action="store_true",
                    help="affiche aussi les indécis et les muets (par défaut on ne liste "
                         "que ce sur quoi il y a un geste à faire)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cols = {r[1] for r in conn.execute("PRAGMA table_info(events_raw)")}
    corps = "mail_corps" if "mail_corps" in cols else "'' AS mail_corps"
    auj = date.today().isoformat()

    # RÈGLE 5 : seulement ce qui est encore devant nous. Une date fausse sur un événement
    # terminé n'envoie plus personne devant une porte close. C'est `date_event_end` qui
    # décide — une exposition de mai à septembre compte tout l'été.
    where = ("COALESCE(duplicate_of,0)=0 "
             "AND COALESCE(statut,'') NOT IN ('merged','rejected') "
             "AND COALESCE(date_event_start,'') <> '' "
             "AND COALESCE(recurring,0)=0 "
             "AND COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?")
    params: list = [auj]
    if args.en_ligne:
        where += " AND COALESCE(wp_post_id_as,0) <> 0"

    lignes = conn.execute(
        f"SELECT id, title, description, date_start, {corps}, date_event_start, "
        "       date_event_end, date_source, scrape_date, wp_post_id_as, source_name "
        f"FROM events_raw WHERE {where} ORDER BY COALESCE(wp_post_id_as,0) DESC, id DESC",
        params).fetchall()

    compte = {"confirme": 0, "contredit": 0, "annee": 0, "jour": 0,
              "muet": 0, "indecis": 0}
    a_voir: list[tuple] = []
    for r in lignes:
        try:
            ref = date.fromisoformat((r["scrape_date"] or auj)[:10])
        except ValueError:
            ref = date.today()
        stockees = {d for d in ((r["date_event_start"] or "").strip()[:10],
                                (r["date_event_end"] or "").strip()[:10]) if len(d) == 10}
        if not stockees:
            continue
        materiau = _materiau(r)
        v, motif, cible = verdict(stockees, dates_du_texte(materiau, ref))
        # LE JOUR DE SEMAINE PRIME SUR TOUT LE RESTE. Une date « confirmée » (le texte
        # porte bien notre quantième) peut être fausse d'un an sans que rien ne le montre :
        # c'est le cas 1069, où « 7 maggio » figurait des deux côtés. Seul le samedi
        # annoncé séparait 2022 de 2027.
        jour = verdict_jour(stockees, jours_nommes(materiau))
        if jour:
            v, motif, cible = "jour", jour, ""
        compte[v] += 1
        if v in ("contredit", "annee", "jour") or (args.tout and v == "indecis"):
            # LA PHRASE, PAS SEULEMENT LA DATE. Sans elle, le lecteur arbitre à l'aveugle
            # entre deux nombres et tranchera dans le sens de celui qui affiche — c'est
            # l'erreur 14 du 2026-08-11, où j'ai déclaré fausses deux dates qui étaient
            # justes. Ici l'enjeu est plus grand encore : ces fiches sont PUBLIÉES, donc
            # une correction à tort réécrit une page que des gens lisent.
            phrase, exacte = phrase_de_l_annee(_materiau(r), cible)
            a_voir.append((r, v, motif, phrase, exacte))

    total = sum(compte.values())
    print("═══ La source dit-elle la même date que nous ? ═══")
    print(f"Périmètre : {total} fiche(s) datées, encore devant nous"
          + (", PUBLIÉES" if args.en_ligne else "") + " (règle 5).\n")
    print(f"  {compte['confirme']:>5}  confirmées — la date est écrite dans le texte source")
    print(f"  {compte['contredit']:>5}  CONTREDITES — le texte ne dit qu'une date, "
          f"et ce n'est pas la nôtre")
    print(f"  {compte['annee']:>5}  ANNÉE — même jour, autre millésime")
    print(f"  {compte['jour']:>5}  JOUR DE SEMAINE — le texte annonce un autre jour que "
          f"le nôtre ; l'année ne colle pas")
    print(f"  {compte['indecis']:>5}  indécises — plusieurs dates, aucune n'est la nôtre "
          f"(notre date vient peut-être de la page)")
    print(f"  {compte['muet']:>5}  muettes — le texte source ne porte aucune date. "
          f"Ce n'est PAS un doute : on ne peut pas vérifier un silence\n")

    if not a_voir:
        print("Rien à corriger : aucune contradiction franche dans ce périmètre.")
        print("Les indécises et les muettes ne sont pas des tâches — il n'y a pas de "
              "geste au bout, et une file sans geste cache les vraies (règle 6).")
        conn.close()
        return 0

    print(f"═══ {len(a_voir)} fiche(s) à regarder, la plus coûteuse d'abord ═══\n")
    for r, v, motif, phrase, exacte in a_voir:
        etat = f"EN LIGNE #{r['wp_post_id_as']}" if r["wp_post_id_as"] else "hors ligne"
        marque = {"annee": "⚠ ANNÉE", "contredit": "✗ CONTREDIT",
                  "jour": "✗ JOUR DE SEMAINE"}.get(v, "· indécis")
        print(f"  [{r['id']:>5}] {marque}   {etat}   "
              f"(date_source={r['date_source'] or '?'})")
        print(f"          {(r['title'] or '')[:72]}")
        print(f"          {motif}")
        # ON N'AFFICHE QUE LES EXTRAITS PROBANTS. Un extrait trouvé sur la seule année
        # n'est pas une citation, c'est une coïncidence — et il a l'autorité d'une preuve.
        if phrase and exacte:
            print(f"          le texte dit : « {phrase} »")
        print(f"          source : {r['source_name'] or '?'}\n")

    print("SIGNALEMENT, PAS UN VERDICT : notre date peut être la bonne — elle vient "
          "parfois de la page officielle, que ce texte ne contient pas. La correction se "
          "fait page en main, par `completer_verifie --depuis` et sa clause « remplace ».")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
