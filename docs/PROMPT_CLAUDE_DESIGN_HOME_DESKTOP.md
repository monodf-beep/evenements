# Prompt Claude Design — Home DESKTOP (transposition de la home mobile)

*À coller dans Claude Design. La home mobile est la source de vérité (`PROMPT_CLAUDE_DESIGN.md`).
Ce prompt ne crée PAS une nouvelle page : il **réorganise** la même home pour le grand écran,
selon la logique desktop de GuidaTorino (conteneur centré + colonne principale gauche / colonne
latérale droite à partir des modules de cartes). Charte alignée sur le site WordPress
(#18365E / #F7F1E8 / #DC5D45 / #1D1D1B).*

---

Tu conçois la version DESKTOP (1440 px, conteneur centré à 1200 px) de la home de
« Agenda Sabauda » — agenda culturel transfrontalier bilingue FR/IT de l'espace alpin
occidental (4 territoires : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste, Nice/Alpes-
Maritimes), édité par Cultura Sabauda.

CONSIGNE RACINE : c'est la MÊME home que la maquette mobile, PAS une nouvelle page.
Mêmes strates, mêmes composants, même gabarit de carte, même charte. Tu ne fais que
RÉORGANISER la mise en page pour le grand écran, comme la home desktop de GuidaTorino :
un conteneur centré (max 1200 px, marges latérales), et à partir des modules de cartes,
une COLONNE PRINCIPALE à gauche (~66 %) + une COLONNE LATÉRALE à droite (~33 %).
Ne réinvente rien, ne change pas l'ordre éditorial, n'ajoute aucune strate.

CHARTE (identique au site) :
- Bleu Sabauda #18365E (titres, en-tête, marque) · Beige #F7F1E8 (fonds) ·
  Rouge #DC5D45 (accent RARE : dates, étiquettes) · Encre #1D1D1B (texte).
- Pilules territoire : Savoie bleu #1a56b0 · Piémont rouge #b3261e ·
  Vallée d'Aoste vert #1e7d34 · Nice orange #b25e00.
- Titres en serif éditoriale (Fraunces) · données en sans lisible · icônes SVG au trait.
- Logo « Agenda Sabauda » discret + point rouge ; « édité par Cultura Sabauda » en tout petit.

RÉORGANISATION DESKTOP, strate par strate (l'ordre vertical reste le même) :

1. HEADER : en une ligne, horizontal. Logo à gauche · nav complète DÉPLIÉE au centre/droite
   (4 territoires, catégories, à propos — PAS de burger sur desktop) · « FR | IT » ·
   une petite loupe de recherche à droite. Sticky, sobre.

2. CARROUSEL : pleine largeur du conteneur (jusqu'à 1200 px), ratio plus panoramique
   (~16:9 ou 2:1). Grande diapo éditoriale + titre serif en surimpression (overlay sombre)
   + points de pagination + flèches ‹ › discrètes. Swipe/clic MANUEL, jamais d'auto-défilement.
   (Option : diapo principale large + 2 vignettes de sélections à droite — sinon plein largeur.)

3. RECHERCHE : barre pleine largeur sous le carrousel (loupe + « Rechercher un événement,
   une ville… »). Si tu l'as déjà mise dans le header, garde-la aussi ici, discrète.

4. LES 6 TUILES : sur UNE seule rangée de 6 (ou 3 + 3 si trop serré), pas 2 colonnes.
   Grandes tuiles illustrées + libellé serif :
   Ce week-end · Sagres & gastronomie · Concerts · Expositions · En famille · Tout l'agenda.
   Grandes cibles, alignées, respiration entre elles.

--- À PARTIR D'ICI : DEUX COLONNES (principale gauche ~66 % / latérale droite ~33 %) ---

COLONNE PRINCIPALE (gauche) :
5. « À la une » : cartouche-titre + grille de cartes événement au gabarit standard,
   3 PAR RANGÉE (image 3:2 · DATE d'abord en rouge · titre gras 2 lignes · lieu · ville ·
   pilule territoire · « Gratuit » si applicable). Lien « Voir tout → ».
6. « Ce week-end » : même cartouche + cartes 3 par rangée + bouton
   « Voir les 137 événements du week-end → » (compteur visible = exhaustivité).
7. « Le fil » : liste d'articles, 2 PAR RANGÉE sur desktop (vignette + titre serif H2 +
   court extrait + « » »), tous au même alignement. Pagination 1 · 2 · 3.

COLONNE LATÉRALE (droite, sticky au scroll si possible) :
8. « En évidence » : les 6 contenus les plus consultés — liste texte compacte
   (petite vignette + titre), sans fioritures.
9. « L'agenda à venir » : liste dense — petite vignette (~105×66) + titre + date sur une
   ligne, ~8 entrées + « Tout l'agenda → ».
   (+ éventuel encart pub 300×250 discret, comme la sidebar de GuidaTorino.)

--- FIN DES DEUX COLONNES : on repasse pleine largeur ---

10. NEWSLETTER : bande pleine largeur, fond beige ou bleu, 1 champ e-mail + bouton
    (« le vendredi matin »). Sobre.
11. FOOTER : sur plusieurs colonnes alignées — 4 territoires · catégories · le projet ·
    « FR | IT » · « édité par Cultura Sabauda ».

RÈGLES (identiques au mobile) :
- Gabarit de carte CONSTANT partout, date toujours en premier, même ratio d'image.
- Largeur de contenu limitée à 1200 px centré (pas d'étirement plein écran des textes).
- INTERDITS : dégradés IA violet/rose, glassmorphism, blobs, hero à slogan centré,
  carrousel auto-défilant, emoji en guise d'icônes (→ SVG au trait), texte incrusté dans
  les images, zigzag, drapeaux. L'information prime, la marque reste discrète.
- Finition : contraste ≥ 4.5:1, hover 150–300 ms, focus visibles, prefers-reduced-motion,
  zéro layout shift (ratios réservés).

LIVRABLE : la home desktop complète, les 11 strates dans cet ordre, avec la bascule en
deux colonnes à partir de « À la une » (strates 5–7 à gauche, 8–9 à droite).

---

## Correspondance mobile → desktop (mémo pour le build WordPress)

| Strate | Mobile | Desktop |
|---|---|---|
| Header | logo + FR\|IT + burger | logo + nav dépliée + FR\|IT + loupe |
| Carrousel | plein largeur 4:3 | conteneur 1200 px, ~16:9 (+ flèches) |
| 6 tuiles | 2 col × 3 | 1 rangée de 6 (ou 3+3) |
| À la une (5) | 1 col | **colonne principale**, 3 cartes/rangée |
| Ce week-end (6) | 1 col | **colonne principale**, 3 cartes/rangée |
| Le fil (7) | 1 col | **colonne principale**, 2 articles/rangée |
| En évidence (8) | pleine largeur | **colonne latérale droite** |
| À venir (9) | pleine largeur | **colonne latérale droite** (+ pub 300×250) |
| Newsletter (10) | bande | bande pleine largeur |
| Footer (11) | empilé | multi-colonnes |

Traduction JetEngine : les strates 5-7 vivent dans une colonne, 8-9 dans une seconde colonne
(Listing Grid avec réglage « Colonnes » par appareil : 3/2/1 selon desktop/tablette/mobile).
