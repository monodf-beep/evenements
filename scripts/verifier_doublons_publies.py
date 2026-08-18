#!/usr/bin/env python3
"""CONTRADICTEUR — deux fiches EN LIGNE qui racontent le même événement.

D'OÙ ÇA VIENT. Le 2026-08-13, la liste « bande maigre » de `audit_substance_published`
montrait sept titres présents DEUX fois, en italien les deux fois :

    [4421] WP#6380  Tour de l'Avenir 2026 - Strambino Lago Serrù
    [4584] WP#7113  Tour de l'Avenir 2026 - Strambino - Lago Serrù

Personne ne les cherchait. `scripts/dedupe.py` tourne à 8h sur `statut='pending'` : il
dédoublonne ce qui ARRIVE, jamais ce qui est DÉJÀ publié. Son option `--rescan` sait le
faire, mais elle FUSIONNE — c'est-à-dire qu'elle décide toute seule laquelle des deux
pages disparaît. Or CLAUDE.md range la fusion parmi les arbitrages humains, à côté du
défusionnage et du re-classement d'une fiche rejetée par Franck.

Donc ce script ne fusionne rien et n'a pas de `--apply` : il DÉSIGNE, Franck tranche.

CE QU'IL NE FAUT SURTOUT PAS APPARIER. Une traduction française peut porter un titre
italien, quand le nom de l'événement EST italien — « Campionato Italiano Canoa Slalom »
reste tel quel en français. Ces paires-là sont normales : ce sont deux pages liées par
Polylang, une par langue, et les fusionner détruirait le site bilingue. C'est le piège
de la fiche 3588 (« La Rencontre Valdôtaine »), où un portillon a pris un NOM PROPRE
pour la preuve d'une traduction ratée. On écarte donc toute paire dont les deux fiches
sont liées par `translation_of`, dans un sens ou dans l'autre, ou qui traduisent le même
original.

PÉRIMÈTRE — écrit ici et RÉPÉTÉ à côté de chaque nombre (règle 6) : fiches publiées
(`wp_post_id_as` renseigné), non déjà marquées doublon, et ENCORE DEVANT NOUS. Deux
pages jumelles sur un événement de juin ne se réparent pas : plus personne ne les
cherche, et les départager coûterait du temps pour rien (règle 5).

La définition de « même événement » n'est pas réinventée ici : on appelle `_groups` de
`scripts/dedupe.py`, avec ses gardes années et dates. Deux définitions concurrentes de
la ressemblance finiraient par se contredire, et c'est la plus bavarde qu'on croirait.

⚠️ ET LA FAUTE QUE CE SCRIPT A COMMISE LE JOUR DE SA NAISSANCE. Livré le matin du
2026-08-13, il annonçait « 4 doublons EN LIGNE » sur la seule foi du `wp_post_id_as` de
la base. L'après-midi, `reconcile_hors_ligne` — qui INTERROGE WordPress — a montré que
cinq des huit pages concernées étaient déjà à la corbeille : sur le groupe Chagall, une
seule page était encore publique, et le retrait que ce script proposait la visait ELLE.
Un seul des quatre groupes était réel.

C'est la RÈGLE 1 de CLAUDE.md, mot pour mot — « un identifiant en base ne prouve RIEN sur
le site, il survit à une mise à la corbeille » — réintroduite dans un fichier neuf qui la
citait déjà dans ses propres commentaires. D'où `--en-ligne`, et le refus de proposer le
moindre retrait sans lui : un défaut argumenté sur une donnée qui ne prouve rien est pire
qu'un blanc à remplir, parce que le blanc, au moins, ne se fait pas obéir.

Usage (VPS) :
    .venv/bin/python -m scripts.verifier_doublons_publies             # candidats
    .venv/bin/python -m scripts.verifier_doublons_publies --en-ligne  # vérifiés
    .venv/bin/python -m scripts.verifier_doublons_publies --slack
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.dedupe import _groups  # noqa: E402  — MÊME définition que le dédoublonnage
from scripts.audit_substance_published import devant_nous  # noqa: E402
# LA RÈGLE 1, QUE CE SCRIPT A VIOLÉE LE JOUR MÊME DE SA NAISSANCE (2026-08-13).
# `_etat` interroge WordPress post par post — la SEULE façon de savoir si une page est
# publique, à la corbeille ou supprimée. On la réutilise plutôt que d'en écrire une
# variante : c'est déjà la même fonction dans `reconcile_wp_deleted` et
# `reconcile_hors_ligne`, et une quatrième copie finirait par diverger.
from scripts.reconcile_hors_ligne import _etat  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _connect_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def paire_de_traduction(a: dict, b: dict) -> bool:
    """Ces deux fiches sont-elles les deux langues d'un même événement ?

    Trois formes de la même liaison : a traduit b, b traduit a, ou toutes deux
    traduisent le même original (cas des fiches jumelles créées de chaque côté).
    Une paire pareille est NORMALE et ne doit jamais remonter — cf. l'en-tête.
    """
    ta, tb = int(a.get("translation_of") or 0), int(b.get("translation_of") or 0)
    return ta == b["id"] or tb == a["id"] or (ta and ta == tb)


def _lien(ev: dict) -> str:
    """Ce qu'on donne à un humain pour ALLER VOIR. Le permalien s'il est connu ; sinon on
    le dit, parce que `/?p=<id>` répond 404 pour tout `tribe_events`, vivant ou mort
    (règle 1) — proposer cette adresse ferait croire à une page supprimée."""
    return (ev.get("wp_permalink_as") or "").strip() or "(permalien inconnu en base)"


def _periode(ev: dict) -> str:
    d, f = (ev.get("date_event_start") or "")[:10], (ev.get("date_event_end") or "")[:10]
    if ev.get("recurring"):
        return "récurrent"
    if d and f and f != d:
        return f"{d} → {f}"
    return d or f or "sans date"


def analyser(rows: list[dict], today: str) -> tuple[list[list[dict]], dict]:
    """Renvoie les groupes suspects ET le compte de ce qui s'est présenté.

    Le second élément existe pour une raison précise : un `0` doit pouvoir se lire.
    « Aucun doublon » et « aucune fiche examinée » se ressemblent EXACTEMENT dans une
    sortie qui ne compte que le résultat — trois fois le 2026-08-11 un zéro a été pris
    pour une source pauvre alors qu'il venait de la requête.
    """
    vivantes = [ev for ev in rows if devant_nous(ev, today)]
    groupes = [g for g in _groups(vivantes) if len(g) > 1]
    suspects, ecartes = [], 0
    for g in groupes:
        # Un groupe entièrement composé de traductions les unes des autres n'est pas un
        # doublon. On ne retire pas la fiche traduite du groupe : on écarte la PAIRE, car
        # un trio FR/IT + vrai doublon doit continuer de remonter.
        reste = [a for i, a in enumerate(g)
                 if not all(paire_de_traduction(a, b) for j, b in enumerate(g) if j != i)]
        if len(reste) > 1:
            suspects.append(reste)
        else:
            ecartes += 1
    return suspects, {"publiees": len(rows), "vivantes": len(vivantes),
                      "groupes": len(groupes), "traductions": ecartes}


def _article(ev: dict) -> str:
    """Le corps de l'article RÉDIGÉ, ou '' — sans jamais lever sur un JSON abîmé."""
    try:
        return (((json.loads(ev.get("enrich_data") or "") or {}).get("article")
                 or {}).get("corps") or "").strip()
    except (ValueError, TypeError):
        return ""


