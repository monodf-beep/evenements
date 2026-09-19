#!/usr/bin/env python3
"""Le témoin des contrôles de scripts/textes_hubs.py.

CLAUDE.md, règle 3 : « la fixture doit contenir un cas qui doit PASSER, choisi près de la
frontière ». Le témoin est le modèle Chambéry validé le 19/09/2026, et il est sur la
frontière de TROIS bornes à la fois — 5 gras pour un maximum de 5, 4 H2 pour un maximum
de 4, phrase la plus longue à 17 mots pour un maximum de 20. Un texte confortable passerait
même sur un portillon faux ; celui-ci ne passe que si les bornes sont justes.

Les contre-épreuves comptent autant : chacune abîme le témoin d'UNE façon et exige un
refus. Sans elles on ne saurait pas si le portillon regarde vraiment quelque chose — la
faute 21 du 14/09 est née d'un témoin qui n'avait jamais été rouge.

Le test tourne HORS LIGNE : le texte des pages citées est préchargé dans la fixture
(réduit à leurs mots en majuscule, seule chose que le contrôle en lit). Un site tiers qui
change d'arborescence ne doit pas faire rougir notre suite — celui de Chambéry l'a fait
entre le 18 et le 19/09.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import textes_hubs as th  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "textes_hubs.json").read_text(encoding="utf-8"))


def _controle(raw: str, lang: str) -> list[str]:
    return th.controles(raw, lang, FIXTURE["cles"][lang], FIXTURE["dossier"], [],
                        verifier_liens=False, corps=FIXTURE["corps"])


@pytest.mark.parametrize("lang", ["fr", "it"])
def test_le_temoin_passe(lang):
    """Le cas qui DOIT passer. S'il rougit, c'est une borne qui a bougé, pas le texte."""
    assert _controle(FIXTURE["html"][lang], lang) == []


@pytest.mark.parametrize("lang", ["fr", "it"])
def test_les_mesures_annoncees_sont_les_vraies(lang):
    """La fixture annonce 489 mots, 4 H2, 5 gras : on le recompte, on ne le croit pas."""
    import re
    raw, m = FIXTURE["html"][lang], FIXTURE["mesures"][lang]
    nu = th.texte_nu(raw)
    assert len(re.findall(r"[\w’'\-]+", nu)) == m["mots"]
    assert len(re.findall(r"<h2>", raw)) == m["h2"] == th.H2_MAX
    assert len(re.findall(r"<strong>", raw)) == m["gras"] == th.GRAS_MAX


def _refuse_pour(raw: str, lang: str, fragment: str) -> None:
    motifs = _controle(raw, lang)
    assert motifs, "le portillon a laissé passer un texte fautif"
    assert any(fragment in m for m in motifs), \
        f"refusé, mais pour un autre motif que « {fragment} » : {motifs}"


def test_une_phrase_trop_longue_est_refusee():
    raw = FIXTURE["html"]["fr"].replace(
        "Les Bauges et la Chartreuse sont tout proches.",
        "Les Bauges et la Chartreuse sont tout proches, et le massif voisin offre lui "
        "aussi de quoi marcher pendant un long week-end entier sans jamais se répéter.")
    _refuse_pour(raw, "fr", "phrase de")


def test_un_gras_de_trop_est_refuse():
    raw = FIXTURE["html"]["fr"].replace(
        "Les Bauges et la Chartreuse", "<strong>Les Bauges</strong> et la Chartreuse")
    _refuse_pour(raw, "fr", "en gras")


def test_un_gras_sur_un_nom_propre_est_refuse():
    raw = FIXTURE["html"]["fr"].replace(
        "<strong>la vie culturelle</strong>", "<strong>la vie à Chambéry</strong>")
    _refuse_pour(raw, "fr", "nom propre")


def test_un_nom_propre_invente_est_refuse():
    """Le cœur du portillon : un nom qu'aucune source citée ne porte ne doit pas passer.

    Première version de ce test le 19/09 : elle glissait « Casimir Vicario » dans le
    texte, en croyant ce nom absent des sources. Le test est sorti VERT — et il avait
    raison : Vicario est bel et bien sur la page du château de l'office de tourisme, où il
    est décrit comme le peintre piémontais de la voûte de la Sainte-Chapelle. C'est donc
    MON affirmation qui était fausse, pas le portillon. Le nom est maintenant dans le
    texte, à sa vraie place, et la contre-épreuve emploie « Zanetti », vérifié absent des
    cinq sources. Un témoin doit pouvoir rougir : celui-là a servi à corriger le rédacteur.
    """
    raw = FIXTURE["html"]["fr"].replace(
        "Ses décors peints datent de 1834.",
        "Ses décors peints, signés Zanetti, datent de 1834.")
    _refuse_pour(raw, "fr", "invérifiables")


def test_un_terme_interdit_est_refuse(monkeypatch, tmp_path):
    """Le vocabulaire vit dans Obsidian ; ici on fabrique une note temporaire, comme
    tests/test_vocabulaire.py, pour éprouver le branchement et pas la note elle-même."""
    note = tmp_path / "vocab.md"
    note.write_text("| Terme interdit | Pourquoi | Alternative |\n| --- | --- | --- |\n"
                    "| **« royaume de Sardaigne »** | inexact | **les États de Savoie** |\n",
                    encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VOCAB_PATH", str(note))
    raw = FIXTURE["html"]["fr"].replace(
        "Dans l'ancienne capitale des ducs de Savoie",
        "Dans l'ancienne capitale du royaume de Sardaigne")
    _refuse_pour(raw, "fr", "vocabulaire interdit")


def test_la_cle_absente_du_premier_paragraphe_est_refusee():
    raw = FIXTURE["html"]["fr"].replace(
        "Que faire à Chambéry ce week-end : cette page réunit",
        "Cette page réunit", 1)
    _refuse_pour(raw, "fr", "premier paragraphe")


def test_sans_lien_externe_est_refuse():
    import re
    raw = re.sub(r'<a href="https://www\.[^"]+"[^>]*>(.*?)</a>', r"\1", FIXTURE["html"]["fr"])
    _refuse_pour(raw, "fr", "lien externe")


def test_le_tiret_cadratin_est_refuse():
    raw = FIXTURE["html"]["fr"].replace("Façades ocre, volets verts",
                                        "Façades ocre — volets verts")
    _refuse_pour(raw, "fr", "cadratin")


def test_nos_propres_pages_n_autorisent_aucun_nom():
    """Contre-épreuve du garde-fou du 19/09 : nos pages d'agenda listent les événements du
    jour, donc les accepter comme source ouvrirait le portillon tout en le croyant fermé."""
    # noms_autorises ne filtre pas lui-même : c'est lire_adresses qui écarte nos pages.
    # On éprouve donc la chaîne complète, seule à valoir quelque chose — un test sur la
    # seule fonction interne prouverait un garde-fou que la production n'emploie pas.
    raw = FIXTURE["html"]["fr"].replace(
        "Ses décors peints datent de 1834.",
        "Ses décors peints, signés Zanetti, datent de 1834.")
    motifs = th.controles(raw, "fr", FIXTURE["cles"]["fr"], FIXTURE["dossier"], [],
                          verifier_liens=False, corps=FIXTURE["corps"])
    assert any("invérifiables" in m and "Zanetti" in m for m in motifs), motifs


def test_en_tete_de_phrase_c_est_un_avertissement_pas_un_refus():
    """La limite du portillon, éprouvée plutôt que promise.

    En ouverture de phrase, une majuscule inconnue est SIGNALÉE et le texte passe. Ce test
    existe pour que le jour où quelqu'un croit le contrôle total, il lise ici qu'il ne
    l'est pas — et pour qu'un durcissement futur (un dictionnaire français/italien) fasse
    rougir ce test au lieu de passer inaperçu."""
    raw = FIXTURE["html"]["fr"].replace("Casimir Vicario, un peintre piémontais",
                                        "Zanetti, un peintre piémontais")
    avert: list[str] = []
    motifs = th.controles(raw, "fr", FIXTURE["cles"]["fr"], FIXTURE["dossier"], [],
                          verifier_liens=False, corps=FIXTURE["corps"], avertissements=avert)
    assert motifs == [], f"attendu un simple avertissement, obtenu un refus : {motifs}"
    assert any("Zanetti" in a for a in avert), avert
