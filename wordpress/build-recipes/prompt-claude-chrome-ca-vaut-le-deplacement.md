# Prompt pour Claude dans Chrome — reconstruction "Ça vaut le déplacement"

Contexte : site WordPress agendasabauda.eu, page "Accueil" (id 928), éditeur
Gutenberg (wp-admin → Pages → Accueil → Modifier). Un bloc "HTML personnalisé"
existant doit être remplacé par des blocs natifs.

## Repérage

Dans la liste des blocs (icône plan de la page, en haut à gauche), le bloc à
remplacer est le 9e bloc "HTML personnalisé", situé juste après le groupe
contenant "Nouveautés sur Agenda Sabauda" et juste avant un bloc "Classique".
Son contenu commence par le commentaire :
`<!-- CA VAUT LE DEPLACEMENT — PLACEHOLDER v1 (même mécanisme non tranché que mobile) -->`

## Construction (NE PAS supprimer l'ancien bloc avant que tout soit vérifié)

Insérer, juste après ce bloc HTML personnalisé, la structure suivante :

1. **Bloc Titre (H2)** : texte `Ça vaut le déplacement`. Dans Avancé → Classe(s)
   CSS supplémentaire(s) : `as-desktop-section-title__label`

2. **Bloc Colonnes** (2 colonnes égales). Dans CHAQUE colonne, dans cet ordre :
   - **Bloc Image** : pas d'image réelle pour l'instant, juste le placeholder
     par défaut du bloc (pas besoin d'uploader). Ratio libre.
   - **Bloc Paragraphe** : texte `ITINÉRAIRE À DÉFINIR`. Couleur du texte :
     rouge `#DC5D45`. Taille : petite (~10.5px si réglable). Majuscules
     (transformation du texte en majuscules si l'option existe dans les
     réglages de typographie du bloc, sinon taper directement en majuscules).
   - **Bloc Titre (H3)** : texte `Titre de l'événement transfrontalier`
   - **Bloc Paragraphe ou Bouton (lien simple, pas un bouton plein)** : texte
     `Y aller →`, couleur `#1D1D1B` (noir), gras

3. **Bloc Bouton** (en dehors des colonnes, centré) : texte
   `Voir dans les autres territoires →`, fond noir `#1D1D1B`, texte couleur
   crème `#F7F1E8`, coins légèrement arrondis.

## Vérification avant de continuer

Une fois ces blocs insérés, prendre une capture d'écran du résultat et la
décrire (ou la montrer) avant de supprimer l'ancien bloc HTML personnalisé.
Comparer visuellement avec le bloc HTML existant juste avant (même structure,
2 colonnes + bouton en bas).

## Ce qu'il ne faut PAS faire

- Ne pas publier/mettre à jour la page tant que la comparaison visuelle n'est
  pas validée par l'utilisateur.
- Ne pas toucher aux autres blocs de la page.
- Ne pas essayer de connecter les blocs à de vraies données dynamiques
  (JetEngine Dynamic Field) — ce sera fait dans un second temps par un autre
  assistant (Claude Code, via l'API REST WordPress), une fois la structure
  validée.
