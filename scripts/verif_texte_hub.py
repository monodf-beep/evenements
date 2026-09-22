# -*- coding: utf-8 -*-
"""Contrôle MÉCANIQUE d'un texte de page hub, pas une relecture à l'œil.
Reprend les seuils MESURÉS sur le modèle validé de Chambéry
(config/modele_hub_chambery.json) : 4 H2, 4 à 5 gras, phrase la plus longue
sous 20 mots, clé présente 3 fois."""
import html as H
import re
import sys

# Les interdits valent dans les DEUX langues : une version italienne n'est pas
# une traduction, mais la doctrine ne s'arrête pas à la frontière du français.
INTERDITS_IT = [
    ("frontiera", "oltre le Alpi / in Piemonte"),
    ("transfrontalier", "sabaudo · tra Savoia e Piemonte"),
    ("Venezia delle Alpi", "nominare la città, senza sostituto"),
    ("regno di Sardegna", "gli Stati di Savoia"),
    ("spazio alpino", "spazio sabaudo"),
    ("francoprovenzale", "savoiardo"),
    ("lingue regionali", "nominare la lingua"),
    ("patois", "nominare la lingua"),
]
INTERDITS = [
    ("frontière", "au-delà des Alpes / en Piémont"),
    ("langues régionales", "nommer la langue"),
    ("francoprovençal", "savoyard"),
    ("patois", "nommer la langue"),
    ("espace alpin", "espace sabaudo"),
    ("transfrontalier", "sabaud · entre Savoie et Piémont"),
    ("royaume de Sardaigne", "les États de Savoie"),
    ("Venise des Alpes", "nommer la ville, sans remplacement"),
]
ITALIENS = ["città", "però", "anche", "questo", "della", "degli", "sono", "perché"]
FRANCAIS = ["cette", "aujourd'hui", "semaine ", "week-end", "ville d", "les "]


# --- Le PÉRISSABLE -----------------------------------------------------------
# Arbitrage de Franck, 2026-09-22 : « on n'est pas le site officiel. S'il change,
# c'est pas à nous la responsabilité. Donc pas de chiffres, pas de choses
# périssables. » Ces pages sont écrites une fois et restent en ligne des années ;
# un tarif ou un horaire recopié dedans devient faux sans que personne le sache,
# sur 192 pages à la fois. On NOMME le lieu et on RENVOIE à son site, qui est
# responsable de ses propres horaires.
#
# La frontière n'est pas « chiffre ou pas chiffre » : une date d'histoire
# (1859, le 10 décembre 1838, de 1502 à 1578) ne périme jamais, et c'est
# justement elle qui distingue une page des 191 autres. Ce qui périme, c'est ce
# qui décrit l'EXPLOITATION d'un lieu : prix, heures d'ouverture, jour de
# fermeture, gratuité datée.
PERISSABLE = [
    (r"\d+(?:[.,]\d+)?\s*\u20ac", "un prix"),
    (r"\b\d+\s*euros?\b", "un prix"),
    (r"\b\d{1,2}\s*h\s*\d{0,2}\b", "une heure d'horloge"),
    (r"\b\d{1,2}:\d{2}\b", "une heure d'horloge"),
    (r"\bferm\w+[^.!?]{0,60}?\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b",
     "un jour de fermeture"),
    (r"\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b[^.!?]{0,40}?\bferm\w+",
     "un jour de fermeture"),
    (r"\b(?:chius\w+|chiud\w+)[^.!?]{0,60}?\b(?:luned\w*|marted\w*|mercoled\w*|gioved\w*|venerd\w*|sabato|domenica)\b",
     "un jour de fermeture"),
    (r"\b(?:luned\w*|marted\w*|mercoled\w*|gioved\w*|venerd\w*|sabato|domenica)\b[^.!?]{0,40}?\b(?:chius\w+|chiud\w+)",
     "un jour de fermeture"),
    (r"\b(?:plein|premier|dernier)\s+tarif\b|\btarif\s+r\u00e9duit\b", "un tarif"),
    (r"\bbiglietto\s+ridotto\b|\btariffa\b", "un tarif"),
    (r"premier dimanche du mois|prima domenica del mese", "une gratuit\u00e9 dat\u00e9e"),
    (r"derni\u00e8re entr\u00e9e|ultimo ingresso", "une consigne d'exploitation"),
]


