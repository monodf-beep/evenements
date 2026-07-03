# Prompt Claude Design — Agenda Sabaudo (maquette épurée, scroll-first)

*À coller dans Claude Design. Modèle : la home mobile de GuidaTorino — épurée, on scrolle,
l'œil descend TOUT DROIT (pas de zigzag), UX simple, UI minimale où l'information prime.
Intègre les arbitrages de `CRITIQUE_SYNTHESE.md` : temps primaire, exhaustivité visible,
pas d'équilibre forcé, pas de personnalisation.*

---

Tu conçois l'UX/UI de **Agenda Sabaudo**, agenda culturel **transfrontalier bilingue FR/IT** de
l'espace alpin occidental — **4 territoires** : Savoie/Haute-Savoie, Piémont, Vallée d'Aoste,
Nice/Alpes-Maritimes. Édité par **Cultura Sabauda**. WordPress. **Conçois d'abord le MOBILE.**

## Le principe directeur : ÉPURÉ + SCROLL DROIT
- La home est une **colonne unique** de rubriques empilées. **L'œil descend en ligne droite** :
  pas de mise en page en zigzag, pas de colonnes alternées, pas de masonry, pas d'images tantôt
  à gauche tantôt à droite. **Alignement CONSTANT** d'une carte à l'autre (le même gabarit
  répété) pour que le regard glisse tout droit vers le bas.
- **UX simple** : on scrolle, on tape. Pas de filtres imposés sur la home, pas de menus à
  explorer pour comprendre, pas de choix multiples qui bloquent.
- **UI minimale : l'INFORMATION prime, pas la marque.** Photo + titre + date dominent. L'identité
  du site = **petits rappels discrets** (logo réduit, accent rouge rare, pilules de couleur
  territoire). Beaucoup de blanc, respiration, une seule police de titres, une de texte.

## Anti « design slop » (interdits stricts)
Pas de dégradés « IA » violet/rose, glassmorphism, blobs, hero vide à slogan centré, sections
« features », **carrousels auto-défilants** (swipe manuel uniquement), animations décoratives,
**emoji en guise d'icônes** (→ SVG au trait, Heroicons/Lucide), **texte dans les images**. Tout
est du **texte HTML réel**.

## Charte (applique-la, la DA reste à toi — RESTE ÉPURÉ)
- Marine profond `#1a2b4a` (titres, éléments de marque). Rouge `#c8102e` = **seul accent, rare**.
- Pilules territoire : Savoie bleu `#1a56b0` · Piémont rouge `#b3261e` · Vallée d'Aoste vert
  `#1e7d34` · Nice orange `#b25e00`.
- Logo « Agenda Sabaudo » **discret** + point rouge ; « édité par Cultura Sabauda » en tout petit.
- Typo : serif éditoriale (titres) + sans lisible (données). Icônes SVG au trait.

## LA HOME (mobile) — une colonne, de haut en bas

1. **Header minimal sticky** : petit logo · **champ de recherche visible** (loupe qui déplie un
   champ) · **FR | IT** (texte). Épuré.
