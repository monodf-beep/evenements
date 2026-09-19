#!/usr/bin/env python3
"""Ce qu'un visiteur voit et qui ne devrait pas y être — daté, illustré, mesuré.

LECTURE SEULE. Aucun réseau, aucun appel LLM, aucune écriture.

D'OÙ ÇA VIENT. Capture d'écran de Franck, 2026-08-18, 22h18, depuis son téléphone :
« j'espère que c'est une blague cette image ». Trois défauts sur une seule vue de la page
d'accueil :

  1. « Musicanti Estivo: Giua », daté **09/07** — six semaines DANS LE PASSÉ ;
  2. son visuel est le bandeau de notre PROPRE observatoire économique, pas une image de
     l'événement ;
  3. la carte suivante affiche un programme de saison en corps 6, illisible en vignette.

Ce script mesure les deux premiers, qui se lisent en base. Le troisième est un jugement
sur l'image elle-même : il demande de la REGARDER, et `scripts/image_audit.py` est fait
pour ça.

⚠️ IL NE PROUVE PAS CE QUE LE SITE AFFICHE (règle 1). Il lit la base : `wp_post_id_as`
renseigné survit à une mise à la corbeille. Ce qu'il rend, ce sont des CANDIDATS —
« voici les fiches qui, si elles sont en ligne, produisent ce qu'on a vu ». La preuve
reste une interrogation de WordPress.

Usage :
    .venv/bin/python -m scripts.audit_home_visible
    .venv/bin/python -m scripts.audit_home_visible --slack    # verdict dans la boîte du jour
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.completeness import is_recurring

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# Hôtes de PLATEFORMES D'EMAILING. Une image servie depuis là vient d'une newsletter, et
# la première image d'une newsletter est son bandeau — jamais une photo de l'événement.
# `utils.sources.is_logo_image` ne peut pas les voir : elle juge sur le NOM DE FICHIER, et
# ces plateformes servent des identifiants opaques
# (mcusercontent.com/…/57e13b2d-646c-58c8-5a42-14e2ebd0e8ae.jpg, relevé le 2026-08-17).
_HOTES_EMAILING = (
    "mcusercontent.com", "mailchimp", "list-manage.com",      # Mailchimp
    "musvc", "sendinblue", "brevo.com",                       # Sendinblue / Brevo
    "sendgrid", "cdn-images.mailchimp.com", "campaign-archive",
    "acumbamail", "mailerlite", "hubspotusercontent",
)


def image_de_newsletter(url: str) -> str:
    """L'hôte d'emailing reconnu dans l'URL, "" sinon. Le NOM de l'hôte, pas un booléen —
    un relevé qui dit « suspecte » sans dire pourquoi ne se vérifie pas."""
    hote = (urlparse((url or "").lower()).netloc or "")
    for h in _HOTES_EMAILING:
        if h in hote:
            return h
    return ""


def _jour(v):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v or ""))
    return date.fromisoformat(m.group(1)) if m else None


def evenement_passe(ev: dict, auj: date) -> bool:
    """Vrai si l'événement est TERMINÉ — jamais « sans date » (règle 5).

    Une fiche sans date n'est PAS un événement passé : c'est une donnée manquante, que
    `dates.py` remplira peut-être demain. Et un récurrent n'a pas de date unique, donc
    n'est jamais passé.
    """
    if is_recurring(ev):
        return False
    fin = _jour(ev.get("date_event_end")) or _jour(ev.get("date_event_start"))
    return fin is not None and fin < auj


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fiches publiées visiblement fautives. Lecture seule.")
    p.add_argument("--slack", action="store_true",
                   help="Dépose le verdict dans la boîte du jour (digest).")
    p.add_argument("--exemples", type=int, default=12)
    args = p.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}\n(lancer ce script sur le VPS.)")
        return 1
    auj = date.today()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM events_raw WHERE COALESCE(wp_post_id_as,0) > 0 "
        "AND duplicate_of IS NULL AND wp_deleted_at IS NULL")]
    conn.close()

    passes = [e for e in rows if evenement_passe(e, auj)]
    bandeaux = [(e, image_de_newsletter(e.get("url_image") or "")) for e in rows]
    bandeaux = [(e, h) for e, h in bandeaux if h]

    print("=" * 78)
    print(f"Ce qu'un visiteur peut voir et qui ne devrait pas y être — {auj.isoformat()}")
    print("=" * 78)
    print(f"Fiches liées à un post WordPress : {len(rows)}")
    print(f"…dont l'événement est TERMINÉ    : {len(passes)}")
    print(f"…dont l'image vient d'un envoi   : {len(bandeaux)}")
    print()
    print("⚠️ Ce relevé lit la BASE. Un `wp_post_id_as` renseigné survit à une mise à la")
    print("   corbeille : ce sont des CANDIDATS, pas une preuve de ce que le site affiche.")
    print()

    print("## Événements TERMINÉS encore liés à un post\n")
    if not passes:
        print(f"Aucun sur les {len(rows)} fiches examinées. Les sans-date et les récurrents")
        print("ne comptent pas comme passés (règle 5) — ce zéro ne les cache pas, il les")
        print("écarte du calcul, ce qui n'est pas la même chose.\n")
    else:
        print("Chacun est soit à dépublier, soit porteur d'une date fausse. Les deux se")
        print("distinguent en ouvrant la fiche : si la date affichée ne correspond pas à")
        print("l'événement réel, c'est la DATE qu'il faut corriger, pas la page qu'il faut")
        print("retirer.\n")
        for e in sorted(passes, key=lambda x: str(x.get("date_event_end") or ""))[:args.exemples]:
            print(f"- WP#{e['wp_post_id_as']:<6} fin={str(e.get('date_event_end') or '—')[:10]} "
                  f"· {(e.get('title') or '')[:56]}")
        if len(passes) > args.exemples:
            print(f"- …et {len(passes) - args.exemples} autre(s).")
        print()

    print("## Images servies depuis une plateforme d'emailing\n")
    if not bandeaux:
        print(f"Aucune sur les {len(rows)} fiches examinées.\n")
    else:
        print("La première image d'une newsletter est son BANDEAU. `is_logo_image` ne peut")
        print("pas les voir : elle juge sur le nom de fichier, et ces plateformes servent")
        print("des identifiants opaques.\n")
        for e, h in sorted(bandeaux, key=lambda c: c[1])[:args.exemples]:
            print(f"- WP#{e['wp_post_id_as']:<6} [{h}] {(e.get('title') or '')[:52]}")
        if len(bandeaux) > args.exemples:
            print(f"- …et {len(bandeaux) - args.exemples} autre(s).")
        print()

    if args.slack:
        from utils import slack
        lignes = [f"🔎 *Ce qu'un visiteur peut voir* — sur {len(rows)} fiches liées à un post :"]
        lignes.append(f"{'🔴' if passes else '·'} {len(passes)} événement(s) TERMINÉ(s) "
                      f"encore liés à une page")
        lignes.append(f"{'🔴' if bandeaux else '·'} {len(bandeaux)} image(s) venant d'une "
                      f"plateforme d'emailing (bandeau de newsletter)")
        for e in sorted(passes, key=lambda x: str(x.get("date_event_end") or ""))[:3]:
            lignes.append(f"   · WP#{e['wp_post_id_as']} fin "
                          f"{str(e.get('date_event_end') or '—')[:10]} — "
                          f"{(e.get('title') or '')[:40]}")
        lignes.append("_Lu en base : ce sont des candidats, pas une preuve de ce que le "
                      "site affiche._")
        slack.notify("\n".join(lignes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
