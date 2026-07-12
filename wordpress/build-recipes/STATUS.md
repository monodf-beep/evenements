# État du build WordPress — agendasabauda.eu

*Dernière mise à jour : session autonome du 2026-07-12.*

## ✅ Fait & vérifié en live

| Élément | Détail | Traçabilité |
|---|---|---|
| Tokens de la charte | Snippet Code Snippets #11, site-css | `wordpress/scripts/apply-tokens.mjs` |
| CSS composants (carte/header/footer/home) | Snippet #12, site-css | `wordpress/scripts/apply-components.mjs` |
| Identité du site | Titre « Agenda Sabauda » + accroche | `wordpress/scripts/apply-settings.mjs` |
| 7 pages piliers | Accueil (928), Aujourd'hui (929), Ce week-end (930), Cette semaine (931), Tout l'agenda (932), À propos (933), Proposer (934) | `wordpress/scripts/build-structure.mjs` |
| Menu « Principal FR » | ID 272, 24 items (temporel, Catégories▾ 11, Territoires▾ 4, Agenda▾, À propos, Proposer) | `wordpress/scripts/build-structure.mjs` |
| Theme Parts (shells) | Header (960), Footer (961), Single Event (962) — posts jet-theme-core créés, contenu à construire | via MCP `wp_add_cpt` |
| **Meta box `as_statut` + `as_accent`** | JetEngine Meta Box « Champs Agenda — Statut & mise en avant » sur `tribe_events`. `as_statut` (select : a_venir/complet/annule/reporte), `as_accent` (switcher). **Testé de bout en bout** sur l'événement 578 (round-trip confirmé après reload). | Construit manuellement dans l'admin (formulaire JetEngine, pas d'API dédiée) |
| Listing JetEngine `carte-evenement` | Shell créé (post 927, source tribe_events, vue Elementor) | — |

## ⚠️ Trouvaille utile pour la suite

TEC expose nativement les meta `_tribe_events_status` et `_tribe_events_status_reason` sur chaque événement (vides par défaut). C'est l'alternative native évoquée dans `build-recipes/carte-evenement.md` §7.1. On a choisi `as_statut` (JetEngine, propre à notre contrat `as_*`) plutôt que le champ natif TEC — cohérent avec le reste du contrat méta. Décision : garder `as_statut`, ignorer les champs natifs TEC.

## ⏳ Reste à faire — nécessite un builder visuel (session supervisée)

L'automatisation du **glisser-déposer Elementor a été testée et confirmée non fiable** (3 tentatives échouées : drag simple, double-clic, bouton +). En revanche, **les formulaires standards** (Meta Boxes, réglages) s'automatisent très bien via `find` + `form_input`.

Reste à construire en builder (Elementor/JetEngine), à faire avec Franck :
1. **Binding de la carte-événement** (post 927) : les 10 widgets Dynamic Field/Image/Terms de `build-recipes/carte-evenement.md` §3.3, y compris le nouveau `.cs-ev-status` piloté par `as_statut`.
2. **Header** (post 960) : logo/wordmark, nav Principal FR (menu 272), recherche, FR|IT — `build-recipes/header-menu.md`.
3. **Footer** (post 961) : colonnes territoire/catégorie, à-propos, mention éditeur — `build-recipes/footer.md`.
4. **Single Event** (post 962) : template fiche événement.
5. **Homepage** (page 928) : Listing Grids + Query Builder — `build-recipes/homepage.md`. Puis réglage `page_on_front=928` (bloqué par le classifieur auto-mode tant que la page est vide — normal).
6. Attribution des Theme Parts (conditions d'affichage : Header/Footer sur tout le site) — se fait dans l'admin JetThemeCore.

## Point de méthode confirmé pour la suite

- **Formulaires WordPress standards** (Meta Boxes, réglages, taxonomies) → automatisables de façon fiable via `find` (obtenir une ref fraîche) + `form_input` (indépendant du scroll). Éviter les clics sur des refs répétées sans rafraîchir (staleness) et éviter les toggles/checkbox « hidden » par coordonnées (a causé une navigation accidentelle une fois).
- **Builder Elementor/JetEngine (drag-drop de widgets)** → PAS automatisable de façon fiable actuellement. À faire en session supervisée.
