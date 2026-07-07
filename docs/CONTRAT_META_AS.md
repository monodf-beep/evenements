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
