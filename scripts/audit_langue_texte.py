#!/usr/bin/env python3
"""Le TEXTE publié est-il dans la langue de la page qui le porte ?

LECTURE SEULE. Aucun appel LLM, aucune écriture. Lit l'API REST PUBLIQUE de WordPress,
une fiche à la fois (règle 2 : une liste REST ne prouve rien, un post se lit par son
numéro).

D'OÙ ÇA VIENT (23/09/2026, au soir). Sur les fiches des Journées du patrimoine, cinq
paires avaient leurs deux textes INVERSÉS — l'italien sur la page française, le français
sur la page italienne (Colline Torinesi, Biella, Pizza Show, atelier rap Kento) — plus
Montrottier, texte français sous étiquette italienne. Toutes retouchées à la main dans
une session Cowork le matin même, donc GELÉES : aucun cron ne pouvait les réparer, et
aucun ne les voyait.

`audit_langue_polylang` ne pouvait pas les voir non plus, et ce n'est pas un défaut : il
compare la langue DEMANDÉE en base au VERSANT où WordPress a rangé la page. Ici les deux
concordaient. Ce qui était faux, c'est le texte lui-même — qu'aucun script ne relisait
une fois publié. Deux audits, donc, pour deux questions différentes (et non deux
détecteurs pour la même chose, journal du 08/09) : « la page est-elle du bon côté ? »
et « ce qu'elle dit est-il dans la langue de son côté ? ».

CE QU'ON EN FAIT. Si la fiche n'est pas gelée, `translate_events --retranslate <original>`
la réécrit. Si elle l'est (retouche humaine), le texte est à remettre à sa place — le
23/09, ce fut un échange des textes entre les deux jumelles, fait à la main.

Usage (VPS) :
    .venv/bin/python -m scripts.audit_langue_texte           # relevé complet
    .venv/bin/python -m scripts.audit_langue_texte --slack   # + une ligne au bilan
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.lang import langue_du_texte, cote_du_permalien  # noqa: E402

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
UA = {"User-Agent": "Mozilla/5.0 (compatible; CulturaSabaudaAudit/1.0)"}


def texte_brut(rendu_html: str) -> str:
    """Le texte lisible d'un contenu WordPress rendu, sans balises ni pied « En savoir plus »
    (liens automatiques, identiques dans les deux langues, qui brouilleraient le compte)."""
    t = html.unescape(re.sub(r"<[^>]+>", " ", rendu_html or ""))
    t = re.split(r"\bEn savoir plus\b|\bScopri di più\b", t)[0]
    return re.sub(r"\s+", " ", t).strip()


def verdict(page: dict) -> tuple[str, str, str]:
    """(versant de la page, langue du texte, 'ecart' | 'ok' | 'muet') pour une réponse REST
    `{link, content: {rendered}}`. Le versant se lit dans l'adresse (`/it/` ou rien) : c'est
    la réponse de WordPress, pas une devinette."""
    versant = cote_du_permalien(page.get("link") or "")
    langue = langue_du_texte(texte_brut((page.get("content") or {}).get("rendered") or ""))
    if not versant or not langue:
        return versant, langue, "muet"
    return versant, langue, ("ok" if versant == langue else "ecart")


def lire(wp_url: str, post_id: int):
    import requests
    try:
        r = requests.get(f"{wp_url}/wp-json/wp/v2/tribe_events/{post_id}",
                         params={"_fields": "id,link,content,title"}, headers=UA, timeout=20)
    except requests.RequestException:
        return None
    return r.json() if r.status_code == 200 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Langue du texte publié vs versant de la page.")
    ap.add_argument("--slack", action="store_true", help="une ligne au bilan quotidien")
    ap.add_argument("--delai", type=float, default=0.2)
    args = ap.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    wp_url = os.getenv("WP_AS_URL", "https://agendasabauda.eu").rstrip("/")
    auj = date.today().isoformat()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    # Règle 5 : ce qui est encore devant nous. Sans date = donnée manquante, gardée.
    ids = [r[0] for r in conn.execute(
        "SELECT DISTINCT wp_post_id_as FROM events_raw WHERE COALESCE(wp_post_id_as,0)>0 "
        "AND duplicate_of IS NULL AND statut NOT IN ('rejected','merged') "
        "AND (COALESCE(date_event_end, date_event_start, '') = '' "
        "     OR substr(COALESCE(date_event_end, date_event_start),1,10) >= ?)", (auj,))]
    conn.close()

    ecarts, muets, illisibles = [], 0, 0
    for pid in ids:
        page = lire(wp_url, pid)
        time.sleep(args.delai)
        if not page:
            illisibles += 1          # corbeille, brouillon, réseau : pas un écart, compté
            continue
        versant, langue, v = verdict(page)
        if v == "muet":
            muets += 1
        elif v == "ecart":
            titre = html.unescape(((page.get("title") or {}).get("rendered") or ""))[:60]
            ecarts.append((pid, versant, langue, titre, page.get("link") or ""))

    lues = len(ids) - illisibles
    perimetre = f"fiches en base encore devant nous, lues sur le site le {auj}"
    print(f"Examinées : {len(ids)} ({perimetre}) — lues : {lues}, illisibles : {illisibles}, "
          f"sans verdict (texte trop court ou mêlé) : {muets}")
    print(f"Texte dans l'autre langue que sa page : {len(ecarts)}")
    for pid, versant, langue, titre, link in ecarts:
        print(f"  WP#{pid} page {versant}, texte {langue} — {titre}\n      {link}")
    if args.slack:
        from utils import slack
        tete = "⚠️" if ecarts else "✅"
        ligne = (f"{tete} *Textes dans la mauvaise langue* : {len(ecarts)} sur {lues} page(s) "
                 f"lue(s) ({muets} sans verdict, {illisibles} illisible(s) ; à venir).")
        if ecarts:
            ligne += ("\n" + ", ".join(f"WP#{e[0]}" for e in ecarts[:12])
                      + (f" … (+{len(ecarts) - 12})" if len(ecarts) > 12 else "")
                      + "\nRelevé : `.venv/bin/python -m scripts.audit_langue_texte`")
        slack.notify(ligne)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
