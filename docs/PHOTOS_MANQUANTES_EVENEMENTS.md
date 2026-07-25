# Événements sans vraie photo (affichant une image de repli)

> Livrable actionnable pour le chantier « une vraie photo par événement ».
> Établi le 2026-07-26 par requête directe sur le site live (lecture seule).

## Découverte importante : les images de repli sont bakeées comme miniatures

Contrairement à ce qu'on supposait, un événement « sans photo » n'a **pas** de
`_thumbnail_id` vide. À un moment, les images de repli (`fallback-<territoire>-<categorie>`)
ont été **inscrites en dur comme vraie miniature** (`_thumbnail_id`) sur les
événements qui n'avaient pas de photo propre.

**Conséquence méthodologique** : pour détecter un événement sans vraie photo, il
faut tester si le **slug de la miniature commence par `fallback-`**, et NON si
`_thumbnail_id` est vide (il ne l'est jamais). Un diagnostic qui teste seulement
« thumbnail vide » conclura à tort « 0 événement sans photo ».

**Conséquence technique à noter** : le filtre de repli à l'affichage (snippet 87)
est en partie redondant pour ces événements, puisqu'ils portent déjà l'image de
repli comme vraie miniature. À vérifier si on veut nettoyer.

## Chiffres (événements futurs, `_EventEndDate >= maintenant`)

| Langue | Total futurs | Vraie photo | Image de repli (à sourcer) |
|---|---|---|---|
| FR | 118 | 99 | **19** |
| IT | 88 | 65 | **23** |

## Liste FR (19) — cibles pour sourcing d'une vraie photo

Triée par date de début. `src` = présence d'une URL de source officielle
(`as_source_officielle_url`), utile pour retrouver un visuel côté organisateur.

| Territoire | Ville | ID | Titre | Catégorie | Début | Source |
|---|---|---|---|---|---|---|
| Savoie | Chambéry | 2013 | Quand la nuit s'affiche | Expositions & Patrimoine | 2025-09-20 | oui |
| Comté de Nice | Nice | 1856 | Jazz Art | Concerts & Musique | 2026-05-13 | oui |
| Comté de Nice | Saint-Paul-de-Vence | 588 | Peter Knapp: the era of Courrèges | Expositions & Patrimoine | 2026-05-14 | oui |
| Savoie | Montmélian | 599 | Festival Photo de Montmélian, 9e édition | Expositions & Patrimoine | 2026-06-13 | oui |
| Comté de Nice | Villefranche-sur-Mer | 804 | Exposition « L'Absurde et le Rêve » (Joana Vasconcelos, Arne Quinze) | Expositions & Patrimoine | 2026-06-20 | oui |
| Vallée d'Aoste | Bard | 608 | Au Forte di Bard, l'été des enfants explorateurs | Jeune public & Famille | 2026-06-23 | oui |
| Comté de Nice | Saint-Jean-Cap-Ferrat | 612 | À Saint-Jean-Cap-Ferrat, un piano flotte sur le port | Festivals | 2026-06-27 | oui |
| Comté de Nice | Saint-Laurent-du-Var | 617 | Beach Sport Festival 2026 | Sport | 2026-06-30 | oui |
| Comté de Nice | Vence | 1119 | Exposition : Itinérances | Expositions & Patrimoine | 2026-07-14 | oui |
| Vallée d'Aoste | Aoste | 1668 | Rencontres musicales de la Vallée : festival d'été à Aoste | Festivals | 2026-07-25 | NON |
| Comté de Nice | Vence | 1971 | Visites guidées | Expositions & Patrimoine | 2026-07-29 | oui |
| Savoie | Chambéry | 1674 | Marché gourmand de Chambéry | Marchés & Foires | 2026-08-01 | NON |
| Piémont | Pragelato | 1677 | Sagra della Toma e dei Sapori di Montagna | Gastronomie & Sagre | 2026-08-03 | NON |
| Comté de Nice | Nice | 1680 | Atelier famille au Muséum d'Histoire Naturelle de Nice | Jeune public & Famille | 2026-08-05 | NON |
| Savoie | Chambéry | 1683 | Spectacle de rue : la Compagnie Les Arpenteurs | Spectacle vivant | 2026-08-07 | NON |
| Savoie | Aillon-le-Jeune | 1902 | Les Noces de Figaro | Concerts & Musique | 2026-08-07 | oui |
| Piémont | Torino | 1686 | Course pédestre des Collines : trail urbain à Turin | Sport | 2026-08-10 | NON |
| Savoie | Chambéry | 911 | Visite flash : patrimoine vivant | Expositions & Patrimoine | 2026-09-18 | oui |
| Piémont | Cuneo | 2271 | Dialoghi sul Talento con George Clooney | Conférences & Rencontres | 2027-04-08 | oui |

Édition admin d'un événement : `/wp-admin/post.php?post=<ID>&action=edit`.

## Priorité de sourcing suggérée

1. Les **6 sans source** (`src:NON`) : pas d'URL organisateur pour retrouver un
   visuel, ce sont les plus « aveugles » (IDs 1668, 1674, 1677, 1680, 1683, 1686).
2. Les **13 avec source** : le visuel peut souvent être récupéré depuis le site
   de l'organisateur (droits à vérifier).

Les 23 événements IT équivalents sont majoritairement les traductions de ces
mêmes événements : sourcer la photo côté FR et la réutiliser côté IT couvre les
deux d'un coup (même événement, post distinct par langue).