def _permalien_propre(ev: dict) -> bool:
    """Un permalien de la forme `/evenement/mon-titre/` plutôt que `?post_type=…&p=1984`.

    Ce n'est pas cosmétique : la seconde forme veut dire qu'on n'a jamais enregistré le
    permalien réel du post. Entre deux jumelles, celle qui a un vrai chemin est celle que
    Google connaît et que les partages pointent."""
    return "/evenement" in (ev.get("wp_permalink_as") or "") or \
           "/eventi" in (ev.get("wp_permalink_as") or "")


def famille(ev: dict, par_id: dict[int, dict]) -> list[dict]:
    """La fiche ET son jumeau dans l'autre langue — la plus petite unité qu'on puisse
    retirer sans laisser d'orphelin.

    POURQUOI CE N'EST PAS UN DÉTAIL. Le groupe Chagall du 2026-08-13 comptait quatre
    pages : 3021 (it) ↔ 4194 (fr) d'un côté, 3026 (fr) ↔ 4195 (it) de l'autre. Deux
    PAIRES bilingues correctes, et c'est l'exposition entière qui est en double. Retirer
    « la fiche 4194 » aurait laissé 3021 seule en italien, liée par Polylang à un post
    corbeillé : un site à moitié réparé, plus difficile à diagnostiquer qu'avant.
    On raisonne donc par famille, jamais par fiche."""
    fam = {ev["id"]: ev}
    orig = int(ev.get("translation_of") or 0)
    if orig and orig in par_id:
        fam[orig] = par_id[orig]
    for autre in par_id.values():
        if int(autre.get("translation_of") or 0) in fam:
            fam[autre["id"]] = autre
    return [fam[k] for k in sorted(fam)]


