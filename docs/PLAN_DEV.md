# Plan de développement — Agenda Sabauda

*Feuille de route unique, de l'état actuel au lancement. Deux chantiers en parallèle :*
- **Chantier WordPress** (toi + Claude-in-Chrome) : thème, charte, composants JetEngine, pages.
- **Chantier backoffice** (moi, Python) : le pont `publisher.py` → WordPress, routage, contrat de méta.

Principe directeur figé : **The Events Calendar = la donnée · JetEngine = la mise en forme · GeneratePress = le socle.**
Objectif transverse : **rester rapide** (Core Web Vitals = SEO). **Jamais d'Elementor.**

Légende propriétaire : 🧑 = toi (via Claude-in-Chrome) · 🤖 = moi (backoffice) · 🧑🤖 = à deux.

---

## ✅ Déjà fait (socle en place)

- WordPress installé sur OVH Pro, **HTTPS**, interface FR, domaine **agendasabauda.eu** (Gandi → OVH).
- Extensions actives : **The Events Calendar, Rank Math, Polylang, JetEngine, JetSmartFilters, Code Snippets**.
- Thème : **GeneratePress + thème enfant** actif (pas de Kava, pas de démo importée).
- Snippet **agenda-sabauda-core** actif : taxonomie `territoire` (4 territoires + villes) · 11 catégories · noindex des vues techniques TEC.
- Config SEO/i18n : slugs TEC (`evenements`/`evenement`) · Rank Math (schema Évènements = *Aucun*, IndexNow ON, Google OFF) · **Polylang FR/IT** (URLs `/it/`, support Évènements + taxonomies) · robots.txt.

---

## Phase 0 — Finir la config (presque bouclé) 🧑

| # | Tâche | Qui | État |
|---|---|---|---|
| 0.1 | **Charte : couleurs globales** GeneratePress (`#18365E`/`#F7F1E8`/`#DC5D45`/`#1D1D1B`) | 🧑 | ⏳ en cours (prompt Chrome envoyé) |
| 0.2 | **Typographie** : corps lisible + titres « pinstripe » en display uniquement | 🧑 | à faire (prompt à venir) |
| 0.3 | **Google Search Console** : propriété **domaine** vérifiée par **DNS TXT chez Gandi** | 🧑 | à faire (besoin de ton login Google) |
| 0.4 | Fermer l'onglet parasite (ex-wizard JetPlugins) | 🧑 | trivial |

**Livrable Phase 0 :** WordPress propre, charte posée, indexation sous contrôle.

---

## Phase 1 — Le composant central : `carte-evenement` 🧑🤖

Le bloc réutilisé partout. On le construit **une fois** dans **JetEngine → Listing Items**.

- Structure : image 3:2 → **DATE d'abord** (`_EventStartDate`, format `d/m`) → titre gras → lieu · ville → **pilule territoire** (couleur conditionnelle par terme) → badge « Gratuit » si `as_gratuit`. Carte entièrement cliquable → permalien.
- Variantes : `carte-compacte` (vignette + texte, listes denses) · `carte-hero` (plein-largeur, carrousel).
- Test : le poser sur une **Query « à venir »** et vérifier le rendu avec 2-3 événements de test.

**Dépendance :** j'aurai livré la **liste définitive des clés méta `as_*`** (contrat §2 du build) pour que les champs dynamiques pointent au bon endroit.

**Livrable Phase 1 :** une carte propre, cohérente avec la charte, réutilisable.

---

## Phase 2 — Les requêtes (JetEngine Query Builder) 🧑🤖

À créer une fois, réutilisées par les Listings :

- **À la une** : `tribe_events`, à venir, `as_score ≥ 8`, tri score desc, limite 4.
- **Ce week-end** : chevauchant [ven→dim], limite 4 (+ compteur).
- **Aujourd'hui** : chevauchant aujourd'hui (module home ; hub `noindex`).
- **Par catégorie / par territoire / par ville** : filtrés, à venir.
- **Transfrontalier** : `territoire IN {voisins}`, `as_score ≥ 8`, limite 3 — **masquer si 0 résultat** (table dans `PROXIMITE_TRANSFRONTALIERE.md`).
- **Tout l'agenda** : à venir, paginé.

**Livrable Phase 2 :** la bibliothèque de requêtes prête à alimenter les pages.

---

## Phase 3 — La Home 🧑

