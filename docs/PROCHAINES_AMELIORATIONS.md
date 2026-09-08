# Prochaines améliorations — pistes non urgentes

Document de suivi pour des idées jugées valables mais pas prioritaires : le
diagnostic et les options y sont consignés une fois, pour ne pas les
reperdre, sans obligation de les traiter vite.

---

## Cartes portrait sur les homepages

**Origine** : Franck, 2026-09-08, à partir d'une capture d'écran — « on n'a
que des cards d'événements en mode paysage alors qu'il y a pas mal
d'événements qu'on affiche en mode portrait. Est-ce qu'il ne faudrait pas
afficher ces cartes en portrait ? » — avec la réserve explicite : « je ne
suis pas sûr de vouloir tout de suite révolutionner ça ».

### Constat

- Toutes les cartes du site sont à ratio fixe **3:2** avec
  `object-fit:cover` (`code-snippets/21-cs-composants-carte-partage.php`,
  `code-snippets/134-cs-bloc-a-lire.php`). Une affiche portrait est donc
  **recadrée au centre** — la bande du milieu est gardée, le haut et le bas
  (souvent le titre et les dates de l'affiche) sont coupés.
- Le pipeline distingue déjà les deux orientations en base :
  `url_image_portrait` et `url_image_wide` (`scripts/scraper_events.py`,
  `scripts/images_wide.py`). `publisher_as.py` envoie la version portrait
  vers la carte quand elle existe. La matière est là ; c'est l'AFFICHAGE
  qui l'écrase, pas l'absence de donnée.
- Non mesuré à ce jour : la proportion de fiches publiées à venir dont
  l'image est nativement portrait. Requête à faire avant toute décision :
  ```sql
  SELECT COUNT(*) FROM events_raw
  WHERE statut='publie' AND url_image_portrait != '';
  ```
  (comparer au total publié à venir pour avoir un pourcentage, pas un
  chiffre brut — règle 6 de CLAUDE.md).

### Pourquoi ne pas le faire tel quel

- Les grilles de la home reposent sur des **rangées pleines** (l'allocateur
  #44, règle « 4 ou 8, jamais 5 »). Des cartes de hauteurs différentes
  cassent l'alignement ; un mode masonry ferait perdre l'ordre de lecture
  gauche→droite qui porte l'ordre éditorial (score, date).
- Sur mobile (grille 2 colonnes), une carte portrait à côté d'une paysage
  laisse un trou visible sous la paysage.
- Coût de mise en œuvre : deux widgets JetEngine par section (1695/1696),
  plusieurs snippets de cartes, deux pages d'accueil FR/IT, plus
  l'allocateur — plusieurs jours de travail avec risque de régression sur
  la page la plus vue du site.
- Effet de bord éditorial non désiré : une carte plus haute se lit comme
  plus importante ; on introduirait une hiérarchie visuelle pilotée par le
  hasard du format de l'affiche source, pas par le score éditorial.

### Pistes à coût réduit, à envisager d'abord

1. **`object-position: top` conditionné à l'orientation** — pour une image
   portrait, cadrer sur le haut plutôt que le centre (le titre d'une
   affiche est en haut). Une ligne de CSS, aucun changement de grille.
2. **Une zone dédiée au format vertical**, ex. le bloc « En évidence » en
   desktop : affiche entière à côté d'un texte, façon « affiche +
   programme ». Respecte la grille ailleurs et donne un usage au portrait
   là où il a du sens (expositions, festivals où l'affiche EST
   l'information).

### Prochaine étape

Faire tourner la requête de mesure ci-dessus. Si la part de portrait est
faible (~15 %), l'option 1 suffit. Si elle est large (~50 % et plus), le
sujet mérite une vraie maquette avant tout développement.
