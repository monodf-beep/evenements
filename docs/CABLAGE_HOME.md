# Câblage de la home — brancher les règles du wireframe

*Applique, section par section, les règles de la page « Wireframe home » du back-office.
Chaque section = une **requête JetEngine** (Query Builder, Posts Query sur `tribe_events`)
branchée sur le Listing Grid correspondant de la home. Prérequis vérifiés : le score est
stocké en méta **`as_score`** (numérique) ; dates via **`_EventStartDate`** ; taxonomies
**`territoire`** et **`tribe_events_cat`** ; fraîcheur via **`post_date`**. Langue : forcer
`'lang' => pll_current_language()` dans le filtre des args (décision étape 5).*

> **MISE À JOUR (2026-07-29) — deux scores distincts, ne pas confondre.** `as_score` =
> **pertinence** (l'événement mérite-il d'être publié, évalué AVANT rédaction). `as_home_score`
> (0-10) = **qualité de mise en avant** (panel de personas lecteurs + source officielle +
> affiches officielles, calculé APRÈS rédaction — cf. `docs/CONTRAT_META_AS.md` §Extensions).
> Les sections « À la une »/« En évidence » ci-dessous doivent trier sur **`as_home_score`**,
> pas `as_score` — c'est le signal qui reflète vraiment « on a l'info ET l'image, sans deviner ».
> **Avant tout tri par score**, filtrer `as_home_override != 'excluded'` ; puis faire
> remonter en tête les `as_home_override == 'featured'` (indépendamment du score) ; le reste
> trié par `as_home_score` DÉCROISSANT. C'est l'override manuel posé par Franck au
> back-office (`/set-home-override`) — sans lui, une fiche peu engageante mais bien notée
> peut squatter le haut de la home, et inversement un vrai coup de cœur mal cadré n'y monte
> jamais.

---

## Prompt à coller dans la session connectée à Novamira

```
On CÂBLE la home d'Agenda Sabauda : on branche chaque section sur une requête JetEngine
qui applique sa règle. Stack JetEngine + Gutenberg. Par étapes, verify-first, réversible,
confirmation avant chaque écriture. Ne touche pas au CPT « selection » en cours.

Rappels techniques (déjà vérifiés) :
- Score de PERTINENCE = méta « as_score » (numérique, avant rédaction).
- Score de MISE EN AVANT = méta « as_home_score » (décimal 0-10, panel lecteurs + source
  officielle + affiches, calculé après rédaction) — c'est CELUI-LÀ qui doit trier « À la
  une »/« En évidence », pas as_score.
- Override manuel = méta « as_home_override » (''/featured/excluded), posé par Franck au
  back-office : à lire en PRIORITÉ, avant le tri par as_home_score (voir étapes 2-3).
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
Requête « evenement-vedette » : tribe_events, date ≥ aujourd'hui, Meta Query as_home_override
!= 'excluded', tri par (1) as_home_override = 'featured' en tête puis (2) as_home_score
DÉCROISSANT (meta_value_num), limite 1. Branche-la sur le bloc « En vedette » (1 grande
carte). Si JetEngine ne sait pas faire un tri à deux clés dont une textuelle, deux requêtes
suffisent : d'abord une requête « featured » (as_home_override = 'featured', limite 1),
et si elle est vide, repli sur la requête triée as_home_score.

ÉTAPE 3 — « En évidence »
Requête « evenements-evidence » : tribe_events, date ≥ aujourd'hui, as_home_override !=
'excluded', ET as_home_score ≥ 5 (Meta Query numérique) OU as_home_override = 'featured',
tri as_home_score DÉCROISSANT, limite 3–4. Branche sur « En évidence ».
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

ÉTAPE 6 — « Ça vaut le déplacement » (transfrontalier — RÈGLE « autre versant »)
Décision Franck (2026-07-20) : requête AUTOMATIQUE « côté autre versant » (plus de
placeholder manuel). Deux requêtes, une par langue, branchées sur le Listing Grid (2 cartes)
de la home correspondante :
  - Home FR (lang=fr) : tribe_events à venir, Tax Query territoire IN
    (piemont, vallee-d-aoste) [= côté italien], tri as_score DÉCROISSANT, limite 2.
  - Home IT (lang=it) : tribe_events à venir, Tax Query territoire IN
    (savoie-haute-savoie, nice-alpes-maritimes) [= côté français], tri as_score DÉCROISSANT,
    limite 2.
Le CPT « selection » reste disponible pour un override manuel plus tard, mais la règle par
défaut est cette requête (la section n'est donc jamais vide).

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
