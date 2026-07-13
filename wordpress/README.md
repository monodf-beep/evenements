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
| `scripts/apply-homepage.mjs` | Pousse le contenu Gutenberg de la home mobile (24 sections) sur la page Accueil (928) |
| `scripts/apply-single-event-meta.mjs` | Pousse le snippet PHP qui ajoute pilule territoire/statut/crédit photo/"Vérifié le" sur la fiche événement native TEC |
| `scripts/apply-liste-pages.mjs` | ⚠️ Obsolète — poussait l'ancien contenu Gutenberg (Listing Grid `.ag-row`) des pages 930/932, remplacé par `apply-liste-evenements-template.mjs` (template_redirect intercepte avant, contenu Gutenberg inutilisé) |
| `scripts/apply-cs-cards.mjs` | Pousse `design-system/cs-cards.php` (composants carte partagés `cs_card_standard`/`cs_card_compact`/`cs_card_rail`), snippet global — prérequis pour les 3 scripts ci-dessous |
| `scripts/apply-taxonomy-archive-query.mjs` | Pousse le snippet PHP qui débloque les archives de taxonomie territoire/catégories (force post_type=tribe_events) |
| `scripts/apply-taxonomy-archive-template.mjs` | Pousse le snippet PHP qui prend le contrôle du rendu des Hubs territoire/catégorie (vraie carte "standard", pilules colorées) |
| `scripts/apply-liste-evenements-template.mjs` | Pousse le snippet PHP qui prend le contrôle du rendu de "Ce week-end" (930) / "Tout l'agenda" (932) (vraie carte "compacte") |
| `scripts/apply-search-events.mjs` | Pousse le snippet PHP qui élargit la recherche aux événements (date + territoire sous chaque résultat) — vestige, plus vraiment utilisé côté rendu depuis `apply-search-page-template.mjs` |
| `scripts/apply-search-page-template.mjs` | Pousse le snippet PHP qui prend le contrôle du rendu de la page de recherche (`is_search()`) |
| `scripts/apply-site-header-footer.mjs` | Pousse le snippet PHP qui injecte le header/footer de marque site-wide (sauf Accueil) |
| `scripts/apply-proposer-evenement-template.mjs` | Pousse le snippet PHP qui prend le contrôle du rendu ET du traitement du formulaire "Proposer un événement" (934) |
| `scripts/apply-venue-single-template.mjs` | Pousse le snippet PHP de la fiche lieu (`tribe_venue`) — prêt mais inatteignable tant que le bug de permaliens n'est pas résolu |
| `scripts/apply-le-fil-template.mjs` | Pousse le snippet PHP du listing "Le Fil" (page 994, brouillon — pas encore publiée) |
| `scripts/apply-article-single-template.mjs` | Pousse le snippet PHP de la fiche article "Le Fil" (native `post`, `is_single()`) |

## Plan de développement — 7 gabarits minimum pour ouvrir (source : `docs/TEMPLATES_WORDPRESS.md`)

| # | Gabarit | Statut |
|---|---|---|
| — | Structure (menu, 7 pages, taxonomies, tokens) | ✅ Fait |
| — | **Carte-événement** (composant réutilisé partout) | 🟡 v1 (titre/cat/territoire OK ; manque heure formatée, lieu, statut, clic, groupement par jour) |
| — | **Carte "à la une"** (grid 2×2 avec image, section homepage) | 🟡 v1 (image/territoire/titre OK ; manque heure formatée, comme carte-événement) |
| — | Header / Footer (parties de thème) | ✅ v1 site-wide via hooks PHP (`wp_body_open`/`wp_footer`), pas de Theme Builder. Vraie menu WP ("Principal FR", 24 items). Exclut la page Accueil (a déjà les siens) |
| 1 | Home | ✅ v1 complet **mobile + desktop** (basculés en CSS, `min-width:1024px`), vérifiée visuellement. Plusieurs sections restent statiques/placeholder (transfrontalier, expositions, réseaux sociaux, pages footer manquantes) — détail dans `build-recipes/homepage-mobile.md` |
| 2 | Fiche événement (single TEC) | ✅ v2 : template natif TEC + pilule territoire, badge de statut, crédit photo, "Vérifié le", et 3 rails liés (même lieu/catégorie/à venir) — tout en PHP, pas de Theme Builder |
| 3 | Hub catégorie (×11) | ✅ v2 : vraie carte "standard" (`cs_card_standard`, pilules colorées), fil d'Ariane, filtres cosmétiques, newsletter légère — manque intro éditoriale réelle (à récupérer auprès de Franck) |
| 4 | Hub territoire (×4) | ✅ v2 Idem — vérifié sur `/territoire/piemont/` |
| 5 | Fiche lieu (venue TEC) | 🟡 Gabarit prêt (`venue-single-template.php`, fil d'Ariane + événements à venir + adresse) mais 🚧 toujours inatteignable — bug de permaliens `/lieu/{slug}/`. Nouvelle piste : réglage TEC "Enable Venue and Organizer Pages" probablement désactivé — à vérifier par Franck dans wp-admin (nécessite une connexion, hors de portée de cette session). Détail dans STATUS.md |
| 6 | « Ce week-end » + « Tout l'agenda » (liste filtrable) | ✅ v2 : gabarit PHP dédié (`template_redirect`), vraie carte "compacte" (`cs_card_compact`), compteur, filtres cosmétiques, pagination — vérifié visuellement sur les deux pages. Filtre par date pas encore câblé (nécessite meta_query dédiée) — "Ce week-end" affiche tous les événements pour l'instant |
| 7 | Recherche + 404 | ✅ v2 : gabarit PHP dédié (`is_search()`, `template_redirect`) — champ fonctionnel, filtres cosmétiques, état "Raccourcis" (avant saisie), résultats en carte compacte, état vide avec CTA. Vérifié visuellement (avec/sans requête). 404 = gabarit générique du thème, hérite du header/footer de marque — acceptable en l'état |
| 8 | Proposer un événement (formulaire, page 934) | ✅ Formulaire public fonctionnel (`template_redirect` sur `is_page(934)`) — crée un `tribe_events` en statut draft à chaque soumission (jamais publié automatiquement), nonce + honeypot anti-spam. Vérifié de bout en bout (6 soumissions de test créées puis supprimées). Dates/lieu en texte libre, à structurer par la rédaction avant publication |
| 9 | Le Fil (magazine, listing + article) | 🟡 Gabarits prêts et vérifiés (post natif `post`) mais page listing (994, "Le Fil") créée en **brouillon** — publication bloquée par le classifieur auto-mode (nouvelle page publique sans validation), à confirmer explicitement avant mise en ligne. Encadrés Quand/Où/Prix pilotés par des champs meta libres, pas encore une Meta Box structurée |

Détail complet, limitations connues et méthode dans `build-recipes/STATUS.md`.
