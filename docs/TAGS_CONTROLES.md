# Étiquettes contrôlées — vocabulaire v1 (brouillon)

*But : remplacer les tags auto-LLM libres (chaos) par une **liste FIXE**. Un tag n'existe
que s'il correspond à une **section / un filtre transversal réel** du site — jamais un
doublon de catégorie (11), de territoire (4) ou de ville (déjà portés ailleurs).*

## Deux modes d'attribution
- **AUTO (données)** — dérivé d'un champ sûr, **zéro LLM**, 100 % fiable.
- **CONTRÔLÉ (LLM depuis la liste)** — l'agent ne peut choisir **QUE** dans cette liste,
  et seulement quand c'est pertinent (ex. genre musical uniquement si catégorie = Concerts).

## Liste v1 (à valider/élaguer à la maquette, selon les sections qu'on construira)

| Tag | Mode | Règle d'attribution |
|---|---|---|
| **Gratuit** | AUTO | `as_gratuit = 1` |
| **En famille** | AUTO | catégorie = « Jeune public & Famille » (sinon LLM depuis la liste) |
| **Transfrontalier** | AUTO | événement mis en avant dans le module cross-border (voisins) |
| **Plein air** | CONTRÔLÉ | le texte indique un cadre extérieur (parc, place, plage, cloître…) |
| **Nocturne** | CONTRÔLÉ | soirée/nuit (concert du soir, nocturne de musée…) |
| **Classique** | CONTRÔLÉ | si catégorie = Concerts & Musique ET genre classique/lyrique |
| **Jazz** | CONTRÔLÉ | idem, genre jazz |
| **Pop-Rock** | CONTRÔLÉ | idem, pop / rock / variété |
| **Chanson** | CONTRÔLÉ | idem, chanson française |
| **Électro** | CONTRÔLÉ | idem, électro / DJ |
| **Musiques du monde** | CONTRÔLÉ | idem, world / trad |
| **Opéra** | CONTRÔLÉ | idem, opéra / art lyrique |

## Règles d'or
1. **Liste fermée** : aucun tag hors de ce tableau. Le publisher filtre tout le reste.
2. **Pas de doublon** de catégorie / territoire / ville / date.
3. **Priorité à l'AUTO** : dès qu'un tag peut être dérivé d'un champ (`as_gratuit`, catégorie,
   module transfrontalier), on ne dérange pas le LLM.
4. **On câble d'abord les AUTO** (fiables, gratuits) ; les CONTRÔLÉS (LLM) viendront quand
   on aura tranché **quelles sections** le site expose (à la maquette).

## Statut
- ✅ Tags auto-LLM libres **coupés** (publisher envoie `tags = []`).
- ⏳ Ce vocabulaire = **v1 à valider**. On le finalise + on le câble au moment du build du site.
- 1er candidat à câbler tout de suite : **Gratuit** (AUTO, trivial et 100 % fiable).
