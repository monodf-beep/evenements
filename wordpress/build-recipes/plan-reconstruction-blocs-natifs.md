# Plan + prompts de reconstruction de la home (928) en Elementor + Crocoblock

Workflow : Claude dans Chrome construit par glisser-déposer dans Elementor
(widgets natifs + Crocoblock : JetEngine, JetElements, JetMenu...), Claude
Code configure ensuite le contenu/les données dynamiques via l'API REST
WordPress une fois la structure posée. **Garde-fous valables pour TOUTES les
sections ci-dessous** : ne rien supprimer de l'ancien contenu avant capture
d'écran comparative validée, ne jamais cliquer "Publier"/"Mettre à jour"
sans confirmation explicite.

État de départ (2026-07-14) : toute la page Accueil semble avoir été
aspirée par Elementor dans un unique widget "Éditeur de texte" au premier
chargement (à reconfirmer en étape 0 du premier prompt). On construit les
nouvelles sections À CÔTÉ, sans toucher à ce widget, jusqu'à validation
complète.

---

## 1. Masthead + Navigation (JetMenu) — PRIORITÉ 1

Prompt déjà détaillé dans `prompt-elementor-masthead-nav.md`. Résumé :
nouveau Conteneur en tout début de page → Widget Image (logo
`masthead-agenda-sabauda-v7.png`, ~460px centré, lien `/`) → Widget
Titre/Texte petit gris majuscules (`Quoi faire, où manger · 4 territoires`)
→ Widget **JetMenu** lié au menu WordPress existant **"Principal FR"** (id
272) → texte `FR | IT`.

## 2. Sélecteur de territoire actif

Reste en widget Texte/HTML pour l'instant (pas d'équivalent Crocoblock
évident pour ce dropdown précis) : `Vous regardez **Savoie / Haute-Savoie**
| Changer : Piémont · Vallée d'Aoste · Comté de Nice` — texte simple avec
liens, sur fond `#FBF7F0`, sans interaction dropdown pour l'instant (v1).
Pas prioritaire, à construire après les sections dynamiques.

## 3. Carrousel hero (photo + titre)

**Construction** : un **Conteneur** avec image de fond (onglet Style →
Arrière-plan → Image, choisir/uploader une photo — ex. château de Conflans
déjà utilisé) + un **Widget Titre** superposé en bas à gauche, texte blanc
`Mille ans de mémoire, un week-end à Conflans`, police display (Saira
Condensed/Semplicita si disponible dans les réglages de police du thème).
Hauteur du conteneur : ~500px desktop. Pas de vrai carrousel/slider pour
l'instant (image statique, cohérent avec le choix déjà fait cette session).

## 4. Barre de recherche

**Construction** : chercher un widget **"Recherche"** natif Elementor
(catégorie Général) ou JetSearch si disponible dans le panneau Crocoblock.
Le configurer avec le placeholder `Rechercher un événement, une ville…` et
un bouton `Chercher`. Si aucun widget de recherche stylable n'est trouvé
facilement, le signaler — on gardera le champ HTML actuel en repli.

## 5. 6 tuiles + newsletter

**Construction** : un **Conteneur** en 2 colonnes (grille de tuiles à
gauche, encart newsletter à droite) :
- Colonne gauche : grille 3×2 de **Widget Icon Box** (JetElements ou natif
  Elementor) — 6 tuiles : "Ce week-end", "Saveurs & gastronomie",
  "Concerts", "Expositions", "En famille", "Tout l'agenda", chacune avec
  une icône + libellé, fond `#FBF7F0`, lien vers la page correspondante
  quand elle existe (`/ce-week-end/`, `/tout-l-agenda/`), `#` sinon.
- Colonne droite : un **Conteneur** fond rouge `#DC5D45`, avec Widget Titre
  `Recevez l'essentiel des quatre territoires` (blanc), Widget Texte
  `Chaque vendredi matin, dans votre boîte.` (blanc, plus petit), Widget
  Bouton `S'inscrire à la newsletter` (fond crème `#F7F1E8`, texte rouge).

## 6. À la une / Ce week-end / Événements d'aujourd'hui

