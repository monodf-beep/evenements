# wordpress/ — Construction du site Agenda Sabauda

Chantier **distinct** du backoffice Python (agrégation d'événements). Ici on
construit le site public **agendasabauda.eu** à partir du design system
« Cultura Sabauda » (Claude Design), sur la stack **GeneratePress + The Events
Calendar + Crocoblock/JetEngine + Elementor + Polylang**.

## Principes (voir docs/BUILD_WORDPRESS_CROCOBLOCK.md + le design system)

- **TEC = la donnée** : les événements sont des `tribe_events`. On **ne crée pas**
  de CPT `evenement` JetEngine (le blueprint design est adapté à TEC). Champs
  extra non-natifs (statut, accent, billetterie) → petite meta box JetEngine
  greffée sur `tribe_events`.
- **Tokens = la charte** : couleurs/typo/espacements viennent de
  `design-system/tokens.css` (copie versionnée de la source Claude Design).
  Appliqués en **interim** via Code Snippets (`scope site-css`) ; cible finale =
  `theme.json` du child theme GeneratePress quand le SFTP OVH sera en place.
- **Traçabilité** : toute modif du site passe par un script versionné ici, puis
  poussé sur GitHub. Le secret (App Password) reste dans `.env` (gitignored).
- **⚠️ CSS via Code Snippets** : le plugin installé est la version **gratuite** —
  son scope CSS natif "site-css" n'émet RIEN côté front (fonctionnalité Pro,
  échoue silencieusement). `apply-tokens.mjs`/`apply-components.mjs` contournent
  ça en générant un snippet **PHP** (scope `front-end`) qui échote la CSS via
  `wp_head`. Ne jamais recréer un snippet CSS-type pour du style destiné au
  public — toujours passer par ce contournement. Détail : `build-recipes/STATUS.md`.
  **Toujours vérifier un nouveau composant visuellement dans un vrai navigateur**
  (pas seulement via le HTML brut REST) avant de le marquer "vérifié".

## Outils

- **Node ≥ 18** (fetch natif, zéro dépendance). Les scripts lisent `.env`
  (`WP_AS_URL` / `WP_AS_USER` / `WP_AS_APP_PASSWORD`).

## MCP vs Claude-in-Chrome — répartition (leçon de la session du 2026-07-12)

MCP est rapide (API REST directe) ; Claude-in-Chrome est lent et le canvas Elementor
s'est révélé **non automatisable de façon fiable** (3 échecs confirmés : drag simple,
double-clic, bouton +). Règle : **tout ce qui peut s'écrire en JSON/REST → MCP.**

| Tâche | Canal |
|---|---|
| Contenu, structure, taxonomies, réglages, CSS (Code Snippets) | 🟢 MCP |
| Meta Box JetEngine (formulaire) | 🟢 MCP + `find`/`form_input` (fiable) |
| **Contenu des gabarits JetEngine, SI vue = Blocks (Gutenberg)** | 🟢 MCP (`post_content` = texte REST) |
| Schéma des blocs JetEngine | 🟢 MCP (`GET /wp-json/wp/v2/block-types`, natif WP) |
| Créer un nouveau Listing Item/Theme Part (modal initial) | 🌐 Chrome (fiable) |
| Conditions d'affichage Theme Builder (Header/Footer) | 🌐 Chrome (capricieux) |
| Canvas Elementor (widgets glisser-déposer) | ❌ à éviter — non fiable |

**Décision de stack confirmée par `docs/BUILD_WORDPRESS_CROCOBLOCK.md` §0 : PAS Elementor,
Gutenberg + JetEngine recommandé.** Le contournement technique trouvé cette session
(Listing Items en vue Blocks) correspond donc à la direction officielle du plan, pas
seulement à un palliatif d'automatisation. Écart à trancher : le site live a Elementor
actif malgré cette recommandation.

## Scripts

| Script | Rôle |
|---|---|
| `scripts/apply-tokens.mjs` | Pousse `design-system/tokens.css` dans Code Snippets (site-css, idempotent) |
| `scripts/apply-settings.mjs` | Identité du site (titre, accroche, fuseau) |
| `scripts/build-structure.mjs` | 7 pages piliers + menu « Principal FR » (idempotent) |
| `scripts/apply-components.mjs` | Pousse `design-system/components.css` (site-css, idempotent) |
| `scripts/apply-carte-evenement.mjs` | Met à jour le contenu Gutenberg du Listing Item carte-événement (post 969) |
| `scripts/apply-carte-a-la-une.mjs` | Met à jour le contenu Gutenberg du Listing Item carte "à la une" (post 976) |
| `scripts/apply-homepage.mjs` | Pousse le contenu Gutenberg de la home mobile (sections 1-11) sur la page Accueil (928) |

## Plan de développement — 7 gabarits minimum pour ouvrir (source : `docs/TEMPLATES_WORDPRESS.md`)

| # | Gabarit | Statut |
|---|---|---|
| — | Structure (menu, 7 pages, taxonomies, tokens) | ✅ Fait |
| — | **Carte-événement** (composant réutilisé partout) | 🟡 v1 (titre/cat/territoire OK ; manque heure formatée, lieu, statut, clic, groupement par jour) |
| — | **Carte "à la une"** (grid 2×2 avec image, section homepage) | 🟡 v1 (image/territoire/titre OK ; manque heure formatée, comme carte-événement) |
| — | Header / Footer (parties de thème) | ❌ Shells vides, CSS jamais vérifié contre la vraie maquette |
| 1 | Home | ✅ v1 complet (24/24 sections), vérifiée visuellement. Plusieurs sections restent statiques/placeholder (transfrontalier, expositions, réseaux sociaux, pages footer manquantes) — détail dans `build-recipes/homepage-mobile.md` |
| 2 | Fiche événement (single TEC) | ❌ |
| 3 | Hub catégorie (×11) | ❌ |
| 4 | Hub territoire (×4) | ❌ |
| 5 | Hub lieu (venue TEC) | ❌ |
| 6 | « Ce week-end » + « Tout l'agenda » (liste filtrable) | ❌ |
| 7 | Recherche + 404 | ❌ |

Détail complet, limitations connues et méthode dans `build-recipes/STATUS.md`.
