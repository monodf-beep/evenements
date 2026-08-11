#!/usr/bin/env python3
"""Ferme les points « À vérifier » dont la réponse est CONNUE, et l'inscrit.

Franck, 2026-08-11 au soir, capture d'écran de la file à l'appui : « on a encore toutes
ces erreurs ». Il montrait « Stefania Marchiano : autrice de l'article ou organisatrice ? »,
« Rôle exact d'Amelio Ambrosi », « Ambra Angiolini présente-t-elle aussi la clôture ? »…

C'est-à-dire EXACTEMENT les points que j'avais vérifiés le matin même, un par un, sur les
sources officielles — à sa demande (« c'est à toi de vérifier »). J'ai écrit les réponses
dans docs/VERIFICATION_2026-08-11.md, et je n'ai jamais fermé les points. Le travail était
fait, il n'a simplement jamais atteint l'écran.

C'est la même faute que le cron posé dans le mauvais fichier, que le compteur au mauvais
périmètre, que l'après-midi passé à optimiser le mauvais stock : **un résultat qui n'arrive
pas là où on le regarde n'existe pas.**

CE QUE FAIT CE SCRIPT
  • il ferme (statut « done », comme le bouton ✓ du back-office — réversible) les points
    dont la réponse est établie ;
  • il POSE LA RÉPONSE en clair, en ajoutant un point déjà vérifié qui la porte. Sans ça,
    la question disparaît sans que personne sache ce qu'elle est devenue, et elle
    reviendra au prochain enrichissement ;
  • pour une fiche EN LIGNE dont l'ARTICLE affirme encore le contraire, il ouvre un point
    PRÉCIS à la place du doute — « l'organisateur est la Pro Loco, pas Stefania
    Marchiano » — parce que fermer sans corriger laisserait croire le site réparé
    (règle 1). Un doute sans réponse devient une correction à faire : c'est une tâche
    avec un geste au bout, ce que la règle 6 exige.

  .venv/bin/python -m scripts.solder_verifications          # simulation
  .venv/bin/python -m scripts.solder_verifications --apply
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "events.db"))

# (fiche, fragment du point, réponse établie, correction à porter dans l'article ou None)
# Toutes vérifiées le 2026-08-11 sur les sources officielles — détail et liens dans
# docs/VERIFICATION_2026-08-11.md.
_REPONSES: list[tuple[int, str, str, str | None]] = [
    (473, "organisateur reel", "La Foire de Saint-Ours est organisée par la Région "
     "autonome Vallée d'Aoste (Assessorat de l'artisanat). Arabella Pezza signe "
     "l'article (regione.vda.it).",
     "Organisateur : Région autonome Vallée d'Aoste, PAS Arabella Pezza (journaliste)."),
    (3995, "stefania marchiano", "Organisateur : la Pro Loco de Saint-Rhémy-en-Bosses. "
     "Stefania Marchiano signe l'article (laprimalinea.it, 05/08/2026).",
     "Organisateur : Pro Loco de Saint-Rhémy-en-Bosses, PAS Stefania Marchiano."),
    (4381, "amelio ambrosi", "Organisateurs : Assessorat de l'agriculture de la Région "
     "autonome Vallée d'Aoste, Commune de Bard, Chambre valdôtaine et Forte di Bard. "
     "22e édition, 10-11 octobre 2026 (aostaoggi.it). Amelio Ambrosi est contact presse.",
     "Organisateurs : Assessorat de l'agriculture, Commune de Bard, Chambre valdôtaine, "
     "Forte di Bard — PAS Amelio Ambrosi."),
    (4127, "denis falconieri", "Denis Falconieri n'est pas l'organisateur : il signe "
     "l'article. Tsantì de Bouva est l'AIRE VERTE de Fénis, pas un événement.",
     "La fiche prend un LIEU pour un événement : Tsantì de Bouva est l'aire verte de "
     "Fénis, qui accueille plusieurs rendez-vous distincts dans la saison."),
    (4127, "date unique ou", "Ni l'un ni l'autre : Tsantì de Bouva est un LIEU. Il "
     "accueille le Raduno des fanfares (mai-juin), Le Cors dou Heralt (24-25 juillet) et "
     "Etetrad (27-30 août). La fiche est à retailler sur un rendez-vous précis.", None),
    (3545, "emilie dupont", "Non : organisateurs = Ville de Nice avec le Collectif des "
     "Arts Traditionnels – Lou Cat (nice.fr). « Emilie DUPONT » est un nom-bouchon.",
     "Organisateurs : Ville de Nice + Collectif des Arts Traditionnels – Lou Cat."),
    (4125, "loterie romande", "Soutien financier, pas co-organisateur. Le Collontrek a "
     "été fondé en 2009 par Laurent Pitteloud (versant suisse) et Maurizio Lanivi "
     "(versant italien), qui le coordonnent.", None),
    (4621, "cloture", "Ouverture seulement, au Teatro Regio avec le directeur Giulio "
     "Base (torinofilmfest.org). Aucun nom n'est annoncé pour la clôture à ce jour : "
     "ce n'est pas un doute, c'est une information qui n'existe pas encore.", None),
    (2043, "macedoine du nord", "Oui. 66e édition, 12-16 août 2026, cinq pays : Mexique, "
     "Macédoine du Nord, Timor-Leste, Cuba, Bénin (nice.fr).", None),
    (3558, "luz do samba", "Un GROUPE, pas un intitulé de soirée : répertoire brésilien "
     "(Djavan, Ivan Lins, João Donato) relu au prisme du jazz, programmé le 30 juillet.",
     None),
    (3498, "billet unique", "Billetterie PAR SOIRÉE (museireali.midaticket.com). Le "
     "billet donne accès à une section du musée, différente chaque soir, et au spectacle "
     "programmé. Certaines dates ont leur tarif propre.", None),
    (1080, "serie a2", "Oui, en A2 en 2025/26 comme en 2026/27 (legapallacanestro.com). "
     "Mais la division d'un club de basket ne change rien à un événement d'été au "
     "Blooming Playground : ce point n'aurait pas dû exister.", None),
    (580, "fin de tournee", "29 août, à Beaulieu-sur-Mer. Le 28, c'est Vence. Tournée : "
     "La Bollène-Vésubie 19, Clans 20, Isola 21, Levens 24, Tourrette-Levens 26, "
     "Vence 28, Beaulieu-sur-Mer 29 — 20h30, gratuit (nicecotedazur.org).", None),
    (580, "vence fait-elle", "Oui pour la MÉTROPOLE (Vence est l'une des 51 communes de "
     "la Métropole Nice Côte d'Azur). NON pour le Comté de Nice : Vence est dans "
     "l'arrondissement de GRASSE, donc hors périmètre éditorial.", None),
    (3527, "jonathan nott", "NON. Nott a quitté la direction de l'Orchestre de la Suisse "
     "Romande fin 2025 ; Tugan Sokhiev est chef principal (rts.ch). Si l'article le dit "
     "« directeur musical », c'est faux au présent.",
     "Jonathan Nott n'est plus directeur musical de l'OSR depuis fin 2025."),
    (3083, "contre-la-montre", "NON : étape de montagne en circuit, 99 km, ascensions du "
     "col d'Èze, arrivée sur la Promenade des Anglais (letourfemmes.fr).", None),
    (3094, "michael", "Les deux à la fois : le spectacle officiel « This Is Michael » "
     "(Lenny Jay) ET Jennifer Batten, guitariste de Michael Jackson pendant dix ans, "
     "pour leur seule date européenne (guitare-en-scene.com).", None),

    # ── Deuxième fournée, 2026-08-11 au soir. Franck a remis la file à l'écran : « on en
    # fait quoi de ce qui reste ? ». Sur huit points, QUATRE avaient une réponse et
    # personne n'était allé la chercher ; les quatre autres n'en ont pas, et c'est ça
    # qu'il fallait écrire.
    (4705, "titre complet du film", "Rien n'est tronqué : « De la Comédie-Française » EST "
     "le titre complet. Comédie de Martin Darondeau et Bertrand Usclat, sortie le "
     "22/07/2026, avec Pauline Clément et Laurent Stocker, quatre prix à l'Alpe d'Huez "
     "(allociné, villefranche-sur-mer.fr : « 24 août, De la Comédie-Française »). Le "
     "doute venait de ce que le titre commence par une préposition.", None),
    (3594, "nature exacte de liveplay", "Un DJ, pas un orchestre ni un groupe : Live Play "
     "est un service d'animation professionnel (liveplay.fr) qui anime le bal de la "
     "Citadelle Saint-Elme depuis quatorze ans.", None),
    (3734, "format exact", "Ni masterclass ni concert : les rendez-vous « Chitarra Jazz "
     "(Prof. L. Tessarollo) » du calendrier du Conservatoire sont des sessions d'EXAMEN "
     "(« Appello Esami »), 9h-14h, Aula 13, via Mazzini 11 (conservatoriotorino.eu). "
     "La fiche est donc écartée : un examen n'a pas de public visé.", None),
    (3734, "tessarollo joue seul", "Ni l'un ni l'autre : ce sont les ÉLÈVES qui passent "
     "leur examen devant lui. Voir le point ci-dessus.", None),

    # ── LES QUATRE SANS RÉPONSE POSSIBLE, et c'est une réponse ────────────────────────
    # Règle 6 : « avant d'ajouter une ligne à une file, se demander ce que le lecteur en
    # FERA ». Ici il n'en fera rien — l'information n'existe nulle part. Les laisser
    # ouverts, c'est reconstituer la file des 454 « points à contrôler » dont 315
    # n'étaient que les silences de la source. On les ferme EN DISANT pourquoi, sinon
    # l'enrichissement suivant les rouvrira à l'identique.
    (3026, "langue de la mediation", "NON PUBLIÉ. Ni le musée ni le dossier de presse "
     "n'indiquent les langues de l'audioguide. Ce n'est pas un doute sur un fait, c'est "
     "une information qui n'existe pas : ni Franck ni le modèle ne peuvent y répondre. "
     "À la réécriture, ne rien affirmer sur ce point.", None),
    (3545, "accueil pmr", "NON PUBLIÉ. La page de la Ville ne dit ni le mode d'accès "
     "(libre ou sur réservation) ni l'accueil PMR. Point fermé sans réponse — à la "
     "réécriture, ne rien affirmer là-dessus.", None),
    (924, "tarif de 28", "NON PUBLIÉ. La formule à 28 € est annoncée avec le transport ; "
     "la source ne dit pas s'il existe un tarif sans bus. À demander à la salle si la "
     "question revient — elle ne se tranche pas depuis le web.", None),
    (13, "seconde seance", "NON PUBLIÉ à ce jour. La saison « Un été à Albé » court "
     "jusqu'au 20 septembre mais son programme n'annonce qu'une séance de plein air ; "
     "la seconde n'est pas datée publiquement. Rien à corriger : la fiche n'affirme "
     "rien de faux, elle est simplement incomplète sur un point que la source tait.",
     None),
]


def _norm(s: str) -> str:
    n = unicodedata.normalize("NFKD", (s or "").lower())
    return " ".join("".join(c for c in n if not unicodedata.combining(c)).split())


# Les deux libellés que ce script ÉCRIT lui-même. Il ne doit jamais les relire comme des
# doutes à résoudre.
_PREFIXE_CORRECTION = "À CORRIGER dans l'article en ligne — "
_PREFIXE_REPONSE = "✓ Vérifié le 11/08 : "


def _libelle_correction(correction: str) -> str:
    return f"{_PREFIXE_CORRECTION}{correction}"


def _est_de_moi(label: str) -> bool:
    """Ce point a-t-il été écrit par ce script ? Alors on n'y touche pas.

    LE SERPENT QUI SE MORD LA QUEUE, vu en production le 2026-08-11 à 20h50 dans la sortie
    d'un `--apply` que Franck venait de coller. Le script avait ROUVERT, puis refermé, puis
    réécrit ses propres corrections :

        [ 3995] À CORRIGER dans l'article en ligne — Organisateur : Pro Loco de Saint-…
                ✓ Organisateur : la Pro Loco de Saint-Rhémy-en-Bosses…
                ⚠ article EN LIGNE à corriger : Organisateur : Pro Loco…

    La correction posée au premier run contient forcément le fragment recherché (« Stefania
    Marchiano »), donc le second run la prend pour le doute d'origine, la ferme, réinscrit
    la réponse et rouvre une correction NEUVE. Chaque exécution ajoutait deux lignes à la
    table et remettait à zéro l'ancienneté de la tâche — celle qui dit depuis combien de
    temps l'article en ligne est faux.

    C'est la faute que ce dépôt combat depuis le matin, commise par le script écrit pour la
    combattre : un état terminal qui se rejoue sur la même entrée. Et elle était invisible
    dans le code, comme les autres — c'est la LISTE des onze points fermés qui l'a montrée,
    trois d'entre eux portant un libellé que j'avais moi-même rédigé trois heures plus tôt.
    """
    n = _norm(label)
    return n.startswith(_norm(_PREFIXE_CORRECTION)) or n.startswith(_norm(_PREFIXE_REPONSE))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="écrit (défaut : simulation)")
    args = ap.parse_args(argv)

    if not DB_PATH.exists():
        print(f"Base introuvable : {DB_PATH}")
        return 1
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    a_fermer: list[tuple] = []
    for eid, fragment, reponse, correction in _REPONSES:
        ev = conn.execute("SELECT wp_post_id_as FROM events_raw WHERE id=?",
                          (eid,)).fetchone()
        for c in conn.execute("SELECT id, label FROM checks WHERE event_id=? "
                              "AND status='pending'", (eid,)):
            if _est_de_moi(c["label"]):
                continue
            if _norm(fragment) not in _norm(c["label"]):
                continue
            en_ligne = bool(ev and ev["wp_post_id_as"])
            # Ne pas rouvrir une correction qui existe DÉJÀ : elle serait posée deux fois,
            # et la plus ancienne — celle qui porte la vraie date d'ouverture — serait
            # fermée au passage.
            deja = correction and conn.execute(
                "SELECT 1 FROM checks WHERE event_id=? AND label=? AND status='pending'",
                (eid, _libelle_correction(correction))).fetchone()
            a_fermer.append((c["id"], eid, c["label"], reponse,
                             None if deja else correction, en_ligne))

    if not a_fermer:
        print("Aucun point en attente ne correspond aux vérifications du 2026-08-11.")
        conn.close()
        return 0

    print(f"═══ {len(a_fermer)} point(s) dont la réponse est établie ═══\n")
    corrections = 0
    for _cid, eid, label, reponse, correction, en_ligne in a_fermer:
        print(f"  [{eid:>5}] {label[:70]}")
        print(f"          ✓ {reponse[:100]}")
        if correction and en_ligne:
            corrections += 1
            print(f"          ⚠ article EN LIGNE à corriger : {correction[:88]}")

    if not args.apply:
        print(f"\nSimulation — RIEN n'a été écrit. {len(a_fermer)} point(s) seraient "
              f"fermés, {corrections} correction(s) d'article ouverte(s) à la place.")
        conn.close()
        return 0

    for cid, eid, _label, reponse, correction, en_ligne in a_fermer:
        conn.execute("UPDATE checks SET status='done', resolved_at=datetime('now') "
                     "WHERE id=?", (cid,))
        # La réponse est INSCRITE, déjà vérifiée : sans elle, la question disparaît sans
        # que personne sache ce qu'elle est devenue — et elle reviendra au prochain
        # enrichissement, puisque sync_checks ne connaît que les points « pending ».
        libelle = f"{_PREFIXE_REPONSE}{reponse}"
        # Rejouable : la réponse ne s'inscrit qu'une fois. Sans ce test, dix exécutions
        # laissent dix copies de la même phrase sur la fiche.
        if not conn.execute("SELECT 1 FROM checks WHERE event_id=? AND label=?",
                            (eid, libelle)).fetchone():
            conn.execute("INSERT INTO checks (event_id, label, status, resolved_at) "
                         "VALUES (?, ?, 'done', datetime('now'))", (eid, libelle))
        if correction and en_ligne:
            conn.execute("INSERT INTO checks (event_id, label) VALUES (?, ?)",
                         (eid, _libelle_correction(correction)))
    conn.commit()

    # Recompté en base, sur le périmètre de l'écran (règle 6).
    from datetime import date
    sys.path.insert(0, str(ROOT / "app"))
    restant = conn.execute(
        "SELECT COUNT(*) FROM checks c JOIN events_raw e ON e.id=c.event_id "
        "WHERE c.status='pending' AND COALESCE(e.duplicate_of,0)=0 "
        "AND COALESCE(e.statut,'') NOT IN ('merged','rejected') "
        "AND (COALESCE(e.recurring,0)=1 OR COALESCE(NULLIF(e.date_event_end,''), "
        "     NULLIF(e.date_event_start,''), '9999') >= ?)",
        (date.today().isoformat(),)).fetchone()[0]
    conn.close()
    print(f"\n✅ {len(a_fermer)} point(s) fermé(s), leur réponse inscrite en clair.")
    print(f"   {corrections} correction(s) d'article ouverte(s) — ces fiches sont EN "
          f"LIGNE et affirment encore le contraire ; fermer sans corriger laisserait "
          f"croire le site réparé (règle 1).")
    print(f"   {restant} point(s) restent en attente, tous périmètres de l'écran "
          f"confondus (avant filtre des absences, donc ≥ ce que la pastille affiche).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
