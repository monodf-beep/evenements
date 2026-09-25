# -*- coding: utf-8 -*-
"""Le portillon « donnée périssable » de scripts/verif_texte_hub.py.

Arbitrage de Franck, 2026-09-22 : « on n'est pas le site officiel. S'il change,
c'est pas à nous la responsabilité. Donc pas de chiffres, pas de choses
périssables. » Écrit après avoir publié, le matin même, six pages d'Annecy
portant les tarifs (8 €, 9 € en juillet-août), les horaires (10 h 30 – 18 h) et
le jour de fermeture des musées.

CE QUI REND CE TEST UTILE, ce n'est pas la liste des cas qui doivent être
REFUSÉS — celle-là ne fait que confirmer le design. C'est la liste des cas qui
doivent PASSER, choisis juste à côté de la frontière (règle 3 du CLAUDE.md,
payée le 2026-08-06 sur un portillon qui n'avait que des cas favorables) :

    une date d'histoire ne périme JAMAIS, et c'est elle qui distingue une page
    des 191 autres. Un portillon qui refuserait « en 1859 » ou « le 10 décembre
    1838 » viderait les pages de ce qui fait leur intérêt.

Le modèle de Chambéry fournit ces cas-limites : il est en ligne, validé, et il
porte quatre dates d'histoire sans un seul chiffre périssable.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.verif_texte_hub import perissable

# --- Doivent PASSER : juste à côté de la frontière ---------------------------
# Tous tirés de textes réellement en ligne (Chambéry et Annecy, 22/09/2026).
ACCEPTES = [
    "Son inauguration date du 10 décembre 1838, en hommage à Benoît de Boigne.",
    "Le décret Rattazzi refait la carte administrative en 1859.",
    "Les ducs y gardent le Saint-Suaire de 1502 à 1578.",
    "Ses décors peints datent de 1834.",
    "Le sculpteur lui donne près de dix-huit mètres de haut.",
    "Cette avenue transforme la ville au XIXe siècle.",
    "La rive orientale aligne Veyrier, Menthon et Talloires en une vingtaine de kilomètres.",
    "Le même site publie leurs horaires, qui changent avec la saison.",
    "Bonlieu, la scène nationale, joue souvent deux ou trois soirs de suite.",
    "La città era la capitale del Genevois, una delle province degli Stati di Savoia.",
    # « fermeture » SANS jour : c'est une phrase de récit, pas un horaire.
    "Les salles du Carré Curial prennent le relais après la fermeture des musées.",
]

# --- Doivent être REFUSÉS : tous publiés pour de vrai le 22/09 au matin ------
REFUSES = [
    ("Il coûte 8 €, et 9 € en juillet et août.", "un prix"),
    ("Un abonnement annuel à 22 € ouvre les deux musées.", "un prix"),
    ("De juin à septembre, ils ouvrent en continu, de 10 h 30 à 18 h.",
     "une heure d'horloge"),
    ("Da giugno a settembre aprono senza pausa, dalle 10:30 alle 18.",
     "une heure d'horloge"),
    ("Les deux musées ferment le mardi, toute l'année.", "un jour de fermeture"),
    ("I due musei chiudono il martedì.", "un jour de fermeture"),
    ("Le premier dimanche du mois est gratuit, d'octobre à mai.",
     "une gratuité datée"),
    ("Dernière entrée quarante-cinq minutes avant la fermeture.",
     "une consigne d'exploitation"),
]


def test_les_dates_d_histoire_passent():
    """La contre-épreuve qui compte : le portillon ne doit pas manger l'histoire."""
    for phrase in ACCEPTES:
        trouve = perissable(phrase)
        assert not trouve, "refusé à tort : {!r} → {}".format(phrase, trouve)


def test_le_perissable_est_refuse():
    for phrase, quoi in REFUSES:
        trouve = perissable(phrase)
        assert trouve, "accepté à tort : {!r}".format(phrase)
        assert quoi in [q for _, q in trouve], (
            "refusé pour le mauvais motif : {!r} → {}".format(phrase, trouve))


def test_le_temoin_serait_rouge_sur_la_version_fautive():
    """Un témoin qui n'a jamais été rouge ne prouve rien (CLAUDE.md, 14/09).

    Ici le « témoin » est le texte d'Annecy tel qu'il a été publié le 22/09 au
    matin : il DOIT être refusé en bloc. S'il passait, le portillon ne servirait
    à rien puisque c'est exactement ce qu'il est censé attraper."""
    fautif = (
        "<p><strong>Les deux musées ferment le même jour</strong>, le mardi. "
        "De juin à septembre, ils ouvrent en continu, de 10 h 30 à 18 h. "
        "Le reste de l'année, ils coupent de 12 h 30 à 14 h. "
        "Dernière entrée quarante-cinq minutes avant la fermeture.</p>"
    )
    trouve = perissable(fautif)
    motifs = {q for _, q in trouve}
    assert "un jour de fermeture" in motifs, trouve
    assert "une heure d'horloge" in motifs, trouve
    assert "une consigne d'exploitation" in motifs, trouve
