#!/usr/bin/env python3
"""Fixture de `lieu_depuis_libelles` / `venue_from_page` (scripts/venues.py, 2026-09-08).

MESURÉ le 2026-09-08 : 19 fiches marquées `venue_source='novenue'` en production (pages
municipales sans JSON-LD `location`) écrivent pourtant le lieu, sous un libellé « Dove /
Luogo / Lieu » ou une icône d'épingle. `docs/CE_QUE_DISENT_LES_SOURCES_OFFICIELLES.md`
§7 détaille la mesure par site.

Deux des extraits ci-dessous (`BCT_EXTRAIT`, `BIELLA_SOMMAIRE` + `BIELLA_LUOGO`) sont des
FRAGMENTS RÉELS téléchargés depuis bct.comune.torino.it et comune.biella.it le 08/09 —
pas des synthèses. `BIELLA_SOMMAIRE` est le premier « Luogo » de la page Biella (un lien
de sommaire vers l'ancre #luogo, PAS le champ) : c'est le piège n°2 documenté dans
scripts/venues.py, reproduit tel quel.

Usage : .venv/bin/python -m tests.test_venues_libelles
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.venues import venue_from_page, lieu_depuis_libelles  # noqa: E402
from utils.lieux import ville_du_domaine  # noqa: E402
from tests._venues_reels import BCT_EXTRAIT, BIELLA_SOMMAIRE, BIELLA_LUOGO  # noqa: E402

echecs = 0


def verifier(nom: str, condition: bool, detail: str = "") -> None:
    global echecs
    if condition:
        print(f"OK    {nom}")
    else:
        echecs += 1
        print(f"ÉCHEC {nom}" + (f" — {detail}" if detail else ""))


# ──────────────────────────────────────────────────────────────────────────
# 1. RÉEL — bct.comune.torino.it, « Tutti in coro », libellé « Dove » seul dans
#    sa balise, valeur dans le bloc suivant (<a>don Lorenzo Milani</a>).
# ──────────────────────────────────────────────────────────────────────────
lieu, adresse = lieu_depuis_libelles(BCT_EXTRAIT)
verifier("bct.comune.torino.it (RÉEL) : lieu extrait du libellé « Dove »",
         lieu == "don Lorenzo Milani", f"obtenu {lieu!r}")

lieu2, ville2, src2 = venue_from_page(BCT_EXTRAIT, url="https://bct.comune.torino.it/eventi-attivita/tutti-in-coro-8")
verifier("bct.comune.torino.it (RÉEL) : ville tirée du DOMAINE (aucune commune dans le lieu/adresse)",
         (lieu2, ville2, src2) == ("don Lorenzo Milani", "Torino", "page_libelle"),
         f"obtenu {(lieu2, ville2, src2)!r}")

# ──────────────────────────────────────────────────────────────────────────
# 2. RÉEL — comune.biella.it, « Musica in Piazza », PIÈGE DU SOMMAIRE : le
#    PREMIER « Luogo » de la page est un lien d'ancre vers la section, pas le
#    champ. Seul le second (BIELLA_LUOGO, section réelle) doit être retenu.
# ──────────────────────────────────────────────────────────────────────────
lieu_sommaire, _ = lieu_depuis_libelles(BIELLA_SOMMAIRE)
verifier("comune.biella.it (RÉEL) : le « Luogo » du sommaire seul ne rend RIEN "
         "(pas de bloc-valeur plausible juste après)",
         lieu_sommaire == "", f"obtenu {lieu_sommaire!r}")

lieu3, ville3, src3 = venue_from_page(BIELLA_LUOGO, url="https://comune.biella.it/eventi/musica-in-piazza-2/")
verifier("comune.biella.it (RÉEL) : la section « Luogo » réelle rend « Piazza Battistero »",
         lieu3 == "Piazza Battistero", f"obtenu {lieu3!r}")
verifier("comune.biella.it (RÉEL) : ville tirée du domaine « comune.biella.it » → Biella",
         ville3 == "Biella", f"obtenu {ville3!r}")

# La page COMPLÈTE (sommaire + vraie section, dans l'ordre du document) : le
# sommaire ne doit pas faire dérailler la vraie section qui le suit.
page_complete = BIELLA_SOMMAIRE + BIELLA_LUOGO
lieu4, ville4, _ = venue_from_page(page_complete, url="https://comune.biella.it/eventi/musica-in-piazza-2/")
verifier("comune.biella.it (RÉEL, page complète sommaire+section) : le sommaire n'aveugle "
         "pas l'extraction, la vraie valeur passe",
         lieu4 == "Piazza Battistero", f"obtenu {lieu4!r}")

# ──────────────────────────────────────────────────────────────────────────
# 3. SYNTHÉTIQUE — villefranche-sur-mer.fr (Elementor) : le libellé est une
#    ICÔNE d'épingle (<i class="fas fa-map-marker-alt">), pas un mot.
# ──────────────────────────────────────────────────────────────────────────
elementor = (
    '<div class="elementor-icon"><i class="fas fa-map-marker-alt" aria-hidden="true"></i></div>'
    '<div class="elementor-widget-container">Promenade de l’Octroi</div>'
    '<div class="elementor-widget-container">Quand : 12 septembre 2026</div>'
)
lieu5, ville5, src5 = venue_from_page(elementor, url="https://www.villefranche-sur-mer.fr/evenement/x")
verifier("villefranche-sur-mer.fr (synthétique, épingle Elementor) : lieu extrait",
         lieu5 == "Promenade de l’Octroi", f"obtenu {lieu5!r}")

# ──────────────────────────────────────────────────────────────────────────
# 4. PIÈGE — « Sede » qui désigne le SIÈGE de l'organisateur, dans le pied de
#    page, jamais accepté comme lieu de l'événement (torinoclick.it, en-tête
#    de phrase dans un paragraphe de footer).
# ──────────────────────────────────────────────────────────────────────────
footer_sede = (
    '<article><h1>Un article de presse quelconque</h1><p>Du texte, du texte.</p></article>'
    '<footer><p>Sede: piazza Palazzo di Città 1 – Torino</p>'
    '<p>Redazione: redazione@example.it</p></footer>'
)
lieu6, _ = lieu_depuis_libelles(footer_sede)
verifier("footer retiré + « Sede: » en tête de phrase refusé (siège de l'agence, pas "
         "un lieu d'événement) : rien n'est extrait",
         lieu6 == "", f"obtenu {lieu6!r}")

# ──────────────────────────────────────────────────────────────────────────
# 5. CAS FRONTIÈRE QUI DOIT PASSER — « Sede dell'evento », en tête de balise,
#    HORS footer : c'est un libellé légitime (liste explicite), pas un siège
#    social. Si ce cas est rejeté, la règle du footer est devenue trop large.
# ──────────────────────────────────────────────────────────────────────────
sede_evento = '<h3>Sede dell’evento</h3><p>Castello di Rivoli</p>'
lieu7, _ = lieu_depuis_libelles(sede_evento)
verifier("« Sede dell'evento » (frontière, hors footer) : accepté, ce n'est pas un "
         "siège social mais le lieu de l'événement",
         lieu7 == "Castello di Rivoli", f"obtenu {lieu7!r}")

# ──────────────────────────────────────────────────────────────────────────
# 6. Une commune dans l'ADRESSE prime sur le domaine — Casale Monferrato
#    annonçant un événement à Venaria (cas réel mentionné dans le code).
# ──────────────────────────────────────────────────────────────────────────
casale_venaria = (
    '<h2>Luogo</h2><div><a>Reggia di Venaria</a></div>'
    '<div>Piazza della Repubblica, 10078 Venaria Reale (TO)</div>'
)
lieu8, ville8, _ = venue_from_page(casale_venaria, url="https://comune.casale-monferrato.al.it/eventi/x")
verifier("comune.casale-monferrato.al.it annonçant un événement à Venaria : la ville "
         "vient de l'ADRESSE (Venaria), pas du domaine (Casale)",
         ville8 == "Venaria Reale", f"obtenu {(lieu8, ville8)!r}")

# ──────────────────────────────────────────────────────────────────────────
# 7. Rien à trouver : page sans aucun libellé de lieu ni JSON-LD → ("", "", "")
# ──────────────────────────────────────────────────────────────────────────
vide = "<article><h1>Une news municipale</h1><p>Aucune information de lieu ici.</p></article>"
verifier("page sans libellé de lieu : rien n'est inventé",
         venue_from_page(vide, url="https://comune.biella.it/novita/x") == ("", "", ""))

# ──────────────────────────────────────────────────────────────────────────
# 8. ville_du_domaine seule : étiquettes courtes/ambiguës écartées.
# ──────────────────────────────────────────────────────────────────────────
verifier("ville_du_domaine('bct.comune.torino.it') = Torino",
         ville_du_domaine("https://bct.comune.torino.it/x") == "Torino")
verifier("ville_du_domaine('torinoclick.it') = '' (pas une commune, un média)",
         ville_du_domaine("https://www.torinoclick.it/cultura/x") == "")
verifier("ville_du_domaine('') = ''",
         ville_du_domaine("") == "")

print(f"\n{'SUCCÈS' if echecs == 0 else 'ÉCHEC'} — {echecs} problème(s) sur "
      f"{echecs + sum(1 for _ in [1])} vérifications" if False else
      f"\n{'SUCCÈS — 0 problème(s).' if echecs == 0 else f'ÉCHEC — {echecs} problème(s).'}")
sys.exit(1 if echecs else 0)
