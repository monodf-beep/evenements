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

## Outils

- **Node ≥ 18** (fetch natif, zéro dépendance). Les scripts lisent `.env`
  (`WP_AS_URL` / `WP_AS_USER` / `WP_AS_APP_PASSWORD`).

## Scripts

| Script | Rôle |
|---|---|
| `scripts/apply-tokens.mjs` | Pousse `design-system/tokens.css` dans Code Snippets (site-css, idempotent). `node wordpress/scripts/apply-tokens.mjs` |

## Reste à faire (ordre du design system README-claude-code)

1. ~~Tokens (couleurs/typo/espacements)~~ ✅ *(snippet Code Snippets)*
2. Polices SemplicitaPro (@font-face) — upload .woff + snippet, ou mu-plugin via SFTP
3. Meta box JetEngine sur `tribe_events` (statut, accent, billetterie)
4. Carte-événement (JetEngine Listing) — via Claude-in-Chrome
5. Archive/Agenda + filtres (JetSmartFilters)
6. Fiche événement (single TEC)
7. Hubs taxonomies (territoire, catégorie)
8. Homepage
