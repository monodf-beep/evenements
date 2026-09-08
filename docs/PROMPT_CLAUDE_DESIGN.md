# Prompt Claude Design — Agenda Sabauda (calqué sur la home MOBILE de GuidaTorino)

*À coller dans Claude Design. **Consigne racine : ne pas réinventer. Reproduire fidèlement les
strates de la home mobile de GuidaTorino** (le modèle qui marche), en les habillant de notre
charte et de nos 4 territoires. On scrolle et on choisit — pas de filtres imposés sur la home.
L'UI est épurée : l'information prime, la marque est discrète.*

---

Tu conçois l'UX/UI de **Agenda Sabauda**, agenda culturel **transfrontalier bilingue FR/IT** de
l'espace alpin occidental — **4 territoires** : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste,
Nice/Alpes-Maritimes. Édité par **Cultura Sabauda**. WordPress. **Conçois d'abord le MOBILE (375 px).**

## Modèle de référence : la home mobile de GuidaTorino (à reproduire strate par strate)
GuidaTorino empile, en **une seule colonne**, des blocs simples que l'utilisateur **traverse en
scrollant** : un grand carrousel de sélections en tête, une grille de grandes tuiles illustrées
pour choisir, puis des modules de cartes événements « à la une » et « aujourd'hui », puis un fil
d'articles, puis les blocs « populaires » et « à venir ». **On garde exactement cet ordre et ces
composants.** On ne rajoute PAS de barre de filtres temporelle en haut, PAS de hero à slogan,
PAS de mise en page en zigzag. **L'œil descend tout droit.**

