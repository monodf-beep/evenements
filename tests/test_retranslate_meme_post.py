#!/usr/bin/env python3
"""Fixture : `--retranslate` refuse un jumeau qui porte le MÊME post que son original.

⚠️ BASE JETABLE — jamais data/events.db. Aucun réseau, aucun LLM : `_retranslate_one`
ET `postes_geles` sont remplacées par des bouchons, on n'éprouve ici que la SÉLECTION.

CE BOUCHON-LÀ A ÉTÉ AJOUTÉ LE 2026-09-29, et il répare un défaut de MA fixture. Le 28/09,
une session a posé un second garde-fou dans `_retranslate` : ne jamais re-traduire une
fiche dont le SITE dit le texte gelé (`postes_geles()`, route `cs/v1/gel`). Excellent
garde-fou — mais ma fixture emploie de VRAIS numéros de production, et sur le VPS WP#8132
est gelée. La jumelle « saine » se faisait donc écarter, et la fixture passait au rouge
LÀ-BAS en restant verte ici, où la route ne répond pas. Une fixture qui dépend de l'état
du site n'est pas une fixture : elle mesure la production, pas le code.

On garde les numéros réels — ils portent l'incident — et on coupe la dépendance.

D'OÙ ÇA VIENT (2026-09-21, le soir). Le relevé de `repair_lien_polylang` a sorti une
ligne à deux fois le même numéro :

    [2507→3491] WP#2190→WP#2190

La fiche 3491 est enregistrée comme la traduction de 2507 et porte le `wp_post_id_as` de
2507 — une ligne abîmée en base, pas une traduction. La vraie jumelle italienne de 2507
existe par ailleurs : 5223 → WP#8132.

CE QUE ÇA AURAIT FAIT. `_retranslate` prend TOUS les jumeaux d'un original
(`WHERE translation_of IN (...)`) et `_retranslate_one` réécrit chacun EN PLACE, à son
`wp_post_id_as`. Retraduire 2507 aurait donc réécrit WP#2190 — la page FRANÇAISE de
l'original — en italien. Et depuis ce soir, `repair_lien_polylang --retraduire` lance
cette commande TOUTE SEULE depuis le cron du dimanche : personne n'aurait rien demandé.

LE GARDE-FOU VIT DANS `_retranslate`, et pas seulement chez l'appelant, parce que
`audit_langue_polylang` IMPRIME cette commande pour qu'un humain la tape. Un garde-fou
posé chez un appelant protège cet appelant-là, pas la fonction.

CE QUE LA FIXTURE SURVEILLE :
  1. le jumeau au même post est REFUSÉ, et l'original n'est pas réécrit ;
  2. ⚠️ le cas qui doit PASSER, pris dans la même famille : la vraie jumelle du MÊME
     original, elle, est bien retraduite. Un refus trop large ferait un cul-de-sac de
     plus — on aurait protégé la page en cessant de réparer ;
  3. le garde-fou du GEL (28/09) écarte aussi une jumelle que le site a gelée ;
  4. et une route MUETTE (None) ne bloque rien — « on ne sait pas » n'est pas « rien
     n'est gelé », et une route en panne ne doit pas arrêter toutes les reprises.

Lancer : .venv/bin/python -m tests.test_retranslate_meme_post
"""
import os
import sqlite3
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Ce conteneur de session n'a pas python-dotenv (le VPS, lui, l'a) ; la fixture ne lit
# aucun `.env`.
if "dotenv" not in sys.modules:
    try:
        import dotenv  # noqa: F401
    except ModuleNotFoundError:
        faux = types.ModuleType("dotenv")
        faux.load_dotenv = lambda *a, **k: False
        sys.modules["dotenv"] = faux

tmp = Path(tempfile.mkdtemp()) / "fixture.db"
os.environ["DB_PATH"] = str(tmp)

from scripts.scraper_events import init_db   # noqa: E402
import scripts.translate_events as te        # noqa: E402

te.DB_PATH = tmp

echecs = 0


def _check(label, cond, detail=""):
    global echecs
    if cond:
        print(f"OK    {label}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} {detail}")


# (id, translation_of, wp_post_id_as, url_source) — les numéros RÉELS du cas de
# production. `url_source` est UNIQUE en base : deux jumeaux du même original ne peuvent
# pas porter le même marqueur, et c'est bien ce que montre la production — l'un des deux
# est une ligne d'une autre nature.
FICHES = [
    (2507, None, 2190, "https://source/2507"),           # l'original français, page WP#2190
    (3491, 2507, 2190, "translated:2507:fr"),            # ⚠️ ligne abîmée : porte la page de 2507
    (5223, 2507, 8132, "translated:2507:it"),            # la VRAIE jumelle italienne
]
conn = sqlite3.connect(tmp)
init_db(conn)
for eid, orig, wp, src in FICHES:
    conn.execute(
        "INSERT INTO events_raw (id, title, description, url_source, wp_post_id_as, "
        "statut, translation_of, translated_lang, duplicate_of) "
        "VALUES (?,?,?,?,?,?,?,?,NULL)",
        (eid, f"Terra Madre {eid}", "Description.", src,
         wp, "published_sub", orig, "it" if orig else None))
conn.commit()
conn.close()

# Mouchards : on n'éprouve QUE la sélection, donc rien ne doit partir vers le réseau.
vus = []
te._retranslate_one = lambda tw, args, client, voix: (vus.append(tw["id"]) or "done")


class _Args:
    ids = [2507]
    apply = True
    model = "x"
    retranslate = True


def _passage(geles):
    """Rejoue la sélection avec une réponse donnée de la route `cs/v1/gel`."""
    vus.clear()
    te.postes_geles = lambda: geles
    te._retranslate(_Args(), client=object(), voix="")
    return list(vus)


print("──── qui part en retraduction, et qui reste dehors (rien de gelé) ────")
vus1 = _passage(set())
_check("⚠️ le jumeau qui porte le MÊME post que son original est REFUSÉ",
       3491 not in vus1, vus1)
_check("⚠️ la VRAIE jumelle du même original, elle, est bien retraduite "
       "(le cas qui doit passer)", 5223 in vus1, vus1)
_check("   et l'original lui-même n'est jamais traité comme un jumeau",
       2507 not in vus1, vus1)
_check("   exactement une fiche retraduite, pas deux", len(vus1) == 1, vus1)

print("\n──── et si le SITE dit que la jumelle est gelée (garde-fou du 28/09) ────")
# Le cas exact rencontré sur le VPS le 29/09 : WP#8132 gelée. Les deux garde-fous se
# cumulent, chacun pour son motif, et il ne reste personne à re-traduire — c'est voulu.
vus2 = _passage({8132})
_check("la jumelle gelée est écartée à son tour", vus2 == [], vus2)

print("\n──── et si la route ne répond pas (le site est muet) ────")
# `postes_geles()` rend None, et surtout pas set() : « on ne sait pas » n'est pas
# « rien n'est gelé ». Le garde-fou doit alors continuer sans bloquer — sinon une route
# muette gèlerait toutes les reprises du dépôt sans que personne le sache.
vus3 = _passage(None)
_check("un site muet ne bloque pas la reprise, il la laisse passer", vus3 == [5223], vus3)
_check("   et le garde-fou du même post tient quand même", 3491 not in vus3, vus3)

print("\n" + ("TOUT PASSE" if not echecs else f"{echecs} ÉCHEC(S)"))
raise SystemExit(1 if echecs else 0)
