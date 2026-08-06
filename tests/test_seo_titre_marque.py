#!/usr/bin/env python3
"""Fixture : `utils.seo._ajuste_titre_seo` fait rentrer un titre SEO dans le budget
(60 caractères visés) sans jamais couper un mot en deux — et laisse tomber le
suffixe de marque " — Agenda Sabauda" AVANT de toucher au nom de l'événement.

TROUVÉ le 2026-08-06 en discutant avec Franck d'une capture Yoast (« Foire de
Saint-Ours Aoste 2027 — Agenda Sabauda ») : le seul filet existant était un
troncage brut à 70 caractères (`[:70]`), sans égard pour un mot coupé en deux ni
pour le suffixe lui-même amputé (« — Agenda Sabau »). Aucun réseau, fonction pure.

Lancer : .venv/bin/python -m tests.test_seo_titre_marque
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.seo import _ajuste_titre_seo  # noqa: E402

echecs = 0


def _check(label, obtenu, attendu):
    global echecs
    if obtenu == attendu:
        print(f"OK    {label} → {obtenu!r}")
    else:
        echecs += 1
        print(f"ÉCHEC {label} : attendu {attendu!r}, obtenu {obtenu!r}")


# 1. Déjà dans le budget, suffixe inclus → inchangé.
_check("court avec suffixe, dans le budget",
       _ajuste_titre_seo("Foire de Saint-Ours Aoste 2027 — Agenda Sabauda"),
       "Foire de Saint-Ours Aoste 2027 — Agenda Sabauda")

# 2. Trop long AVEC le suffixe, mais tient SANS lui → suffixe retiré, rien coupé.
titre_sans_suffixe = "Le grand marché de Noël du centre historique"  # 44 caractères
assert len(titre_sans_suffixe) <= 60, "le cas de test doit tenir sans le suffixe"
titre_long = titre_sans_suffixe + " — Agenda Sabauda"  # 62 caractères, dépasse
assert len(titre_long) > 60, "le cas de test doit dépasser le budget AVEC le suffixe"
obtenu = _ajuste_titre_seo(titre_long)
_check("suffixe retiré, aucun mot coupé", obtenu, titre_sans_suffixe)
_check("le résultat ne contient plus le mot 'Agenda'", "Agenda" not in obtenu, True)

# 3. Toujours trop long MÊME sans le suffixe → coupé au dernier mot entier, pas en
#    plein milieu (jamais un titre du genre « ...centre histori »).
titre_tres_long = ("Le grand marché artisanal de Noël et ses animations en famille au cœur "
                   "du centre historique de la vieille ville — Agenda Sabauda")
obtenu = _ajuste_titre_seo(titre_tres_long)
_check("coupé à 60 caractères max", len(obtenu) <= 60, True)
_check("pas de mot coupé (le titre ne finit pas par un fragment collé à la limite)",
       titre_tres_long.startswith(obtenu.rstrip(" ,.;:—-")), True)
print(f"      (titre obtenu : {obtenu!r}, {len(obtenu)} caractères)")

# 4. Sans suffixe du tout, déjà court → inchangé.
_check("sans suffixe, déjà court", _ajuste_titre_seo("Musilac 2026 — Aix-les-Bains"),
       "Musilac 2026 — Aix-les-Bains")

# 5. Exactement 60 caractères → inchangé (pas de coupe pour rien).
pile_60 = "x" * 60
_check("exactement 60 caractères, inchangé", _ajuste_titre_seo(pile_60), pile_60)

# 6. Espaces parasites nettoyés avant mesure (comme le reste du module, via _clean).
_check("espaces multiples nettoyés",
       _ajuste_titre_seo("Musilac   2026  —  Aix-les-Bains"), "Musilac 2026 — Aix-les-Bains")

print(f"\n{'ÉCHEC' if echecs else 'SUCCÈS'} — {echecs} problème(s).")
sys.exit(1 if echecs else 0)
