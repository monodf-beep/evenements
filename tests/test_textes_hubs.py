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


def test_une_panne_de_credit_est_une_panne_generale():
    """Une panne qui vaut pour toutes les pages doit arrêter le run, pas se rejouer.

    Mesuré le 19/09/2026 : le premier dry-run a brûlé DEUX appels API pour la même erreur
    « credit balance is too low », et il en aurait brûlé un par paire sans le --cap 2."""
    vraie = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error',"
             " 'message': 'Your credit balance is too low to access the Anthropic API.'}}")
    assert th._est_panne_generale(Exception(vraie))
    assert th._est_panne_generale(Exception("authentication_error: invalid x-api-key"))


def test_une_panne_propre_a_une_page_n_arrete_pas_le_run():
    """Contre-épreuve : sans elle, on ne saurait pas si le détecteur regarde quoi que ce
    soit. Un dépassement de tokens ou une coupure réseau concernent UNE page — les autres
    doivent être tentées."""
    assert not th._est_panne_generale(Exception("stop_reason=max_tokens"))
    assert not th._est_panne_generale(Exception("APIConnectionError: Connection reset"))
    assert not th._est_panne_generale(Exception("overloaded_error"))


def test_les_listes_ne_sont_pas_refusees_au_nom_de_la_charte():
    """La charte Agenda AUTORISE les listes (surcharge explicite de la voix de référence).

    Mon premier motif de refus disait « la charte veut de la prose » : c'était faux, et
    ce test existe pour que personne ne le réécrive. Le refus reste, mais pour la raison
    qui vaut ICI — le shortcode rend déjà les faits structurés, et lui se met à jour."""
    raw = FIXTURE["html"]["fr"].replace(
        "<p>Deux spécialités tiennent aussi à Chambéry.",
        "<ul><li>truffe</li></ul><p>Deux spécialités tiennent aussi à Chambéry.")
    motifs = _controle(raw, "fr")
    listes = [m for m in motifs if "liste à puces" in m]
    assert listes, "la liste aurait dû être signalée sur CE gabarit"
    assert "charte veut de la prose" not in listes[0]
    assert "autorisées ailleurs" in listes[0], listes[0]


# Les trois formes de shortcode RÉELLEMENT en ligne, relevées sur WordPress le 19/09/2026
# (192 pages de gabarit : 84 à ville unique, 36 à liste, 72 de territoire). Elles sont
# copiées telles quelles, pas reconstruites de mémoire.
SHORTCODES_REELS = {
    "ville_unique": '[cs_hub_ville villes="Chambéry" territoire="savoie" quand="weekend"]',
    "liste_fr_it": '[cs_hub_ville villes="Aoste,Aosta" territoire="vda" quand="weekend"]',
    "territoire_fr": '[cs_hub_ville territoire="vda" ville_label="Vallée d\'Aoste" '
                     'prep_fr="en" prep_it="in" quand="weekend"]',
    "territoire_it": '[cs_hub_ville territoire="vda" ville_label="Valle d\'Aosta" '
                     'prep_fr="en" prep_it="in" quand="weekend"]',
}


def test_une_liste_de_villes_n_est_pas_une_ville():
    """villes="Aoste,Aosta" désigne UNE cible écrite des deux côtés, pas une ville nommée
    « Aoste,Aosta ». Ma première version comparait la chaîne entière : --villes Aoste ne
    matchait jamais, et la base n'avait évidemment aucune fiche pour cette ville-là."""
    cib = th.cible(th.atts_hub(SHORTCODES_REELS["liste_fr_it"]))
    assert cib["villes"] == ["Aoste", "Aosta"]
    assert cib["label"] == "Aoste"
    assert not cib["est_territoire"]


def test_une_page_de_territoire_n_a_pas_de_ville():
    """72 pages sur 192 n'ont pas d'attribut villes. Se replier sur territoire="vda"
    revenait à chercher des fiches dont la VILLE vaut « vda » : il n'y en a aucune."""
    cib = th.cible(th.atts_hub(SHORTCODES_REELS["territoire_fr"]))
    assert cib["est_territoire"]
    assert cib["villes"] == []
    assert cib["territoire"] == "vda"
    assert cib["label"] == "Vallée d'Aoste"


