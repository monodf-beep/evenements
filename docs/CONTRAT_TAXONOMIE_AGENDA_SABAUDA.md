# Contrat de taxonomie · Agenda Sabauda

*Référence commune pour le back-office (saisie / import) et le site (affichage). Le
back-office étiquette, WordPress affiche : les deux doivent parler des mêmes termes, avec
les mêmes identifiants. Ce document est la source de vérité. Toute création ou renommage de
catégorie passe d'abord par ici.*

**Dernière synchronisation base :** 2026-07-22. Renommage des slugs de territoire (`savoie`,
`savoia`, `comte-de-nice`, `contea-di-nizza` ; anciens slugs redirigés en 301) et nom IT de Nice
passé à « Contea di Nizza ». Convention de nommage détaillée : `docs/NOMMAGE_TERRITOIRES.md`.

---

## 0. Les trois invariants

Tout événement publié (`tribe_events`, statut `publish`) doit avoir :

1. **exactement une langue** Polylang (`fr` ou `it`) ;
2. **au moins un territoire** (taxonomie `territoire`) ;
3. **au moins une catégorie** (taxonomie `tribe_events_cat`).

Un événement FR et sa traduction IT sont **deux posts distincts**, liés par Polylang, chacun
portant les termes de **sa** langue (un événement FR porte la catégorie FR et le territoire
FR ; sa traduction IT porte les termes IT correspondants). Ne jamais mélanger un terme FR sur
un post IT : c'est la cause historique des « fiches italiennes sur page française ».

État au 2026-07-21 : 270 publiés, **0 sans catégorie, 0 sans territoire, 0 sans langue**. La
discipline est saine ; le vrai enjeu est le **volume** et la **répartition territoriale**, pas
les erreurs de tag.

---

## 1. Catégories (`tribe_events_cat`)

12 catégories, appariées FR ↔ IT par Polylang. **Les `term_id` sont stables : ne pas les
recréer.**

| Thème | FR (term_id · slug) | IT (term_id · slug) |
|---|---|---|
| Cinéma | 21 · `cinema` | 306 · `cinema-it` |
| Concerts & Musique | 13 · `concerts-musique` | 288 · `concerti-musica` |
| Conférences & Rencontres | 24 · `conferences-rencontres` | 312 · `conferenze-incontri` |
| Curiosités | 344 · `curiosites` | 346 · `curiosita` |
| Expositions & Patrimoine | 12 · `expositions-patrimoine` | 285 · `mostre-patrimonio` |
| Festivals | 15 · `festivals` | 294 · `festival-it` |
| Fêtes & Traditions populaires | 25 · `fetes-traditions` | 315 · `feste-tradizioni` |
| Gastronomie & Sagre | 17 · `gastronomie-sagre` | 297 · `gastronomia-sagre` |
| Jeune public & Famille | 22 · `jeune-public-famille` | 309 · `per-bambini-famiglia` |
| Marchés & Foires | 18 · `marches-foires` | 300 · `mercati-fiere` |
| Spectacle vivant | 14 · `spectacle-vivant` | 291 · `spettacolo-dal-vivo` |
| Sport | 20 · `sport` | 303 · `sport-it` |

---

## 2. Territoires (`territoire`)

4 territoires racines, appariés FR ↔ IT, avec des sous-territoires (villes). La taxonomie est
**hiérarchique** : un événement peut être taggé au niveau ville, mais dans les faits tout est
taggé au niveau région (les compteurs des pages région comptent le terme région lui-même, pas
la somme des villes). **Règle : toujours tagger le territoire région ; ajouter la ville en
complément si connue, jamais à la place.**

| Territoire | FR (term_id · slug) | IT (term_id · slug) | Sous-territoires FR (term_id) |
|---|---|---|---|
| Savoie | 3 · `savoie` | 318 · `savoia` | Annecy (4), Chambéry (5) |
| Piémont | 6 · `piemont` | 321 · `piemonte` | Turin (7) |
| Vallée d'Aoste | 8 · `vallee-d-aoste` | 324 · `valle-d-aosta` | Aoste (9) |
| Comté de Nice | 10 · `comte-de-nice` | 327 · `contea-di-nizza` | Nice (11) |

Ces valeurs sont la copie exacte de `cs_terr_canon_data()` (mu-plugin
`cs-territoire-persistant.php`). Si l'une change, mettre à jour **les deux** au même moment.

---

## 3. Règles de mapping (comment choisir la catégorie)

