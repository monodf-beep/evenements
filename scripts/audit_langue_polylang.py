#!/usr/bin/env python3
"""Les traductions publiées portent-elles la langue qu'on leur a demandée ?

LECTURE SEULE. Aucun appel LLM, aucune écriture, aucun réseau.

D'OÙ ÇA VIENT (2026-08-17). En réparant la séparation des versants de « À la une », j'ai
regardé comment la langue Polylang est réellement posée, et trouvé ceci :

  · `scripts.translate_events` publie une traduction avec `force_lang` — la langue est
    IMPOSÉE, jamais devinée. C'est le bon chemin ;
  · `scripts.publish_batch_as --update`, lui, republie les mêmes fiches depuis la base
    SANS `force_lang`. `publisher_as._lang` retombe alors sur `detect_lang`, qui devine
    à partir du titre, de la description et — en dernier recours — du TERRITOIRE.

Le texte d'une traduction est bien traduit (titre ET description), donc la devinette
tombe juste la plupart du temps. Mais quand le texte ne tranche pas — titre court, nom
propre, programme sans phrase — c'est le territoire qui décide : « Piemonte » ⇒ italien.
Une traduction FRANÇAISE d'un événement piémontais peut donc être republiée en ITALIEN,
et se retrouver du mauvais côté du sélecteur de langue.

Ce script ne prouve RIEN sur le site : il dit seulement quelles fiches sont exposées à
l'écart. La règle 1 tient toujours — pour savoir ce que WordPress sert, il faut le lui
demander, et la dernière colonne donne l'adresse à ouvrir pour ça.

CE QU'ON EN FAIT. Une ligne ici veut dire : « republier cette fiche pourrait changer sa
langue ». Le geste est alors `translate_events --retranslate <id de l'original>`, qui
repasse par `force_lang`. S'il n'y a aucune ligne, le compteur dit quand même combien de
fiches ont été examinées — un zéro qui ne dit pas son dénominateur ne prouve pas qu'il
n'y a rien à trouver (journal du 2026-08-11).

Usage (VPS) :
    .venv/bin/python -m scripts.audit_langue_polylang
    .venv/bin/python -m scripts.audit_langue_polylang --tout   # passé compris
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.publisher_as import _lang as _lang_publiee
from scripts.audit_substance_published import devant_nous

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


def cote_du_permalien(url: str) -> str:
    """Le versant que WordPress a servi à la publication, lu dans l'adresse — '' si muet.

    Polylang préfixe les adresses de la langue secondaire (`/it/…`). L'adresse enregistrée
    est donc la RÉPONSE de WordPress au moment de la publication : bien plus solide qu'une
    devinette faite depuis la base.

    ⚠️ Mais ce n'est pas une preuve de l'état ACTUEL — c'est un champ de la base, écrit un
    jour donné, et la règle 1 dit exactement ce qu'il vaut. Une republication ultérieure a
    pu déplacer la page sans que cette colonne bouge. D'où le libellé « à la publication »
    partout où cette valeur s'affiche, et l'adresse laissée en clair pour aller voir.
    """
    u = (url or "").strip().lower()
    for lang in ("it", "fr"):
        if f"/{lang}/" in u:
            return lang
    return ""


def url_de_verification(url: str, post_id) -> str:
    """L'adresse REST qui répond VRAIMENT — pas le lien public, qui ment.

    ⚠️ ÉCRIT APRÈS AVOIR ENVOYÉ FRANCK DANS LE MUR (2026-08-17). Ce relevé affichait
    `wp_permalink_as` en disant « ouvrir l'adresse ». Or pour ces deux fiches, l'adresse
    enregistrée est la forme provisoire `…/?post_type=tribe_events&p=2205` — et CLAUDE.md
    documente depuis le 2026-08-02 que cette forme rend 404 pour TOUT `tribe_events`,
    vivant, corbeillé ou supprimé. Franck a donc vu une page « 404 Pagina non trovata »
    qui ne disait rien du tout, et j'avais présenté ça comme « dix secondes qui tranchent,
    règle 1 ». La règle 1 dit exactement le contraire : c'est l'API REST, et elle seule,
    qui sépare les trois états.

    On construit donc l'adresse REST à partir de l'origine du permalien (pas d'appel
    réseau ici, pas de lecture d'environnement : ce script reste en lecture seule) et on
    la donne à la place. `_fields` la rend lisible dans un navigateur : trois valeurs au
    lieu d'un pavé JSON. C'est `link` qu'il faut regarder — le permalien PROPRE, dont le
    préfixe `/it/` ou son absence donne le versant réel.
    """
    origine = ""
    u = (url or "").strip()
    if "//" in u:
        origine = "/".join(u.split("/")[:3])          # https://agendasabauda.eu
    if not origine or not post_id:
        return "—"
    return (f"{origine}/wp-json/wp/v2/tribe_events/{post_id}"
            f"?_fields=link,status,title")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Langue Polylang des traductions. Lecture seule.")
    p.add_argument("--tout", action="store_true",
                   help="Inclure les événements passés (par défaut : seulement ce qui "
                        "est encore devant nous, règle 5).")
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1
    auj = date.today().isoformat()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND translation_of IS NOT NULL "
        "AND COALESCE(translated_lang,'') <> ''")]
    # L'ORIGINAL de chaque traduction : `--retranslate` part de LUI, et il ne peut pas
    # partir d'une fiche que la publication refuse. Sans ça le relevé proposait un geste
    # impossible — vu en vrai sur la fiche 3509, dont l'original 308 est une fiche RADAR
    # non résolue, que `publish_batch_as` écarte à chaque passage.
    originaux = {r["id"]: dict(r) for r in conn.execute(
        "SELECT id, title, statut, wp_post_id_as, source_type FROM events_raw")}
    conn.close()

    examinees = [r for r in rows if args.tout or devant_nous(r, auj)]
    # Le périmètre s'écrit À CÔTÉ du nombre, pas dans le titre d'une section (règle 6).
    perimetre = "toutes dates" if args.tout else "encore devant nous"

    ecarts = []
    for r in examinees:
        voulue = (r.get("translated_lang") or "").strip().lower()
        devinee = _lang_publiee({k: v for k, v in r.items() if k != "force_lang"})
        if devinee != voulue:
            ecarts.append((r, voulue, devinee))

    print("=" * 78)
    print("Langue Polylang des traductions publiées")
    print("=" * 78)
    print(f"Traductions publiées   : {len(rows)}, toutes dates")
    print(f"EXAMINÉES ici          : {len(examinees)} ({perimetre})")
    print(f"Exposées à un écart    : {len(ecarts)}")
    print()

    if not ecarts:
        print(f"Aucun écart sur les {len(examinees)} traduction(s) examinée(s) : une")
        print("republication par `publish_batch_as --update` leur rendrait la même langue")
        print("que celle demandée à la traduction. Rien à faire.")
        return 0

    print("Pour chacune, une republication SANS `force_lang` poserait l'autre langue.")
    print("La colonne « Servie » dit de quel côté WordPress a rangé la page À LA")
    print("PUBLICATION, d'après le préfixe de son adresse. C'est sa réponse à lui, pas")
    print("notre devinette — mais c'est un champ de la base, écrit un jour donné.\n")
    print("⚠️  Pour l'état d'AUJOURD'HUI, ouvrir l'adresse REST de la dernière colonne,")
    print("    JAMAIS le lien public : `?p=<id>` répond 404 pour tout tribe_events, en")
    print("    ligne ou non (CLAUDE.md, règle 1). Regarder `link` dans la réponse — son")
    print("    préfixe /it/, ou son absence, donne le versant réel.\n")
    print("| Fiche | Voulue | Devinée | Servie | Titre | Vérifier (API REST) |")
    print("|---:|---|---|---|---|---|")
    for r, voulue, devinee in ecarts:
        servie = cote_du_permalien(r.get("wp_permalink_as") or "")
        # On ne met en gras QUE ce qui contredit la langue demandée : un tableau où tout
        # crie ne désigne plus rien.
        marque = f"**{servie}**" if servie and servie != voulue else (servie or "—")
        print(f"| {r['id']} | {voulue} | {devinee} | {marque} | "
              f"{(r.get('title') or '')[:34]} | "
              f"{url_de_verification(r.get('wp_permalink_as') or '', r.get('wp_post_id_as'))} |")
    print()

    deja = [(r, v) for r, v, _d in ecarts
            if cote_du_permalien(r.get("wp_permalink_as") or "") not in ("", v)]
    if deja:
        print(f"⚠️  {len(deja)} sur {len(ecarts)} n'est pas un risque À VENIR : l'adresse")
        print("    enregistrée montre que la page était DÉJÀ du mauvais côté. Le sélecteur")
        print("    de langue renvoie donc le lecteur vers une page qu'il ne sait pas lire.")
        print()

    # LE GESTE, ET SEULEMENT QUAND IL EXISTE. `--retranslate` repart de l'ORIGINAL : si
    # celui-ci n'est pas publiable, la commande est un cul-de-sac. Les proposer ensemble
    # ferait une file dont une partie ne mène nulle part — précisément ce que la règle 6
    # interdit.
    faisables, bloques = [], []
    for r, _v, _d in ecarts:
        orig = originaux.get(r.get("translation_of")) or {}
        if orig and int(orig.get("wp_post_id_as") or 0) > 0:
            faisables.append(str(r["translation_of"]))
        else:
            bloques.append((r, orig))
    if faisables:
        print("Le geste, si la page est du mauvais côté du sélecteur de langue :")
        print(f"    .venv/bin/python -m scripts.translate_events --retranslate "
              f"{' '.join(sorted(set(faisables)))} --apply")
        print("(il republie par `force_lang`, donc il IMPOSE la langue au lieu de la deviner.)")
        print()
    for r, orig in bloques:
        print(f"⚠️  Fiche {r['id']} : PAS de geste automatique. Son original "
              f"{r.get('translation_of')} n'est pas en ligne "
              f"(« {(orig.get('title') or '?')[:44]} », statut {orig.get('statut') or '—'}) — "
              f"`--retranslate` partirait d'une fiche que la publication refuse.")
        print("    Une traduction en ligne dont l'original ne l'est pas est un arbitrage,")
        print("    pas une réparation : à trancher à la main.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