def _valeur(fam: list[dict]) -> tuple:
    """De quoi CLASSER deux familles, du plus décisif au moins décisif.

    Aucun de ces critères n'est un jugement éditorial : ils décrivent ce qui a été fait
    sur chaque fiche, pas ce qu'elle vaut. Le choix reste à Franck — mais un défaut
    ARGUMENTÉ vaut mieux qu'un blanc à remplir, parce qu'un blanc ne se remplit jamais.
    """
    return (
        sum(1 for e in fam if _article(e)),        # ① un article écrit chez nous
        sum(len(_article(e)) for e in fam),        # ② et le plus fourni
        sum(1 for e in fam if _permalien_propre(e)),  # ③ l'adresse que Google connaît
        -min(e["id"] for e in fam),                # ④ à égalité, la plus ancienne
    )


def recommandation(groupe: list[dict], par_id: dict[int, dict]) -> tuple[list, list, str]:
    """(famille à garder, fiches à retirer, phrase qui dit pourquoi).

    Rend ([], [], "") quand les deux familles se valent : dans ce cas, proposer un défaut
    serait faire passer un tirage au sort pour un avis.
    """
    familles, vues = [], set()
    for ev in groupe:
        if ev["id"] in vues:
            continue
        fam = famille(ev, par_id)
        vues |= {e["id"] for e in fam}
        familles.append(fam)
    if len(familles) < 2:
        return [], [], ""
    familles.sort(key=_valeur, reverse=True)
    garde, reste = familles[0], [e for f in familles[1:] for e in f]
    if _valeur(garde) == _valeur(familles[1]):
        return [], [], ("les deux se valent sur tous les critères mesurables — "
                        "aucun défaut proposé, c'est à vous de regarder")
    n_art = sum(1 for e in garde if _article(e))
    n_art_autre = sum(1 for e in familles[1] if _article(e))
    if n_art > n_art_autre:
        motif = (f"gardée parce qu'elle porte {n_art} article(s) rédigé(s) chez nous "
                 f"contre {n_art_autre}")
    elif sum(len(_article(e)) for e in garde) > sum(len(_article(e)) for e in familles[1]):
        motif = "gardée parce que son article est le plus fourni"
    elif sum(1 for e in garde if _permalien_propre(e)) > \
            sum(1 for e in familles[1] if _permalien_propre(e)):
        motif = "gardée parce que son adresse est un vrai permalien, pas un `?p=`"
    else:
        motif = "gardée parce que c'est la plus ancienne — elle porte l'historique"

    # ══ QUAND LE DÉFAUT EST MINCE, LE DIRE ════════════════════════════════════════════
    # Ajouté le 2026-08-13 en lisant la sortie réelle sur le groupe Chagall. Le critère
    # qui a départagé était une différence de longueur d'article — et la famille proposée
    # au RETRAIT portait le seul vrai permalien du lot,
    # `/evenement/marc-chagall-entre-poesie-et-spiritualite/`, c'est-à-dire l'adresse que
    # Google connaît et que les partages pointent. La retirer est peut-être le bon choix,
    # mais ce n'est plus un choix évident, et un « ← retirer » sans réserve le ferait
    # passer pour tel.
    #
    # C'est la forme générale du défaut de la journée : une recommandation qui n'affiche
    # pas ce qui la contredit se lit comme une certitude. On ne change donc PAS le
    # classement — inverser l'ordre des critères déplacerait le problème sans le résoudre
    # — on affiche la contradiction à côté.
    perd_permalien = (sum(1 for e in familles[1] if _permalien_propre(e))
                      > sum(1 for e in garde if _permalien_propre(e)))
    if perd_permalien and "permalien" not in motif:
        adresses = [(e.get("wp_permalink_as") or "") for e in familles[1]
                    if _permalien_propre(e)]
        motif += ("\n       ⚠ MAIS la famille à retirer porte l'adresse indexée "
                  f"({adresses[0][:70]}…),\n         et celle qu'on garde n'en a pas. "
                  "À regarder avant d'appliquer : ce critère-ci\n         n'a pas départagé, "
                  "il a été contredit.")
    return garde, reste, motif


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Deux fiches EN LIGNE sur le même événement. Lecture seule.")
    parser.add_argument("--slack", action="store_true", help="Poster le bilan sur Slack.")
    # ══ RÈGLE 1 — CE SCRIPT L'A VIOLÉE LE JOUR DE SA NAISSANCE ════════════════════════
    #
    # Livré le 2026-08-13 au matin, il annonçait « 4 doublons EN LIGNE » en lisant le seul
    # `wp_post_id_as` de la base. L'après-midi, le dry-run de `reconcile_hors_ligne` — qui
    # interroge WordPress, lui — a montré que sur les huit pages concernées, CINQ étaient
    # déjà à la corbeille :
    #
    #   · Chagall : 3021, 4194 et 4195 retirés ; SEUL 3026 (WP#2020) est public.
    #     Il n'y a donc aucun doublon Chagall sur le site — et le défaut que je proposais
    #     revenait à corbeiller la seule page vivante ;
    #   · EVO : 2466 (WP#1984) était déjà à la corbeille.
    #
    # Un seul des quatre groupes était réel. C'est la première règle de CLAUDE.md, mot
    # pour mot — « un identifiant en base ne prouve RIEN sur le site, il survit à une mise
    # à la corbeille » — et je l'ai réintroduite dans un script neuf, écrit le jour même
    # où je citais cette règle dans ses propres commentaires.
    #
    # D'où le choix ici : SANS `--en-ligne`, le script montre les groupes mais ne propose
    # AUCUN retrait. Un défaut argumenté sur une donnée qui ne prouve rien est pire qu'un
    # blanc à remplir — le blanc, au moins, ne se fait pas obéir.
    parser.add_argument("--en-ligne", action="store_true",
                        help="Interroger WordPress post par post (REST) avant de "
                             "conclure. OBLIGATOIRE pour obtenir une commande de retrait.")
    args = parser.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n"
              f"(data/ est hors dépôt Git — lancer ce script sur le VPS.)")
        return 1

    conn = _connect_ro(DB_PATH)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL").fetchall()]
    conn.close()

    suspects, compte = analyser(rows, date.today().isoformat())

    # LA SONDE, quand on la demande. Un appel REST par post concerné, jamais une
    # collection : The Events Calendar exclut les événements PASSÉS de ses listes (règle
    # 2), donc une liste ne prouverait aucune absence. On ne sonde que les fiches des
    # groupes suspects — pas les 357 publiées : le but est de trancher, pas d'inventorier.
    etats: dict[int, str] = {}
    if args.en_ligne:
        import time
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
        vises = sorted({ev["id"] for g in suspects for ev in g}
                       | {e["id"] for g in suspects for ev in g
                          for e in famille(ev, {r["id"]: r for r in rows})})
        print(f"Interrogation de WordPress pour {len(vises)} post(s)…")
        par_id_tmp = {r["id"]: r for r in rows}
        for n, eid in enumerate(vises):
            etats[eid] = _etat(wp_url, par_id_tmp[eid]["wp_post_id_as"])
            if n + 1 < len(vises):
                time.sleep(0.4)
        # Un groupe dont UNE SEULE page est publique n'est pas un doublon EN LIGNE : le
        # site montre une page, pas deux. C'est le cas Chagall du 2026-08-13 — quatre
        # fiches en base, une seule visible.
        avant = len(suspects)
        suspects = [g for g in suspects
                    if sum(1 for ev in g if etats.get(ev["id"]) == "public") > 1]
        compte["retires_du_site"] = avant - len(suspects)
        # UN ZÉRO NE DIT PAS S'IL VIENT D'UN ÉCHEC OU D'UNE ABSENCE DE CAS.
        #
        # `_etat` rend 'indetermine' quand la requête échoue, et c'est le bon choix : un
        # aléa réseau n'autorise aucune action. Mais le filtre ci-dessus ne garde que les
        # groupes dont DEUX pages sont 'public' — donc si le site est injoignable, TOUS
        # les sondages rendent 'indetermine', tous les groupes disparaissent, et le
        # rapport annonce « SUSPECTS (VÉRIFIÉS) : 0 ».
        #
        # Un feu vert impeccable, produit par une panne de réseau, et présenté comme
        # VÉRIFIÉ alors que rien ne l'a été. Le 2026-08-18, l'hébergement du site a cessé
        # de répondre à l'adresse du VPS pendant tout l'après-midi : ce cron de 9h50 aurait
        # rendu ce zéro-là le lendemain matin.
        #
        # On compte donc les sondages sans réponse, et le rapport le dira.
        compte["indetermines"] = sum(1 for v in etats.values() if v == "indetermine")
        compte["sondages"] = len(vises)

    print("=" * 78)
    print("DOUBLONS PARMI LES FICHES PUBLIÉES — lecture seule, rien n'a été modifié")
    print("=" * 78)
    print(f"Base                     : {DB_PATH}")
    print(f"Publiées (toutes dates)  : {compte['publiees']}")
    print(f"…dont encore devant nous : {compte['vivantes']}  ← LE PÉRIMÈTRE EXAMINÉ")
    print(f"Groupes de titres proches: {compte['groupes']}")
    print(f"…écartés (paires FR/IT)  : {compte['traductions']}  — normales, à LIER, "
          f"jamais à fusionner")
    if args.en_ligne:
        print(f"…écartés APRÈS SONDAGE   : {compte['retires_du_site']}  — une seule de "
              f"leurs pages est encore publique")
        ind, tot = compte.get("indetermines", 0), compte.get("sondages", 0)
        if ind and ind == tot:
            # Rien n'a été vérifié : le dire, et ne surtout pas rendre un zéro rassurant.
            print(f"SONDAGE IMPOSSIBLE       : {ind}/{tot} interrogations sans réponse")
            print()
            print("⚠️  AUCUNE VÉRIFICATION N'A EU LIEU. WordPress n'a répondu à aucune")
            print("    interrogation — site injoignable depuis ce serveur. Le nombre de")
            print("    suspects ci-dessus ne vaut RIEN : il est bas parce que le sondage a")
            print("    échoué, pas parce que le site est sain. Relancer quand le site")
            print("    répond ; en attendant, ce rapport n'autorise aucun geste.")
            print()
        elif ind:
            print(f"…sondages SANS RÉPONSE   : {ind}/{tot}  ⚠ ces pages n'ont pas été "
                  f"vérifiées — un groupe réel a pu être écarté à tort")
        print(f"SUSPECTS (VÉRIFIÉS)      : {len(suspects)}"
              + ("  ⚠ CHIFFRE NON FIABLE, voir ci-dessus" if ind == tot and tot else ""))
    else:
        print(f"SUSPECTS (NON VÉRIFIÉS)  : {len(suspects)}  ⚠ d'après la BASE seule")
    print()
    if not args.en_ligne:
        # RÈGLE 1, ET LE PIÈGE EST DANS LE MOT « publiée ». Un `wp_post_id_as` renseigné
        # survit à une mise à la corbeille : la base dit « publiée » d'une page que
        # personne ne voit. Le 2026-08-13, cinq des huit pages listées ici étaient déjà
        # retirées, et le retrait que je proposais visait la seule encore vivante.
        print("⚠️  SANS `--en-ligne`, CES GROUPES NE SONT QUE DES CANDIDATS. Un identifiant")
        print("    WordPress en base survit à une mise à la corbeille : il ne prouve pas")
        print("    qu'une page est visible. Le 13/08, cinq des huit pages listées ici")
        print("    étaient déjà retirées — et un seul des quatre groupes était réel.")
        print("    Aucune commande de retrait n'est proposée tant que WordPress n'a pas")
        print("    été interrogé post par post :")
        print("      .venv/bin/python -m scripts.verifier_doublons_publies --en-ligne")
        print()

    if not suspects:
        print("Aucun groupe suspect. Ce zéro se lit : "
              f"{compte['vivantes']} fiches examinées, {compte['groupes']} groupes formés,")
        print(f"{compte['traductions']} écartés comme paires de traduction. Un zéro sur "
              f"zéro fiche examinée aurait la même tête ;")
        print("c'est pour ça que les deux nombres sont là.")
        return 0

    par_id = {ev["id"]: ev for ev in rows}
    a_retirer: list[int] = []
    for n, g in enumerate(suspects, 1):
        print(f"--- {n}. {len(g)} fiches en ligne sur le même événement ---")
        garde, reste, motif = recommandation(g, par_id)
        ids_garde = {e["id"] for e in garde}
        ids_reste = {e["id"] for e in reste}
        for ev in sorted(g, key=lambda e: e["id"]):
            marque = ("  ← GARDER" if ev["id"] in ids_garde else
                      "  ← retirer" if ev["id"] in ids_reste else "")
            if not args.en_ligne:
                marque = ""          # rien à recommander sur une donnée qui ne prouve rien
            elif etats.get(ev["id"]) and etats[ev["id"]] != "public":
                marque = f"  · {etats[ev['id']]} sur le site — rien à faire"
            print(f"  [{ev['id']:>5}] WP#{ev['wp_post_id_as']:<6} {_periode(ev):<24} "
                  f"{(ev.get('title') or '')[:44]}{marque}")
            print(f"          {_lien(ev)}")
        if garde and args.en_ligne:
            print(f"     → défaut proposé : {motif}.")
            # LES JUMEAUX SUIVENT LEUR ORIGINAL. Retirer une fiche sans sa traduction
            # laisserait l'autre langue seule, liée par Polylang à un post corbeillé —
            # un site à moitié réparé, plus dur à diagnostiquer qu'avant. Le groupe
            # Chagall du 2026-08-13 comptait DEUX paires bilingues correctes pour une
            # seule exposition : c'est la paire entière qui part.
            caches = [e for e in reste if e not in g]
            if caches:
                print(f"       (dont {len(caches)} jumeau(x) dans l'autre langue, "
                      f"absent(s) du groupe ci-dessus : "
                      f"{', '.join(str(e['id']) for e in caches)} — les laisser en ligne "
                      f"ferait un orphelin)")
            a_retirer.extend(sorted(ids_reste))
        elif args.en_ligne:
            print(f"     → {motif or 'aucun défaut proposé'}.")
        print()

    # LE GESTE AU BOUT DE LA LIGNE (règle 6). Une file sans geste n'est pas une file :
    # sur les 454 « points à contrôler » du 2026-08-11, trois cents n'avaient rien qu'un
    # humain puisse faire, et le seul qui comptait était noyé dessous.
    if not args.en_ligne:
        print("Relancer avec `--en-ligne` pour savoir lesquels de ces groupes existent")
        print("vraiment sur le site, et obtenir une commande de retrait.")
        return 0

    print("CE QU'IL Y A À FAIRE. Le choix reste ÉDITORIAL — mais un défaut argumenté vaut")
    print("mieux qu'un blanc à remplir, parce qu'un blanc ne se remplit jamais. Les ← ci-")
    print("dessus disent ce que je retirerais, et sur quel critère mesurable.")
    print()
    print("  • ouvrir les pages marquées « retirer » ; si ce sont bien des doublons, une")
    print("    seule commande les corbeille toutes (RÉVERSIBLE, dry-run sans --apply) :")
    if a_retirer:
        ids = " ".join(str(i) for i in sorted(set(a_retirer)))
        # `--statut rejected` N'EST PAS UN ORNEMENT. `trash_by_ids` REFUSE de corbeiller
        # une fiche `published_sub` sans lui, et il a raison : corbeiller sans changer le
        # statut laisse la fiche « retenue, sans post WP », c'est-à-dire dans le profil
        # exact que `publish_batch_as` republie le lendemain matin. On aurait retiré la
        # page et elle serait revenue seule, sur une adresse neuve.
        # Écrit ici le 2026-08-13 après avoir dicté à Franck la commande AMPUTÉE, que le
        # garde-fou a heureusement rejetée. Une commande incomplète dans un rapport est
        # une commande qu'on retapera de travers : elle se donne entière ou pas du tout.
        opts = '--statut rejected --motif "doublon d\'une fiche déjà en ligne"'
        print(f"      .venv/bin/python -m scripts.trash_by_ids {ids} {opts}")
        print(f"      puis, une fois la sortie lue : … --apply")
        print(f"      (`--statut rejected` est OBLIGATOIRE : sans lui, la fiche reste")
        print(f"       « retenue sans post », et le lot de demain matin la republie.)")
    else:
        print("      (aucun défaut proposé — les groupes se valent, il faut regarder)")
    print("  • si ce sont DEUX ÉDITIONS différentes (2025 et 2026, ou deux dates), il n'y")
    print("    a rien à faire : les garder toutes les deux et me le dire, pour que la")
    print("    garde années/dates de dedupe soit corrigée plutôt que contournée.")

    _slack(args, suspects, compte, a_retirer)
    return 0