À l'import ou à la saisie, en cas d'hésitation, appliquer dans l'ordre :

| Nature de l'événement | Catégorie |
|---|---|
| Sagra, fête gastronomique, foire aux produits, dégustation, salon du goût | **Gastronomie & Sagre** |
| Vide-grenier, brocante, marché de Noël, foire commerciale non alimentaire | **Marchés & Foires** |
| Fête patronale, carnaval, tradition locale, bataille des reines, cortège | **Fêtes & Traditions populaires** |
| Manifestation multi-jours à programmation (musique, cinéma, arts) | **Festivals** |
| Concert, récital, DJ set (soirée unique) | **Concerts & Musique** |
| Théâtre, danse, cirque, one-man-show | **Spectacle vivant** |
| Exposition, visite de patrimoine, musée | **Expositions & Patrimoine** |
| Conférence, table ronde, rencontre d'auteur, atelier adulte | **Conférences & Rencontres** |
| Atelier enfant, spectacle jeune public, animation famille | **Jeune public & Famille** |
| Projection, ciné-club, avant-première | **Cinéma** |
| Compétition, tournoi, course, rencontre sportive | **Sport** |
| Insolite, ne rentrant dans aucune autre case | **Curiosités** |

Principes :
- **Une catégorie principale suffit.** N'ajouter une seconde catégorie que si l'événement
  relève réellement des deux (ex. un festival gastronomique → Festivals + Gastronomie). Éviter
  le sur-étiquetage qui dilue les pages.
- **Festival vs événement simple** : « festival » = plusieurs jours + programmation ; une
  soirée unique va dans sa catégorie de fond (Concerts, Spectacle, Cinéma).
- **Sagra** va toujours en Gastronomie, même si elle comporte de la musique.

---

## 4. Audit d'étiquetage (à relancer à la demande)

Requêtes de contrôle. Un événement qui remonte ici viole un invariant ou signale un
déséquilibre à corriger côté contenu.

```sql
-- (a) Publiés sans catégorie  (doit renvoyer 0)
SELECT p.ID, p.post_title FROM wp_posts p
WHERE p.post_type='tribe_events' AND p.post_status='publish'
  AND p.ID NOT IN (SELECT tr.object_id FROM wp_term_relationships tr
    JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id=tr.term_taxonomy_id
    WHERE tt.taxonomy='tribe_events_cat');

-- (b) Publiés sans territoire  (doit renvoyer 0)
SELECT p.ID, p.post_title FROM wp_posts p
WHERE p.post_type='tribe_events' AND p.post_status='publish'
  AND p.ID NOT IN (SELECT tr.object_id FROM wp_term_relationships tr
    JOIN wp_term_taxonomy tt ON tt.term_taxonomy_id=tr.term_taxonomy_id
    WHERE tt.taxonomy='territoire');
```

Contrôles supplémentaires (côté PHP, via Novamira) :
- **sans langue Polylang** : `pll_get_post_language($id)` vide → à corriger ;
- **déséquilibre territoire × catégorie** : matrice des événements à venir par territoire et
  catégorie ; une case vide n'est pas un bug (le repli inter-territoires prend le relais à
  l'affichage) mais signale un territoire à nourrir en contenu.

Snapshot 2026-07-21 : combinaisons territoire × catégorie **vides** (événements à venir) =
6 / 44. Gastronomie n'existe qu'en Piémont (0 en Savoie, Vallée d'Aoste, Nice) ; la Vallée
d'Aoste est globalement la plus pauvre. Ce sont des cibles d'approvisionnement, pas des bugs.

---

## 5. Comportements d'affichage qui dépendent de ce contrat

- **Repli inter-territoires** (`cs-*` snippet 15, Hub) : sur une page catégorie scopée à un
  territoire donnant ≤ 3 résultats, le site propose la même catégorie dans les autres
  territoires, sous « Ailleurs dans l'espace alpin ». Ce repli n'a de sens que si les
  catégories sont appariées FR ↔ IT comme au § 1.
- **Menus IT** (`cs-menu-it.php`) : libellés courts par `taxonomy:term_id` (ex. `13` →
  « Concerti »). Un changement de `term_id` casse ces libellés.
- **Persistance territoire** (`cs-territoire-persistant.php`) : lit `cs_terr_canon_data()`,
  copie exacte du § 2.

Toute modification de la taxonomie doit être répercutée dans ces trois endroits.
