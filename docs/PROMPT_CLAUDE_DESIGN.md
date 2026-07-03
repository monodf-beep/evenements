# Prompt Claude Design — Agenda Sabaudo (maquette v2, mobile-first « scroll & choisir »)

*Prompt complet à coller dans Claude Design. Modèle : la home mobile de GuidaTorino — une PILE de
rubriques curées qu'on parcourt en scrollant, UI épurée, l'information prime sur la marque.*

---

Tu conçois l'UX/UI de **Agenda Sabaudo**, l'agenda culturel **transfrontalier bilingue FR/IT** de
l'espace alpin occidental — **4 territoires** : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste,
Nice/Alpes-Maritimes. Édité par le média **Cultura Sabauda**. Site WordPress. **Conçois d'abord
le MOBILE** (puis l'adaptation desktop).

## Le modèle : GuidaTorino sur mobile — « on scrolle et on choisit »
La home est une **pile verticale de rubriques curées** qu'on **parcourt en scrollant**. Le
visiteur **ne filtre pas, ne va pas dans le menu** : il descend, son œil n'a pas à chercher, il
**tape** la rubrique ou la carte qui l'intéresse. Chaque rubrique = un **petit titre de section**
(en capitales, discret) + une **sélection de cartes** (carrousel horizontal ou petite grille) +
un lien **« voir tout → »**.

**Trois règles qui découlent de ce modèle :**
1. **Curé, PAS exhaustif.** Chaque rubrique montre un **best-of**, pas tout. La seule exhaustivité
   est derrière une entrée **« Tout l'agenda → »** (liste filtrable). Ailleurs, on fait des choix.
2. **UI épurée au maximum : l'INFORMATION prime, pas la marque.** La photo + le titre + la date
   dominent. L'identité du site = **petits rappels** (logo discret, l'accent rouge avec
   parcimonie, les pilules de couleur territoire). **Pas de gros branding**, pas de chrome lourd.
3. **On scrolle, c'est simple.** Pas de filtres sur la home, pas de personnalisation, pas de
   géolocalisation, la home ne devine rien.

## Anti « design slop » (interdits)
Pas de dégradés SaaS, glassmorphism, blobs, hero vide à slogan centré, sections « features »,
carrousels **auto-défilants** (les carrousels sont à **swipe manuel**), animations décoratives,
**emoji en guise d'icônes** (icônes au trait), texte dans les images. Tout est du **texte HTML
réel**. Accessible (contrastes AA, focus visibles).

## Charte (applique-la, la DA reste à toi — mais RESTE ÉPURÉ)
- **Marine profond** `#1a2b4a` (titres, petits éléments de marque).
- **Rouge de Savoie** `#c8102e` = **le seul accent**, rare (CTA, filets, urgences).
- **Couleurs territoire** (pilules sur les cartes) : Savoie bleu `#1a56b0` · Piémont rouge
  `#b3261e` · Vallée d'Aoste vert `#1e7d34` · Nice orange `#b25e00`.
- Logo « Agenda Sabaudo » **discret** + point rouge ; « édité par Cultura Sabauda » en tout petit.
- Typo : à toi (piste : serif éditoriale pour les titres + sans lisible pour les données).

## LA HOME (mobile) — la pile de rubriques, dans cet ordre

1. **Header minimal (sticky)** : petit logo, **loupe**, **menu** (burger), commutateur **FR | IT**
   (texte, jamais de drapeau). Épuré.
2. **Carrousel « À la une »** (swipe manuel) : 3-5 grandes cartes = les temps forts de l'espace
   Sabaudo, **ÉQUILIBRÉS** (au moins 1 par territoire), chaque carte avec sa **pilule territoire**.
3. **Grille de portes (icônes au trait)** — c'est ici que se fait le CHOIX :
   - **d'abord les 4 TERRITOIRES** (Savoie · Piémont · Vallée d'Aoste · Nice), chacun sa couleur
     — **c'est l'axe primaire, la 1ʳᵉ décision « où ? »** ;
   - puis quelques grandes entrées : **Ce week-end · Expositions · Concerts · Sagre · En famille ·
     Tout l'agenda**.
4. **« Ce week-end »** : titre de section + carrousel de cartes (best-of équilibré) + « Tout le
   week-end → ».
