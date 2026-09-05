#!/usr/bin/env python3
"""Fixture : la charte de voix ne doit JAMAIS être tronquée en silence.

INCIDENT RÉEL, constaté le 2026-09-05 en préparant la refonte de /ou-manger/ :
`docs/voix/VOIX.md` pesait 6775 caractères pour un plafond `VOIX_MAX_CHARS` de 6000.
`load_voix()` en coupait donc 775 — c'est-à-dire la règle entière « Les Alpes ne sont
pas une frontière » ET la section « Deux longueurs ». Le pipeline ne les a jamais vues.

C'est le pire genre de panne, celui que ce dépôt documente depuis un an : elle ne
ressemble pas à une panne. Un texte écrit sans les dernières règles reste plausible,
bien tourné, publiable. Rien ne signale que la charte s'applique amputée. La note elle-
même dit « garde-la sous 6000 caractères » ; personne ne mesurait si c'était le cas.

Deux volets, parce qu'un seul ne prouverait rien :
  1. la voix RÉELLEMENT livrée par le dépôt passe en entier (cas qui doit PASSER,
     choisi au plus près de la frontière : c'est le fichier de production) ;
  2. CONTRE-ÉPREUVE : une note délibérément trop longue DOIT déclencher l'avertissement.
     Sans ce volet, un plafond relevé à l'infini passerait au vert sans rien garantir.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils import voix  # noqa: E402


def test_voix_du_depot_passe_en_entier():
    """Volet 1 — la charte versionnée doit être chargée SANS perte."""
    brut = voix._strip_obsidian(voix._DEFAULT_VOIX.read_text(encoding="utf-8"))
    charge = voix.load_voix()
    perdu = len(brut) - len(charge)
    assert perdu <= 0, (
        f"{perdu} caractères de la charte sont coupés : la FIN de docs/voix/VOIX.md "
        f"n'est pas appliquée. Note = {len(brut)} car., plafond = {voix._max_chars()}. "
        f"Relever VOIX_MAX_CHARS ou raccourcir la note."
    )


def test_les_dernieres_regles_sont_bien_la():
    """Volet 1 bis — on vérifie le RÉSULTAT, pas seulement une longueur.

    Une longueur suffisante ne prouve pas que les bonnes règles sont présentes : on
    cherche donc nommément les deux sections qui avaient disparu le 05/09.
    """
    charge = voix.load_voix()
    for regle in ("Les Alpes ne sont pas une frontière", "Deux longueurs"):
        assert regle in charge, (
            f"la section « {regle} » est absente de la voix chargée : "
            f"elle est tombée hors du plafond, comme le 2026-09-05."
        )


def test_contre_epreuve_une_note_trop_longue_est_signalee(
        tmp_path, caplog, capsys, monkeypatch):
    """Volet 2 — une note qui DÉPASSE le plafond doit être annoncée, pas rognée en
    silence. C'est ce volet qui donne sa valeur au premier.

    On lit `caplog` ET `capsys` : l'avertissement part par le logger du projet, mais
    tombe sur un `print` si `utils.logger` est indisponible. Une première version de ce
    test ne regardait que `capsys` et passait ou échouait selon la façon dont pytest
    interceptait le handler — un test instable, qui aurait fini par être ignoré.
    """
    import logging

    note = tmp_path / "VOIX-trop-longue.md"
    note.write_text("# Voix de test\n" + ("Phrase de remplissage. " * 600),
                    encoding="utf-8")
    monkeypatch.setenv(voix.VOIX_ENV, str(note))
    monkeypatch.setenv("VOIX_MAX_CHARS", "500")

    with caplog.at_level(logging.WARNING):
        texte = voix.load_voix()
    assert len(texte) <= 500, "le plafond doit rester appliqué"

    bruit = capsys.readouterr()
    trace = (caplog.text + bruit.out + bruit.err).lower()
    assert "tronqu" in trace, (
        "une charte tronquée doit le DIRE (log ou stdout). Sans ce signal, la faute "
        "du 2026-09-05 se reproduit à l'identique et reste invisible."
    )


if __name__ == "__main__":
    test_voix_du_depot_passe_en_entier()
    test_les_dernieres_regles_sont_bien_la()
    print("OK — la voix passe en entier et ses dernières règles sont présentes.")
    print("    (la contre-épreuve demande pytest : monkeypatch/capsys)")