**Ne PAS reconstruire depuis zéro** — ces trois sections utilisent déjà le
composant JetEngine "carte à la une" (Listing Item post 976). Chercher le
widget **"JetEngine – Listing Grid"** dans le panneau Crocoblock, le glisser,
et dans ses réglages sélectionner comme source le Listing Item existant
(chercher "carte-a-la-une" ou l'ID 976 dans le sélecteur). Configurer :
- "À la une" : 3 colonnes, 3 événements, titre de section + lien "Voir tout"
- "Ce week-end" : 3 colonnes, 6 événements
- "Événements d'aujourd'hui" : 4 colonnes, 4 événements

Si le Listing Item 976 n'apparaît pas dans la liste (il a été construit en
vue Blocks/Gutenberg, peut-être pas visible depuis un widget Elementor), le
signaler avant de continuer — il faudra alors le recréer en vue Elementor,
étape à faire avec prudence (historiquement peu fiable en automatisation).

## 7. Ça vaut le déplacement

Prompt déjà écrit en version Gutenberg (`prompt-claude-chrome-ca-vaut-le-deplacement.md`)
— **adapter en widgets Elementor** : un **Conteneur** 2 colonnes, dans
chaque colonne un Widget Image (placeholder) + Widget Texte rouge majuscule
`ITINÉRAIRE À DÉFINIR` + Widget Titre `Titre de l'événement transfrontalier`
+ lien `Y aller →`. Sous les 2 colonnes, un Widget Bouton centré `Voir dans
les autres territoires →` (fond noir `#1D1D1B`, texte crème `#F7F1E8`).

## 8. 3 colonnes : Nouveautés / En évidence / L'agenda à venir

**Construction** : un **Conteneur** 3 colonnes égales :
- Colonne 1 "Nouveautés sur Agenda Sabauda" : Widget Titre + 2× (Widget
  Image + Widget Titre H3 + Widget Texte avec lien "»") — contenu éditorial
  statique pour l'instant (pas de vraies données Le Fil).
- Colonne 2 "En évidence" : Widget Titre + **Widget JetEngine Listing Grid**
  (même Listing Item 976, 1 colonne, 2 événements) + grille 2×2 de Icon Box
  ("Aux alentours", "Musées", "Curiosités", "En famille") + un encart pub
  (déjà câblé côté PHP, ne pas y toucher ici).
- Colonne 3 "L'agenda à venir" : Widget Titre + **Widget JetEngine Listing
  Grid** (Listing Item 976, 1 colonne, 3 événements) + lien "Tout l'agenda"
  + 2 boutons Instagram/Facebook + encadré "Faire de la publicité".

## 9. Bandeau newsletter pleine largeur

**Construction** : un **Conteneur** pleine largeur, fond rouge `#DC5D45`,
2 colonnes : à gauche Widget Titre `L'essentiel des quatre territoires,
dans votre boîte` (blanc, grand) + Widget Texte descriptif ; à droite un
champ email + Widget Bouton `S'inscrire`.

## 10. Footer

**Ne rien construire ici** — déjà unifié site-wide via
`site-header-footer.php` (hook PHP, hors contenu de page). Le footer
s'affiche automatiquement sur toutes les pages, y compris l'Accueil.

## 11. Barre pub sticky (mobile + desktop)

**Avant de construire quoi que ce soit** : vérifier dans wp-admin →
Réglages → Ad Inserter si un des types de bloc propose une **position fixe
native** (bas d'écran, avec bouton de fermeture) — si oui, ça remplace
entièrement le besoin de construire ce widget dans Elementor, il suffit de
configurer le bloc Ad Inserter correspondant (déjà câblé en shortcode
`[adinserter block="6"]` desktop / `[adinserter block="12"]` mobile côté
PHP, cf. `homepage-template.php`/contenu existant).

## 12. Gouttières pub (160×600)

**Ne rien construire ici** — gérées en PHP (`homepage-template.php`,
position fixe, shortcodes Ad Inserter `#1`/`#2`), hors du contenu de page
Elementor.

---

## Ordre d'exécution recommandé

1 (masthead+nav) → 3 (hero) → 5 (tuiles+newsletter) → 6 (listings existants,
vérifier compatibilité Elementor) → 7 (ça vaut le déplacement) → 8 (3
colonnes) → 9 (bandeau newsletter) → 4 (recherche) → 2 (sélecteur territoire)
→ 11 (vérifier Ad Inserter avant de construire quoi que ce soit).