Assemblée au constructeur, dans l'ordre figé de `PROMPT_CLAUDE_DESIGN.md` :
carrousel · recherche · **6 tuiles** (liens hubs) · Listing **À la une** · Listing **Ce week-end** (+ compteur + bouton noir « Voir tout l'agenda du week-end ») · **Le fil** (articles) · tuiles secondaires · **module transfrontalier** · newsletter · footer.

**Livrable Phase 3 :** page d'accueil vivante branchée sur les requêtes.

---

## Phase 4 — Les hubs & pages SEO 🧑

- **Hub catégorie** : intro pérenne + Listing filtré + **JetSmartFilters** (date/ville).
- **Hub territoire** : intro + « ce week-end en X » + Listing local + **module transfrontalier**.
- **`/[ville]/ce-week-end/`** : gabarit **daté** (titre « Que faire ce week-end à [Ville] ? ») — cf. `INTENTIONS_RECHERCHE_SEO.md`.

**Livrable Phase 4 :** les pages qui captent la recherche « que faire à [ville] ».

---

## Phase 5 — La fiche événement 🧑

**Single template** (override TEC ou JetEngine Single), **mode minimal** :
image + crédit + badges + catégorie + titre + lieu + pilule territoire + **bloc pratique** (`as_tarif`/`as_horaire`/`as_billetterie_url`) + « **Vérifié le** » (`as_verifie_le`) + **3 rails liés** (même ville / même catégorie / voisins).

**Livrable Phase 5 :** la page de destination de chaque événement.

---

## Phase 6 — Le pont `publisher.py` → WordPress 🤖 *(mon terrain, en parallèle)*

- **Compte dédié** WordPress + **Application Password** (révocable), scope admin minimal.
- `publisher.py` écrit les événements TEC via **REST** + les **méta `as_*`** (contrat figé).
- **Routage éditorial** : score ≥ 7 → *Cultura Sabauda* · < 7 → *Agenda Sabauda*.
- **Statut = brouillon** systématique (jamais de publication auto).
- Filtre mu-plugin pour le slug **`luoghi`** des lieux (si retenu).
- **Sources radar jamais créditées ni liées** — seulement `as_source_officielle_url`.

**Livrable Phase 6 :** injection automatisée d'événements en brouillon, prêts à valider.

---

## Phase 7 — Pages statiques & légales 🧑

Annoncer (pub) · Proposer un événement (formulaire) · Mentions légales / confidentialité · 404 · Recherche.
Réf : `TEMPLATES_WORDPRESS.md`, `PAGE_PUBLICITE.md`.

---

## Phase 8 — Perf & pré-lancement 🧑🤖

- **Cache** (LiteSpeed/W3TC/FlyingPress) + cache objet OVH si dispo.
- **Images** WebP (ShortPixel/Imagify), lazy-load, ratios réservés.
- **PageSpeed Insights** sur chaque gabarit → viser **LCP < 2,5 s mobile**.
- Désactiver les widgets Jet inutilisés · limiter les Listing Grids par page · mettre en cache les requêtes.
- Sitemaps soumis, hreflang FR/IT vérifiés, GSC OK.

---

## Phase 9 — Amorçage éditorial & ouverture 🧑🤖

1. Le publisher injecte les **premiers vrais événements** (brouillons).
2. Tu **valides / complètes** via le tableau de bord **Pilotage** (l'advisor te dit quoi faire).
3. Traductions IT des termes + fiches phares.
4. **Ouverture publique** quand chaque territoire a un stock minimal et la home ne montre pas de trous.

---

## Chemin critique (l'ordre qui compte)

```
Phase 0 (charte) → Phase 1 (carte) → Phase 2 (requêtes) → Phase 3 (home)
                                          ↘ Phase 6 (publisher, en //) ↗
   → Phase 4 (hubs/SEO) → Phase 5 (fiche) → Phase 7 (pages) → Phase 8 (perf) → Phase 9 (ouverture)
```

Le **contrat de méta `as_*`** (Phase 6) est le point d'alignement entre mon publisher et tes composants JetEngine (Phases 1 & 5) — je te le fige avant que tu câbles les champs dynamiques.

---

## Prochain pas immédiat

1. 🧑 Terminer **Phase 0.1** (charte couleurs — prompt Chrome déjà donné) → me dire « fait ».
2. 🧑🤖 J'enchaîne sur le **pas-à-pas de la `carte-evenement`** (Phase 1) + je te livre la liste **définitive** des clés `as_*`.
