# Prompts de reconstruction de la home (928) — Elementor + Crocoblock

Règle pour TOUTES les sections ci-dessous : Claude dans Chrome pose
uniquement la **structure** (conteneur, colonnes/grille si besoin) et des
**widgets vides** (sans régler leur contenu), puis clique **Mettre à jour**.
Claude Code configure ensuite le contenu (texte, images, liens, données
dynamiques) via l'API REST WordPress. Ne jamais supprimer l'ancien widget
"Éditeur de texte" existant avant qu'une section de remplacement soit
entièrement validée.

---

## 1. Masthead + Navigation

Nouveau conteneur en tout début de page. Ajouter, sans les configurer :
1. Widget **Image**
2. Widget **Titre**
3. Widget **JetMenu**
4. Widget **Texte** (pour "FR | IT")

Cliquer **Mettre à jour**.

## 2. Sélecteur de territoire actif

Nouveau conteneur, juste après la section 1. Ajouter :
1. Widget **Texte**

Cliquer **Mettre à jour**.

## 3. Carrousel hero

Nouveau conteneur. Ajouter :
1. Widget **Titre** (à l'intérieur du conteneur — l'image de fond se règle
   dans les Styles du conteneur lui-même, pas besoin d'un widget Image séparé)

Cliquer **Mettre à jour**.

## 4. Barre de recherche

Nouveau conteneur. Ajouter :
1. Widget **Recherche** (natif Elementor) — si introuvable, le signaler et
   passer à la section suivante sans bloquer.

Cliquer **Mettre à jour**.

## 5. 6 tuiles + newsletter

Nouveau conteneur, diviser en **2 colonnes**.
- Colonne gauche : grille interne 3×2 (conteneur imbriqué) avec **6 widgets
  Icon Box** vides.
- Colonne droite : conteneur avec **3 widgets** : Titre, Texte, Bouton.

Cliquer **Mettre à jour**.

## 6. À la une / Ce week-end / Événements d'aujourd'hui (3 blocs séparés)

Pour CHACUNE des 3 sections (à répéter 3 fois), nouveau conteneur avec :
1. Widget **Titre**
2. Widget **JetEngine – Listing Grid**

Si le widget "JetEngine – Listing Grid" n'apparaît pas dans le panneau, ou
si aucun Listing Item n'est proposé dans ses réglages, le signaler avant de
continuer — ne pas en créer un nouveau.

Cliquer **Mettre à jour** après chaque section.

## 7. Ça vaut le déplacement

Nouveau conteneur avec Widget Titre, puis diviser en **2 colonnes**. Dans
chaque colonne :
1. Widget **Image**
2. Widget **Texte**
3. Widget **Titre**
4. Widget **Texte** (lien)

Sous les 2 colonnes : Widget **Bouton**.

Cliquer **Mettre à jour**.

## 8. 3 colonnes : Nouveautés / En évidence / L'agenda à venir

Nouveau conteneur, diviser en **3 colonnes égales**.
- Colonne 1 : Widget Titre + 2× (Widget Image + Widget Titre + Widget Texte)
- Colonne 2 : Widget Titre + Widget **JetEngine Listing Grid** + grille
  interne 2×2 avec 4× Widget Icon Box
- Colonne 3 : Widget Titre + Widget **JetEngine Listing Grid** + Widget
  Texte (lien) + 2× Widget Bouton

Cliquer **Mettre à jour**.

## 9. Bandeau newsletter pleine largeur

Nouveau conteneur pleine largeur, diviser en **2 colonnes**.
- Colonne gauche : Widget Titre + Widget Texte
- Colonne droite : Widget Texte (champ email) + Widget Bouton

Cliquer **Mettre à jour**.

## 10. Footer

**Rien à construire** — déjà unifié côté PHP (`site-header-footer.php`),
s'affiche automatiquement sur toutes les pages.

## 11. Barre pub sticky

**Avant de construire** : vérifier dans wp-admin → Réglages → Ad Inserter
si un type de bloc propose une position fixe native. Si oui, ne rien
construire ici — le signaler à Claude Code qui configurera directement le
bloc Ad Inserter correspondant.

## 12. Gouttières pub

**Rien à construire** — gérées en PHP, hors du contenu de page Elementor.

---

## Ordre d'exécution

1 → 3 → 5 → 6 (×3) → 7 → 8 → 9 → 4 → 2 → 11 (vérification seulement).

Après chaque "Mettre à jour", Claude Code prend le relais pour configurer
le contenu de la section avant de passer à la suivante.
