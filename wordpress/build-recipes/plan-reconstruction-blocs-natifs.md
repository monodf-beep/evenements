# Plan de reconstruction de la home (928) en blocs natifs

Nouveau workflow (2026-07-14) : Claude dans Chrome place la structure par
glisser-déposer (blocs natifs WordPress + JetEngine/Crocoblock), Claude Code
configure ensuite le contenu/les données dynamiques via l'API REST WordPress
(MCP). Objectif : remplacer les blocs "HTML personnalisé" par des blocs
natifs, éditables visuellement, sans les bugs du HTML fait main rencontrés
cette session (empilement cassé, centrage cassé, cascade CSS en conflit avec
JetEngine).

**Opportunité d'architecture** : les blocs Colonnes et Navigation natifs
s'adaptent déjà tout seuls à la largeur d'écran. Pour les sections encore en
HTML, on peut donc viser **un seul arbre responsive** au lieu de la
duplication actuelle `.as-home` (mobile) / `.as-home-desktop` (desktop) —
qui est la source de plusieurs bugs corrigés cette session (contenu non
masqué, empilement cassé). Les blocs JetEngine Listing Grid (À la une, Ce
week-end...) sont DÉJÀ nativement responsives (attributs `columns` /
`columns_tablet` / `columns_mobile`) et n'ont pas besoin de cette
duplication — c'est la preuve que ça marche.

## Sections, dans l'ordre de la page

| # | Section | État actuel | Cible |
|---|---|---|---|
| 1 | Masthead + navigation | Dupliqué mobile/desktop, logo en `<img>` custom, burger en CSS pur (checkbox hack) | Bloc **Image** (logo) + Bloc **Navigation** natif (menu "Principal FR", id 272) — repli mobile automatique, **un seul arbre** |
| 2 | Sélecteur de territoire actif | HTML custom (dropdown CSS pur) | Reste HTML pour l'instant (pas d'équivalent natif évident) — pas prioritaire |
| 3 | Carrousel hero (photo Conflans + titre) | HTML custom, image statique | Bloc **Cover** (image de fond + texte superposé), nativement responsive |
| 4 | Barre de recherche | HTML custom (form GET) | À tester : bloc **Recherche** natif WordPress, sinon garder HTML |
| 5 | 6 tuiles + newsletter | HTML custom (grid CSS) | Bloc **Colonnes** avec Image/Titre par tuile + bloc **Groupe** coloré pour la newsletter |
| 6 | À la une / Ce week-end / Événements d'aujourd'hui | **Déjà des blocs JetEngine Listing Grid natifs** | Aucun changement structurel — juste retirer le wrapper `.as-desktop-grid-3`/`-4` devenu inutile (cf. STATUS.md, bug du 2026-07-14) |
| 7 | Ça vaut le déplacement | HTML custom, placeholder | **Prompt déjà écrit** : `prompt-claude-chrome-ca-vaut-le-deplacement.md` |
| 8 | 3 colonnes Nouveautés / En évidence / L'agenda à venir | HTML custom + 2 Listing Grid imbriqués | Bloc **Colonnes** (3), Listing Grid JetEngine dans 2 colonnes, contenu éditorial dans la 1ère |
| 9 | Bandeau newsletter pleine largeur | HTML custom | Bloc **Groupe** (fond rouge) + Colonnes (texte + formulaire) |
| 10 | Footer | **Déjà unifié** (site-header-footer.php, hors contenu de page) | Rien à faire |
| 11 | Barre pub sticky | HTML custom + shortcode Ad Inserter | À vérifier : Ad Inserter propose un mode "position fixe" natif — pourrait remplacer tout le HTML custom |
| 12 | Gouttières pub (160×600) | PHP (`homepage-template.php`) + shortcode Ad Inserter | Reste en PHP (position fixe hors du flux de contenu, pas un bloc de page) |

## Prompt prêt à l'emploi — Masthead + Navigation (priorité 1)

C'est la section qui a causé le plus de bugs cette session (logo cassé,
header dupliqué, nav non sticky, centrage cassé). La reconstruire en blocs
natifs est la meilleure démonstration de la méthode.

**Repérage** : dans la liste des blocs de la page Accueil (928), les tout
premiers blocs "HTML personnalisé" contiennent le masthead — un pour la
version mobile (commentaire `<!-- MASTHEAD -->` puis `<!-- BARRE FR|IT +
BURGER -->` puis `<!-- MENU (overlay) -->`), un autre plus bas pour la
version desktop (commentaire `<!-- MASTHEAD -->` puis `<!-- NAV STICKY -->`).
**Ne pas les supprimer avant d'avoir la nouvelle version validée.**

**Construction**, à insérer en tout début de page (avant le premier bloc
existant) :

1. **Bloc Image** : uploader `https://agendasabauda.eu/wp-content/uploads/2026/07/masthead-agenda-sabauda-v7.png`
   (déjà dans la médiathèque WordPress — chercher "masthead" dans le
   sélecteur média plutôt que ré-uploader). Largeur max ~460px, centré. Lien
   de l'image vers la page d'accueil (`/`).
2. **Bloc Paragraphe** (petit texte centré, gris `#6F6B62`, majuscules) :
   `Quoi faire, où manger · 4 territoires`
3. **Bloc Navigation** (rechercher "Navigation" dans l'inserteur de blocs) :
   - Dans les réglages du bloc, choisir de lier au menu WordPress existant
     **"Principal FR"** (pas besoin de recréer les liens un par un).
   - Vérifier dans les réglages qu'un mode d'affichage mobile (icône
     hamburger / "Overlay menu") est activé — c'est le comportement natif
     qui remplace le checkbox-hack CSS actuel.
   - Ajouter, aligné à droite du bloc Navigation, un petit texte ou bloc
     séparé `FR | IT` (pas de bloc natif pour un sélecteur de langue —
     texte simple pour l'instant).

**Vérification avant de continuer** : capture d'écran à largeur mobile
(< 768px) ET desktop (> 1024px), vérifier que le menu se replie bien en
version mobile (icône hamburger cliquable) et reste lisible en desktop.
Comparer avec le rendu actuel du site (les deux mastheads existants,
mobile et desktop) avant de les supprimer.

**Ce qu'il ne faut PAS faire** :
- Ne pas supprimer les anciens blocs HTML avant validation visuelle.
- Ne pas essayer de rendre le bloc Navigation sticky au scroll pour
  l'instant — ce sera ajouté après (CSS additionnelle) une fois la
  structure validée.
- Ne pas publier la page avant confirmation.

## Suite (à préparer une fois les sections 1 et 7 validées)

Prompts à écrire ensuite, dans cet ordre : #3 (carrousel), #5 (tuiles +
newsletter), #8 (3 colonnes), #9 (bandeau newsletter). Je les rédigerai au
fur et à mesure, une fois qu'on aura confirmé que la méthode fonctionne bien
sur les deux premières sections.
