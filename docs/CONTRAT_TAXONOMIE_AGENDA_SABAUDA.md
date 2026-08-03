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

### 2bis. Provinces (niveau intermédiaire, Piémont UNIQUEMENT)

**Décidé le 2026-07-30, en réouverture ciblée de la clause « figée » ci-dessus.** Raison : les 4
territoires ne sont pas de taille comparable — Savoie ≈ un département français, Comté de Nice ≈
le département des Alpes-Maritimes, Vallée d'Aoste ≈ une petite région autonome, mais **Piémont
représente une région italienne entière** (8 provinces, 4,3M d'habitants) compressée dans un seul
terme. La ville de Turin y écrase tout le reste (32 événements à venir vs 16 pour les 7 autres
provinces réunies au 2026-07-30) sans qu'aucune autre ville individuelle n'ait assez de volume
pour mériter sa propre page.

**Portée : Piémont seulement.** Les 3 autres territoires gardent leur structure `territoire >
ville` à 2 niveaux, inchangée. On insère `territoire > province > ville` uniquement sous Piémont.

| Province | Sigle | FR (term_id · slug) | IT (term_id · slug) |
|---|---|---|---|
| Turin | TO | 7 · `turin` *(réutilisé, renommé « Province de Turin »)* | 568 · `provincia-torino` |
| Cuneo | CN | 570 · `province-cuneo` | 572 · `provincia-cuneo` |
| Asti | AT | 574 · `province-asti` | 576 · `provincia-asti` |
| Alexandrie | AL | 578 · `province-alexandrie` | 580 · `provincia-alessandria` |
| Biella | BI | 582 · `province-biella` | 584 · `provincia-biella` |
| Novare | NO | 586 · `province-novare` | 588 · `provincia-novara` |
| Vercelli | VC | 590 · `province-vercelli` | 592 · `provincia-vercelli` |
| VCO (Verbano-Cusio-Ossola) | VB | 594 · `province-vco` | 596 · `provincia-vco` |

Créés le 2026-07-30 (session Novamira). Backup de la taxonomie complète avant modification :
option WordPress `cs_bk_taxonomie_territoire_avant_provinces`.

**Rattachement ville → province** (liste complète maintenue dans `_PROVINCE_PAR_VILLE`,
`scripts/publisher_as.py` — volontairement large, villes sans événement aujourd'hui incluses) :
- Turin (TO) : Torino, Rivoli, Ivrea, Venaria Reale, Collegno, Moncalieri, Chieri, Pinerolo,
  Nichelino, Settimo Torinese, Chivasso, Bosconero, Pragelato, Usseglio
- Cuneo (CN) : Cuneo, Mondovì, Alba, Bra, Fossano, Saluzzo, Savigliano, Carrù, **Vicoforte**,
  Villanova Mondovì, Roccaforte e Frabosa Sottana
- Asti (AT) : Asti, Nizza Monferrato, Canelli
- Alexandrie (AL) : Alessandria, Novi Ligure, Tortona, Acqui Terme, Casale Monferrato
- Biella (BI) : Biella, Cossato
- Novare (NO) : Novara, Borgomanero, Arona
- Vercelli (VC) : Vercelli
- VCO (VB) : Verbania, Stresa, Domodossola, Omegna

*(Correction du 2026-07-30 : Vicoforte avait été classé par erreur sous Vercelli dans une
version précédente de ce document — c'est une commune de la province de Cuneo, corrigé ici et
dans le code.)*

**Piège connu à éviter** (cf. bug Annecy/Aoste de la même session) : ne pas dupliquer un terme
ville sous plusieurs orthographes différentes — normaliser AVANT de tagger, sinon le filtrage par
province rate une partie du contenu.

**État au 2026-07-30 : phases 1, 2 et 4 terminées.**
- ✅ Les 16 termes sont créés en base et liés Polylang (vérifié).
- ✅ Rétro-tagging fait : les 96 événements Piémont déjà publiés (FR+IT) ont reçu leur province
  en plus du territoire région (vérifié en base : Turin 79, Cuneo 14, Vercelli 3 — Asti,
  Alexandrie, Biella, Novare, VCO à 0 pour l'instant, faute de contenu, pas de tag manquant).
- ✅ Pipeline branché : `_map_province()` dans `scripts/publisher_as.py` (nouveau champ
  `province` dans le payload envoyé à `cs/v1/event`) + `cs-publish.php` (snippet WordPress #6 ET
  copie locale `deploy/wordpress/cs-publish.php`, les deux mis à jour et resynchronisés — le
  déploiement automatique du dépôt vers le serveur étant cassé, cf. `push-wordpress.sh`) ajoute
  le terme province EN PLUS du territoire région, sans rien changer si le champ est vide ou la
  ville non reconnue. Testé en direct (requête réelle sur `cs/v1/event`, terme "Province de
  Cuneo" bien assigné, post de test supprimé après vérification).

**Phase 4 (pages hub province + filtre) — faite le 2026-07-30, session Novamira.**

Mécanique réutilisée telle quelle : le gabarit générique `cs_hub_ville_render` (snippet Code
Snippets #61, `[cs_hub_ville]`) a été étendu avec un attribut optionnel `province="<term_id>"` qui
ANDe un second terme de la même taxonomie `territoire` en plus du terme région — même moteur que
les pages ville existantes (Turin, Chambéry…), pas de nouveau gabarit. Backup du code avant
modification : option WordPress `cs_bk_snippet61_avant_provinces_2026-07-30`. Syntaxe vérifiée
(`token_get_all(..., TOKEN_PARSE)`) avant écriture en base.

8 pages créées (FR uniquement, `cs_hub_ville=1`, réutilisent takeover + carte standard) :

| Province | URL | ID page |
|---|---|---|
| Turin | https://agendasabauda.eu/province-de-turin/ | 6109 |
| Cuneo | https://agendasabauda.eu/province-de-cuneo/ | 6110 |
| Asti | https://agendasabauda.eu/province-d-asti/ | 6111 |
| Alexandrie | https://agendasabauda.eu/province-d-alexandrie/ | 6112 |
| Biella | https://agendasabauda.eu/province-de-biella/ | 6113 |
| Novare | https://agendasabauda.eu/province-de-novare/ | 6114 |
| Vercelli | https://agendasabauda.eu/province-de-vercelli/ | 6115 |
| VCO | https://agendasabauda.eu/province-du-vco/ | 6116 |

Indexation SEO conditionnelle et **automatique** (nouveau snippet #114, « CS · Provinces Piémont
(indexation + chips filtre) ») : à chaque chargement d'une page province, un filtre `wp_robots`
(hooké en `PHP_INT_MAX`, après l'intégration Yoast 28.0 qui se branche elle-même très haut sur ce
même hook core) relit le nombre réel d'événements à venir de la province (région + province ANDés,
requête identique à celle du shortcode) et force `noindex, follow` si < 15, sinon laisse Yoast
afficher `index, follow` par défaut. Rien n'est codé en dur — le terme province est extrait par
regex du shortcode présent dans le contenu de la page courante, donc valable pour n'importe quelle
page utilisant ce motif, pas seulement les 8 créées ici. Vérifié en direct le 2026-07-30 :

| Province | Événements à venir | Balise robots observée |
|---|---|---|
| Turin | 29 | `index, follow, …` |
| Cuneo | 6 | `noindex, follow, …` |
| Asti | 0 | `noindex, follow, …` |
| Alexandrie | 0 | `noindex, follow, …` |
| Biella | 0 | `noindex, follow, …` |
| Novare | 0 | `noindex, follow, …` |
| Vercelli | 1 | `noindex, follow, …` |
| VCO | 0 | `noindex, follow, …` |

Module de filtre sur la page Piémont existante (id 2859, https://agendasabauda.eu/que-faire-dans-le-piemont/) :
shortcode `[cs_province_chips]` (même snippet #114) inséré dans son contenu (backup avant
modification : option `cs_bk_page2859_avant_chips_provinces_2026-07-30`), 8 chips texte (pas
d'icônes/drapeaux) menant à chaque page province, état actif en rouge Piémont `#b3261e` (le
shortcode est générique et pourra aussi surligner l'état actif si réutilisé plus tard sur une
page province elle-même). Vérifié en direct : les 8 liens s'affichent avec les bonnes URLs.

Non fait (hors scope au moment de la phase 4) : carrousel home.

**Versions IT des 8 pages province, créées le 2026-07-30 (session Novamira, suite immédiate).**

Même mécanisme `[cs_hub_ville]`, avec `province="<term_id IT>"` (568/572/576/580/584/588/592/596,
cf. tableau § 2bis) et `territoire="piemont"` inchangé (résolu automatiquement vers le term_id IT
321 par `cs_terr_canon_data()` selon `pll_current_language()`). Chaque page liée à sa page FR via
`PLL()->model->post->save_translations()` (vérifié : `pll_get_post_translations()` retourne bien
les deux ID pour chacune des 8 paires). Intro éditoriale traduite en italien (pas de traduction
automatique). `ville_label` sans article + `prep_it="nella"` pour obtenir la contraction correcte
(« nella provincia di Torino »).

| Province | URL IT | ID page IT | ID page FR liée |
|---|---|---|---|
| Turin | https://agendasabauda.eu/it/provincia-di-torino/ | 6118 | 6109 |
| Cuneo | https://agendasabauda.eu/it/provincia-di-cuneo/ | 6119 | 6110 |
| Asti | https://agendasabauda.eu/it/provincia-di-asti/ | 6120 | 6111 |
| Alexandrie | https://agendasabauda.eu/it/provincia-di-alessandria/ | 6121 | 6112 |
| Biella | https://agendasabauda.eu/it/provincia-di-biella/ | 6122 | 6113 |
| Novare | https://agendasabauda.eu/it/provincia-di-novara/ | 6123 | 6114 |
| Vercelli | https://agendasabauda.eu/it/provincia-di-vercelli/ | 6124 | 6115 |
| VCO | https://agendasabauda.eu/it/provincia-del-vco/ | 6125 | 6116 |

Vérifié en direct le 2026-07-30 : les 8 pages renvoient HTTP 200, H1 et intro corrects, et
affichent les événements italiens de la province quand il y en a (Turin 33, Cuneo 8, Vercelli 2 ;
Asti, Alexandrie, Biella, Novare, VCO à 0 événement propre pour l'instant, page fonctionnelle avec
repli « Nei dintorni », pas un bug).

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