def test_les_jumelles_d_un_territoire_se_regroupent_malgre_le_libelle():
    """« Vallée d'Aoste » et « Valle d'Aosta » sont la MÊME page en deux langues.

    Regrouper sur le libellé les séparerait, chaque jumelle resterait seule, et le script
    ne les écrirait jamais — il refuse d'écrire la moitié d'une paire."""
    fr = th.cible(th.atts_hub(SHORTCODES_REELS["territoire_fr"]))
    it = th.cible(th.atts_hub(SHORTCODES_REELS["territoire_it"]))
    assert fr["label"] != it["label"]
    assert fr["groupe"] == it["groupe"] == ("T", "vda")


def test_une_ville_et_son_territoire_ne_se_melangent_pas():
    """Contre-épreuve : la page « Aoste » et la page « Vallée d'Aoste » partagent
    territoire="vda". Si le regroupement ne les distinguait pas, quatre pages tomberaient
    dans le même panier et deux seraient écrasées."""
    ville = th.cible(th.atts_hub(SHORTCODES_REELS["liste_fr_it"]))
    terr = th.cible(th.atts_hub(SHORTCODES_REELS["territoire_fr"]))
    assert ville["groupe"] != terr["groupe"]


def test_le_dossier_interroge_les_bonnes_lignes():
    """La requête doit viser la VILLE pour une page de ville et le TERRITOIRE pour une
    page de territoire. On le vérifie sur une base jetable, jamais sur data/events.db."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events_raw (id INTEGER PRIMARY KEY, ville TEXT, "
                 "territoire TEXT, lieu TEXT, llm_categorie TEXT, wp_post_id_as INTEGER, "
                 "date_event_start TEXT, date_event_end TEXT)")
    conn.executemany("INSERT INTO events_raw (ville, territoire, lieu, llm_categorie, "
                     "wp_post_id_as, date_event_end) VALUES (?,?,?,?,?,?)", [
        ("Aosta", "vda", "Teatro Splendor", "Concerts", 1, "2099-01-01"),
        ("Courmayeur", "vda", "Jardin de l'Ange", "Expositions", 2, "2099-01-01"),
        ("Chambéry", "savoie", "Espace Malraux", "Concerts", 3, "2099-01-01"),
        ("Aosta", "vda", "Teatro Splendor", "Concerts", None, "2099-01-01"),   # non publiée
        ("Aosta", "vda", "Vieux Théâtre", "Concerts", 4, "2000-01-01"),        # passée
    ])
    ville = th.dossier(conn, th.cible(th.atts_hub(SHORTCODES_REELS["liste_fr_it"])))
    assert ville["fiches_en_ligne"] == 1, ville          # ni la non publiée, ni la passée
    assert ville["lieux"] == ["Teatro Splendor"]
    assert ville["villes_voisines"] == ["Courmayeur"]    # le reste du territoire
    terr = th.dossier(conn, th.cible(th.atts_hub(SHORTCODES_REELS["territoire_fr"])))
    assert terr["fiches_en_ligne"] == 2, terr           # Aosta + Courmayeur, pas Chambéry
    assert sorted(terr["villes_voisines"]) == ["Aosta", "Courmayeur"]
    conn.close()


# La section « Anti-patterns clés » telle que la voix Obsidian la porte au 20/09/2026,
# collée par Franck. Elle sert d'ENTRÉE au test : ce conteneur n'atteint pas Obsidian, et
# le test doit rester stable même quand Franck édite la note.
VOIX_ANTI = ("## Anti-patterns clés\n\nÉditorialiser frontalement · superlatifs / propagande "
             "(« exceptionnel », « historique », « innovant ») · citations institutionnelles "
             "vides · hedging excessif · formules d'appel au lecteur · transitions scolaires · "
             "connecteurs interdits (« en conclusion », « force est de constater »…).\n\n"
             "> [!warning] Dette\n")


def _avec_voix(rendu):
    """Remplace utils.voix.load_voix le temps d'un test, puis le remet.

    Pourquoi pas monkeypatch sur sys.modules : `anti_patterns()` fait
    `from utils import voix`, qui lit l'ATTRIBUT du paquet `utils` déjà importé et ignore
    une entrée posée dans sys.modules. Le premier jet de ce test est donc sorti rouge sans
    que le code soit en cause — c'est le test qui ne patchait rien."""
    import contextlib
    from utils import voix as _v

    @contextlib.contextmanager
    def _ctx():
        vrai = _v.load_voix
        _v.load_voix = rendu
        try:
            yield
        finally:
            _v.load_voix = vrai
    return _ctx()