2. **Barre temporelle (l'axe PRIMAIRE)** — chips : **Aujourd'hui · Ce week-end · Cette semaine ·
   Choisir des dates**. C'est par le TEMPS qu'on entre (« quand ? »), pas par le territoire.
3. **« Ce week-end »** (la rubrique reine) : un carrousel **swipe** de 5-8 cartes (best-of,
   **qualité d'abord — PAS d'équilibre forcé entre territoires**) + une ligne forte
   **« Voir les 137 événements du week-end → »** (le compteur rend l'**exhaustivité visible**).
4. **« À ne pas manquer »** : sélection éditoriale (choix manuel), 3-5 cartes.
5. **« Sagre & gastronomie »** : rubrique thématique dédiée (aimant à trafic) + « voir tout → ».
6. **« Explorer »** (secondaire, sobre) : une rangée simple des **4 territoires** (pilule
   couleur) + un accès **catégories** et **villes**. C'est de l'exploration, PAS le menu
   principal — le temps reste primaire. Pas de mur de 10 icônes.
7. **« Le fil »** : derniers articles/dossiers (« Les 10 du week-end »).
8. **Bloc newsletter** (léger, 1 champ, « le vendredi matin »).
9. **« Tout l'agenda → »** : la liste **exhaustive filtrable** (date · **ville** · catégorie ·
   territoire). La seule page exhaustive — accessible aussi via le compteur (point 3).
10. **Footer léger** : 4 territoires · catégories · projet · FR|IT · « édité par Cultura Sabauda ».

> **Rythme visuel** : chaque rubrique = un petit titre de section (capitales discrètes) + une
> rangée de cartes au **gabarit identique**. Même hauteur, même alignement, même ratio d'image.
> L'œil descend sans jamais avoir à chercher où regarder.

## LA CARTE ÉVÉNEMENT (le composant central — gabarit CONSTANT)
Toujours le même ordre, jamais inversé : **image (ratio ~3:2)** → **DATE en premier**
(« 05/07 » ou « 05/07 – 19/07 ») → **titre** (2 lignes max) → **lieu · ville** + **pilule
territoire** (couleur) + « Gratuit » si applicable. Carte **entièrement cliquable**. Pas
d'extrait. Variantes au **même alignement** : héro (carrousel) · standard · compacte-liste
(vignette à gauche + texte à droite, **toutes les lignes identiques** → l'œil descend le long
d'une seule colonne).

## Badges d'état (fermé, discrets)
En cours · Dernier week-end / Plus que X jours (rouge) · Date à confirmer (gris) · Gratuit.

## Autres écrans
- **Hub temporel « Ce week-end »** (le plus important pour le SEO) : titre + dates + courte intro
  + **filtres date/ville/catégorie** (ici, oui, on filtre) + liste exhaustive.
- **Hub territoire** (ex. Savoie) : intro + « ce week-end en Savoie » + flux local filtrable par
  ville/catégorie + petit encart « De l'autre côté des Alpes » (2-3 pépites, discret).
- **Fiche événement — MODE MINIMAL D'ABORD** (beaucoup d'événements n'ont PAS d'article) : image
  (ou bannière territoire) + crédit photo · badges · catégorie · titre · lieu · ville · pilule
  territoire · **bloc pratique** (dates humanisées, horaires, lieu + carte, prix / « Gratuit »,
  bouton « Réserver — site officiel ») · description courte · « Vérifié le JJ/MM » · 3 rails liés
  (mêmes dates près d'ici · même territoire · même catégorie). Puis mode riche (article).
- **« Tout l'agenda »** : liste exhaustive filtrable (date · ville · catégorie · territoire).

## Finition professionnelle (checklist pré-livraison)
Icônes SVG (Heroicons/Lucide) · `cursor-pointer` + hover 150-300 ms · focus visibles ·
`prefers-reduced-motion` · **contraste ≥ 4.5:1** (surtout texte sur image : overlay sombre) ·
responsive **375 / 768 / 1024 / 1440** · ombres douces, transitions 200-300 ms · cibles tactiles
**≥ 44 px** · **zéro layout shift** (ratios d'image réservés).

## Les 3 livrables prioritaires (fais-les justes)
1. **La carte événement** (date en premier, pilule territoire, gabarit constant).
2. **La home mobile** — la colonne épurée : recherche + barre temps → Ce week-end (+ compteur) →
   à ne pas manquer → sagre → explorer → le fil → tout l'agenda.
3. **La fiche en mode minimal.**

## À NE PAS faire
Home-feed brut · **cacher l'exhaustivité** (le compteur + la recherche doivent être visibles) ·
équilibre territorial forcé (qualité d'abord) · faire du **territoire l'axe primaire** (c'est le
**temps**) · mur de 10+ icônes · deux menus territoire/activité co-égaux · personnalisation /
géoloc / sélecteur imposé à l'entrée · mise en page en zigzag ou colonnes alternées · carrousel
auto · drapeaux · emoji-icônes · texte dans les images.
