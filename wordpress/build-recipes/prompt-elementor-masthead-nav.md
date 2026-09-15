# Prompt Claude dans Chrome — Masthead + Navigation (Elementor + JetMenu)

Onglet déjà ouvert : édition Elementor de la page "Accueil" (agendasabauda.eu,
id 928, tabId 305323705 ou équivalent actuel).

## Étape 0 — confirmer l'étendue avant de construire

Dans le panneau **Structure** (à droite), faire défiler entièrement la liste
pour compter le nombre total de widgets sous le Conteneur racine. Dire
précisément : y a-t-il UN SEUL widget "Éditeur de texte" pour toute la page,
ou plusieurs widgets/sections distincts plus bas ? Ne rien construire tant
que cette réponse n'est pas donnée.

## Étape 1 — ajouter un nouveau conteneur EN TOUT DÉBUT DE PAGE

Sans toucher au widget "Éditeur de texte" existant : ajouter un **nouveau
Conteneur** juste avant lui (utiliser le "+" d'ajout d'élément positionné
au-dessus de l'élément existant dans le canvas, ou glisser un nouveau
Conteneur depuis le panneau de gauche tout en haut de la Structure).

Dans ce nouveau conteneur, ajouter dans l'ordre :

1. **Widget Image** : cliquer "Choisir une image" → Médiathèque → chercher
   "masthead" → sélectionner `masthead-agenda-sabauda-v7.png` (déjà
   uploadée, ne pas en re-uploader une autre). Largeur ~460px, centrée.
   Dans l'onglet Contenu, section Lien : mettre l'URL de la page d'accueil
   (`https://agendasabauda.eu/`).

2. **Widget Titre ou Texte** (petit, centré, gris `#6F6B62`, majuscules) :
   `Quoi faire, où manger · 4 territoires`

3. **Widget JetMenu** : chercher "JetMenu" dans le panneau de widgets à
   gauche (catégorie Crocoblock/Jet), le glisser dans le conteneur. Dans ses
   réglages (onglet Contenu), chercher un champ "Menu" ou "Source du menu" —
   sélectionner le menu WordPress existant **"Principal FR"** s'il apparaît
   dans la liste déroulante (menu id 272, déjà construit avec Aujourd'hui,
   Ce week-end, Catégories▾ [11 sous-items], Territoires▾ [4 sous-items],
   Agenda▾, À propos, Proposer un événement). Si "Principal FR" n'apparaît
   pas dans la liste, le signaler avant de continuer — ne pas recréer les
   liens à la main dans JetMenu.

4. À côté du widget JetMenu : un petit texte `FR | IT` (texte simple, pas de
   fonctionnalité de bascule de langue pour l'instant).

## Vérification avant de continuer

Capture d'écran du résultat à largeur desktop (>1024px, le canvas Elementor
suffit) et, si possible, en aperçu mobile (bouton d'aperçu responsive
d'Elementor, icône mobile en bas de l'éditeur). Vérifier que le menu JetMenu
affiche bien tous les items (y compris les sous-menus Catégories/Territoires
au survol ou au clic) et qu'il se transforme en menu hamburger en mobile.

## Ce qu'il ne faut PAS faire

- Ne pas supprimer le widget "Éditeur de texte" existant.
- Ne pas cliquer sur "Mettre à jour"/"Publier" — la page ne doit pas être
  sauvegardée tant que la comparaison visuelle n'est pas validée par
  l'utilisateur.
- Ne pas essayer de rendre la navigation sticky pour l'instant (ce sera fait
  après, une fois la structure validée).
