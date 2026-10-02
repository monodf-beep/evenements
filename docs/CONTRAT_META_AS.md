# Contrat de méta `as_*` — publisher ↔ JetEngine (FIGÉ)

*Point d'alignement unique entre le backoffice (`publisher.py` / `cs-seo-meta.php`) qui **écrit** ces
champs, et les composants JetEngine (`carte-evenement`, fiche événement) qui les **lisent**. Ces clés
sont **immuables** : ne pas les renommer après le premier événement publié (casse les champs dynamiques).*

Convention : préfixe **`as_`** (Agenda Sabauda), `snake_case`, une seule valeur par clé (pas de tableaux).
Côté JetEngine : lecture par **« Meta Field »** en tapant la clé **exactement** telle qu'écrite ici.

---

## Les 8 clés du contrat

| # | Clé méta | Type | Écrite par le publisher | Lue / affichée par JetEngine |
|---|---|---|---|---|
| 1 | `as_score` | entier `0`–`10` | note qualité de l'évaluateur LLM | **jamais affichée** — sert au tri « À la une » (`≥ 8`) et au routage éditorial |
| 2 | `as_gratuit` | `0` / `1` | `1` si entrée libre | **badge « Gratuit »** sur la carte + **filtre** JetSmartFilters |
| 3 | `as_tarif` | texte court | ex. « 8 € / réduit 5 € » | bloc pratique de la fiche (ligne « Tarif ») — masqué si vide |
| 4 | `as_horaire` | texte court | ex. « 10 h – 18 h » | bloc pratique de la fiche (ligne « Horaires ») — masqué si vide |
| 5 | `as_billetterie_url` | URL | lien billetterie **officiel** | bouton **« Réserver — site officiel »** — masqué si vide |
| 6 | `as_source_officielle_url` | URL | site **officiel** de l'événement | lien « Source » de la fiche — **jamais la source radar** — masqué si vide |
| 7 | `as_verifie_le` | date `AAAA-MM-JJ` | date de dernière vérification | mention **« Vérifié le JJ/MM/AAAA »** en pied de fiche |
| 8 | `as_image_credit` | texte court | crédit / © de la photo | légende **crédit photo** sous l'image — masqué si vide |

**Rien d'autre n'est un `as_*`.** Tout le reste vient nativement de TEC ou d'une taxonomie (voir plus bas).

---

## Extensions post-gel (ajoutées après le figeage initial, non renommables non plus)

| Clé méta | Type | Écrite par le publisher | Lue / affichée par JetEngine |
|---|---|---|---|
| `as_home_score` | décimal `0`–`10` | score HOME = qualité panel lecteurs + source officielle + affiches (`scripts/enrich.py`, colonne `home_score`) | tri des sections « À la une »/« En évidence » — **câblé** (cf. `docs/CABLAGE_HOME.md`). **Ne suffit pas comme filtre d'éligibilité** : une fiche jamais rédigée a `as_home_score=""` (≈0), donc classée dernière, mais reste techniquement incluse — voir `as_enrich_status` |
| `as_enrich_status` | `enriched` / vide | statut RÉEL de rédaction (colonne `enrich_status`) | **filtre d'ÉLIGIBILITÉ, en amont du tri par `as_home_score`** : une fiche `enrich_status` vide (jamais passée par `scripts/enrich.py`) ne doit jamais entrer dans le pool « À la une »/« En évidence », même si la section manque de contenu bien noté ce jour-là — **à câbler côté allocateur home** (constat Franck 2026-07-30 : sans ce filtre, le repli « remplir avec le meilleur disponible » de l'allocateur finissait par inclure du contenu jamais rédigé) |
| `as_home_override` | `''` / `featured` / `excluded` | override MANUEL posé au back-office (`/set-home-override`), prime sur `as_home_score` | **à câbler** : à lire en PRIORITÉ — `excluded` retire la fiche de toute section mise en avant, `featured` la force en tête, `''` = laisser `as_home_score` décider |
| `as_home_order` | entier ou vide | rang manuel PARMI les fiches `as_home_override='featured'` (flèches ▲▼ back-office, `/set-home-order`) — plus petit = plus haut | **à câbler** : tri secondaire de la section « À la une »/« En vedette » QUAND plusieurs fiches sont `featured` (sinon `as_home_score` suffit) |
| `as_lieu` / `as_ville` | texte | lieu/ville en plat (doublon du Venue TEC, pour un binding trivial) | carte-événement JetEngine |
| `as_image_original` | URL | image officielle NON recadrée | fiche événement (affiche en grand) |
| `as_panel_mean` | décimal `0`–`5` ou vide | moyenne du panel de personas LOCAUX (`scripts.enrich.reader_panel`) | détail du score, back-office éditorial — vide si jamais relu (court, ou enrichi avant le panel) |
| `as_panel_vmean` | décimal `0`–`5` ou vide | moyenne du panel de personas VISITEURS (aire adjacente). ⚠️ **Malgré son intitulé, mesure la RICHESSE DE L'ARTICLE, pas l'ampleur de l'événement** — le persona note ce qu'il lit (`interet: 0=creux, 5=riche`), pas ce qu'il sait. Constaté en production 2026-08-01 : Musilac (110 000 festivaliers) notait `1.0`, une petite expo `3.0`, seulement parce que son article était maigre | détail du score, back-office. **Utilisable comme FILTRE de qualité (écarter les fiches creuses), JAMAIS comme tri de la section « Ça vaut le déplacement »** — pour ça, voir `as_deplacement` |
| `as_deplacement` | entier `0`–`8` ou vide | score « ça vaut le déplacement », DÉTERMINISTE (zéro appel LLM) : somme de 4 des 5 critères d'importance de `scripts/evaluator.py` stockés en base (`llm_score_detail`) — `rayonnement` (transfrontalier FR-IT = 2) + `specificite_territoriale` (identitaire = 1) + `notoriete_lieu` + `edition_tradition`. `organisateur_moyens` volontairement exclu (le budget de l'organisateur n'entre pas dans la décision d'un visiteur). Vide = non mesuré (**≠ 0** : ne pas classer les non-mesurés comme « sans intérêt »). Cf. `utils/deplacement.py` | **tri de la section home « Ça vaut le déplacement »**, qui triait jusqu'ici par simple ordre chronologique sans aucun critère de qualité. Auditable : `llm_score_detail` conserve la justification écrite de chaque critère |
| `as_panel_votes` | entier ou vide | nb de lecteurs ayant voté « révision » | idem |
| `as_panel_verdict` | `ok` / `revise` / vide | verdict du panel sur la version FINALE (après révision éventuelle) | idem |
| `as_panel_revision` | `aucune` / `appliquée` / `tentée` / vide | l'article a-t-il été réécrit suite aux retours du panel, et la réécriture a-t-elle été retenue (`tentée` = réécrit mais le brouillon initial notait mieux → réécriture écartée) | idem — répond à « a-t-on relu et corrigé grâce au panel ? » |
| `as_affiches` | `aucune` / `une` / `deux` / `photo officielle` / vide | statut des visuels officiels trouvés (dossier de presse ou photo du site officiel) | badge visuel possible sur la fiche/l'admin |
| `as_placement` | texte libre | où cette fiche PEUT aller (hero home, en évidence, catalogue…), déduit du score + visuels | aide à la décision éditoriale, pas un champ à afficher au public |

