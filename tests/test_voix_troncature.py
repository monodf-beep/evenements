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


def test_rien_n_est_coupe_en_silence():
    """Volet 1 — ce qui est CHARGÉ doit être ce qui est SERVI, sur cette machine-ci.

    ⚠️ CE VOLET ACCUSAIT LE MAUVAIS COUPABLE, et ça a coûté un correctif inutile
    (2026-09-22). Il comparait `docs/voix/VOIX.md` à `load_voix()` et, dès qu'ils
    différaient, annonçait « la FIN de la note n'est pas appliquée… relever
    VOIX_MAX_CHARS ». Sur le VPS, les deux différaient de 3 202 caractères et le message
    a envoyé relever le plafond — alors que le plafond ne mordait pas du tout : les
    COUCHES choisies au back-office y servent d'autres notes que la charte versionnée.
    Mesuré ce jour-là sur le serveur : `voix_integrale()` rendait 3 972 caractères, et
    `load_voix()` les rendait tous. Rien n'était tronqué.

    Un compteur doit dire ce qu'il compte. La troncature, c'est l'écart entre ce que les
    sources contiennent (`voix_integrale`, sans plafond) et ce qui est réellement livré
    (`load_voix`, plafonné). C'est cet écart-là qu'on mesure désormais, et il vaut la
    même chose sur toutes les machines, quelles que soient les couches configurées.
    """
    integrale = voix.voix_integrale()
    charge = voix.load_voix()
    perdu = len(integrale) - len(charge)
    assert perdu <= 0, (
        f"{perdu} caractères sont coupés EN SILENCE : les sources de voix de cette "
        f"machine pèsent {len(integrale)} car., le plafond est à {voix._max_chars()}. "
        f"Relever VOIX_MAX_CHARS, ou raccourcir les notes."
    )


def test_la_charte_versionnee_tient_sous_le_plafond():
    """Volet 1 bis — garantie du DÉPÔT, celle-là indépendante de toute machine.

    Le volet précédent ne dit rien d'une machine qui n'aurait pas configuré de couches :
    elle servira `docs/voix/VOIX.md`, et il faut donc que ce fichier-là tienne. C'est
    exactement l'incident du 2026-09-05, où la note avait dépassé le plafond sans que
    personne ne mesure.
    """
    brut = voix._strip_obsidian(voix._DEFAULT_VOIX.read_text(encoding="utf-8"))
    assert len(brut) <= voix._max_chars(), (
        f"docs/voix/VOIX.md pèse {len(brut)} car. pour un plafond de "
        f"{voix._max_chars()} : sur une machine sans couches configurées, sa FIN ne "
        f"serait pas appliquée. Relever VOIX_MAX_CHARS ou raccourcir la note."
    )


def test_les_dernieres_regles_sont_bien_la():
    """Volet 1 ter — on vérifie le RÉSULTAT, pas seulement une longueur.

    Une longueur suffisante ne prouve pas que les bonnes règles sont présentes : on
    cherche donc nommément les deux sections qui avaient disparu le 05/09.

    On les cherche dans la CHARTE VERSIONNÉE chargée seule, pas dans `load_voix()` :
    une machine dont les couches servent d'autres notes n'a aucune raison de porter ces
    deux titres-là, et exiger leur présence reviendrait à interdire de configurer des
    couches. C'est la même confusion que celle corrigée au volet 1.
    """
    brut = voix._strip_obsidian(voix._DEFAULT_VOIX.read_text(encoding="utf-8"))
    tronque = brut[:voix._max_chars()]
    for regle in ("Les Alpes ne sont pas une frontière", "Deux longueurs"):
        assert regle in tronque, (
            f"la section « {regle} » tomberait hors du plafond de "
            f"{voix._max_chars()} caractères, comme le 2026-09-05."
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
    test_rien_n_est_coupe_en_silence()
    test_la_charte_versionnee_tient_sous_le_plafond()
    test_les_dernieres_regles_sont_bien_la()
    print("OK — la voix passe en entier et ses dernières règles sont présentes.")
    print("    (la contre-épreuve demande pytest : monkeypatch/capsys)")
