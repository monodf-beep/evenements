# Câblage de la home — brancher les règles du wireframe

*Applique, section par section, les règles de la page « Wireframe home » du back-office.
Chaque section = une **requête JetEngine** (Query Builder, Posts Query sur `tribe_events`)
branchée sur le Listing Grid correspondant de la home. Prérequis vérifiés : le score est
stocké en méta **`as_score`** (numérique) ; dates via **`_EventStartDate`** ; taxonomies
**`territoire`** et **`tribe_events_cat`** ; fraîcheur via **`post_date`**. Langue : forcer
`'lang' => pll_current_language()` dans le filtre des args (décision étape 5).*

---

## Prompt à coller dans la session connectée à Novamira

```
On CÂBLE la home d'Agenda Sabauda : on branche chaque section sur une requête JetEngine
qui applique sa règle. Stack JetEngine + Gutenberg. Par étapes, verify-first, réversible,
confirmation avant chaque écriture. Ne touche pas au CPT « selection » en cours.

Rappels techniques (déjà vérifiés) :
- Score = méta « as_score » (numérique) sur chaque tribe_events.
- Date de début = méta « _EventStartDate » (Y-m-d H:i:s).
- Taxonomies : « territoire », « tribe_events_cat ».
- Fraîcheur = post_date. Langue : forcer 'lang' => pll_current_language() dans le
  filtre jet-engine/query-builder/types/posts-query/args (comme pour ce-week-end).

ÉTAPE 0 — CARTOGRAPHIE (ne rien modifier)
Sur la page d'accueil (FR id 928, IT id 1717), repère chaque Listing Grid et dis-moi à
quelle SECTION il correspond (À la une, Ce week-end, Événements d'aujourd'hui, Nouveautés,
En évidence, L'agenda à venir, Par catégorie, Ça vaut le déplacement). Donne-moi le
mapping bloc → section avant de câbler.

ÉTAPE 1 — CORRIGER « Événements d'aujourd'hui » → « à venir » (le plus visible)
Requête « evenements-a-venir-7j » : tribe_events, Date Query _EventStartDate entre
AUJOURD'HUI 00:00 et +7 jours 23:59, tri _EventStartDate ASC, limite 8. Branche-la sur
le Listing Grid « aujourd'hui ». But : ne plus jamais afficher « No data was found ».

ÉTAPE 2 — « À la une / En vedette »
Requête « evenement-vedette » : tribe_events, date ≥ aujourd'hui, tri par as_score
DÉCROISSANT (meta_value_num), limite 1. Branche-la sur le bloc « En vedette » (1 grande
carte). Note : sur Agenda Sabauda les scores sont < 7, mais le tri relatif reste valide.

ÉTAPE 3 — « En évidence »
Requête « evenements-evidence » : tribe_events, date ≥ aujourd'hui ET as_score ≥ 5
(Meta Query numérique), tri as_score DÉCROISSANT, limite 3–4. Branche sur « En évidence ».
(Si trop peu de résultats, abaisse le seuil — dis-moi le nombre obtenu.)

ÉTAPE 4 — « Nouveautés sur Agenda Sabauda » (aujourd'hui = faux articles codés en dur)
Requête « evenements-nouveautes » : tribe_events, date ≥ aujourd'hui, tri par post_date
DÉCROISSANT (récemment ajoutés), limite 3. REMPLACE les 3 blocs éditoriaux placeholder
par un Listing Grid sur cette requête.

ÉTAPE 5 — « Par catégorie » (En famille · Concerts · Expositions · Gastronomie)
Pour chaque catégorie, une requête : tribe_events, date ≥ aujourd'hui, Tax Query
tribe_events_cat = le terme voulu, tri as_score DÉCROISSANT puis _EventStartDate ASC,
limite 4. Slugs : jeune-public-famille, concerts-musique, expositions-patrimoine,
gastronomie-sagre. Branche chaque Listing Grid de section sur sa requête.

ÉTAPE 6 — « Ça vaut le déplacement » (placeholder transfrontalier)
Celle-ci utilise le CPT « selection » (mode manuel, événements voisins épinglés) — on la
fera APRÈS avoir validé la sélection test. Pour l'instant, laisse le placeholder ; ne le
câble pas encore.

RÈGLES : par étapes, confirmation avant chaque modif, rollback documenté (garde l'ancienne
query_id pour pouvoir revenir). Toutes les requêtes en langue courante (Polylang).
Commence par l'ÉTAPE 0 (cartographie) et donne-la-moi.
```

---

## Ordre de priorité (impact visuel)
1. **Étape 1** (aujourd'hui → à venir) — fin du « No data », tout de suite visible.
2. **Étapes 2-3** (vedette / évidence) — la home prend un vrai relief éditorial via le score.
3. **Étape 4** (nouveautés) — remplace les faux articles.
4. **Étape 5** (catégories) — sections « par envie ».
5. **Étape 6** (transfrontalier) — après la sélection test.

*Rappel : toutes ces sections tirent du même vivier d'événements ; leur qualité dépend du
**contenu** (plus d'événements, surtout italiens). Le câblage rend la home vivante ; le
sourcing la remplit.*
