#!/usr/bin/env python3
"""LE LIEN QUI NE MÈNE PLUS NULLE PART — refermer les fiches dont le post n'est pas public.

CE QU'IL FERME, ET POURQUOI PERSONNE NE LE FERMAIT. Relevé sur la production le
2026-08-04 : **85 fiches portent un `wp_post_id_as` dont le post n'est PAS public, dont 28
encore devant nous** (à venir, en cours, ou récurrentes). Réparties ainsi :

  • 16 en `published_sub` — la base les croit en ligne, le site dit non : retrait SUBI ?
  • 10 en `evaluated` avec un identifiant WordPress alors qu'aucune publication n'a jamais
    été enregistrée : ça ressemble à un lien PÉRIMÉ plus qu'à un retrait ;
  • 1 en `published_cs` (« ESTATE REALE 2026 », en cours jusqu'au 31/10) ;
  • 1 en `rejected`.
Et parmi elles des doublons manifestes — « Jazz Art » deux fois, « Marc Chagall » trois
fois — qui sont, eux, très probablement des retraits VOULUS.

Trois scripts voient ce cas et aucun ne le referme, chacun pour une bonne raison :

  • `reconcile_wp_deleted` GARDE délibérément le lien d'un post corbeillé (il est
    restaurable, couper le lien détruirait de l'information) et se contente de poser
    `wp_deleted_at`, le constat ;
  • `refresh_deplacement` REFUSE d'y pousser — republier un post corbeillé le ferait
    remonter d'entre les morts — et l'écrit dans son bilan, sans pouvoir agir ;
  • `site_audit` imprime « vider wp_post_id_as pour qu'il reparte au prochain lot »…
    et rien, nulle part, n'applique cette phrase.

C'est le motif de `docs/ETATS_TERMINAUX.md` sous sa forme la plus coûteuse : **le
diagnostic sans issue**. Le problème est vu, décrit, renvoyé — et on relit le même
paragraphe chaque semaine sans jamais pouvoir le refermer. Un renvoi qui n'aboutit pas
coûte plus cher qu'une absence de renvoi : il donne l'impression que la question est
traitée.

CINQ FAMILLES, ET UNE SEULE SE TRANCHE TOUTE SEULE
--------------------------------------------------
  ① LIEN MORT — post `inexistant`. Il n'y a plus rien au bout : aucun jugement à rendre.
    On vide `wp_post_id_as`/`wp_permalink_as`. **Appliqué par `--apply` seul.**
    (Même geste que `reconcile_wp_deleted` sur cette famille — volontairement identique,
    et idempotent : les deux scripts peuvent tourner dans n'importe quel ordre.)

  ② LIEN PÉRIMÉ — statut `evaluated` et post non public. La fiche n'a JAMAIS été
    confirmée publiée : aucune ligne de la base ne dit qu'elle l'a été. L'identifiant
    ressemble donc à un reliquat (relink approximatif, collision, ancienne poussée) plutôt
    qu'à la trace d'un retrait. Mais « ressemble » n'est pas « prouve ». **`--perimes`.**

  ③ RETRAIT PROBABLEMENT VOULU — post à la corbeille, et une fiche SŒUR porte un autre
    post encore public (voir `_soeurs`). Quelqu'un a vu deux fois la même chose sur le
    site et en a retiré une. On consigne la décision en base : `statut='rejected'`, on
    GARDE l'identifiant (le post est restaurable en un clic). **`--voulus`.**

  ④ RETRAIT PROBABLEMENT SUBI — post à la corbeille, aucune sœur publique, événement
    encore devant nous. On vide le lien : la fiche repart au lot du lendemain et se
    republie d'elle-même sur un post neuf. **`--subis`.**
    ②/④ ne vident QUE ce qui reviendra : une fiche sans date (récurrente, ou en attente de
    `dates.py`) verrait son lien coupé sans que `publish_batch_as` la reprenne jamais. Le
    script REFUSE et le dit — le post corbeillé, lui, reste restaurable.

  ⑤ DÉJÀ COHÉRENTE — statut `rejected` et post retiré : la base et le site disent la même
    chose. C'est l'état d'ARRIVÉE que ③ fabrique, pas un problème. **Aucun geste** : vider
    le lien détruirait le chemin vers un post restaurable sans rien gagner, puisqu'une
    fiche rejetée ne repart pas de toute façon. C'est le cas de la seule fiche `rejected`
    des 28.

CE QU'IL REFUSE DE TRANCHER, ET C'EST TOUT LE SUJET
---------------------------------------------------
Un post à la corbeille ne dit pas POURQUOI il y est. La base ne l'enregistre nulle part et
WordPress non plus. L'heuristique ci-dessus est un pari, pas une preuve — et elle se trompe
dans les deux sens, avec un contre-exemple nommé de chaque côté :

  • « sœur publique donc retrait voulu » se trompe quand les deux fiches ne sont pas deux
    copies mais **deux événements distincts au titre proche** (deux concerts d'un même
    festival). C'est exactement le cas que `resolve_wp_collision` refuse de trancher, et
    on emprunte sa parade : une sœur dont la date diffère de la nôtre n'est PAS retenue.
  • « pas de sœur donc retrait subi » se trompe quand **Franck a retiré la fiche à la
    main** pour un motif éditorial (hors périmètre, non-événement) sans penser à la
    rejeter en base. La republier annulerait sa décision, en silence, à 9h30 le lendemain.

D'où les deux options séparées : le script CLASSE et EXPLIQUE toujours, il n'ÉCRIT que ce
qu'on lui a explicitement demandé d'écrire. Rien de tout cela ne tourne en cron avec
`--voulus`/`--subis` ; en dry-run, en revanche, il est fait pour ça.

⚠️ RESTAURER PLUTÔT QUE RECRÉER. Pour ④, vider le lien fait naître un post NEUF : nouvelle
adresse, ancien post abandonné dans la corbeille. Quand le retrait est récent et manifestement
accidentel, restaurer le post depuis l'admin WordPress vaut mieux — même page, même URL,
mêmes liens partagés. Ce geste-là est dans l'admin, pas ici, et ce script ne touche JAMAIS
à WordPress en écriture : il lit, et il écrit en base.

LES TROIS QUESTIONS DE docs/ETATS_TERMINAUX.md (aucun nouvel état terminal créé)
-------------------------------------------------------------------------------
1. **Qui rouvre ?**
   • familles ①②④ (lien vidé) → `publish_batch_as`, au lot de 9h30, sans personne : une
     fiche retenue, datée, à venir et sans post EST son critère de création. Et c'est LUI
     qui efface `wp_deleted_at` en republiant, donc la marque ne survit pas à la
     réouverture.
   • famille ③ (`rejected`) → les trois chemins qui existaient déjà pour ce statut :
     `unreject_wp_online` (le post est ressorti de la corbeille), `reconcile_catalogue`,
     et le bouton du back-office. On ne crée pas d'état, on écrit dans un état qui a
     DÉJÀ ses réouvertures — et on ne touche pas à `llm_score`, précisément parce que le
     rejet le met à 0 ailleurs et que plus rien ne sait le rendre (cf. `unreject_wp_online`).
2. **À quelle condition ?** Un événement, pas un délai : la fiche repart dès qu'elle
   redevient publiable. Aucune attente, aucune commande à taper.
3. **Où se voit le nombre de fiches garées ?** Dans ce script, à chaque passage, y compris
   en dry-run : la section « DÉLIÉES ET PAS ENCORE REPARTIES ». Le marqueur est
   `wp_deleted_at` renseigné + `wp_post_id_as` vide, et chaque ligne dit POURQUOI la fiche
   n'est pas repartie. C'est le point qui compte, parce que la réponse 1 a un trou connu :
   **`publish_batch_as` exige une date** (`COALESCE(date_event_start,'') <> ''`). Une fiche
   non datée ne repart donc pas toute seule. Les familles ②/④ refusent pour cette raison de
   couper un lien qui ne serait pas repris — mais la famille ① n'a pas le choix (le post
   n'existe plus), et `reconcile_wp_deleted` produit la même situation depuis toujours sans
   que rien ne la compte. C'est ce que cette section rend visible : jusqu'ici, ces fiches-là
   n'apparaissaient dans AUCUN bilan.

Usage :
    .venv/bin/python -m scripts.reconcile_hors_ligne                 # dry-run (défaut)
    .venv/bin/python -m scripts.reconcile_hors_ligne --apply         # ① seule
    .venv/bin/python -m scripts.reconcile_hors_ligne --apply --perimes
    .venv/bin/python -m scripts.reconcile_hors_ligne --apply --subis --voulus
    .venv/bin/python -m scripts.reconcile_hors_ligne --ids 1789 2153 --apply --subis

Le dry-run n'écrit rien et n'appelle WordPress qu'en LECTURE : il est fait pour tourner en
cron, et c'est ce qui donne sa réponse à la question 3 ci-dessus. Ligne à ajouter à
`crontab.txt`, le lundi juste avant `weekly_digest` (8h00) :
    30 7 * * 1 cd /root/evenements && .venv/bin/python -m scripts.reconcile_hors_ligne \\
               >> logs/reconcile_hors_ligne.log 2>&1
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.dedupe import cross_lang_same
from utils.completeness import is_recurring
from utils.logger import get_logger

log = get_logger("reconcile-hors-ligne")
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaHorsLigne/1.0)"}

# Statuts « retenus » du pipeline — MÊME LISTE que scripts/publish_batch_as.py:60 et
# scripts/trash_by_ids.py:44. Elle est recopiée ici (et pas importée) comme dans les deux
# autres, mais le risque est réel : si elle diverge, `_repartira` ci-dessous annonce une
# republication qui n'aura pas lieu — c'est-à-dire exactement le renvoi qui n'aboutit pas
# que ce script est écrit pour supprimer.
RETENUS = ("evaluated", "published_cs", "published_sub")

MOTIF_VOULU = ("Retrait constaté sur WordPress le {jour} : le post était à la corbeille "
               "et la fiche [{soeur}] couvre le même événement sur un post encore en "
               "ligne (scripts/reconcile_hors_ligne --voulus).")


def _etat(wp_url: str, post_id: int) -> str:
    """'public' | 'non_public' | 'inexistant' | 'indetermine' — repris de
    `scripts/reconcile_wp_deleted._etat`, à l'identique et pour les mêmes raisons.

    ⚠️ NE JAMAIS interroger le front-end pour ça. `/?p=<id>` renvoie 404 pour TOUT post de
    type tribe_events sur cette installation, vivant ou mort (vérifié : le post 601,
    parfaitement en ligne, y répond 404). Et même sous la forme correcte
    `/?post_type=tribe_events&p=<id>`, un post en CORBEILLE répond 404 exactement comme un
    post supprimé — indistinguables. C'est ce qui a produit la fausse alerte « 61 posts
    supprimés » du 2026-08-02 : aucun ne l'était, tous étaient à la corbeille.

    Interrogation PAR NUMÉRO, jamais par collection (règle 2) : The Events Calendar exclut
    les événements PASSÉS de ses listes REST. Or ce script travaille aussi sur des
    expositions en cours et sur des fiches sans date — une liste ne prouverait donc rien,
    et surtout pas une absence.

    Et la distinction commande TOUT : 'inexistant' se répare seul (il n'y a plus rien au
    bout), 'non_public' demande un arbitrage (le post est restaurable, donc le retrait
    peut avoir été voulu). Un aléa réseau reste 'indetermine' et n'autorise rien.
    """
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}",
                         timeout=20, headers=UA)
    except requests.RequestException:
        return "indetermine"
    if r.status_code == 200:
        return "public"
    code = ""
    try:
        code = str((r.json() or {}).get("code") or "")
    except ValueError:
        pass
    if code == "rest_post_invalid_id":
        return "inexistant"
    if code == "rest_forbidden" or r.status_code in (401, 403):
        return "non_public"
    return "indetermine"


def _ensure_col(conn: sqlite3.Connection) -> None:
    """`wp_deleted_at` — le constat « à cette date, ce post n'était plus public ».

    Posée à l'origine par `reconcile_wp_deleted` ; on la repose ici pour ne pas dépendre
    de l'ordre des scripts sur une base qui n'y est jamais passée."""
    try:
        conn.execute("ALTER TABLE events_raw ADD COLUMN wp_deleted_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass


def _jour(v) -> date | None:
    """Date ISO d'une valeur de base, ou None si elle n'en est pas une.

    None pour une valeur ILLISIBLE, et pas une date arbitraire : règle 5, une mauvaise
    fusion a déjà mis en base la date d'un autre événement (WP#6798). Une date qu'on ne
    sait pas lire ne doit surtout pas servir à classer une fiche en « passé ».
    """
    try:
        return date.fromisoformat(str(v or "").strip()[:10])
    except ValueError:
        return None


def _devant_nous(ev: dict, auj: date) -> tuple[bool, str]:
    """(retenu, motif) — règle 5, les trois seules familles qui méritent du travail.

    • RÉCURRENT : pas de date unique, donc jamais « passé » (utils.completeness) ;
    • SANS DATE (ou date illisible) : donnée MANQUANTE, pas événement terminé. `dates.py`
      la remplira peut-être demain. La classer « passée » l'enterrerait pour de bon ;
    • sinon c'est `date_event_end` qui décide, JAMAIS `date_event_start` seule — une
      exposition de mai à septembre compte tout l'été.
    """
    if is_recurring(ev):
        return True, "récurrent"
    fin = _jour(ev.get("date_event_end")) or _jour(ev.get("date_event_start"))
    if fin is None:
        return True, "sans date"
    return (fin >= auj), ("en cours / à venir" if fin >= auj else "passé")


def _repartira(ev: dict, auj: date) -> tuple[bool, str]:
    """La fiche sera-t-elle reprise par `publish_batch_as` une fois son lien vidé ?

    RECOPIE DE SON `_select` (publish_batch_as.py:59-71), et c'est volontairement littéral :
    annoncer « elle repart au lot du lendemain » sans vérifier les quatre conditions
    reproduirait le défaut qu'on répare — un renvoi qui n'aboutit pas.

    La condition qui piège est la DATE : `COALESCE(date_event_start,'') <> ''`. Une fiche
    récurrente ou non datée ne repart PAS, et `publish_batch_as` refuse d'ailleurs
    explicitement toute création sans date (« TEC la daterait du jour de publication »).
    Vider son lien la sort donc du site sans que rien ne l'y ramène : c'est ce que la
    section « déliées et pas encore reparties » a pour rôle de garder sous les yeux.
    """
    if (ev.get("statut") or "") not in RETENUS:
        return False, f"statut '{ev.get('statut')}' hors file de publication"
    if ev.get("duplicate_of"):
        return False, f"fusionnée dans [{ev['duplicate_of']}]"
    if not (ev.get("date_event_start") or "").strip():
        # Deux motifs qu'il serait commode de confondre, et qui n'ont pas la même suite :
        # une fiche non datée attend `dates.py` et peut repartir la semaine prochaine ;
        # une RÉCURRENTE n'a pas de date par nature, `dates.py` ne lui en donnera jamais,
        # et aucun automatisme ne la republiera. Écrire « attend dates.py » sur celle-là
        # serait le renvoi qui n'aboutit pas — la deuxième fois qu'on le ferait ici.
        if is_recurring(ev):
            return False, ("RÉCURRENTE : publish_batch_as refuse toute création sans date "
                           "et dates.py n'en donnera jamais — arbitrage humain")
        return False, ("sans date_event_start — publish_batch_as REFUSE la création "
                       "(attend scripts/dates.py)")
    fin = _jour(ev.get("date_event_end")) or _jour(ev.get("date_event_start"))
    if fin is None:
        return False, "date illisible en base"
    if fin < auj:
        return False, "événement passé"
    return True, "repart au prochain lot"


def _jumelles(a: dict, b: dict) -> bool:
    """Paire de TRADUCTION FR↔IT — à ne surtout pas confondre avec un doublon.

    Les deux versions d'un même événement sont censées être en ligne TOUTES LES DEUX
    (l'appariement hreflang en dépend, cf. reconcile_catalogue._avec_jumeaux). Que la
    jumelle italienne soit publique ne dit donc rien du retrait de la française : conclure
    « voulu » sur ce signal-là rejetterait une fiche parfaitement légitime, et casserait
    la paire au passage.
    """
    if a.get("translation_of") and a["translation_of"] == b.get("id"):
        return True
    if b.get("translation_of") and b["translation_of"] == a.get("id"):
        return True
    return bool(a.get("translation_of")) and a.get("translation_of") == b.get("translation_of")


def _meme_evenement(a: dict, b: dict) -> bool:
    """Deux fiches décrivent-elles le même événement ?

    Deux signaux, du plus sûr au moins sûr : le lien de fusion déjà posé en base
    (`duplicate_of`), puis `dedupe.cross_lang_same` sur les titres.

    POURQUOI CELUI-LÀ et pas `utils.sources.same_story`, essayé d'abord : same_story exige
    trois mots significatifs de 4+ lettres ou un nom propre à MAJUSCULE INTERNE (RareEarth).
    Vérifié sur fixture, il ne rapproche même pas « Jazz Art Festival 2026 » de lui-même —
    « Art » fait trois lettres, « festival » n'est pas distinctif, et aucun mot ne porte de
    capitale interne. Il est fait pour ne pas répéter une UNE, pas pour reconnaître un
    doublon d'événement. `cross_lang_same` est l'outil que `dedupe` utilise pour décider de
    FUSIONNER deux fiches — donc exactement la question posée ici — et il est plus sévère
    là où il faut : ≥ 2 tokens communs qui ne soient pas des années, recouvrement ≥ 0,5, et
    années incompatibles écartées (deux éditions ne sont pas deux copies).
    """
    if a.get("duplicate_of") and a["duplicate_of"] == b.get("id"):
        return True
    if b.get("duplicate_of") and b["duplicate_of"] == a.get("id"):
        return True
    if a.get("duplicate_of") and a.get("duplicate_of") == b.get("duplicate_of"):
        return True
    return cross_lang_same(a.get("title") or "", b.get("title") or "")


def _dates_compatibles(a: dict, b: dict) -> bool:
    """Deux fiches datées de JOURS DIFFÉRENTS ne sont pas deux copies : ce sont deux
    événements distincts (deux concerts d'un même festival, deux éditions).

    Garde-fou emprunté à `resolve_wp_collision._dates_incompatibles`, et il est ici la
    moitié la plus importante de l'heuristique : sans lui, « Jazz Art, 12 juillet » et
    « Jazz Art, 19 juillet » se prendraient l'une pour le doublon de l'autre et le script
    conclurait « retrait voulu » sur un retrait qui ne l'était pas. Une date manquante ne
    tranche rien, donc ne disqualifie rien.
    """
    ja, jb = _jour(a.get("date_event_start")), _jour(b.get("date_event_start"))
    return ja is None or jb is None or ja == jb


def _soeurs(ev: dict, autres: list[dict]) -> list[dict]:
    """Fiches candidates au titre de « doublon encore en ligne » — non vérifiées ici.

    On ne rend que des CANDIDATES : leur post est ensuite interrogé un par un (`_etat`),
    parce qu'un `wp_post_id_as` renseigné ne prouve rien (règle 1) — et c'est précisément
    l'erreur que ce script existe pour ne plus commettre.
    """
    out = []
    for o in autres:
        if o["id"] == ev["id"] or int(o.get("wp_post_id_as") or 0) == int(ev["wp_post_id_as"]):
            continue
        if _jumelles(ev, o) or not _meme_evenement(ev, o):
            continue
        if not _dates_compatibles(ev, o):
            continue
        out.append(o)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Referme les fiches dont le post WordPress n'est pas public.")
    p.add_argument("--apply", action="store_true",
                   help="Écrit (sinon dry-run). Seul, ne traite que les LIENS MORTS.")
    p.add_argument("--perimes", action="store_true",
                   help="Vide aussi le lien des fiches 'evaluated' (jamais confirmées "
                        "publiées) dont le post n'est pas public.")
    p.add_argument("--subis", action="store_true",
                   help="Vide aussi le lien des posts CORBEILLÉS sans sœur publique : la "
                        "fiche repart au lot du lendemain sur un post NEUF.")
    p.add_argument("--voulus", action="store_true",
                   help="Passe en 'rejected' (id conservé) les fiches dont une SŒUR porte "
                        "un post encore public — retrait présumé volontaire.")
    p.add_argument("--ids", type=int, nargs="+", default=None, help="Limiter à ces ids.")
    p.add_argument("--delay", type=float, default=0.8, help="Pause entre deux appels REST.")
    p.add_argument("--cap-liste", type=int, default=30,
                   help="Nombre de lignes détaillées par section (défaut 30).")
    args = p.parse_args(argv)

    load_dotenv(ROOT / ".env")
    wp_url = (os.getenv("WP_AS_URL") or "https://agendasabauda.eu").rstrip("/")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_col(conn)
    auj = date.today()

    sql = "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0"
    params: list = []
    if args.ids:
        sql += f" AND id IN ({','.join('?' * len(args.ids))})"
        params = list(args.ids)
    liees = [dict(r) for r in conn.execute(sql + " ORDER BY id", params)]

    # PÉRIMÈTRE AVANT RÉSEAU (règle 5). On écarte le passé AVANT d'interroger WordPress :
    # 85 fiches liées mais 28 devant nous, ce sont 57 appels REST qu'on ne fait pas — et
    # surtout 57 lignes de rapport qui fabriqueraient du travail au lieu d'en désigner.
    # Le compte des écartées est imprimé : une fiche qui sort d'une file sort aussi des
    # bilans si on ne la compte pas explicitement (règle 6).
    candidates, ecartees = [], []
    for ev in liees:
        garde, motif = _devant_nous(ev, auj)
        (candidates if garde else ecartees).append((ev, motif))

    print(f"\n{len(liees)} fiche(s) portent un identifiant WordPress · "
          f"{len(candidates)} encore devant nous, {len(ecartees)} passée(s) — non traitées.")
    # Dire COMBIEN DE TEMPS ça va prendre, avant de se taire pendant trois minutes.
    if candidates:
        secondes = int(len(candidates) * (args.delay + 0.35))
        print(f"Interrogation de WordPress, un post à la fois — environ "
              f"{secondes // 60} min {secondes % 60:02d} s. Rien n'est écrit.", flush=True)

    # Univers des sœurs possibles : TOUTES les fiches liées à un post, y compris passées.
    # Une exposition terminée peut parfaitement être le doublon publié qui explique le
    # retrait de celle qu'on examine.
    autres = [dict(r) for r in conn.execute(
        "SELECT id, title, statut, wp_post_id_as, duplicate_of, translation_of, "
        "       date_event_start FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0")]

    cache: dict[int, str] = {}

    def etat(post_id: int) -> str:
        """Un appel par POST, pas par fiche : deux doublons se citent mutuellement.

        LE SONDAGE DOIT SE VOIR. 198 posts à 0,8 s de pause font près de trois minutes
        pendant lesquelles ce script n'affichait RIEN. Franck a collé sa sortie en croyant
        qu'elle était complète — elle s'arrêtait au milieu du sondage. Un long silence ne
        se distingue pas d'un plantage, surtout pour quelqu'un qui ne lit pas le code.
        Une ligne tous les 25 posts suffit, et elle annonce le total pour qu'on sache
        combien de temps attendre. (2026-08-13)
        """
        pid = int(post_id)
        if pid not in cache:
            cache[pid] = _etat(wp_url, pid)
            if len(cache) % 25 == 0:
                print(f"    …{len(cache)}/{len(candidates)} post(s) interrogé(s)",
                      flush=True)
            if args.delay:
                time.sleep(args.delay)
        return cache[pid]

    familles: dict[str, list[dict]] = {k: [] for k in
                                       ("lien_mort", "perime", "voulu", "subi",
                                        "coherent", "public", "indetermine")}
    for ev, _motif in candidates:
        e = etat(ev["wp_post_id_as"])
        if e == "public":
            # La base et le site sont d'accord — rien à réconcilier ici. On les compte
            # quand même : c'est le dénominateur qui rend le reste lisible.
            familles["public"].append({"ev": ev, "etat": e})
            continue
        if e == "indetermine":
            familles["indetermine"].append({"ev": ev, "etat": e})
            continue

        repart, pourquoi = _repartira(ev, auj)
        fiche = {"ev": ev, "etat": e, "soeur": None,
                 "repart": repart, "pourquoi": pourquoi}

        if e == "inexistant":
            # Le constat le plus dur d'abord : il n'y a plus AUCUN post au bout du lien,
            # donc plus rien à arbitrer — ni retrait voulu, ni retrait subi, juste un
            # pointeur mort. On ne cherche même pas de sœur : ce serait payer des appels
            # REST pour une question qui ne se pose pas.
            familles["lien_mort"].append(fiche)
            continue
        if (ev.get("statut") or "") == "rejected":
            # RIEN À RÉCONCILIER : la base dit « écartée », le site dit « retirée ». Les
            # deux sont d'accord, c'est l'état d'arrivée que --voulus fabrique. Vider le
            # lien détruirait le seul chemin vers un post restaurable sans rien gagner —
            # une fiche rejetée ne repart de toute façon pas (publish_batch_as l'exclut).
            familles["coherent"].append(fiche)
            continue

        # À partir d'ici, et seulement ici : post en CORBEILLE sur une fiche que la base
        # tient pour vivante. C'est le cas ambigu, celui qui vaut la recherche de sœur.
        soeur = None
        for cand in _soeurs(ev, autres):
            if etat(cand["wp_post_id_as"]) == "public":
                soeur = cand
                break
        fiche["soeur"] = soeur

        if soeur is not None:
            familles["voulu"].append(fiche)
        elif (ev.get("statut") or "") == "evaluated":
            # Jamais confirmée publiée : aucune colonne de la base n'atteste d'une
            # publication (statut resté 'evaluated', published_as_date en général vide).
            # L'identifiant est plus vraisemblablement un reliquat qu'un retrait — mais
            # c'est une vraisemblance, pas une preuve, d'où sa propre option.
            familles["perime"].append(fiche)
        else:
            familles["subi"].append(fiche)

    def _lignes(titre: str, cle: str, entete: list[str]) -> None:
        lot = familles[cle]
        if not lot:
            return
        print(f"\n--- {len(lot)} {titre} ---")
        for l in entete:
            print(f"    {l}")
        for f in lot[:args.cap_liste]:
            ev = f["ev"]
            suite = ""
            if f.get("soeur"):
                suite = (f" · sœur [{f['soeur']['id']}] WP#{f['soeur']['wp_post_id_as']} "
                         f"EN LIGNE")
            elif "repart" in f:
                suite = f" · {f['pourquoi']}" if not f["repart"] else " · repart au lot"
            # ── CE QUI DÉCIDE VRAIMENT POUR UN « SUBI » (ajouté le 2026-08-13) ────────
            # `--subis` republie. Reste à savoir CE QU'ON REPUBLIE, et la réponse tient à
            # une relation que la base connaît déjà : la fiche est-elle la TRADUCTION
            # d'un original encore public ?
            #
            #   · oui → la republier rend au site sa page dans l'autre langue, qui manque
            #     aujourd'hui. C'est une réparation, pas un pari ;
            #   · non → on remet en ligne une page que quelqu'un a peut-être retirée
            #     exprès, sans que rien ne l'ait consigné.
            #
            # Sans cette ligne, les vingt-six « subis » se ressemblaient tous, et j'ai
            # moi-même averti Franck que republier 3533 et 4195 « recréerait des
            # doublons » — c'était faux : ce sont les versions italiennes manquantes de
            # deux fiches françaises en ligne. Je raisonnais sur une liste qui n'affichait
            # pas ce qui distinguait ses lignes.
            trad_de = int(ev.get("translation_of") or 0)
            if cle == "subi" and trad_de:
                orig = next((o for o in autres if o["id"] == trad_de), None)
                if orig and int(orig.get("wp_post_id_as") or 0):
                    e_orig = cache.get(int(orig["wp_post_id_as"]))
                    if e_orig == "public":
                        suite += (f" · TRADUCTION de [{trad_de}], dont la page est EN "
                                  f"LIGNE — la republier rend la langue manquante")
                    elif e_orig:
                        suite += (f" · traduction de [{trad_de}], retirée elle aussi — "
                                  f"les deux langues sont hors ligne")
                    else:
                        suite += f" · traduction de [{trad_de}] (page non sondée)"
                else:
                    suite += f" · traduction de [{trad_de}], original sans page"
            print(f"  [{ev['id']:>5}] WP#{ev['wp_post_id_as']:<6} "
                  f"{(ev.get('title') or '')[:44]:46} statut={ev.get('statut')}"
                  f" · {(ev.get('date_event_start') or '—')[:10]}{suite}")
        if len(lot) > args.cap_liste:
            print(f"  …et {len(lot) - args.cap_liste} autre(s).")

    _lignes("LIEN MORT — le post n'existe plus", "lien_mort",
            ["(--apply vide wp_post_id_as/wp_permalink_as : rien à quoi se raccrocher.",
             " Aucun jugement là-dedans, c'est la seule famille qui se tranche seule.)"])
    _lignes("LIEN PÉRIMÉ — 'evaluated', jamais confirmée publiée", "perime",
            ["(--perimes vide le lien. La base n'a JAMAIS enregistré de publication pour",
             " ces fiches : l'identifiant ressemble à un reliquat, pas à un retrait.)"])
    _lignes("RETRAIT PROBABLEMENT VOULU — une sœur est encore en ligne", "voulu",
            ["(--voulus pose statut='rejected' et GARDE l'identifiant : le post reste",
             " restaurable, et 'rejected' a déjà trois chemins de réouverture.",
             " ⚠️ heuristique : deux fiches au titre proche PEUVENT être deux événements",
             "    distincts. Les dates sont vérifiées, les titres ne prouvent rien.)"])
    _lignes("RETRAIT PROBABLEMENT SUBI — corbeille, aucune sœur en ligne", "subi",
            ["(--subis vide le lien : la fiche repart au lot du lendemain sur un post NEUF",
             " — nouvelle adresse, ancien post laissé à la corbeille.",
             " ⚠️ si le retrait était un geste éditorial de Franck jamais consigné en base,",
             "    ceci l'annule en silence. Restaurer le post dans l'admin est souvent",
             "    le meilleur geste ; il ne se fait pas d'ici.)"])

    if familles["coherent"]:
        print(f"\n--- {len(familles['coherent'])} DÉJÀ COHÉRENTE(S) — rejetée(s) en base "
              f"ET retirée(s) du site ---")
        print("    (rien à faire : c'est l'état d'arrivée. L'identifiant est conservé, le")
        print("     post reste restaurable ; unreject_wp_online sait rouvrir le jour où il")
        print("     ressort de la corbeille.)")
    if familles["public"]:
        print(f"\n--- {len(familles['public'])} EN LIGNE — base et site d'accord, "
              f"rien à faire ---")
    if familles["indetermine"]:
        print(f"\n--- {len(familles['indetermine'])} INDÉTERMINÉE(S) — aléa réseau, "
              f"NON touchées, à revérifier ---")
        for f in familles["indetermine"][:args.cap_liste]:
            print(f"  [{f['ev']['id']}] WP#{f['ev']['wp_post_id_as']} "
                  f"{(f['ev'].get('title') or '')[:50]}")

    # --- Ce qui sera écrit, famille par famille, selon les options données -------------
    # ⚠️ ON NE VIDE LE LIEN D'UN POST CORBEILLÉ QUE SI LA FICHE REVIENDRA.
    # Sans ce filtre, `--subis` sur « Atelier permanent de gravure » (récurrente, donc
    # SANS date par nature) couperait son lien alors que `publish_batch_as` exige
    # `date_event_start` : la fiche sortirait du site et rien, jamais, ne l'y ramènerait —
    # `dates.py` ne datera pas un événement qui n'a pas de date. Ce serait créer un
    # cul-de-sac dans le script écrit pour en fermer un (c'est le sixième de la journée du
    # 2026-08-03, né en corrigeant les cinq autres). Le post, lui, est à la corbeille donc
    # RESTAURABLE : garder le lien ne coûte rien et conserve le seul chemin vers lui.
    # Deux gestes humains referment ces cas, tous deux nommés dans le rapport.
    # La famille ① échappe à ce filtre : son post n'existe plus, il n'y a aucun chemin à
    # préserver, et c'est déjà ce que fait reconcile_wp_delete sur ses « dormantes ».
    a_vider = list(familles["lien_mort"])
    refus_strand = []
    for cle, actif in (("perime", args.perimes), ("subi", args.subis)):
        if not actif:
            continue
        for f in familles[cle]:
            (a_vider if f["repart"] else refus_strand).append(f)
    a_rejeter = list(familles["voulu"]) if args.voulus else []

    if refus_strand:
        print(f"\n--- ⛔ {len(refus_strand)} NON VIDÉE(S) : elles ne reviendraient pas ---")
        print("    (leur post est à la CORBEILLE, donc restaurable — on garde le lien.")
        print("     Couper serait les sortir du site sans retour possible. Deux issues,")
        print("     humaines : restaurer le post dans l'admin, ou rejeter la fiche en base.)")
        for f in refus_strand:
            print(f"  [{f['ev']['id']:>5}] WP#{f['ev']['wp_post_id_as']:<6} "
                  f"{(f['ev'].get('title') or '')[:44]:46} → {f['pourquoi']}")

    en_attente = []
    if not args.perimes and familles["perime"]:
        en_attente.append(f"{len(familles['perime'])} lien(s) périmé(s) — relancer avec --perimes")
    if not args.subis and familles["subi"]:
        en_attente.append(f"{len(familles['subi'])} retrait(s) présumé(s) SUBI(s) — --subis")
    if not args.voulus and familles["voulu"]:
        en_attente.append(f"{len(familles['voulu'])} retrait(s) présumé(s) VOULU(s) — --voulus")

    if not args.apply:
        print(f"\nDry-run — rien n'a été écrit. --apply viderait {len(a_vider)} lien(s) "
              f"et rejetterait {len(a_rejeter)} fiche(s).")
        for l in en_attente:
            print(f"   ⏸  {l}")
        _garees(conn, auj, args.cap_liste)
        conn.close()
        return 0

    stamp = datetime.now().isoformat(timespec="seconds")
    for f in a_vider:
        ev = f["ev"]
        # On pose `wp_deleted_at` EN MÊME TEMPS qu'on coupe le lien. Ce n'est pas un
        # verrou : `publish_batch_as` l'efface lui-même en republiant (sinon site_audit
        # cesserait définitivement de relire la fiche). C'est la TRACE qui permet de
        # compter, plus bas, les fiches déliées qui ne sont pas encore reparties.
        conn.execute("UPDATE events_raw SET wp_post_id_as=NULL, wp_permalink_as=NULL, "
                     "wp_deleted_at=? WHERE id=?", (stamp, ev["id"]))
        log.info("[%s] WP#%s lien coupé (%s) — %s", ev["id"], ev["wp_post_id_as"],
                 f["etat"], (ev.get("title") or "")[:55])
    for f in a_rejeter:
        ev, soeur = f["ev"], f["soeur"]
        # On GARDE wp_post_id_as : le post est à la corbeille, donc restaurable en un clic,
        # et couper le lien détruirait le seul chemin vers lui (c'est le raisonnement de
        # reconcile_wp_deleted, et il vaut ici aussi). On ne touche PAS à llm_score : les
        # autres chemins de rejet le mettent à 0 et plus rien ne sait le rendre, ce qui
        # laisse la fiche définitivement sous le seuil de rédaction d'enrich.py.
        conn.execute("UPDATE events_raw SET statut='rejected', wp_deleted_at=?, "
                     "llm_justification=? WHERE id=?",
                     (stamp, MOTIF_VOULU.format(jour=auj.isoformat(), soeur=soeur["id"]),
                      ev["id"]))
        log.info("[%s] WP#%s rejetée — doublon de [%s] restée en ligne — %s",
                 ev["id"], ev["wp_post_id_as"], soeur["id"], (ev.get("title") or "")[:55])
    conn.commit()

    # RECOMPTER EN BASE (règle 6) : on relit l'état obtenu au lieu d'annoncer la longueur
    # des listes qu'on vient de parcourir. Un UPDATE qui ne trouve pas sa ligne ne lève
    # rien — sans relecture, « 12 fiches traitées » serait une intention, pas un résultat.
    def _compte(ids: list[int], where: str) -> int:
        if not ids:
            return 0
        m = ",".join("?" * len(ids))
        return conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE id IN ({m}) AND {where}",
                            ids).fetchone()[0]

    ids_vides = [f["ev"]["id"] for f in a_vider]
    ids_rejet = [f["ev"]["id"] for f in a_rejeter]
    vides = _compte(ids_vides, "COALESCE(wp_post_id_as,0) = 0")
    rejetees = _compte(ids_rejet, "statut = 'rejected'")

    print(f"\n✅ {vides}/{len(ids_vides)} lien(s) réellement vidé(s) · "
          f"{rejetees}/{len(ids_rejet)} fiche(s) réellement rejetée(s).")
    if vides < len(ids_vides) or rejetees < len(ids_rejet):
        print("⚠️  Écart entre le demandé et le constaté — relire les logs avant de conclure.")
    repartiront = sum(1 for f in a_vider if f["repart"])
    if ids_vides:
        # Les « non » sont ici les liens MORTS d'une fiche que rien ne reprendra (② et ④
        # ont déjà été écartées plus haut). Les nommer : elles ne sont plus en ligne et
        # n'y reviendront pas seules — c'est le genre de chose qui se découvre trois
        # semaines plus tard si on ne l'écrit pas (règle 6).
        print(f"   {repartiront} repartiront d'elles-mêmes au lot de 9h30 ; "
              f"{len(ids_vides) - repartiront} non"
              + (" — voir la section « déliées » ci-dessous."
                 if repartiront < len(ids_vides) else "."))
    for l in en_attente:
        print(f"   ⏸  {l}")
    if refus_strand:
        print(f"   ⛔ {len(refus_strand)} non vidée(s) faute de retour possible "
              f"(voir ci-dessus).")
    if familles["indetermine"]:
        print(f"   ⚠️  {len(familles['indetermine'])} indéterminée(s) laissée(s) de côté.")
    if ecartees:
        print(f"   {len(ecartees)} passée(s) écartée(s) d'office (règle 5).")

    _garees(conn, auj, args.cap_liste)
    conn.close()
    log.info("Hors-ligne : %d lien(s) vidé(s), %d rejetée(s), %d indéterminée(s), "
             "%d passée(s) écartée(s) le %s",
             vides, rejetees, len(familles["indetermine"]), len(ecartees), stamp)
    return 0


def _garees(conn: sqlite3.Connection, auj: date, cap: int) -> None:
    """LA TROISIÈME QUESTION DE docs/ETATS_TERMINAUX.md : où se voit le nombre de fiches
    garées ?

    Ici, à chaque passage, dry-run compris — donc visible sans avoir à taper une commande
    dont on ignore l'existence. Le marqueur est `wp_deleted_at` renseigné + `wp_post_id_as`
    vide : « son lien mort a été coupé, et elle n'est pas encore revenue en ligne ». Il
    compte aussi les fiches déliées par `reconcile_wp_deleted` (famille « réellement
    inexistante »), qui n'étaient comptées nulle part jusqu'ici.

    Ce qui compte n'est pas le nombre mais le MOTIF : une fiche retenue et datée repartira
    demain toute seule, il n'y a rien à faire ; une fiche sans date ne repartira JAMAIS
    sans `dates.py`, et c'est celle-là qu'il faut voir. Nommées et datées, comme les
    exclusions de vitrine dans weekly_digest — « 3 fiches » se lit et s'oublie, « depuis
    le 4 août » se rouvre.

    Règle 5 : seules celles encore devant nous.
    """
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, title, statut, date_event_start, date_event_end, duplicate_of, "
            "       recurring, wp_deleted_at FROM events_raw "
            "WHERE COALESCE(wp_post_id_as,0) = 0 AND COALESCE(wp_deleted_at,'') <> '' "
            "ORDER BY wp_deleted_at ASC")]
    except sqlite3.OperationalError:
        return
    vivantes = [r for r in rows if _devant_nous(r, auj)[0]]
    if not vivantes:
        return
    bloquees = [(r, _repartira(r, auj)) for r in vivantes]
    attendent = [(r, m) for r, (ok, m) in bloquees if not ok]
    print(f"\n--- DÉLIÉES ET PAS ENCORE REPARTIES : {len(vivantes)} "
          f"(dont {len(attendent)} qui ne repartiront pas seules) ---")
    for r, motif in attendent[:cap]:
        print(f"  [{r['id']:>5}] déliée le {(r['wp_deleted_at'] or '')[:10]} · "
              f"{(r.get('title') or '')[:44]:46} → {motif}")
    if len(attendent) > cap:
        print(f"  …et {len(attendent) - cap} autre(s).")
    if len(vivantes) > len(attendent):
        print(f"  ({len(vivantes) - len(attendent)} autre(s) attendent simplement le "
              f"prochain lot de publication — rien à faire.)")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
