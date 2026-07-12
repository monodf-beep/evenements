# État du build WordPress — agendasabauda.eu

*Dernière mise à jour : session autonome du 2026-07-12 (2e passe).*

## ✅ Fait & vérifié en live

| Élément | Détail | Traçabilité |
|---|---|---|
| Tokens de la charte | Snippet Code Snippets #11, site-css | `wordpress/scripts/apply-tokens.mjs` |
| CSS composants (carte/header/footer/home) | Snippet #12, site-css | `wordpress/scripts/apply-components.mjs` |
| Identité du site | Titre « Agenda Sabauda » + accroche | `wordpress/scripts/apply-settings.mjs` |
| 7 pages piliers | Accueil (928), Aujourd'hui (929), Ce week-end (930), Cette semaine (931), Tout l'agenda (932), À propos (933), Proposer (934) | `wordpress/scripts/build-structure.mjs` |
| Menu « Principal FR » | ID 272, 24 items (temporel, Catégories▾ 11, Territoires▾ 4, Agenda▾, À propos, Proposer) | `wordpress/scripts/build-structure.mjs` |
| Theme Parts (shells, ⚠️ mal configurés) | Header (960), Footer (961), Single Event (962) — posts jet-theme-core créés, **mais SANS Type ni Display Conditions** (voir constat ci-dessous) | via MCP `wp_add_cpt` |
| **Meta box `as_statut` + `as_accent`** | JetEngine Meta Box « Champs Agenda — Statut & mise en avant » sur `tribe_events`. `as_statut` (select : a_venir/complet/annule/reporte), `as_accent` (switcher). **Testé de bout en bout** sur l'événement 578 (round-trip confirmé après reload). | Construit manuellement dans l'admin (formulaire JetEngine, pas d'API dédiée) |
| Listing JetEngine `carte-evenement` | Shell créé (post 927, source tribe_events, vue Elementor) | — |

## ⚠️ Trouvaille utile pour la suite

TEC expose nativement les meta `_tribe_events_status` et `_tribe_events_status_reason` sur chaque événement (vides par défaut). C'est l'alternative native évoquée dans `build-recipes/carte-evenement.md` §7.1. On a choisi `as_statut` (JetEngine, propre à notre contrat `as_*`) plutôt que le champ natif TEC — cohérent avec le reste du contrat méta. Décision : garder `as_statut`, ignorer les champs natifs TEC.

## ⏳ Reste à faire — nécessite un builder visuel (session supervisée)

Deux surfaces UI distinctes ont été testées en profondeur et confirmées **non fiables** en automatisation navigateur (détail dans la section méthode ci-dessous). En revanche, **les formulaires standards** (Meta Boxes, réglages, Quick Edit) s'automatisent très bien via `find` + `form_input`.

Reste à construire en builder, à faire avec Franck :
1. **Binding de la carte-événement** (post 927, Elementor) : les 10 widgets Dynamic Field/Image/Terms de `build-recipes/carte-evenement.md` §3.3, y compris le nouveau `.cs-ev-status` piloté par `as_statut`.
2. **Header/Footer/Single Event — à RECRÉER proprement** via *Crocoblock → Theme Builder → Grid view → filtrer par type (Section pour Header/Footer, Single pour l'événement) → tuile « + Create new page template »*. **Ne pas réutiliser les posts 960/961/962** (créés via API, orphelins du système de conditions — voir constat) : soit les mettre à la corbeille, soit les recycler en éditant leur contenu une fois qu'un vrai Header/Footer aura été créé par l'assistant.
3. **Homepage** (page 928) : Listing Grids + Query Builder — `build-recipes/homepage.md`. Puis réglage `page_on_front=928` (bloqué par le classifieur auto-mode tant que la page est vide — normal, à refaire une fois la home construite).

## ⚠️ Constat important : les shells Header/Footer/Single Event (960/961/962) sont mal formés

Créés via `wp_add_cpt` (MCP), ces 3 posts `jet-theme-core` n'ont **ni Type (Section/Single) ni Display Conditions** — colonnes vides confirmées dans *Theme Parts* (`edit.php?post_type=jet-theme-core`). Le générateur JetThemeCore attend un flux de création précis (Theme Builder → Grid view → modal avec conditions) qui inscrit ces méta ; les créer à la main via l'API REST générique ne suffit pas. **Ces 3 shells sont donc inutilisables tels quels** pour le système de conditions d'affichage — à recréer via l'assistant natif (voir point 2 ci-dessus).

## Point de méthode confirmé pour la suite (deux passes de tests, 2026-07-12)

- **Formulaires WordPress standards** (Meta Boxes, réglages, Quick Edit, champs de condition une fois le modal ouvert) → automatisables de façon fiable via `find` (obtenir une ref fraîche à chaque fois, ne jamais réutiliser une ref après un re-rendu) + `form_input` (indépendant du scroll). Éviter les clics sur des refs répétées sans rafraîchir (staleness — cause silencieuse d'actions « fantômes ») et éviter les toggles/checkbox « hidden » par coordonnées (a causé une navigation accidentelle une fois, sans perte de données).
- **Builder Elementor (canvas de widgets, drag-drop)** → PAS automatisable de façon fiable (3 tentatives échouées : drag simple, double-clic, bouton +). Le panneau de widgets et la recherche fonctionnent (formulaire), mais l'INSERTION d'un widget dans le canvas ne prend pas.
- **JetThemeCore Theme Builder (arbre de conditions, vue « Tree view »)** → rendu en canvas/SVG avec hit-testing custom, invisible à l'arbre d'accessibilité (`find` ne trouve aucun bouton), clics par coordonnées sans effet. **Vue « Grid view »** est un vrai DOM cliquable et ouvre un modal formulaire fonctionnel (Include/Entire/Entire Site + Add Condition confirmés cliquables et réactifs) — MAIS le bouton final **« Create » ne complète pas la création de façon fiable** (aucun nouvel élément n'apparaît dans la liste après plusieurs tentatives, cause exacte non identifiée : pas de champ nom visible, possible échec de validation silencieux côté JS). Cette UI a aussi provoqué plusieurs timeouts de capture d'écran (CDP), signe d'un rendu React/animations lourd peu compatible avec l'automatisation.
- **Conclusion pratique** : toute tâche nécessitant un builder visuel Crocoblock (Elementor widgets OU Theme Builder conditions) doit se faire en session supervisée avec Franck — un humain cliquant au bon endroit réussira là où l'automatisation échoue de façon intermittente et difficile à diagnostiquer à distance.