5. **« Sagre & gastronomie du moment »** : une rubrique thématique dédiée (GuidaTorino met les
   sagre en avant — c'est un aimant) + « voir tout → ».
6. **« À ne pas manquer »** (sélection éditoriale, choix manuel) : quelques cartes.
7. **« Aujourd'hui »** : les événements du jour.
8. **« Le fil » / nouveautés** : derniers articles/listicles (« Les 10 du week-end », dossiers).
9. **Bloc newsletter** (léger, 1 champ, promesse datée « le vendredi matin »).
10. **« Tout l'agenda → »** : l'entrée unique vers la liste exhaustive **filtrable** (territoire /
    catégorie / date). La seule page exhaustive.
11. **Footer léger** : 4 territoires · 11 catégories · projet · FR|IT · « édité par Cultura
    Sabauda ».

> Équilibre territorial obligatoire dans les rubriques curées (2, 4, 6) : ne pas paraître « site
> savoyard » ni « site turinois ». Chaque carte porte sa **pilule territoire** pour que l'origine
> soit toujours lisible.

## LA CARTE ÉVÉNEMENT (le composant central) — comme GuidaTorino
Ordre visuel : **image (ratio ~3:2)** → **la DATE en premier** (ex. « 05/07/2026 » ou « 05/07 –
19/07 ») → **titre** (2 lignes max) → lieu + ville. + **pilule territoire (sa couleur)**, badge
catégorie discret, « Gratuit » si applicable. **Carte entièrement cliquable.** Pas d'extrait sur
les cartes (date + lieu suffisent). Variantes : **héro** (carrousel) · **standard** (rubriques) ·
**compacte/liste** (résultats, agenda).

## Badges d'état (système fermé, discrets)
`En cours` · `Dernier week-end` / `Plus que X jours` (rouge) · `Date à confirmer` (gris) ·
`Gratuit`.

## Les autres écrans (mobile + desktop)
- **Hub territoire** (ex. Savoie) — LE cas d'usage local : titre + intro courte ; « ce week-end
  en Savoie » ; **flux local filtrable par activité** (barre de filtres date + catégorie —
  ici, oui, on filtre) ; encart « De l'autre côté des Alpes » (2-3 pépites du Piémont).
- **Hub catégorie** (ex. Concerts, Sagre) : par défaut dans un territoire, + vue transversale
  « les 4 territoires ».
- **Fiche événement — MODE MINIMAL D'ABORD** (beaucoup d'événements n'ont PAS d'article) : image
  (ou bannière territoire) + crédit photo ; badges ; catégorie ; titre ; lieu · ville · pilule
  territoire ; **bloc pratique** (dates humanisées, horaires, lieu + carte, prix / « Gratuit »,
  bouton « Réserver — site officiel ») ; description courte ; « Vérifié le JJ/MM » ; **3 rails
  liés** (mêmes dates près d'ici · même territoire · même catégorie). Puis le **mode riche**
  (article : chapô + corps + encadré « En pratique »).
- **« Tout l'agenda »** : la liste exhaustive filtrable (territoire / catégorie / date).

## Desktop
Même logique, la pile devient 1 colonne large (ou 2 colonnes contenu + rail) ; on **ne densifie
pas** au point de perdre l'esprit épuré. Le scroll reste le geste principal.

## Standards de finition professionnels (checklist pré-livraison)
*Repris des bonnes pratiques UI/UX « pro max » — applique-les à chaque écran.*
- **Icônes = SVG au trait (Heroicons ou Lucide)**, jamais d'emoji dans l'UI.
- **`cursor-pointer`** sur tout élément cliquable ; **états hover** avec transition douce
  **150-300 ms**.
- **États focus visibles** (navigation clavier) ; **`prefers-reduced-motion` respecté**.
- **Contraste texte ≥ 4.5:1** (WCAG AA) — vérifie surtout le texte sur les images (overlay/
  dégradé sombre derrière les titres en surimpression).
- **Responsive, mobile-first** : points de rupture **375 / 768 / 1024 / 1440 px**.
- **Ombres douces, transitions 200-300 ms, hover subtils** — mouvement discret, jamais tape-à-l'œil.
- **Bannir les dégradés « IA » violet/rose** et tout effet décoratif gratuit (cf. anti-slop).
- **Cibles tactiles ≥ 44 px** (mobile), espacements généreux, hiérarchie typographique nette.
- **Zéro layout shift** : réserver la place des images (ratio fixe) et des emplacements variables.
- **Theme-aware** (clair/sombre) optionnel — si tu le fais, garde l'esprit épuré dans les deux.
- **Appairage de police** (piste) : une **serif éditoriale** pour les titres (autorité « guide »)
  + une **sans lisible** (ex. Inter / Source Sans) pour les données pratiques. Charge-les proprement.

## Livrables prioritaires (si tu ne fais que 3 choses justes)
1. **La carte événement** (date en premier, pilule territoire).
2. **La home mobile** (pile de rubriques curées : carrousel à la une → portes territoires+catégories
   → ce week-end → sagre → à ne pas manquer → aujourd'hui → tout l'agenda).
3. **La fiche en mode minimal.**

## Rappels des interdits (spécifiques)
Home-feed exhaustif · filtres sur la home · sélecteur de territoire imposé à l'entrée · géoloc ·
carrousel auto-défilant · deux menus territoire/activité co-égaux (le territoire est primaire,
l'activité vient dedans) · gros branding · emoji-icônes · texte dans les images.
