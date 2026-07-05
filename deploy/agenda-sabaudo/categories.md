# Les 11 catégories — Agenda Sabauda

Catégories d'événements TEC (taxonomie native `tribe_events_cat`). À créer dans
**Événements → Catégories**. URL des hubs : `/fr/evenements/{slug}/` (base d'archive
`evenements`, cf. runbook §5). Traduire chaque terme en IT avec Polylang (le slug IT
peut différer ; garder l'ordre et le mapping ci-dessous).

| # | Nom exact (FR) | Slug | Libellé IT (Polylang) |
|---|---|---|---|
| 1 | Expositions & Patrimoine | `expositions-patrimoine` | Mostre & Patrimonio |
| 2 | Concerts & Musique | `concerts-musique` | Concerti & Musica |
| 3 | Spectacle vivant | `spectacle-vivant` | Spettacolo dal vivo |
| 4 | Festivals | `festivals` | Festival |
| 5 | Gastronomie & Sagre | `gastronomie-sagre` | Gastronomia & Sagre |
| 6 | Marchés & Foires | `marches-foires` | Mercati & Fiere |
| 7 | Sport | `sport` | Sport |
| 8 | Cinéma | `cinema` | Cinema |
| 9 | Jeune public & Famille | `jeune-public-famille` | Per bambini & Famiglia |
| 10 | Conférences & Rencontres | `conferences-rencontres` | Conferenze & Incontri |
| 11 | Fêtes & Traditions populaires | `fetes-traditions` | Feste & Tradizioni popolari |

## Notes

- **Slugs figés** : ne pas les modifier après indexation (chaque changement casse
  les URLs et les liens accumulés). Ce sont exactement ceux du plan du site.
- **Ordre** : cet ordre est l'ordre d'affichage souhaité (menu « Catégories ▾»,
  footer). WordPress trie par défaut alphabétiquement — forcer l'ordre via le
  thème/menu, pas via le slug.
- **6 tuiles vedettes de la home** (rappel plan du site §2.1) : Ce week-end,
  Tout l'agenda, Expositions & Patrimoine, Concerts & Musique, Festivals + Sagre,
  En famille. Les 11 restent toutes accessibles via le menu.
- **« Gratuit »** n'est PAS une catégorie : c'est une étiquette + champ booléen
  (vue `/fr/evenements/gratuit/`), cf. taxonomie §2.2.
- **Le temps** (ce week-end, aujourd'hui…) n'est jamais une catégorie : ce sont des
  hubs evergreen qui interrogent les dates.