---

## Ce qui n'est PAS une méta `as_*` (déjà fourni ailleurs)

| Donnée | Source | Lecture JetEngine |
|---|---|---|
| Titre, contenu, image à la une | TEC (Post) | Dynamic Field · source *Post* |
| Date début / fin | TEC (`_EventStartDate` / `_EventEndDate`) | Dynamic Field · source *Post/TEC* |
| Lieu (nom, adresse, ville, lat/lng) | TEC Venue | Dynamic Field · *Venue* |
| Catégorie | `tribe_events_cat` | Dynamic Terms |
| **Territoire** (pilule couleur + filtre) | taxonomie maison `territoire` | Dynamic Terms |

---

## Routage éditorial (signature) — décision de conception

Le score décide **quel média signe** :
- `as_score ≥ 7` → **Cultura Sabauda**
- `as_score < 7` → **Agenda Sabauda**

**Implémentation retenue : via l'auteur WordPress**, pas une méta.
Deux comptes auteurs (« Cultura Sabauda », « Agenda Sabauda ») ; le publisher affecte l'événement au bon
auteur selon le score. Avantages : signature (byline) native, page auteur, cohérence RSS/schema — sans
clé supplémentaire à maintenir. *(Si un jour on veut l'afficher autrement, on ajoutera `as_signature` —
mais par défaut on n'en a pas besoin.)*

---

## Règles d'affichage (côté carte / fiche)

- **Tout champ vide est masqué** (pas de label orphelin « Tarif : »).
- `as_score` **ne s'affiche jamais** — c'est un signal interne (tri/sélection/routage).
- Sur la **carte** : seuls `as_gratuit` (badge) et le score (via la Query « À la une ») entrent en jeu.
- Sur la **fiche** : bloc pratique = `as_tarif` + `as_horaire` + `as_billetterie_url` ; pied = `as_source_officielle_url` + `as_verifie_le` ; sous l'image = `as_image_credit`.

---

## Statut & sécurité (rappel)

- Le publisher écrit toujours l'événement en **`draft`** (jamais de publication automatique).
- `as_source_officielle_url` = **site officiel de l'événement uniquement**. Les **sources radar ne sont
  jamais créditées ni liées**, nulle part.
- Écriture via **REST + Application Password** sur un **compte dédié révocable**.

---

## Pour toi, côté JetEngine (une fois, avant la carte)

Optionnel mais recommandé : déclarer ces 8 clés dans un **JetEngine → Meta Box** attaché au type
`tribe_events`, pour les voir/éditer dans l'admin de chaque événement. Types de champ conseillés :
`as_gratuit` = *Switcher/Checkbox* · `as_score` = *Number* · `as_verifie_le` = *Date* ·
`as_billetterie_url` / `as_source_officielle_url` = *Text (URL)* · le reste = *Text*.
Le publisher écrit la méta directement quoi qu'il arrive ; la Meta Box ne sert qu'au confort d'édition.
