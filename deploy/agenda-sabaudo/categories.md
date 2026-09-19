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
- **Libellés de tuile localisés (Polylang)** : la catégorie `gastronomie-sagre`
  s'affiche **« Gastronomie » en FR** et **« Sagre » en IT** (« sagra » n'existe pas
  en France → obscur en tuile FR ; le mot reste un aimant éditorial dans les listicles
  « Les sagre du Piémont »). Même catégorie dessous.
- **Grille principale de la home (6 tuiles)** : Ce week-end · **Gastronomie**
  (IT : Sagre) · Concerts & Musique · Expositions & Patrimoine · **Jeune public &
  Famille** · Tout l'agenda.
- **Grille secondaire (découverte, 4 tuiles)** : Aux alentours (transfrontalier) ·
  Musées (lieux) · Curiosités (éditorial) · **Jeune public & Famille**.
  ❌ **Pas de tuile « Météo »** (utilitaire hors mission, ambiguë sur 4 territoires,
  dépendance externe). ❌ **Pas de tuile « Gratuit »** (donnée prix non fiable →
  simple filtre/badge plus tard).
- Les 11 catégories restent toutes accessibles via le menu.
- **« Gratuit »** n'est PAS une catégorie : c'est une étiquette + champ booléen
  (vue `/fr/evenements/gratuit/`), cf. taxonomie §2.2.
- **Le temps** (ce week-end, aujourd'hui…) n'est jamais une catégorie : ce sont des
  hubs evergreen qui interrogent les dates.
