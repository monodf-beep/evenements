# Spécifications : visuels génériques de repli (territoire × catégorie)

*Brief pour la production des visuels de repli sur Claude Design. Utilisés quand une
fiche événement n'a pas de photo propre (cf. `docs/CHARTE_EDITORIALE.md` §9 : « si aucune
image, ne rien afficher pour l'instant » — ce document couvre l'alternative prévue en
backlog). Remplace à terme l'aplat de couleur généré par `cs_fallback_visual()`
(snippet #21 "CS · Composants carte (partagé)").*

---

## 1. Contexte technique

Les cartes événement (`cs_card_standard`, `cs_card_compact`, snippet #21) affichent
l'image dans un conteneur `aspect-ratio:3/2`. Quand l'événement n'a pas de miniature
(`get_the_post_thumbnail()` vide), le code retombe sur `cs_fallback_visual($event_id)` :
un aplat de couleur du territoire + monogramme en filigrane + nom de la catégorie en
texte. Ce document définit le remplacement illustré de cet aplat.

## 2. Format

- **Ratio 3:2**, livrer en **1200 × 800 px** (JPG).
- Le CSS redimensionne ensuite en responsive (`object-fit:cover`) — pas besoin de
  décliner plusieurs tailles.
- Poids cible : < 300 Ko par fichier (compression web standard).

## 3. Style

- Cohérent avec le monogramme/skyline en ligne déjà utilisé dans le masthead du site
  (silhouettes alpines en ligne fine, style croquis) — **pas de photo, pas de stock
  image**, un aplat illustré dans le même esprit graphique que l'identité existante.
- Un élément visuel simple évoquant la catégorie (silhouette d'instrument pour
  Concerts, chapiteau pour Festivals, etc.) reste possible mais n'est pas obligatoire :
  l'aplat de couleur + monogramme seul est déjà le comportement actuel, l'objectif est
  de l'enrichir, pas de le complexifier.
- **Pas de texte intégré à l'image** (le nom de la catégorie reste géré en surimpression
  HTML par le code, comme aujourd'hui) — le visuel doit fonctionner sans texte.

## 4. Palette par territoire

| Territoire | Couleur |
|---|---|
| Savoie | `#3E5C74` |
| Piémont | `#8A3E28` |
| Vallée d'Aoste | `#3F6B47` |
| Comté de Nice | `#B96A2E` |

## 5. Nommage des fichiers (obligatoire, pour le câblage automatique)

Motif : `fallback-{territoire-slug}-{categorie-slug}.jpg`

Slugs territoire : `savoie`, `piemont`, `vallee-d-aoste`, `comte-de-nice`
(cf. `docs/CONTRAT_TAXONOMIE_AGENDA_SABAUDO.md` §2).

Slugs catégorie : `cinema`, `concerts-musique`, `conferences-rencontres`, `curiosites`,
`expositions-patrimoine`, `festivals`, `fetes-traditions`, `gastronomie-sagre`,
`jeune-public-famille`, `marches-foires`, `spectacle-vivant`, `sport`
(cf. `docs/CONTRAT_TAXONOMIE_AGENDA_SABAUDO.md` §1).

### 5.1 Liste complète (48 fichiers)

**Savoie**
```
fallback-savoie-cinema.jpg
fallback-savoie-concerts-musique.jpg
fallback-savoie-conferences-rencontres.jpg
fallback-savoie-curiosites.jpg
fallback-savoie-expositions-patrimoine.jpg
fallback-savoie-festivals.jpg
fallback-savoie-fetes-traditions.jpg
fallback-savoie-gastronomie-sagre.jpg
fallback-savoie-jeune-public-famille.jpg
fallback-savoie-marches-foires.jpg
fallback-savoie-spectacle-vivant.jpg
fallback-savoie-sport.jpg
```

**Piémont**
```
fallback-piemont-cinema.jpg
fallback-piemont-concerts-musique.jpg
fallback-piemont-conferences-rencontres.jpg
fallback-piemont-curiosites.jpg
fallback-piemont-expositions-patrimoine.jpg
fallback-piemont-festivals.jpg
fallback-piemont-fetes-traditions.jpg
fallback-piemont-gastronomie-sagre.jpg
fallback-piemont-jeune-public-famille.jpg
fallback-piemont-marches-foires.jpg
fallback-piemont-spectacle-vivant.jpg
fallback-piemont-sport.jpg
```

**Vallée d'Aoste**
```
fallback-vallee-d-aoste-cinema.jpg
fallback-vallee-d-aoste-concerts-musique.jpg
fallback-vallee-d-aoste-conferences-rencontres.jpg
fallback-vallee-d-aoste-curiosites.jpg
fallback-vallee-d-aoste-expositions-patrimoine.jpg
fallback-vallee-d-aoste-festivals.jpg
fallback-vallee-d-aoste-fetes-traditions.jpg
fallback-vallee-d-aoste-gastronomie-sagre.jpg
fallback-vallee-d-aoste-jeune-public-famille.jpg
fallback-vallee-d-aoste-marches-foires.jpg
fallback-vallee-d-aoste-spectacle-vivant.jpg
fallback-vallee-d-aoste-sport.jpg
```

**Comté de Nice**
```
fallback-comte-de-nice-cinema.jpg
fallback-comte-de-nice-concerts-musique.jpg
fallback-comte-de-nice-conferences-rencontres.jpg
fallback-comte-de-nice-curiosites.jpg
fallback-comte-de-nice-expositions-patrimoine.jpg
fallback-comte-de-nice-festivals.jpg
fallback-comte-de-nice-fetes-traditions.jpg
fallback-comte-de-nice-gastronomie-sagre.jpg
fallback-comte-de-nice-jeune-public-famille.jpg
fallback-comte-de-nice-marches-foires.jpg
fallback-comte-de-nice-spectacle-vivant.jpg
fallback-comte-de-nice-sport.jpg
```

## 6. Livraison

À définir avec Franck : soit upload direct dans la médiathèque WordPress sous les noms
exacts ci-dessus, soit remise des fichiers/URLs pour import.

## 7. Câblage prévu (à faire une fois les visuels livrés)

`cs_fallback_visual()` (snippet #21) sera modifiée pour chercher d'abord le fichier
`fallback-{territoire}-{categorie}.jpg` dans la médiathèque (par son nom, pas par ID
fixe, pour rester robuste à un remplacement futur) ; si absent, elle retombe sur
l'aplat de couleur actuel (comportement inchangé, aucune régression tant qu'un visuel
n'a pas été livré pour une combinaison donnée).

## 8. Portée

État au 2026-07-22 : spécification écrite, aucun visuel encore produit, aucun
changement de code encore appliqué. Document de brief uniquement.