def test_les_anti_patterns_se_lisent_dans_la_voix():
    """La liste n'est PAS recopiée dans ce dépôt : elle est extraite de la note Obsidian.

    C'est la leçon de config/vocabulaire_interdit.json, dont le miroir avait divergé dans
    les deux sens avant sa suppression le 05/09/2026. Si Franck ajoute un superlatif à la
    note, le contrôle le connaît au passage suivant, sans qu'on touche au code."""
    with _avec_voix(lambda: VOIX_ANTI):
        assert sorted(th.anti_patterns()) == [
            "en conclusion", "exceptionnel", "force est de constater", "historique", "innovant"]


def test_une_voix_sans_section_anti_patterns_ne_rend_rien():
    """Contre-épreuve : sans elle, on ne saurait pas si l'extraction lit vraiment la
    section, ou si elle ramasse les guillemets de n'importe où dans la note."""
    sans_section = "# Clone Enrico\n\nUn texte sans la section, avec « un mot »."
    with _avec_voix(lambda: sans_section):
        assert th.anti_patterns() == []


def test_obsidian_injoignable_ne_bloque_pas():
    """Même arbitrage qu'utils.vocabulaire, tranché par Franck le 05/09 : une panne
    Obsidian laisse le pipeline tourner SANS filtre plutôt que de bloquer."""
    def boum():
        raise RuntimeError("OBSIDIAN_VOIX_PATH introuvable")
    with _avec_voix(boum):
        assert th.anti_patterns() == []


def test_une_formule_interdite_refuse_un_superlatif_avertit():
    """Les deux sévérités, éprouvées sur le même texte.

    « en conclusion » est une formule : aucun usage innocent, donc refus. « historique » en
    a un, et il est constant — « le centre historique » — donc avertissement. Un refus
    aveugle sur ce mot rejetterait un texte juste à CHAQUE passage et brûlerait deux appels
    API par page pour rien."""
    anti = ["exceptionnel", "historique", "innovant", "en conclusion", "force est de constater"]
    raw = FIXTURE["html"]["fr"].replace(
        "Peu de villes de Savoie en réunissent autant.",
        "En conclusion, peu de villes de Savoie en réunissent autant.")
    avert: list[str] = []
    motifs = th.controles(raw, "fr", FIXTURE["cles"]["fr"], FIXTURE["dossier"], [],
                          verifier_liens=False, corps=FIXTURE["corps"],
                          avertissements=avert, antipatterns=anti)
    assert any("anti-pattern" in m and "en conclusion" in m for m in motifs), motifs

    raw2 = FIXTURE["html"]["fr"].replace("le centre ancien", "le centre historique")
    avert2: list[str] = []
    motifs2 = th.controles(raw2, "fr", FIXTURE["cles"]["fr"], FIXTURE["dossier"], [],
                           verifier_liens=False, corps=FIXTURE["corps"],
                           avertissements=avert2, antipatterns=anti)
    assert motifs2 == [], f"« centre historique » ne doit PAS refuser : {motifs2}"
    assert any("historique" in a for a in avert2), avert2


def test_un_timeout_n_est_pas_un_lien_mort(monkeypatch):
    """Faux refus mesuré le 20/09 : deux de nos adresses italiennes ont dépassé 20 s, le
    contrôle les a déclarées mortes, et quatre re-tests immédiats ont rendu 200.

    Ce refus-là se rejouerait à l'identique chaque jour sur la même matière (règle 3),
    d'où la seconde tentative. Le témoin échoue une fois puis répond : l'adresse doit être
    tenue pour vivante."""
    import requests as _rq
    appels = {"n": 0}

    class Rep:
        status_code = 200
        text = "<html><body>Chambéry</body></html>"

    def faux_get(url, **kw):
        appels["n"] += 1
        if appels["n"] == 1:
            raise _rq.exceptions.ReadTimeout("trop lent")
        return Rep()

    monkeypatch_setattr = getattr(monkeypatch, "setattr", None)
    if monkeypatch_setattr is None:                     # lanceur minimal sans setattr
        vrai = th.requests.get
        th.requests.get = faux_get
        try:
            code, _ = th._fetch("https://agendasabauda.eu/it/cosa-fare-in-savoia/")
        finally:
            th.requests.get = vrai
    else:
        monkeypatch_setattr(th.requests, "get", faux_get)
        code, _ = th._fetch("https://agendasabauda.eu/it/cosa-fare-in-savoia/")
    assert code == 200, "un timeout unique ne doit pas condamner l'adresse"
    assert appels["n"] == 2, "la seconde tentative doit avoir lieu"
