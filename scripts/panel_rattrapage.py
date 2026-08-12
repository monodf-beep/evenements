#!/usr/bin/env python3
"""FAIRE RELIRE PAR LE PANEL LES ARTICLES DÉJÀ ÉCRITS — le rattrapage qui manquait.

LE TROU. Le panel de personas (`enrich.reader_panel`) ne tourne qu'au MOMENT de la
rédaction, dans `enrich_event`. Un article écrit avant son arrivée, ou écrit pendant que
`ENRICH_READER_REVIEW=0`, n'en aura jamais — et rien dans la chaîne ne sait le lui donner
après coup. Mesure du 2026-08-12 : **212 fiches publiées, 86 seulement portent un
verdict**. Les 126 autres attendent depuis leur publication, sans file où figurer.

C'est un état terminal de plus, du genre que `docs/ETATS_TERMINAUX.md` recense : pas un
statut qui bloque, un simple manque que personne ne réclame. La quatrième question du
document — « le rouvreur est-il branché ? » — n'avait ici même pas de rouvreur à brancher.

CE QU'IL FAIT, ET SEULEMENT ÇA
  · il relit l'article DÉJÀ EN BASE (`enrich_data.article.corps`) avec le vrai panel :
    les mêmes personas de `docs/personas/`, le même protocole, le même modèle éco ;
  · il range le résultat dans `enrich_data.reader_panel`, à l'endroit exact où
    `publisher_as._panel_meta` va le chercher.

CE QU'IL NE FAIT PAS, ET C'EST NON NÉGOCIABLE
  · il ne réécrit RIEN. Pas une ligne d'article, ni en base ni sur le site. Le panel
    produit un VERDICT, jamais une publication — la charte impose qu'aucune sortie de
    modèle ne parte en ligne sans validation humaine ;
  · il ne publie pas. Pour que le verdict apparaisse sur WordPress, il faut republier
    explicitement, et c'est un geste séparé qu'il se contente de nommer à la fin ;
  · il ne touche pas aux fiches qui ont DÉJÀ un verdict. Re-juger ce qui a été jugé
    coûterait des appels pour produire un second avis sur la même matière — et deux
    verdicts sur une même fiche, on ne saurait plus lequel croire.

CE QUE LE PREMIER PASSAGE COMPLET A MONTRÉ (2026-08-13, 42 fiches) : **26 « ok » et
16 « revise »**. Les cinq premières relues, elles, donnaient 1 sur 5 — c'était un mauvais
échantillon, trois articles de moins de mille caractères. L'instrument n'est pas sévère
par construction.

ET UNE VALIDATION QUI N'ÉTAIT PAS PRÉVUE. Dix de ces fiches sont des paires FR/IT du même
événement, jugées séparément, sans que le panel sache qu'elles allaient ensemble — et
souvent par des personas différents, puisque le territoire diffère. **Neuf paires sur dix
rendent le même verdict** (MonumenTO, Istituzione musicale, parc d'Aoste, Collontrek,
Cinéma au Valentino, Sous les portiques, Terra Madre, Montrottier, Matisse–YSL). Deux
appels indépendants, le même jugement : c'est la meilleure preuve de stabilité qu'on
puisse avoir sur un instrument de ce genre, et elle est arrivée sans être cherchée.

La dixième diverge — « Orchestre de la Suisse Romande », 3527 en ok 4.0 contre 930 en
revise 2.5. À regarder : le titre de 930 est en minuscules, ce qui sent l'article plus
pauvre plutôt que le panel instable, mais ça n'a pas été vérifié.

Règle 5 : seulement ce qui est encore devant nous. Un article mal noté sur un événement
terminé ne sera ni republié ni relu par personne.

Règle 4 : dry-run par défaut. Le dry-run n'appelle AUCUN modèle — il montre le périmètre
et le coût prévisible, pas un échantillon facturé.

  .venv/bin/python -m scripts.panel_rattrapage                # ce qui serait relu
  .venv/bin/python -m scripts.panel_rattrapage --apply --cap 10
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

# LA CLÉ VIT DANS LE .env, ET IL FAUT LE CHARGER. Oublié à la première version : le
# dry-run passait très bien (il n'appelle rien), et `--apply` s'arrêtait sur
# « ANTHROPIC_API_KEY absente » alors que la clé était là — c'est enrich.py qui appelle
# load_dotenv, pas l'environnement du shell. Un défaut que seul le chemin PAYANT révèle
# est exactement celui qu'une simulation ne peut pas attraper.
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def _data(ev: dict) -> dict:
    try:
        return json.loads(ev.get("enrich_data") or "") or {}
    except (ValueError, TypeError):
        return {}


def a_relire(row: sqlite3.Row, rejuger: bool = False) -> tuple[bool, str]:
    """(à relire ?, pourquoi pas). La raison est rendue pour être COMPTÉE, pas devinée.

    Un « 0 fiche à relire » qui ne dirait pas combien de cas se sont présentés, ni pourquoi
    chacun a été écarté, ne distinguerait pas une base déjà couverte d'une requête vide
    (docs/ERREURS_2026-08-11.md)."""
    ev = dict(row)
    data = _data(ev)
    panel = data.get("reader_panel") or {}
    if panel.get("verdict"):
        # LE SEUL ROUVREUR, ET SA CONDITION EST UN FAIT. Un verdict rendu SANS les infos
        # pratiques de la fiche vient d'un instrument qui ne voyait pas la même chose
        # (cf. enrich._bloc_infos_pratiques, 2026-08-13). `--rejuger` le rouvre — et lui
        # seul : rejouer un verdict rendu par l'instrument ACTUEL sur la MÊME matière
        # serait le refus qui se rejoue à l'identique que la règle 3 interdit.
        from scripts.enrich import PANEL_VERSION
        courant = panel.get("version") == PANEL_VERSION
        if rejuger and not courant:
            return True, ""
        return False, ("a déjà un verdict de la version courante" if courant else
                       f"a un verdict d'une version PÉRIMÉE du panel "
                       f"({panel.get('version') or 'sans marque'} ≠ {PANEL_VERSION}) — "
                       f"`--rejuger` pour le refaire")
    corps = ((data.get("article") or {}).get("corps") or "").strip()
    if not corps:
        return False, "aucun article en base — il n'y a rien à faire relire"
    if len(corps) < 400:
        # LE PANEL EST FAIT POUR LES ARTICLES LONGS. enrich.py ne le déclenche pas sur les
        # « courts », qui sont des entrées de catalogue : leur demander de la substance
        # produirait un « revise » mécanique sur une fiche qui n'a jamais prétendu en avoir.
        return False, "article court (catalogue) — le panel ne s'y applique pas"
    return True, ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="fait tourner le panel pour de vrai (appels facturés). Sans ça, "
                         "simulation SANS AUCUN appel de modèle")
    ap.add_argument("--cap", type=int, default=25,
                    help="nombre maximum de fiches relues en une fois ; le reste est DIT")
    ap.add_argument("--tout", action="store_true",
                    help="inclut les fiches non publiées (par défaut : seulement ce que "
                         "le public lit déjà)")
    ap.add_argument("--ids", nargs="+", type=int, help="se limiter à ces fiches")
    ap.add_argument("--rejuger", action="store_true",
                    help="rouvre AUSSI les verdicts rendus par une version PÉRIMÉE du "
                         "panel (cf. enrich.PANEL_VERSION). Condition de FAIT — "
                         "l'instrument a changé — jamais un délai. Un verdict de la "
                         "version courante reste intouchable")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    auj = date.today().isoformat()

    where = ("COALESCE(duplicate_of,0)=0 "
             "AND COALESCE(statut,'') NOT IN ('merged','rejected') "
             "AND (COALESCE(recurring,0)=1 "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start,'') = '' "
             "     OR COALESCE(NULLIF(date_event_end,''), date_event_start) >= ?)")
    params: list = [auj]
    if not args.tout:
        where += " AND COALESCE(wp_post_id_as,0) <> 0"
    if args.ids:
        where += f" AND id IN ({','.join('?' * len(args.ids))})"
        params += args.ids

    rows = conn.execute(f"SELECT * FROM events_raw WHERE {where} "
                        f"ORDER BY COALESCE(wp_post_id_as,0) DESC", params).fetchall()

    candidats, ecartes = [], {}
    for r in rows:
        ok, motif = a_relire(r, rejuger=args.rejuger)
        if ok:
            candidats.append(r)
        else:
            ecartes[motif] = ecartes.get(motif, 0) + 1

    print("═══ Rattrapage du panel de lecteurs ═══")
    print(f"Périmètre : {len(rows)} fiche(s) vivantes"
          + ("" if args.tout else ", PUBLIÉES") + " (règle 5).\n")
    for motif, n in sorted(ecartes.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>5}  écartées — {motif}")
    # LE LIBELLÉ DIT CE QU'IL COMPTE, ET IL CHANGE AVEC --rejuger. Écrit « aucun verdict »
    # dans les deux cas, il aurait menti sur la moitié des passages : avec --rejuger, les
    # fiches retenues EN ONT un, rendu par l'ancien instrument.
    print(f"  {len(candidats):>5}  À RELIRE — "
          + ("un article existe : aucun verdict, ou un verdict de l'ancien panel"
             if args.rejuger else "un article existe, aucun verdict") + "\n")

    if not candidats:
        print("Rien à relire dans ce périmètre.")
        conn.close()
        return 0

    lot = candidats[:args.cap]
    if len(candidats) > len(lot):
        # AUCUN PLAFOND SILENCIEUX (règle 6).
        print(f"⚠️  {len(candidats) - len(lot)} fiche(s) au-delà de --cap={args.cap} : "
              f"pas relues cette fois. Relancer pour les suivantes.\n")

    if not args.apply:
        print("— DRY-RUN — aucun appel de modèle n'a été fait. Les voici :\n")
        for r in lot:
            corps = (_data(dict(r)).get("article") or {}).get("corps") or ""
            etat = f"WP#{r['wp_post_id_as']}" if r["wp_post_id_as"] else "hors ligne"
            print(f"  [{r['id']:>5}] {etat:<10} {(r['title'] or '')[:56]:<56} "
                  f"{len(corps):>5} car.")
        print(f"\nRelancer avec --apply pour faire relire ces {len(lot)}. Le panel "
              f"interroge plusieurs personas par fiche : c'est l'appel le plus RÉPÉTÉ du "
              f"pipeline, garder --cap bas et regarder la facture avant d'élargir.")
        conn.close()
        return 0

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ANTHROPIC_API_KEY absente — ni dans l'environnement, ni dans "
              f"{ROOT / '.env'}. Le panel ne peut pas tourner.")
        conn.close()
        return 1

    import anthropic
    from scripts.enrich import reader_panel
    # LE MÊME MODÈLE QUE LA CHAÎNE, par le même chemin qu'enrich.py (l.1062) : un
    # rattrapage jugé par un autre modèle produirait des verdicts qu'on ne pourrait pas
    # comparer aux 86 existants.
    from utils import settings as pipeline_settings
    client = anthropic.Anthropic(api_key=api_key, timeout=180.0)
    modele = pipeline_settings.model_eco()

    faits, muets = 0, 0
    for r in lot:
        ev = dict(r)
        data = _data(ev)
        panel = reader_panel({"article": data.get("article") or {}}, ev, client, modele)
        if not panel:
            # {} = aucun persona pour ce territoire, ou l'appel a échoué. On le COMPTE :
            # sans ça, un panel muet ressemblerait trait pour trait à une fiche déjà jugée.
            muets += 1
            continue
        # 'aucune' et pas '' : la relecture a bien eu lieu, aucune révision n'a été
        # demandée au rédacteur — ce script ne réécrit jamais, donc 'appliquée' et
        # 'tentée' ne peuvent pas se produire ici.
        panel.setdefault("revision", "aucune")
        data["reader_panel"] = panel
        conn.execute("UPDATE events_raw SET enrich_data=? WHERE id=?",
                     (json.dumps(data, ensure_ascii=False), ev["id"]))
        conn.commit()
        faits += 1
        print(f"  [{ev['id']:>5}] {panel.get('verdict', '?'):<7} "
              f"moyenne={panel.get('mean')} · {(ev['title'] or '')[:48]}")

    # RECOMPTÉ EN BASE (règle 6), jamais sur la longueur d'une liste.
    ids = [r["id"] for r in lot]
    poses = conn.execute(
        "SELECT COUNT(*) FROM events_raw WHERE enrich_data LIKE '%\"reader_panel\"%' "
        f"AND id IN ({','.join('?' * len(ids))})", ids).fetchone()[0]
    conn.close()

    print(f"\n✅ {faits} verdict(s) écrit(s), {poses} vérifié(s) en base"
          + (f", {muets} panel(s) muet(s) — aucun persona ou appel échoué." if muets
             else "."))
    print("\n⚠️ AUCUN ARTICLE N'A ÉTÉ RÉÉCRIT, et aucun ne le sera par ce script : le "
          "panel rend un verdict, pas une publication.")
    if faits:
        publiees = [r["id"] for r in lot if r["wp_post_id_as"]]
        if publiees:
            print("Pour que ces verdicts apparaissent sur le site :")
            print("  .venv/bin/python -m scripts.publish_batch_as --ids "
                  + " ".join(str(i) for i in publiees) + " --skip-media --delay 2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
