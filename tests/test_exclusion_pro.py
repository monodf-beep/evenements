#!/usr/bin/env python3
"""Test des exclusions éditoriales (config/excluded_event_keywords.txt), volet PRO.

⚠️ TEST SUR FIXTURE, PAS SUR LA BASE. `data/events.db` est hors dépôt Git : les cas
ci-dessous sont RECONSTRUITS à la main. Deux d'entre eux viennent d'un dry-run réel de
`scripts/audit_excluded_events` sur les 348 fiches publiées du 2026-08-04 — ce sont eux
qui ont dicté la conception, pas l'inverse :

  • « Afterwork LifeSciences » (WP#1147) — vrai positif, événement B2B publié ;
  • « Salone Auto Torino 2026 » (WP#6405) — FAUX POSITIF : salon automobile GRAND
    PUBLIC de Turin, dans le périmètre, attrapé parce que « btob » était cherché dans
    les DESCRIPTIONS et que l'article de TorinoClick mentionnait son volet BtoB.

C'est ce faux positif qui a produit les deux portées `[partout]` / `[titre]`. Le test
doit donc prouver les DEUX SENS, sans quoi il ne prouve rien :
  • les marqueurs pro rejettent bien les événements d'affaires ;
  • ils laissent passer les événements que la charte protège — « Conférences &
    Rencontres » est une de nos onze catégories, un salon du livre est un salon, un
    Palais des Congrès est une salle de concert.

Lancer : .venv/bin/python -m tests.test_exclusion_pro
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.sources import is_excluded_event, load_excluded_events_filter  # noqa: E402

# (titre, description, url_source, exclu_attendu, ce que le cas prouve)
CAS = [
    # ── Les deux exemples signalés par Franck le 2026-08-04 ──
    ("Côte d'Azur Life Sciences Afterwork", "Rencontre des acteurs de la santé.",
     "https://us.list-manage.com/track/xyz", True, "« afterwork » dans le titre"),
    ("French Riviera Beauty", "Convention de la filière cosmétique.",
     "https://event.businessfrance.fr/french-riviera-beauty/", True,
     "domaine businessfrance dans l'URL source"),
    ("French Riviera Beauty", "Convention de la filière cosmétique.",
     "https://us.list-manage.com/NEbt0b0Fxb4?e=06a93eea46", True,
     "exclusion NOMMÉE : la fiche réelle (2465) porte une redirection Mailchimp comme "
     "url_source, aucun marqueur générique ne l'attrapait"),

    # ── Le faux positif du dry-run : il doit rester publiable ──
    ("Salone Auto Torino 2026, svelati brand e novità della terza edizione",
     "L'edizione 2026 si terrà in centro città, con un'area BtoB il primo giorno e "
     "ingresso libero per tutti nel fine settimana.",
     "https://www.torinoclick.it/societa/salone-auto-torino-2026/", False,
     "salon GRAND PUBLIC : « btob » en description ne doit plus rejeter"),

    # ── Portée : le même mot rejette dans un titre, pas dans une description ──
    ("Congrès B2B de la plasturgie", "Deux jours de rendez-vous fournisseurs.",
     "https://x.fr", True, "[titre] : « b2b » dans le titre rejette"),
    ("Festival du film alpin", "Un afterwork est prévu pour les partenaires le jeudi.",
     "https://x.fr", False, "[titre] : « afterwork » en description ne rejette pas"),
    ("Serata networking startup Torino", "Ritrovo mensile.", "https://x.it", True,
     "[titre] : marqueur italien dans le titre"),
    ("Turin Tech Night", "Serata networking per startup.", "https://x.it", False,
     "[titre] : le même marqueur en description laisse juger le LLM"),

    # ── Marqueurs [partout] : ils NOMMENT le public, ils ne peuvent pas être anodins ──
    ("Salon professionnel du BTP", "Trois jours d'expositions.", "https://x.fr", True,
     "salon professionnel"),
    ("Visite du chantier naval", "Journée réservée aux professionnels du nautisme.",
     "https://x.fr", True, "« réservée aux professionnels » en description"),
    ("Fiera del mobile", "Ingresso riservato agli operatori del settore.",
     "https://x.it", True, "« riservato agli operatori » en description"),
    ("Alpes Business Meetings", "Rendez-vous d’affaires transfrontaliers.",
     "https://x.fr", True, "apostrophe typographique (’) reconnue"),

    # ── Ce que la charte protège : doit passer ──
    ("Salon du livre de Chambéry", "Dédicaces et rencontres avec les auteurs.",
     "https://x.fr", False, "un salon du livre n'est pas un salon professionnel"),
    ("Café philo : la liberté", "Discussion ouverte à tous.", "https://x.fr", False,
     "catégorie « Conférences & Rencontres »"),
    ("Conférence au musée des Beaux-Arts", "Un conservateur présente l'exposition.",
     "https://x.fr", False, "« conférence » n'est pas un marqueur pro"),
    ("Concert de Noël", "Au Palais des Congrès d'Aix-les-Bains, à 20h30.",
     "https://x.fr", False, "« congrès » est ici le nom d'une SALLE"),
    ("Marché de Noël d'Annecy", "Artisanat et vin chaud. Inscrivez-vous à la lettre.",
     "https://us.list-manage.com/track/abc", False,
     "us.list-manage.com est le facteur (Mailchimp), pas un marqueur pro"),
    ("Workshop de danse contemporaine", "Stage ouvert à tous niveaux.",
     "https://x.fr", False, "« workshop » seul reste au jugement du LLM"),
    ("Masterclass de piano", "Avec les élèves du conservatoire, entrée libre.",
     "https://x.fr", False, "« masterclass » seul reste au jugement du LLM"),
    ("Rencontre avec Erri De Luca", "L'écrivain présente son dernier roman.",
     "https://x.fr", False, "« rencontre » seul reste au jugement du LLM"),
    ("Sagra del tartufo", "Degustazioni aperte a tutti, operatori e pubblico.",
     "https://x.it", False, "« operatori » sans « riservato » ne rejette pas"),

    # ── Les règles historiques ne doivent pas avoir été cassées par les sections ──
    ("Cérémonie du 27e BCA", "Passation de commandement.", "https://x.fr", True,
     "règle BCA d'origine, toujours active sous [partout]"),
]


def main() -> int:
    exclusions = load_excluded_events_filter()
    echecs = 0
    for titre, description, url, attendu, preuve in CAS:
        obtenu = is_excluded_event(titre, description, exclusions, url=url)
        if obtenu != attendu:
            echecs += 1
            print(f"ÉCHEC exclu={obtenu} attendu={attendu} | {titre[:48]} | {preuve}")
        else:
            print(f"OK    exclu={str(obtenu):5} | {titre[:48]:50} | {preuve}")
    print(f"\n{len(CAS) - echecs}/{len(CAS)} cas conformes.")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