def _slack(args, suspects, compte, a_retirer) -> None:
    """Le message Slack — appelé aussi quand il n'y a RIEN, et c'est voulu.

    ⚠️ CETTE FONCTION APPELAIT `slack.post`, QUI N'EXISTE PAS. Le point d'entrée
    d'`utils/slack.py` s'appelle `notify` ; `post` n'a jamais existé. Écrit le
    2026-08-13 au matin, jamais exécuté de la journée parce que `--slack` n'a servi à
    personne — jusqu'à ce que je place ce script dans le crontab le soir même. Il aurait
    planté tous les matins à 9h50, et la seule trace en aurait été une ligne dans
    logs/, que personne ne lit.

    C'est la forme la plus banale du défaut de la journée : un chemin de code écrit,
    relu, commité, et JAMAIS PARCOURU. La fixture le parcourt maintenant.

    Se tait quand il n'y a rien : un message quotidien « aucun doublon » cesse d'être lu
    au bout d'une semaine, et c'est le jour où il dira quelque chose qu'on le ratera.
    """
    if not args.slack or not suspects:
        return
    from utils import slack
    lignes = [f"• {len(g)} pages : " + ", ".join(f"WP#{e['wp_post_id_as']}" for e in g)
              for g in suspects[:10]]
    corps = (f"🔴 *{len(suspects)} doublon(s) EN LIGNE, vérifié(s) sur WordPress* "
             f"(sur {compte['vivantes']} fiches publiées encore devant nous)\n"
             + "\n".join(lignes))
    if a_retirer:
        ids = " ".join(str(i) for i in sorted(set(a_retirer)))
        corps += (f"\n`.venv/bin/python -m scripts.trash_by_ids {ids} "
                  f"--statut rejected --motif \"doublon\"`")
    slack.notify(corps)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