def perissable(texte):
    """Rend la liste des passages qui périmeront sans nous prévenir."""
    trouves = []
    for motif, quoi in PERISSABLE:
        for m in re.finditer(motif, texte, re.I):
            trouves.append((m.group(0).strip(), quoi))
    return trouves


def nu(h):
    """Texte nu, avec une FRONTIÈRE DE PHRASE à chaque fin de bloc.

    Sans ça, un <h2> sans point final se colle au paragraphe suivant et la
    « phrase la plus longue » devient un artefact de mesure. Défaut déjà
    constaté et corrigé dans scripts/textes_hubs.py en septembre : le texte
    aplati faisait passer des titres pour des débuts de phrase."""
    h = re.sub(r"<!--.*?-->", " ", h, flags=re.S)
    h = re.sub(r"</(h2|h3|p|li|div)>", ". ", h, flags=re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"\s*\.\s*\.", ".", h)
    return H.unescape(re.sub(r"\s+", " ", h)).strip()


def controler(chemin, cle, langue, mots_vises):
    brut = open(chemin, encoding="utf-8").read()
    texte = nu(brut)
    print("=== {} ===".format(chemin.split("/")[-1]))

    mots = len(re.findall(r"[\w'’\-]+", texte))
    h2 = len(re.findall(r"<h2[ >]", brut))
    gras = len(re.findall(r"<strong>", brut))
    phrases = [p.strip() for p in re.split(r"(?<=[.!?])\s+", texte) if p.strip()]
    plus_longue = max(phrases, key=lambda p: len(p.split()))
    n_cle = len(re.findall(re.escape(cle), texte, re.I))
    liens_ext = len(re.findall(r'href="https?://(?!agendasabauda)', brut))
    liens_int = len(re.findall(r'href="https://agendasabauda', brut))

    def ligne(libelle, valeur, ok):
        print("  {} {:<34} {}".format("OK  " if ok else "ÉCART", libelle, valeur))

    ligne("mots", "{} (visé ~{})".format(mots, mots_vises), abs(mots - mots_vises) <= 70)
    ligne("chapitres H2", h2, h2 == 4)
    ligne("expressions en gras", gras, 4 <= gras <= 5)
    ligne("phrase la plus longue", "{} mots".format(len(plus_longue.split())),
          len(plus_longue.split()) <= 20)
    ligne("occurrences de la clé", "{} × « {} »".format(n_cle, cle), 2 <= n_cle <= 5)
    ligne("liens externes", liens_ext, liens_ext >= 1)
    ligne("liens internes", liens_int, liens_int >= 2)
    ligne("tiret cadratin (—)", texte.count("—"), texte.count("—") == 0)
    ligne("séparateur ---", brut.count("\n---"), brut.count("\n---") == 0)
    ligne("liste à puces", len(re.findall(r"<li[ >]", brut)),
          len(re.findall(r"<li[ >]", brut)) == 0)
    ligne("marqueur <!--more-->", brut.count("<!--more-->"), brut.count("<!--more-->") == 1)

    perim = perissable(texte)
    ligne("donnée périssable", "aucune" if not perim else perim, not perim)

    liste = INTERDITS + (INTERDITS_IT if langue == "it" else [])
    trouves = [(m, r) for m, r in liste if re.search(re.escape(m), texte, re.I)]
    ligne("vocabulaire interdit", "aucune occurrence" if not trouves else trouves,
          not trouves)

    autre = ITALIENS if langue == "fr" else FRANCAIS
    contamine = [m for m in autre if re.search(r"\b" + re.escape(m), texte, re.I)]
    ligne("contamination de l'autre langue",
          "aucune" if not contamine else contamine, not contamine)

    print("    phrase la plus longue : « {} »".format(plus_longue[:110]))
    print()


if __name__ == "__main__":
    controler(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]))
