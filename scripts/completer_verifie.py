#!/usr/bin/env python3
"""Pose les valeurs VÉRIFIÉES et écarte ce qui n'a rien à faire dans l'agenda.

Franck, 2026-08-11, trois fois dans l'après-midi : « donc on avance pas ? », « pour
l'instant ça avance toujours pas ». La pastille « À compléter » était à 68 le matin et à
67 le soir, après quatre correctifs poussés en production. Tous justes, tous mesurés,
tous sans effet sur son écran — j'optimisais des passes automatiques alors que la file
contenait surtout des fiches qu'AUCUNE passe ne peut servir.

La lecture des 67, une par une, l'a montré :

  • 26 n'ont aucune page lisible — 16 viennent d'un mail (« gmail:… »), 8 pointent vers
    un lien de TRAÇAGE de newsletter (sendibm1, musvc6, marketingcloud) au lieu de la
    page de l'événement, 2 sont des traductions mal marquées ;
  • ~14 ne relèvent pas de la charte — le CCAS de La Ravoire (« gestes qui sauvent »,
    « le sommeil », « visite du stade »), trois congrès, quatre billets de BLOG du
    Circolo dei Lettori dont l'adresse contient « /blog/ » ;
  • et une poignée attendait une donnée que j'avais déjà vérifiée le matin même, pour
    répondre aux doutes de la file « À vérifier ».

Ce script fait ce dernier tiers, qui est le seul à pouvoir bouger aujourd'hui. Il n'est
pas un extracteur de plus : les valeurs sont écrites en dur, chacune avec la source qui
la prouve, parce qu'elles ont été vérifiées à la main et qu'aucun automatisme ne les
aurait trouvées.

CE QU'IL RESPECTE
  • dry-run par défaut (règle 4) ;
  • il n'écrase rien PAR SURPRISE : un champ déjà rempli est laissé tel quel, et il le
    dit. Une seule exception, ajoutée le 2026-08-11 pour les années fausses signalées par
    l'agent : la clause « remplace » du JSON, où l'appelant DÉCLARE la valeur erronée
    qu'il corrige. Si la base ne la porte plus, la correction est refusée — quelqu'un est
    passé après lui (cf. `_valeur_attendue`) ;
  • « écarter » = `statut='rejected'`, c'est-à-dire la même chose que le bouton du
    back-office : une RE-CLASSIFICATION réversible, aucune ligne supprimée ;
  • le bilan est recompté en base après écriture (règle 6).

  .venv/bin/python -m scripts.completer_verifie            # simulation
  .venv/bin/python -m scripts.completer_verifie --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))
COMMUNES = ROOT / "config" / "communes_comte_de_nice.json"

# ── Valeurs vérifiées à la main, avec la source qui les prouve ───────────────────────
# Rien ici ne vient d'une déduction : chaque ligne a été ouverte et lue. La source est
# gardée pour qu'un désaccord futur se règle en rouvrant la page, pas en me croyant.
_VALEURS: dict[int, tuple[dict, str]] = {
    4621: ({"lieu": "Teatro Regio"},
           "torinofilmfest.org — la soirée d'ouverture du 44e TFF a lieu au Teatro Regio"),
    3280: ({"ville": "Torino"}, "teatroregio.torino.it — le Teatro Regio est à Turin"),
    4564: ({"lieu": "Polo Espositivo ARCA", "ville": "Vercelli"},
           "visitvalsesiavercelli.it — l'ARCA est l'ancienne église San Marco, à Verceil"),
    4705: ({"lieu": "Citadelle Saint-Elme", "ville": "Villefranche-sur-Mer"},
           "villefranche-sur-mer.fr — cinéma de plein air à la Citadelle"),
    3948: ({"date_event_start": "2026-06-03", "date_event_end": "2026-09-13"},
           "lavenaria.it — Milo Manara, Il nome della rosa, 3 juin au 13 septembre 2026"),

    # ── Deuxième fournée : pages ouvertes et lues une par une le 2026-08-11 au soir ──
    # Ce que quatre passes automatiques n'avaient pas su lire, une lecture le donne en
    # trois minutes. C'est la conclusion du §1 de docs/CE_QUE_DISENT_LES_SOURCES_
    # OFFICIELLES.md : ces pages écrivent tout, mais en prose, pour des lecteurs.
    4344: ({"date_event_start": "2026-08-21", "date_event_end": "2026-08-21"},
           "villefranche-sur-mer.fr — « Le vendredi 21 août 2026 à 21h, le Théâtre de "
           "Verdure de la Citadelle accueille Tribute to Céline Dion »"),
    4345: ({"date_event_start": "2026-08-15", "date_event_end": "2026-08-15"},
           "villefranche-sur-mer.fr — samedi 15 août 2026, 21h, place Félix Poullan "
           "(programme Citadell'Arte)"),
    4722: ({"ville": "Villefranche-sur-Mer", "date_event_start": "2026-09-19", "date_event_end": "2026-09-19",
            "lieu": "Cour de l'Hôtel de Ville de la Citadelle"},
           "villefranche-sur-mer.fr — samedi 19 septembre 2026, 21h"),
    4723: ({"ville": "Villefranche-sur-Mer", "date_event_start": "2026-09-08", "date_event_end": "2026-09-21",
            "lieu": "Foyer de l'Auditorium de la Citadelle"},
           "villefranche-sur-mer.fr — 8 au 21 septembre 2026, vernissage le 8 à 17h"),
    4721: ({"ville": "Villefranche-sur-Mer", "date_event_start": "2026-09-15", "date_event_end": "2026-09-20",
            "lieu": "Rade de Villefranche-sur-Mer, port de la Darse"},
           "villefranche-sur-mer.fr — « du 15 au 20 septembre 2026 », une soixantaine de "
           "bateaux traditionnels"),
    4720: ({"ville": "Villefranche-sur-Mer", "date_event_start": "2026-09-19", "date_event_end": "2026-09-20",
            "lieu": "Citadelle et Darse"},
           "villefranche-sur-mer.fr — visites de la Citadelle le samedi 19, visites "
           "guidées de la Darse les 19 et 20 septembre 2026"),
    # Trois soirées de la Biblioteca civica : le lieu n'était nulle part dans le flux,
    # il est dans le champ « Dove » de chaque page.
    4688: ({"lieu": "Mausoleo della Bela Rosin"}, "bct.comune.torino.it — champ « Dove »"),
    4727: ({"lieu": "Mausoleo della Bela Rosin"}, "bct.comune.torino.it — champ « Dove »"),
    4728: ({"lieu": "Mausoleo della Bela Rosin"}, "bct.comune.torino.it — champ « Dove »"),
    3017: ({"date_event_start": "2026-09-18", "date_event_end": "2026-09-18"},
           "fondazionemerz.org — « 18 settembre 2026 ore 18 – ingresso gratuito »"),
    4718: ({"lieu": "Tappa della Strada Romantica, près de l'église San Michele Arcangelo",
            "ville": "Mombarcaro"},
           "turismoinlanga.it — rendez-vous à 20h15 à Mombarcaro (CN)"),
    # ── Troisième fournée : la Reggia di Venaria, dont six fiches attendaient une date
    # derrière un lien de traçage de newsletter. Leur page existe et la donne.
    3945: ({"date_event_start": "2026-07-31", "date_event_end": "2026-09-05"},
           "lavenaria.it/evento/sere-destate-alla-reggia — « dal 31 luglio al 5 settembre "
           "2026 », chaque vendredi et samedi de 18h30 à 23h"),
    3946: ({"date_event_start": "2026-04-17", "date_event_end": "2026-09-06"},
           "lavenaria.it/it/mostre — « Regine in scena. L'arte del costume italiano tra "
           "cinema e teatro », 17 avril au 6 septembre 2026"),

    # ── RÉCURRENTS : ce ne sont pas des dates manquantes ────────────────────────────
    # Franck, 2026-08-11 : « à toi de savoir et de mettre ». Ces fiches n'ont pas de date
    # unique à trouver — elles se RÉPÈTENT. Leur poser une date serait faux ; le drapeau
    # `recurring` remplace la date par une note (utils.completeness.recurring_note) et
    # les sort de la file « À compléter », qui n'exige plus de date pour elles.
    #
    # La note est écrite ICI plutôt que laissée au texte par défaut (« vérifiez les dates
    # sur la source ») : un visiteur qui lit « chaque vendredi et samedi soir, de juin à
    # septembre » sait s'il peut y aller. « Vérifiez sur la source » lui demande de faire
    # le travail à notre place.
    3279: ({"ville": "Torino", "recurring": 1,
            "recurring_note": "Ouvertures nocturnes chaque vendredi et samedi soir, "
                              "l'été : église, chapelle du Vœu, montée à la coupole et "
                              "musée ouverts jusqu'à minuit"},
           "basilicadisuperga.org — « ogni venerdì e sabato sera », vérifié le 11/08/2026"),
    1845: ({"recurring": 1,
            "recurring_note": "Promenades accompagnées au château de Serralunga d'Alba, "
                              "toute la saison 2026 — départs à 11h et 15h30"},
           "langhe.net — la page n'annonce que des horaires de départ, pas de date unique"),
    2492: ({"recurring": 1,
            "recurring_note": "Sortie photo avec un guide professionnel, à la demande "
                              "toute l'année — réservation auprès de l'office de tourisme"},
           "explorenicecotedazur.com — prestation à la demande, sans date fixée"),
    899: ({"recurring": 1,
           "recurring_note": "Sentier artistique en accès libre toute la saison, "
                             "aux Éphémères Alpines (Hautecour)"},
          "coeurdetarentaise-tourisme.com — parcours permanent, pas un événement daté"),

    526: ({"date_event_start": "2026-09-26", "date_event_end": "2026-09-26"},
          "opera-nice.org — la date est dans l'adresse même de la page : "
          "/agenda/…/20260926-1500/, soit le 26 septembre 2026 à 15h"),

    # ── Troisième fournée : les neuf de la file, ouvertes une par une le 2026-08-11, 20h40
    # Franck : « on en fait quoi de ce qui reste ? ». Sur neuf : quatre se complètent,
    # trois sont des événements TERMINÉS (plus bas, dans _ECARTS), deux résistent — une
    # page en panne et un rendez-vous que la source ne publie nulle part.
    4527: ({"date_event_start": "2026-08-08", "date_event_end": "2026-10-11"},
           "lavalleenotizie.it / aostasera.it — « Dall'8 agosto all'11 ottobre 2026 la "
           "sala del Corpo di Guardia del Forte di Bard ospita Pastorale », inaugurée le "
           "samedi 8 août à 11h. (L'autre exposition, à Cogne, court du 29 juillet au "
           "7 septembre ; la fiche porte le Forte di Bard, donc ce sont ces dates-là.)"),
    3087: ({"lieu": "Palais des Expositions"},
           "palaisdesexpos.nice.fr — « EVO - NICE 2026 - 9 au 11 octobre 26 - Palais des "
           "Expos - Nice »"),
    4242: ({"date_event_start": "2026-09-20", "date_event_end": "2026-09-20"},
           "patrimoines.savoie.fr (Journées européennes du patrimoine 2026) — « Dimanche "
           "20 septembre 2026 de 14h30 à 15h30 et de 16h à 17h ». À NE PAS confondre avec "
           "l'exposition, qui court du 13 juin au 15 novembre 2026 : la fiche porte la "
           "VISITE COMMENTÉE, qui a une date unique."),
    # RÉCURRENT, et c'est le bon geste. « Sentiers sous-marins du littoral » au pluriel :
    # ce n'est ni un lieu unique ni une date unique. Le Département propose ces sorties
    # tout l'été sur plusieurs sites (Théoule-sur-Mer du 15 juin au 15 septembre,
    # Roquebrune-Cap-Martin chaque vendredi du 10 juillet au 28 août). Poser une date
    # enverrait quelqu'un sur une plage un jour sans animateur.
    4690: ({"recurring": 1,
            "recurring_note": "Sorties accompagnées sur les sentiers sous-marins du "
                              "littoral azuréen, tout l'été et sur plusieurs sites — "
                              "inscription obligatoire, vérifiez le calendrier et le "
                              "point de rendez-vous sur la source"},
           "alpes-maritimes.gouv.fr + roquebrune-cap-martin.fr — programme saisonnier "
           "multi-sites, sans date unique"),
}

# ⚠️ UN NUMÉRO NE DOIT APPARAÎTRE QU'UNE FOIS DANS CE DICTIONNAIRE. Écrit le 2026-08-11
# après m'être fait avoir : en ajoutant « 3279 : récurrent », j'ai ÉCRASÉ le « 3279 :
# ville=Torino » posé trois heures plus tôt — Python garde la dernière clé, sans un mot.
# Les fiches de Villefranche (4720-4723) étaient dans le même cas. Le contrôle ci-dessous
# relit le fichier source et compte les clés écrites, pas celles qui ont survécu.
def _verifie_pas_de_doublon() -> None:
    import ast
    arbre = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Dict):
            continue
        cles = [k.value for k in noeud.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, int)]
        doublons = {c for c in cles if cles.count(c) > 1}
        if doublons:
            raise SystemExit(
                f"scripts/completer_verifie : fiche(s) {sorted(doublons)} écrite(s) deux "
                f"fois — la seconde écrase la première en silence. Fusionner les entrées.")


_verifie_pas_de_doublon()


# ── Fiches à écarter, et POURQUOI (le motif est la moitié de la décision) ────────────
_ECARTS: dict[int, str] = {
    # Événements TERMINÉS, que leur absence de date empêchait de classer (règle 5).
    3082: "Nice Jazz Fest : 23-25 juillet 2026, terminé",
    3094: "Guitare en Scène : la date citée était le 18 juillet 2026, terminé",
    # PAS DES ÉVÉNEMENTS — billets de blog du Circolo dei Lettori. Leur adresse contient
    # « /blog/ », et la 2676 n'a même pas de titre. La charte §3 est explicite : n'est pas
    # un événement ce à quoi on ne peut pas assister à une date.
    218: "billet de blog du Circolo dei Lettori, pas un événement",
    219: "billet de blog du Circolo dei Lettori, pas un événement",
    227: "billet de blog du Circolo dei Lettori (« blog-marginalia »), pas un événement",
    2676: "page de blog du Circolo dei Lettori, sans même un titre",
    # CONGRÈS ET B2B — charte : « un congrès, un colloque scientifique ou un salon B2B
    # n'a pas sa place, même ouvert à tous ». C'est le PUBLIC VISÉ qui décide.
    # INTROUVABLE PARTOUT, et pas faute d'avoir cherché (2026-08-11, 21h). La « balade
    # gourmande aux Charmettes » n'est annoncée que dans la lettre de la Ville de
    # Chambéry. Huit sources ouvertes, aucune ne la connaît : chambery.fr/207 (page des
    # Charmettes), chambery.fr/621 (programme de l'été, 300 animations), l'agenda des
    # musées de Chambéry, chamberymontagnes.com, explore-savoie, agendaculturel 73.
    #
    # Le programme d'été des Charmettes annonce « concerts et siestes musicales dans les
    # jardins, balades BOTANIQUES, séances de Pilates ou ateliers herbier ». Le doute est
    # donc double : la date manque, et l'intitulé lui-même ne correspond à rien de publié.
    #
    # Sans date, la fiche ne peut pas être publiée — la porte qualité l'exige — donc elle
    # resterait indéfiniment dans la file. On ne publie pas un rendez-vous dont on est
    # incapable de dire quand il a lieu. Réversible d'un clic si la Ville l'annonce.
    4247: "Balade gourmande aux Charmettes — annoncée dans la seule lettre de Chambéry, "
          "introuvable sur les huit sources publiques consultées ; le programme des "
          "Charmettes ne mentionne que des balades BOTANIQUES. Sans date, impossible à "
          "publier",

    # PAS UN ÉVÉNEMENT PUBLIC — trouvé le 2026-08-11 en cherchant à répondre au point
    # « format exact : masterclass, cours ouvert ou concert public ? ». Réponse : aucun
    # des trois. Les rendez-vous « Chitarra Jazz (Prof. L. Tessarollo) » du calendrier du
    # Conservatoire sont des sessions d'EXAMEN (« Appello Esami », 9h-14h, Aula 13, via
    # Mazzini 11). La charte demande un public VISÉ ; un examen n'en a aucun. Le doute
    # posé par l'enrichissement était donc mieux fondé qu'il n'en avait l'air — il ne
    # portait pas sur un détail de format, mais sur la nature même de la fiche.
    3734: "Conservatoire de Turin — session d'examen de guitare jazz, pas un rendez-vous "
          "public (conservatoriotorino.eu, « Appello Esami »)",
    3089: "IASP World Conference — congrès professionnel (et Sophia Antipolis est dans "
          "l'arrondissement de Grasse)",
    3090: "Talent in Tech — rencontre professionnelle",
    3091: "Colloque International Villes et Santé Mentale — colloque scientifique",
    # ACTION SOCIALE MUNICIPALE (La Ravoire). Public visé : les administrés d'une commune,
    # pas un public culturel. « Récital chant et piano » (4658) est GARDÉ : celui-là est
    # bien un événement culturel, et la frontière se trace là.
    # ── Les trois de la file du 11/08 au soir dont l'événement est TERMINÉ ─────────────
    # Elles n'avaient pas de date, donc la règle 5 ne pouvait pas les classer en passé —
    # le cercle vicieux : sans date, pas de tri ; sans tri, personne ne va lire la page.
    # La seule sortie est d'aller la lire, et c'est ce qui a été fait.
    3834: "Festival AstroValberg : 17-19 juillet 2026, terminé "
          "(astrovalberg.departement06.fr, alpesdazur-tourisme.fr)",
    3835: "Les Folies des Lacs, lac de La Colmiane : 19 juillet 2026, 26e édition, "
          "terminé (soirees-estivales.departement06.fr, 06-only.fr)",
    4364: "Cordata 4061 : projet de juin 2026 (ascensions les 9-10 et 12-13 juin), "
          "restitution le lundi 27 juillet 2026 à la Maison de la Grivola de Cogne — "
          "terminé. ⚠️ La page gpff.it affiche « 29 Luglio 2026 » : c'est la date de "
          "PUBLICATION du communiqué, pas celle de l'événement. Le même piège que la "
          "colonne date_start, à un étage de plus.",
    4657: "La Ravoire — fête de rentrée municipale",
    4659: "La Ravoire — sensibilisation aux gestes qui sauvent, action de prévention",
    4660: "La Ravoire — thé dansant du CCAS",
    4661: "La Ravoire — atelier « bien vivre à domicile », action sociale",
    4662: "La Ravoire — visite d'équipement municipal",
    4663: "La Ravoire — conférence santé « le sommeil », action de prévention",
    # TROUVÉE EN OUVRANT LA PAGE : cette exposition s'est tenue du 8 juin au 3 septembre
    # 2023. Elle attendait une date depuis TROIS ANS dans la file, et aucune passe ne
    # pouvait la libérer — sans date, la règle 5 refuse (à raison) de la classer en
    # passé. C'est exactement le cercle vicieux décrit ce matin, et la seule sortie était
    # d'aller lire la page.
    4563: "Museo del Risorgimento — exposition du 8 juin au 3 septembre 2023, terminée "
          "depuis trois ans (museorisorgimentotorino.it)",
    # LE GRAND CONTINENT SUMMIT — proposé le matin, tranché le soir. La charte §2 est
    # explicite : « un congrès, un colloque scientifique ou un salon B2B n'a pas sa place,
    # même ouvert à tous ». C'est le PUBLIC VISÉ qui décide, jamais le mot du titre.
    #
    # Ce sommet réunit sur invitation environ 180 chefs de gouvernement, intellectuels et
    # scientifiques ; seul le colloque inaugural est ouvert sur inscription. Et l'édition
    # documentée (3-5 décembre, Grand Hotel Billia puis Petit Cervin) est celle de 2025 —
    # aucune édition 2026 n'était annoncée au 2026-08-11, alors que la fiche affirme
    # « du 3 au 6 décembre ».
    #
    # Ses deux points « À vérifier » (tarif, langue des sessions) sont insolubles pour la
    # même raison : on ne publie pas les conditions d'accès d'un événement sur invitation.
    # Écarter la fiche les fait disparaître avec elle, et c'est la bonne issue — pas un
    # humain qui cherche une réponse qui n'existe pas.
    3379: "Grand Continent Summit — colloque sur invitation (≈180 responsables et "
          "chercheurs), hors charte §2 ; et l'édition documentée est celle de 2025, "
          "aucune 2026 annoncée au 11/08 (regione.vda.it, summit.legrandcontinent.eu)",

    # PROPOSÉS PAR L'AGENT QUOTIDIEN À SON PREMIER RUN, motifs vérifiés et repris ici.
    2374: "Per Olivia (Teatro Stabile) — la page ne porte AUCUNE date, ni au 11/08 ni "
          "auparavant : les dates de la Stagione 2026-2027 vivent sur vivaticket. Rien à "
          "trouver, jamais — vérifié deux fois, le matin et par l'agent le soir",
    4314: "Musei Reali — fiche incohérente : la page décrit le programme du mois d'AOÛT, "
          "la fiche porte lieu='OGR' (un autre établissement) et une fin au 15 septembre. "
          "Trois informations qui ne parlent pas du même événement",
    # VENCE : arrondissement de Grasse, donc hors périmètre (arbitrage confirmé le
    # 2026-08-11). La règle par commune ne l'attrape pas — son champ `ville` est vide,
    # justement parce qu'elle est dans cette file pour ça. D'où l'inscription nominative.
    2611: "Vence — arrondissement de Grasse, hors périmètre (champ ville vide, donc "
          "invisible pour la règle par commune)",
}


def _est_vide(valeur) -> bool:
    """La colonne est-elle à remplir ? Vraie pour NULL, chaîne vide, et 0.

    ÉCRIT APRÈS UN PLANTAGE EN PRODUCTION (2026-08-11, 18h58) : le test était
    `(row[c] or "").strip()`, ce qui suppose une chaîne. Il a tenu tant que le script ne
    posait que du texte — puis `recurring` est arrivé, un ENTIER, et la deuxième exécution
    est tombée sur « 'int' object has no attribute 'strip' ».

    Le défaut n'apparaissait qu'au SECOND passage : au premier, la colonne valait NULL et
    `None or ""` donnait une chaîne. C'est le pire moment pour tomber — après avoir écrit.
    Un script destiné à être rejoué doit être testé rejoué.

    `0` compte comme vide : un `recurring` à zéro n'est pas une décision qu'on protège,
    c'est l'absence de décision."""
    if valeur is None:
        return True
    if isinstance(valeur, (int, float)):
        return not valeur
    return not str(valeur).strip()


def _norm(s: str) -> str:
    n = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return " ".join("".join(c for c in n if not unicodedata.combining(c)).split())


# ── La clause « remplace » : corriger une valeur FAUSSE sans jamais écraser à l'aveugle ──
# Remplie uniquement par --depuis. {id: {colonne: valeur attendue en base}}
_REMPLACEMENTS: dict[int, dict] = {}


def _valeur_attendue(actuelle, attendue) -> bool:
    """La base contient-elle bien ce que l'appelant croit y trouver ?

    POURQUOI CETTE POIGNÉE DE MAIN. Le script refusait jusqu'ici d'écraser tout champ
    rempli — protection juste, et devenue un mur : l'agent quotidien a signalé le
    2026-08-11 trois fiches datées la bonne journée mais la mauvaise ANNÉE (4440 en 2025,
    4691 et 4434 en 2024). Une année fausse n'est pas un trou, c'est une erreur ; la porte
    ne savait combler que les trous. Ces fiches seraient restées fausses indéfiniment —
    et invisibles, puisqu'une date passée les sort de toutes les files (règle 5).

    Ouvrir la porte en grand aurait été pire : un agent qui écrase sur la foi de sa propre
    lecture peut effacer une correction que Franck venait de faire à la main, sans que
    rien ne le signale. D'où la poignée de main : l'appelant doit DÉCLARER la valeur
    fausse qu'il croit remplacer. Si la base dit autre chose, quelqu'un est passé entre
    temps — et c'est lui qui a raison, parce qu'il a agi APRÈS.

    Comparaison souple sur la forme (espaces, casse, accents), stricte sur le fond : on
    tolère « 2024-07-05 » écrit « 2024-07-05 », pas « 2024-07-06 »."""
    if _est_vide(actuelle) and _est_vide(attendue):
        return True
    return _norm(str(actuelle)) == _norm(str(attendue))


def _communes_grasse() -> set[str]:
    """Les 62 communes de l'arrondissement de Grasse — HORS PÉRIMÈTRE.

    Arbitrage Franck confirmé le 2026-08-11 : « hors périmètre », sans nuance. La charte
    le disait déjà (« pas seulement sans étiquette »), le fichier de configuration disait
    l'inverse ; c'est le fichier qui avait tort, il a été corrigé le même jour."""
    d = json.loads(COMMUNES.read_text(encoding="utf-8"))
    return {_norm(c) for c in d["arrondissement_de_grasse"]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    ap.add_argument("--depuis", help="fichier JSON de valeurs vérifiées à ajouter à celles "
                                     "écrites en dur : {\"4621\": {\"champs\": "
                                     "{\"lieu\": \"…\"}, \"source\": \"…\"}}. Pour CORRIGER "
                                     "une valeur fausse (et non combler un trou), ajouter "
                                     "\"remplace\": {\"date_event_start\": \"<la valeur "
                                     "fausse attendue en base>\"}")
    args = ap.parse_args(argv)

    # PORTE D'ENTRÉE DE L'AGENT QUOTIDIEN (2026-08-11). Il ouvre les pages, lit, et dépose
    # ses trouvailles dans un JSON — il n'écrit JAMAIS en base directement. Tout passe donc
    # par les mêmes garde-fous que les valeurs écrites à la main : on n'écrase rien, une
    # source est obligatoire, le bilan est recompté, et le dry-run reste le défaut.
    #
    # C'est délibérément plus étroit qu'un accès SQL : un agent qui écrit lui-même peut se
    # tromper de colonne, de fiche, ou écraser un champ que Franck venait de corriger. Ici
    # il ne peut que PROPOSER des valeurs, dans un format que ce script sait vérifier.
    if args.depuis:
        brut = json.loads(Path(args.depuis).read_text(encoding="utf-8"))
        for cle, val in brut.items():
            champs = (val or {}).get("champs") or {}
            source = ((val or {}).get("source") or "").strip()
            if not champs or not source:
                print(f"  [{cle}] ignorée : il manque les champs ou la source")
                continue
            inconnus = set(champs) - {"lieu", "ville", "date_event_start",
                                      "date_event_end", "url_officiel",
                                      "recurring", "recurring_note"}
            if inconnus:
                print(f"  [{cle}] ignorée : champ(s) non autorisé(s) {sorted(inconnus)}")
                continue
            # ── LA PORTE « ÉVÉNEMENT PASSÉ », ouverte le 2026-08-11 au soir ──────────
            # Franck : « on est passé de quatre cents tâches à une, et sans IA ». Vrai —
            # mais l'essentiel du gain n'est PAS venu de champs comblés : il est venu de
            # fiches ÉCARTÉES parce que l'événement avait déjà eu lieu. Vingt-deux ce
            # jour-là, dont une soirée de soutien à l'Ukraine d'avril 2022 encore en ligne.
            #
            # Or la consigne de l'agent lui interdit d'écarter, et elle a raison : décider
            # qu'un colloque ou un billet de blog n'a pas sa place est un arbitrage
            # ÉDITORIAL. « L'événement a eu lieu le 26 avril 2026 » n'en est pas un : c'est
            # un FAIT, et un fait que ce script peut vérifier tout seul.
            #
            # D'où cette porte étroite : l'agent ne dit pas « écarte-la », il dit « voici
            # la date à laquelle elle a eu lieu, et voici la source ». Le script refuse si
            # la date est illisible, si elle n'est pas passée, ou si la source manque. Il
            # ne peut donc PAS servir à écarter par goût.
            passe = (val or {}).get("passe") or {}
            if passe:
                reelle, preuve = str(passe.get("date") or ""), str(passe.get("source") or "")
                try:
                    d = date.fromisoformat(reelle[:10])
                except ValueError:
                    print(f"  [{cle}] « passe » ignorée : date illisible ({reelle!r})")
                    continue
                if d >= date.today():
                    print(f"  [{cle}] « passe » REFUSÉE : {reelle} n'est pas passé. "
                          f"Un événement à venir ne s'écarte pas sur ce motif.")
                    continue
                if len(preuve.strip()) < 20:
                    print(f"  [{cle}] « passe » ignorée : la source doit porter la PHRASE "
                          f"lue, pas seulement un nom de site")
                    continue
                _ECARTS[int(cle)] = (f"Événement passé — a eu lieu le {reelle}. {preuve}")
                continue

            remplace = (val or {}).get("remplace") or {}
            # On ne peut déclarer remplacer que ce qu'on écrit : une clause « remplace »
            # portant sur un champ absent de « champs » ne veut rien dire, et laisserait
            # croire à une correction qui n'aurait pas lieu.
            orphelines = set(remplace) - set(champs)
            if orphelines:
                print(f"  [{cle}] ignorée : « remplace » porte sur des champs non "
                      f"écrits {sorted(orphelines)}")
                continue
            _VALEURS[int(cle)] = (champs, source)
            if remplace:
                _REMPLACEMENTS[int(cle)] = remplace

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    grasse = _communes_grasse()

    # ── 1. Les valeurs vérifiées ────────────────────────────────────────────────────
    print("═══ Valeurs vérifiées à poser ═══\n")
    a_ecrire: list[tuple[int, dict, str]] = []
    for eid, (champs, source) in _VALEURS.items():
        row = conn.execute("SELECT * FROM events_raw WHERE id=?", (eid,)).fetchone()
        if row is None:
            print(f"  [{eid:5}] introuvable en base — ignorée")
            continue
        # ON N'ÉCRASE JAMAIS SANS LE DIRE : si Franck a rempli le champ entre-temps, sa
        # valeur gagne — SAUF si l'appelant a déclaré exactement la valeur fausse qu'il
        # corrige, et que la base la porte encore (cf. _valeur_attendue).
        attendu = _REMPLACEMENTS.get(eid, {})
        neufs, deja, desaccords = {}, {}, []
        for c, v in champs.items():
            if _est_vide(row[c]):
                neufs[c] = v
            elif c not in attendu:
                deja[c] = row[c]
            elif _valeur_attendue(row[c], attendu[c]):
                neufs[c] = v
            else:
                desaccords.append((c, row[c], attendu[c]))
        if deja:
            print(f"  [{eid:5}] déjà rempli, laissé tel quel : {deja}")
        for c, actuelle, attendue in desaccords:
            print(f"  [{eid:5}] REFUSÉ sur {c} : la base contient « {actuelle} », "
                  f"la correction en attendait « {attendue} ». Quelqu'un est passé "
                  f"depuis — sa valeur gagne.")
        if neufs:
            a_ecrire.append((eid, neufs, source))
            detail = ", ".join(f"{c}={v}" for c, v in neufs.items())
            print(f"  [{eid:5}] {detail}\n          ↳ {source}")
            corriges = sorted(set(attendu) & set(neufs))
            if corriges:
                print(f"          ⚠ CORRECTION d'une valeur fausse sur "
                      f"{', '.join(corriges)} — ancienne valeur déclarée et retrouvée "
                      f"en base ({', '.join(str(attendu[c]) for c in corriges)})")

    # ── 2. Les écarts nommés ────────────────────────────────────────────────────────
    print(f"\n═══ À écarter (statut « rejeté », réversible) ═══\n")
    a_ecarter: list[tuple[int, str]] = []
    for eid, motif in _ECARTS.items():
        row = conn.execute("SELECT id, statut, title FROM events_raw WHERE id=?",
                           (eid,)).fetchone()
        if row is None or row["statut"] == "rejected":
            continue
        a_ecarter.append((eid, motif))
        print(f"  [{eid:5}] {motif}\n          {(row['title'] or '')[:74]}")

    # ── 3. L'arrondissement de Grasse, par la RÈGLE et non par une liste d'identifiants
    # Écrire les numéros à la main aurait raté celles qui arrivent demain. La règle, elle,
    # vaut pour toutes les collectes futures.
    print(f"\n═══ Hors périmètre : arrondissement de Grasse ═══\n")
    for row in conn.execute(
            "SELECT id, ville, title FROM events_raw WHERE COALESCE(ville,'') <> '' "
            "AND statut NOT IN ('rejected','merged')"):
        if _norm(row["ville"]) not in grasse:
            continue
        a_ecarter.append((row["id"], f"{row['ville']} — arrondissement de Grasse"))
        print(f"  [{row['id']:5}] {row['ville']:<24} {(row['title'] or '')[:56]}")

    if not args.apply:
        print(f"\nSimulation — RIEN n'a été écrit."
              f"\n{len(a_ecrire)} fiche(s) recevraient une valeur, "
              f"{len(a_ecarter)} seraient écartées. Ajouter --apply.")
        conn.close()
        return 0

    for eid, neufs, _ in a_ecrire:
        sets = ", ".join(f"{c}=?" for c in neufs)
        conn.execute(f"UPDATE events_raw SET {sets} WHERE id=?", (*neufs.values(), eid))
    for eid, _ in a_ecarter:
        conn.execute("UPDATE events_raw SET statut='rejected' WHERE id=?", (eid,))
    conn.commit()

    # RECOMPTÉ EN BASE, et sur le périmètre EXACT de la pastille (règle 6) : c'est le
    # seul nombre qui répond à « est-ce que ça avance ? ».
    from scripts.lister_a_completer import _clause
    # `date` est importé en tête du module depuis le 2026-08-11 : le ré-importer ICI en
    # faisait une variable LOCALE à main(), donc inaccessible plus haut dans la fonction.
    # Python décide de la portée à la compilation, pas à l'exécution.
    where, params = _clause(date.today().isoformat())
    reste = conn.execute(f"SELECT COUNT(*) FROM events_raw WHERE {where}",
                         params).fetchone()[0]
    rejetees = conn.execute("SELECT COUNT(*) FROM events_raw WHERE statut='rejected'"
                            ).fetchone()[0]
    conn.close()
    print(f"\n✅ {len(a_ecrire)} fiche(s) complétées, {len(a_ecarter)} écartées.")
    print(f"   La file « À compléter » contient maintenant {reste} fiche(s) "
          f"— même périmètre que la pastille du back-office.")
    print(f"   {rejetees} fiche(s) rejetées au total en base (rien n'est supprimé : "
          f"un rejet se défait).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
