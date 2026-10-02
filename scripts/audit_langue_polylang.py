#!/usr/bin/env python3
"""Les traductions publiées sont-elles du côté du site qu'on leur a demandé ?

LECTURE SEULE. Aucun appel LLM, aucune écriture, aucun réseau.

D'OÙ ÇA VIENT (2026-08-17). `scripts.translate_events` publie une traduction avec
`force_lang` — la langue est IMPOSÉE. Mais `scripts.publish_batch_as --update` republiait
les mêmes fiches SANS `force_lang`, et `publisher_as._lang` retombait sur `detect_lang`,
qui DEVINE. Ce script mesurait alors le risque : « republier cette fiche pourrait changer
sa langue ».

CE QUI S'EST PASSÉ QUAND MÊME (2026-09-17). Le risque n'était pas un risque : la page
d'accueil FRANÇAISE affichait « Open Factories 2026: le fabbriche di Torino aprono le
porte » à côté de sa jumelle française. La traduction (WP#9209) avait été créée `it` le
15/09, puis republiée le 16/09 par seo_batch : le détecteur a lu « le » comme du français
(c'est aussi l'article italien pluriel), Polylang a changé l'étiquette ET défait le lien
de traduction. Deux jumelles sur 49. Un audit qui mesure un risque sans jamais tourner ne
protège de rien : celui-ci n'était dans aucun cron.

⚠️ RESTÉ VRAI QUATRE JOURS DE PLUS. Le 2026-09-21, Franck envoie une capture du hub
Vallée d'Aoste : « problème de duplication ». Ce que ce script aurait dit tout seul :
32 traductions du mauvais versant sur 85 encore devant nous — dont celles qui faisaient
deux cartes françaises côte à côte. Il est planifié depuis ce jour-là (crontab.txt,
9h55, juste après les doublons), et `--slack` en pose UNE ligne dans le bilan quotidien,
même à zéro, avec le nombre d'examinées à côté.

DEPUIS, `publisher_as._lang` lit `translated_lang` avant de deviner quoi que ce soit — le
risque est fermé par construction, et ce script ne le simule plus. Il mesure autre chose,
qui aurait montré l'incident dès le 16/09 : le VERSANT où WordPress a rangé la page à sa
dernière publication, lu dans le préfixe de `wp_permalink_as` (`/it/…` ou rien), comparé
à la langue demandée. Ce n'est pas l'état du site aujourd'hui (règle 1 : seule l'API REST
le dit, l'adresse est donnée pour ça), c'est la dernière réponse de WordPress — et un
écart là veut dire qu'un lecteur du mauvais versant est déjà tombé dessus.

Il garde un témoin de code : si `_lang` rendait une autre langue que `translated_lang`
pour une traduction, ce serait la régression du 17/09 qui revient, et il le crie.

CE QU'ON EN FAIT. Le geste est `translate_events --retranslate <id de l'original>`, qui
repasse par `force_lang` ET relie la paire (le lien Polylang est perdu avec l'étiquette).
S'il n'y a aucune ligne, le compteur dit quand même combien de fiches ont été examinées
(journal du 2026-08-11).

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
# `cote_du_permalien` est née ici le 17/08 ; elle vit dans utils.lang depuis le
# 21/09, parce que le dédoublonnage en a besoin aussi. Même définition, un seul
# endroit.
from utils.lang import cote_du_permalien  # noqa: F401

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))


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
    p.add_argument("--slack", action="store_true",
                   help="Poster UNE ligne dans le bilan quotidien (via la boîte du "
                        "digest). Le relevé complet reste à l'écran.")
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

    ecarts, regressions, muettes = [], [], []
    for r in examinees:
        voulue = (r.get("translated_lang") or "").strip().lower()
        # Témoin de code : depuis le 17/09, _lang LIT translated_lang. S'il rend autre
        # chose, la republication redeviendrait une devinette — on le dit en premier.
        devinee = _lang_publiee({k: v for k, v in r.items() if k != "force_lang"})
        if devinee != voulue:
            regressions.append((r, voulue, devinee))
        servie = cote_du_permalien(r.get("wp_permalink_as") or "")
        if not servie:
            muettes.append(r)
        elif servie != voulue:
            ecarts.append((r, voulue, servie))

    print("=" * 78)
    print("Langue Polylang des traductions publiées")
    print("=" * 78)
    print(f"Traductions publiées   : {len(rows)}, toutes dates")
    print(f"EXAMINÉES ici          : {len(examinees)} ({perimetre})")
    print(f"Du mauvais versant     : {len(ecarts)} (à la dernière publication, d'après l'adresse)")
    print(f"Adresse muette         : {len(muettes)} (forme provisoire, versant inconnu)")
    print()

    if regressions:
        print(f"🔴 RÉGRESSION DE CODE : pour {len(regressions)} traduction(s), publisher_as._lang")
        print("   rend une autre langue que `translated_lang`. Une republication redeviendrait")
        print("   une devinette (incident du 17/09/2026). Corriger _lang AVANT tout geste.")
        for r, voulue, devinee in regressions[:10]:
            print(f"   fiche {r['id']} : voulue {voulue}, _lang rend {devinee} — {(r.get('title') or '')[:50]}")
        print()

    # ══ LE BILAN QUOTIDIEN — UNE LIGNE, JAMAIS LE TABLEAU ════════════════════════════
    #
    # Branché le 2026-09-21, sur « oui » de Franck. Ce script portait depuis le 17/09, dans
    # sa propre docstring, la phrase « un audit qui mesure un risque sans jamais tourner ne
    # protège de rien » — et il n'était dans aucun cron. Mesuré ce jour-là : 32 traductions
    # servies du mauvais versant, découvertes parce que Franck a envoyé une capture du hub.
    #
    # UNE LIGNE, et pas le tableau : le digest existe parce que sept messages par jour ne
    # se lisent plus (slack_digest, 13/08). Le relevé complet reste à l'écran, à une
    # commande — et la ligne la nomme.
    #
    # ET ELLE PART MÊME À ZÉRO, avec le nombre d'examinées à côté : un « 0 » sur une file
    # vide et un « 0 » sur une requête cassée ont exactement la même tête (journal du
    # 11/08). C'est pour ça que le message porte les deux nombres et son périmètre.
    if args.slack:
        from utils import slack
        tete = "⚠️" if ecarts else "✅"
        lignes = [f"{tete} *Traductions du mauvais versant* : {len(ecarts)} sur "
                  f"{len(examinees)} examinée(s) ({perimetre})."]
        if ecarts:
            lignes.append("Leurs deux pages sont du même côté du site : le lecteur du hub "
                          "les voit comme des doublons, et le sélecteur de langue tombe "
                          "sur une page qu'il ne sait pas lire.")
            lignes.append("Relevé et geste : "
                          "`.venv/bin/python -m scripts.audit_langue_polylang`")
        if regressions:
            lignes.append(f"🔴 {len(regressions)} régression(s) de code : `_lang` rend une "
                          f"autre langue que `translated_lang`.")
        slack.notify("\n".join(lignes))

    if not ecarts:
        print(f"Aucun écart sur les {len(examinees)} traduction(s) examinée(s) : à leur")
        print("dernière publication, WordPress les a toutes rangées du versant demandé.")
        print("Rien à faire.")
        return 1 if regressions else 0

    print("Pour chacune, l'adresse enregistrée à la dernière publication est du MAUVAIS")
    print("versant : un lecteur du sélecteur de langue tombe sur une page qu'il ne sait")
    print("pas lire. C'est la réponse de WordPress ce jour-là, pas une devinette.\n")
    print("⚠️  Pour l'état d'AUJOURD'HUI, ouvrir l'adresse REST de la dernière colonne,")
    print("    JAMAIS le lien public : `?p=<id>` répond 404 pour tout tribe_events, en")
    print("    ligne ou non (CLAUDE.md, règle 1). Regarder `link` dans la réponse — son")
    print("    préfixe /it/, ou son absence, donne le versant réel.\n")
    print("| Fiche | Voulue | Servie | Titre | Vérifier (API REST) |")
    print("|---:|---|---|---|---|")
    for r, voulue, servie in ecarts:
        print(f"| {r['id']} | {voulue} | **{servie}** | "
              f"{(r.get('title') or '')[:34]} | "
              f"{url_de_verification(r.get('wp_permalink_as') or '', r.get('wp_post_id_as'))} |")
    print()

    # LE GESTE, ET SEULEMENT QUAND IL EXISTE. `--retranslate` repart de l'ORIGINAL : si
    # celui-ci n'est pas publiable, la commande est un cul-de-sac. Les proposer ensemble
    # ferait une file dont une partie ne mène nulle part — précisément ce que la règle 6
    # interdit.
    faisables, bloques = [], []
    for r, _v, _s in ecarts:
        orig = originaux.get(r.get("translation_of")) or {}
        if orig and int(orig.get("wp_post_id_as") or 0) > 0:
            faisables.append(str(r["translation_of"]))
        else:
            bloques.append((r, orig))
    if faisables:
        print("Le geste :")
        print(f"    .venv/bin/python -m scripts.translate_events --retranslate "
              f"{' '.join(sorted(set(faisables)))} --apply")
        print("(il republie par `force_lang`, donc il IMPOSE la langue, et il RELIE la paire —")
        print(" le lien Polylang est perdu en même temps que l'étiquette.)")
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