## Le principe : ÉPURÉ + SCROLL DROIT + on CHOISIT en scrollant
- **Colonne unique** de rubriques empilées, **gabarit constant** d'une carte à l'autre.
- **On scrolle et on tape** dans une tuile/carte. Pas de filtres imposés sur la home (les filtres
  vivent DANS les pages de liste, pas à l'accueil).
- **UI minimale : l'INFORMATION prime, pas la marque.** Photo + titre + date dominent. L'identité
  = rappels discrets (logo réduit, accent rouge rare, pilules de couleur territoire).

## Anti « design slop » (interdits stricts)
Pas de dégradés « IA » violet/rose, glassmorphism, blobs, hero vide à slogan centré, sections
« features », **carrousels auto-défilants** (swipe manuel uniquement), animations décoratives,
**emoji en guise d'icônes** (→ SVG au trait, Heroicons/Lucide), **texte incrusté dans les images**.
Tout est du **texte HTML réel**.

## Charte (applique-la, la DA reste à toi — RESTE ÉPURÉ)
- Marine profond `#1a2b4a` (titres, éléments de marque). Rouge `#c8102e` = **seul accent, rare**
  (comme le rouge `#fb4f4f` de GuidaTorino : réservé aux dates/étiquettes, jamais partout).
- Pilules territoire : Savoie bleu `#1a56b0` · Piémont rouge `#b3261e` · Vallée d'Aoste vert
  `#1e7d34` · Nice orange `#b25e00`.
- Logo « Agenda Sabauda » **discret** + point rouge ; « édité par Cultura Sabauda » en tout petit.
- Typo : **serif éditoriale pour les titres** (esprit Georgia de GuidaTorino) + sans lisible pour
  les données. Icônes SVG au trait.

## LA HOME (mobile) — les strates, dans l'ordre de GuidaTorino

1. **Header minimal sticky** : petit logo à gauche · **FR | IT** (texte) · **menu burger** à
   droite (ouvre la nav complète : 4 territoires, catégories, à propos). Sobre, une ligne.

2. **CARROUSEL de sélections (strate 1 — swipe manuel)** — l'équivalent du metaslider.
   4-8 grandes diapos plein-largeur (ratio ~4:3), chacune = **une sélection éditoriale**
   cliquable renvoyant vers un listicle ou un hub : « **Ce week-end** », « **Les 10 sagres du
   mois** », « **Gratuit ce week-end** », « **Concerts de juillet** », « **À faire en famille** »…
   Chaque diapo : image forte + **titre en serif** en surimpression (overlay sombre pour le
   contraste) + petits points de pagination. **Swipe uniquement, pas d'auto-défilement.**

3. **Champ de recherche** pleine largeur (loupe + « Rechercher un événement, une ville… »).
   Visible, simple, juste sous le carrousel (comme GuidaTorino).

4. **Grille de 6 GRANDES TUILES illustrées (on choisit ici — pas de filtre)** — l'équivalent des
   6 `mainlink`. 2 colonnes × 3 rangées, tuiles carrées avec **illustration/photo + libellé en
   serif**. C'est l'entrée principale par le CHOIX :
   **Ce week-end · Sagres & gastronomie · Concerts · Expositions · En famille · Tout l'agenda**.
   *(Variante possible orientée lieux : les 4 territoires + « Sagres » + « Tout l'agenda ». Garde
   « Sagres » et « Tout l'agenda » dans tous les cas.)* Grandes cibles tactiles, pas un mur de
   petites icônes.

5. **« À la une »** (équivalent *Eventi in primo piano*) : petit cartouche-titre de section +
   **4 cartes événement** au gabarit standard (image 3:2 · **DATE d'abord** · titre gras 2 lignes ·
   lieu · ville · pilule territoire). Sélection éditoriale, **qualité d'abord** (pas d'équilibre
   forcé entre territoires). Lien « Voir tout → ».

6. **« Ce week-end »** (équivalent *Eventi di oggi* — on remplace « aujourd'hui » par le créneau
   reine) : même cartouche + **4 cartes** au même gabarit + **« Voir les 137 événements du
   week-end → »** (le compteur rend l'**exhaustivité visible**).

7. **« Le fil »** (équivalent *Novità da Guida Torino* — le loop d'articles) : liste verticale de
   **~6-8 articles/dossiers**, chacun = **vignette + titre en serif (H2) + court extrait + « » »**,
   toutes les lignes au **même alignement** (l'œil descend droit). **Pagination 1 · 2 · 3** en bas.
   C'est ici que vivent les listicles (« Les 10 du week-end », « Où manger après une rando »…).

8. **« En évidence »** (équivalent *In Evidenza* / sidebar remontée en mobile) : bloc compact des
   **6 contenus les plus consultés** — liste texte simple (petite vignette + titre), sans fioritures.

9. **« L'agenda à venir »** (équivalent *Eventi a Torino* widget) : liste dense des prochains
   événements — **petite vignette (~105×66) + titre + date** sur une ligne, ~6 entrées + « Tout
   l'agenda → ».

10. **Bloc newsletter** (léger, 1 champ, « le vendredi matin ») — comme la bannière newsletter de
    GuidaTorino sous les tuiles, mais on le pose ici en bas.

11. **Footer léger** : 4 territoires · catégories · projet · **FR | IT** · « édité par Cultura
    Sabauda ». (GuidaTorino a un footer sur 2 rangées : même esprit.)

> **Rythme visuel** : chaque strate = un **petit titre de section** (capitales/serif discret) +
> son bloc. Alternance carrousel → grille → cartes → fil → listes : c'est la respiration de
> GuidaTorino. Même hauteur de carte, même ratio d'image, même position de la date d'un module à
> l'autre.

## LA CARTE ÉVÉNEMENT (composant central — gabarit CONSTANT)
Toujours le même ordre, jamais inversé : **image (ratio ~3:2)** → **DATE en premier**
(« 05/07 » ou « 05/07 – 19/07 », en rouge discret) → **titre gras** (2 lignes max) → **lieu ·
ville** + **pilule territoire** (couleur) + « Gratuit » si applicable. Carte **entièrement
cliquable**, pas d'extrait. Trois variantes au **même alignement** : diapo-carrousel (strate 2) ·
carte standard (strates 5-6) · ligne compacte (strates 9 : vignette gauche + texte droite).

## Badges d'état (fermés, discrets)
En cours · Dernier week-end / Plus que X jours (rouge) · Date à confirmer (gris) · Gratuit.

## Autres écrans (secondaires — après la home)
- **Hub « Ce week-end »** (clé SEO) : titre + dates + courte intro + **filtres date/ville/catégorie**
  (ici, oui, on filtre) + liste exhaustive au gabarit compact.
- **Hub territoire** (ex. Savoie) : intro pérenne + « ce week-end en Savoie » + flux local filtrable
  par ville/catégorie + petit encart « De l'autre côté des Alpes » (2-3 pépites, discret).
- **Fiche événement — MODE MINIMAL D'ABORD** (beaucoup d'événements n'ont PAS d'article) : image
  (ou bannière territoire) + crédit photo · badges · catégorie · titre · lieu · ville · pilule
  territoire · **bloc pratique** (dates humanisées, horaires, lieu + carte, prix / « Gratuit »,
  bouton « Réserver — site officiel ») · description courte · « Vérifié le JJ/MM » · 3 rails liés.
  Puis mode riche (article) quand il existe.
- **« Tout l'agenda »** : la seule page exhaustive, filtrable (date · ville · catégorie · territoire).

## Finition professionnelle (checklist pré-livraison)
Icônes SVG (Heroicons/Lucide) · `cursor-pointer` + hover 150-300 ms · focus visibles ·
`prefers-reduced-motion` · **contraste ≥ 4.5:1** (texte sur image → overlay sombre) · responsive
**375 / 768 / 1024 / 1440** (sur desktop, la strate 8-9 peut repasser en colonne latérale comme
la sidebar de GuidaTorino) · ombres douces, transitions 200-300 ms · cibles tactiles **≥ 44 px** ·
**zéro layout shift** (ratios d'image réservés).

## Les 3 livrables prioritaires (fais-les justes)
1. **La home mobile complète** — les 11 strates ci-dessus, dans cet ordre (carrousel → recherche →
   6 tuiles → à la une → ce week-end → le fil → en évidence → à venir → newsletter → footer).
2. **La carte événement** (date en premier, pilule territoire, gabarit constant), dans ses 3 variantes.
3. **La fiche en mode minimal.**

## À NE PAS faire
Inventer un ordre de strates différent de GuidaTorino · mettre une **barre de filtres temporelle**
en tête de home (le temps s'attrape via le carrousel et les tuiles, pas via une barre) · hero à
slogan centré · cacher l'exhaustivité (compteur + recherche + « Tout l'agenda » doivent être
visibles) · mur de 10+ petites icônes (on veut **6 grandes tuiles**) · mise en page en zigzag ou
colonnes alternées · carrousel auto-défilant · drapeaux · emoji-icônes · texte incrusté dans les
images.
