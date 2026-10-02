# Diagnostic des 5 bugs visibles — agendasabauda.eu

**Date :** 2026-08-01 · **Périmètre :** investigation seule, aucun fichier du site modifié, rien de déployé.

---

## 0. Méthode — ce qui a été réellement observé

Tout ce qui suit a été mesuré sur les **pages publiques réellement téléchargées**, pas sur une
représentation mentale du site. Concrètement :

1. `curl` sur `https://agendasabauda.eu/`, `/explore/savoie/`,
   `/evenements/categorie/jeune-public-famille/`, `/type-de-lieu/musee/`, `/tout-l-agenda/`
   (User-Agent iPhone et desktop — les deux réponses sont identiques à 4 octets près : **le site ne
   sert pas de HTML différent selon l'appareil**, tout le mobile/desktop est fait en CSS).
2. Extraction des **27 blocs `<style>` inline** et des **70 blocs `<script>`** de la home, chacun
   sauvegardé et lu.
3. Rendu réel dans **Chromium headless** (Playwright), en viewport mobile 390×844 et desktop
   1366×860, avec relais réseau (chaque requête du navigateur est rejouée telle quelle vers le
   site), **CPU bridé ×6 et réseau bridé** pour reproduire un chargement de téléphone.
4. Mesures : `getComputedStyle`, `getBoundingClientRect`, `PerformanceObserver('layout-shift')`,
   enregistrement image par image (`requestAnimationFrame`) pendant le chargement.

**Pièges de lecture rencontrés et évités** (la classe de faux positifs de ce soir) :

- Les titres de section sont en **minuscules dans le HTML** (`<div class="as-desktop-section-title__label">Les 7 prochains jours</div>`) ;
  les capitales viennent de `text-transform: uppercase` dans `.as-desktop-section-title__label`.
  Chercher `LES 7 PROCHAINS JOURS` dans le HTML ne donne rien — ce n'est pas une absence.
- La chaîne `7 prochains jours` apparaît **3 fois** dans la home. J'ai lu le contexte de chacune
  avant de conclure, et la répartition n'est pas celle qu'on suppose : offset **81004 = un
  commentaire CSS** (le bloc « Doublons desktop sur mobile »), offset **186189 = du vrai HTML**
  (le rail mobile `.as-day-rail`), offset **289006 = du vrai HTML** (le titre desktop). Conclure
  « une seule section » à partir d'un comptage brut aurait été faux : il y a bien **deux
  occurrences réelles dans le corps de page**, une mobile et une desktop.
- Sur mes premières captures d'écran, les vignettes apparaissaient vides. **Ce n'était pas un bug du
  site** mais du lazy-loading non déclenché en capture pleine page. Après un défilement complet,
  toutes les images se chargent. Aucune alerte n'a été écrite sur cette base.

**Où vit le code que le site sert réellement** (identifié par l'attribut `id` des `<style>`) :

| `id` du bloc | Taille | Origine | Contenu |
|---|---|---|---|
| `cs-design-tokens` | 5 036 c. | snippet Code Snippets | variables de couleurs/typo |
| `cs-composants-styles` | **70 875 c.** | snippet « CS · Composants (styles) » | **la quasi-totalité du design du site** |
| `cs-nav-logo-reveal` | 178 c. | snippet | apparition du logo desktop |
| `cs-cat-empty-hide` | 159 c. | snippet | masquage des tuiles catégorie vides |
| `cs-hdr-compact` | 6 896 c. | **snippet #62** | header compact + menu overlay + footer |
| `cs-no-hide-empty-cols` | 4 540 c. | **snippet #77** (priorité 999) | anti-flash carrousel, colonnes mobile |

> ⚠️ **Piège de déploiement à connaître avant toute correction.**
> Le dépôt contient `wordpress/design-system/components.css` (31 050 octets, 571 lignes) et le script
> `wordpress/scripts/apply-components.mjs` qui l'écrase sur le site. Or le snippet réellement en
> ligne fait **70 875 caractères** et contient des blocs absents du dépôt (`cs-cvld-grid`,
> « SYSTEME DE CARTE UNIFIE », « Doublons desktop sur mobile »…). **Lancer `apply-components.mjs`
> aujourd'hui ferait perdre ~40 Ko de CSS de production.** Les correctifs ci-dessous se posent
> **dans l'admin WordPress (Code Snippets)**, pas via ce script, tant que le dépôt n'a pas été
> resynchronisé depuis la production.

---

## Bug 1 — Menu mobile vide

### Ce qui a été observé

**Le menu fonctionne aujourd'hui, sur les deux familles de pages.** Test en Chromium mobile 390 px,
clic réel sur le hamburger :

- **Home** (`/`) : le panneau `.as-menu-overlay` s'ouvre (`transform: matrix(1,0,0,1,0,0)`,
  rect `[0,0,390,844]`), **24 liens, 24 visibles** (Aujourd'hui, Ce week-end, Catégories + 11
  sous-liens, Territoires + 4, Agenda + 2).
- **Page catégorie** (`/evenements/categorie/jeune-public-famille/`) : panneau
  `.as-site-header__mobile-menu` (`display: block`), **22 liens, 22 visibles**.

Le balisage est **rendu côté serveur**, pas injecté en JS : les `<ul>` sont dans le HTML servi
(vérifié dans la source `curl`, offsets 138659 pour la home et 118065 pour le header site-wide).

### Cause la plus probable — **certain sur le mécanisme, résolu sur le fond**

Le bug avait **deux causes cumulées**, toutes deux aujourd'hui neutralisées :

1. **Emplacement de menu non assigné** dans Apparence → Menus (correction notée dans
   `docs/site_issues.json` #6 : « Menu réassigné dans Apparence > Menus, confirmé sur mobile »).
2. **Une règle CSS qui vidait visuellement le panneau de la home.** L'overlay de la home réutilise
   la classe de la nav desktop :

   ```html
   <div class="as-menu-overlay"> … <ul class="as-site-header__menu"> … </ul> … </div>
   ```

   or `cs-composants-styles` ligne 780 contient :

   ```css
   @media (max-width: 720px) { .as-site-header__menu { display: none; } }
   ```

   Le panneau s'ouvrait donc **vide** (titre « Menu » + croix, aucun lien). Le rattrapage est
   aujourd'hui dans le snippet **#62** (`cs-hdr-compact`) :

   ```css
   .as-menu-overlay .as-site-header__menu{ display:block !important; }
   ```

### ⚠️ Mais un autre défaut du menu mobile, lui, est bien présent aujourd'hui

En ouvrant le menu **après avoir scrollé** (home mobile, scroll 600 px), le panneau de menu s'ouvre
**sous le header fixe**. Mesures :

```
.as-menu-overlay      → position: fixed, z-index: 40
.as-home-sticky-panel → position: fixed, z-index: 41, y = 0, hauteur = 101 px
document.elementFromPoint(195, 30) → un DIV du header, PAS un descendant de l'overlay
```

Conséquence, capture d'écran à l'appui : les **101 premiers pixels du menu sont recouverts** — la
barre « MENU » et **sa croix de fermeture sont inaccessibles**, et la première entrée
« Aujourd'hui » est cachée. Le menu s'ouvre visuellement sur « Ce week-end ». C'est un défaut réel,
reproductible, et il ressemble beaucoup à un « problème de menu en mobile ».

Correctif, une ligne :

```css
/* Le panneau de header fixe (z-index:41) recouvrait les 101 premiers pixels du menu
   ouvert (z-index:40) : croix de fermeture et 1re entrée inaccessibles après scroll.
   Un panneau ouvert passe devant le header, jamais dessous. */
.as-menu-overlay{ z-index: 60 !important; }
```

**Où le poser :** snippet **#62 (`cs-hdr-compact`)**, juste à côté de la règle qui pose
`z-index: 41` sur `.as-home-sticky-panel` — les deux valeurs doivent se lire ensemble.
**Risque : nul** (aucun autre élément du site ne dépasse z-index 41, hors bandeau cookies).

### Correctif proposé pour le bug initial

**Aucun correctif à appliquer** sur le menu vide lui-même — mais une consolidation à 1 ligne, pour
que le bug ne puisse pas revenir si le snippet #62 est désactivé, réordonné ou réécrit :

```css
/* À coller dans le snippet « CS · Composants (styles) », juste après la règle
   @media (max-width:720px){ .as-site-header__menu{display:none} } (ligne ~780).
   Le masquage ne vise que la nav de header, jamais un panneau ouvert. */
@media (max-width: 720px){
  .as-menu-overlay .as-site-header__menu,
  .as-site-header__mobile-menu .as-site-header__menu{ display: block !important; }
}
```

**Où le poser :** snippet **CS · Composants (styles)**, à l'endroit même de la règle fautive — pour
que la règle et son exception se lisent ensemble. (Le mettre dans le CSS additionnel du thème
marcherait aussi mais éloignerait la cause de son antidote.)

### Risque : nul.

---

## Bug 2 — Décalage au chargement (carrousel + barre de menu)

Deux défauts distincts, à traiter séparément.

### 2a. Le carrousel apparaît décalé à droite puis se recale — **CERTAIN, cause trouvée et chiffrée**

#### Ce qui a été observé

Enregistrement image par image du carrousel de la home pendant le chargement (réseau bridé à
600 kbit/s, CPU ×6), sur les deux viewports. Le conteneur ne bouge jamais ; **c'est le
`.swiper-wrapper` qui est trop large au début** :

| Instant | Viewport | Conteneur `.jet-listing-grid__slider` | `.swiper-wrapper` | Image |
|---|---|---|---|---|
| t = 743 ms | 390 px | x=20, **largeur 350** | **largeur 370** | x=30, **largeur 350** |
| t = 1746 ms | 390 px | x=20, largeur 350 | largeur **350** | x=30, largeur **330** |
| t = 874 ms | 1366 px | x=221, **largeur 910** | **largeur 930** | x=231, **largeur 910** |
| t = 1964 ms | 1366 px | x=221, largeur 910 | largeur **910** | x=231, largeur **890** |

Soit **exactement +20 px de trop, débordant à droite**, pendant la première seconde — puis retour à
la bonne largeur. Le conteneur étant en `overflow:hidden`, l'utilisateur voit une image légèrement
plus grande et décentrée vers la droite, qui « se recale vers la gauche pour devenir centrée ».
C'est mot pour mot la description de Franck.

#### Cause

Deux règles de `jet-engine/assets/css/frontend.css` (v3.8.11.2), lues dans le CSSOM au moment exact
du défaut :

```css
.jet-listing-grid__items { display:flex; flex-wrap:wrap; margin: 0 -10px; width: calc(100% + 20px); }
.jet-listing-grid__items.swiper-wrapper { flex-wrap:nowrap; margin-left:0; margin-right:0;
                                          --column-gap:0 !important; gap:0 !important; }
```

La 2ᵉ règle **remet les marges négatives à 0 mais oublie de remettre la largeur à 100 %**. Le
wrapper garde donc `width: calc(100% + 20px)` **sans** le `-10px` de gauche qui la compensait :
il déborde de 20 px à droite. Mesure confirmant : `margin-left: 0px`, `margin-right: 0px`,
`padding: 0`, `width: 370px` pour un conteneur de 350 px.

Le défaut disparaît **dès que `swiper.min.css` est appliquée** (elle déclare
`.swiper-wrapper{ width:100% }` et, chargée plus tard, gagne la cascade). Sur une connexion rapide
c'est instantané ; sur un téléphone en 4G moyenne, ça dure ~1 seconde — d'où « on voit que le
chargement se fait mal ».

**Degré de certitude : certain.** Cause identifiée, règles citées, effet mesuré deux fois sur deux
viewports.

#### Correctif proposé (prêt à coller)

```css
/* CARROUSEL — supprime le débordement de 20 px au chargement (2026-08).
   jet-engine/frontend.css donne .jet-listing-grid__items{width:calc(100% + 20px); margin:0 -10px}
   puis, pour la variante slider, remet les marges à 0 SANS remettre la largeur :
   le wrapper déborde de 20 px à droite jusqu'à ce que swiper.min.css (chargée plus
   tard) impose width:100%. Mesuré : wrapper 370px dans un conteneur de 350px sur
   mobile, 930 dans 910 sur desktop, pendant ~1 s. */
.jet-listing-grid__slider .jet-listing-grid__items.swiper-wrapper{
  width: 100% !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
```

**Où le poser :** dans le snippet **#77 (`cs-no-hide-empty-cols`)**, à côté du bloc « Anti-flash
Swiper pre-init » qui traite déjà exactement le même moment de vie du carrousel — les deux règles
se relisent ensemble. À défaut, le snippet **CS · Composants (styles)** convient aussi : les deux
sont émis **en ligne dans le `<head>`**, donc présents dès le premier octet, avant les feuilles
externes. **Ne pas le mettre dans le CSS additionnel du thème** : celui-ci est servi via
`wp-content/themes/generatepress-child/style.css`, un fichier externe, qui peut lui-même arriver
après le premier rendu — le correctif serait en retard sur le problème qu'il corrige.

**Risque : très faible.** La règle ne s'applique qu'aux wrappers de carrousel JetEngine et leur
impose la valeur que `swiper.min.css` finit de toute façon par imposer. Après init, Swiper pilote
la position par `transform`, pas par la largeur du wrapper — rien n'est perturbé.

> Mesure complémentaire : le CLS total de la home mobile est de **0,0075** (un seul déplacement
> notable, un `<form>` de 28 px). C'est très bon. Le « chargement qui se fait mal » perçu par Franck
> est donc bien le décalage **horizontal** du carrousel, pas un empilement vertical.

### 2b. Les deux lignes du header arrivent séparément — **CERTAIN sur desktop, mesuré**

#### Ce qui a été observé

**Desktop (1366 px)** — positions relevées pendant un défilement progressif :

| Scroll | `.as-home-desktop__nav` | `.as-terr-bar-inline` | classe `cs-hdr-min` |
|---|---|---|---|
| 240 px | `sticky`, y = **10** | `static`, y = 59 | non |
| 260 px | `sticky`, y = **−10** *(sorti de l'écran)* | `static`, y = 39 | non |
| 300 px | `fixed`, y = **0** | `fixed`, y = **49** | **oui** |

Entre 250 et 299 px de défilement, **la barre de menu est déjà sortie par le haut** alors que la
barre territoire est encore dans le flux — puis, au franchissement du seuil, les deux **ressautent**
de 10 px pour se recoller en haut. C'est la saccade décrite.

Deux causes cumulées :

1. `.as-home-desktop__nav` est en `position: sticky` mais **sticky ne fonctionne pas** ici : le
   commentaire du snippet #62 le dit lui-même (« position:sticky testée en direct et abandonnée —
   bloquée par `body{overflow-x:hidden}` »), et la mesure le confirme (y = −10 alors que `top:0`).
2. Les deux lignes sont **deux éléments fixés séparément**, avec un décalage **codé en dur** :

   ```css
   body.cs-home.cs-hdr-min .as-home-desktop__nav{ position:fixed; top:0; … }
   body.cs-home.cs-hdr-min .as-home-desktop .as-terr-bar-inline{ position:fixed; top:49px; … }
   ```

   Le `49px` correspond à la hauteur actuelle du nav (mesurée : 49 px). Toute modification de
   padding, de taille de logo ou de police recrée un chevauchement ou une bande morte.

**Mobile (390 px)** : les deux lignes sont déjà **un seul bloc** (`.as-home-sticky-panel`, enfants :
`.as-masthead-block` 136 px, barre FR|IT 42 px, `.as-terr-bar-inline` 39 px). Le passage
static → fixed est propre (la cale JS compense : le contenu sous le header ne bouge pas d'un pixel,
vérifié — la première carte reste à y = 271 avant comme après). **Mais** la hauteur passe de
**229 px à 101 px** : le masthead s'écrase à zéro. C'est précisément ce que Franck ne veut plus.

#### Ce que Franck demande, et le correctif

> « que le menu initial reste sticky, éventuellement un peu plus épais pour accueillir le logo,
> mais que ce soit LE MÊME à l'état initial et à l'état scrollé. »

Traduction technique : **le bandeau collant doit être le même objet dès le chargement** (logo
compact + FR|IT + burger + ligne territoire), et **le grand masthead doit sortir du bandeau** pour
défiler normalement au-dessus.

Ce n'est pas faisable en CSS seul : le masthead est un **enfant** du panneau qui passe en `fixed`.
Il faut le sortir en JS. Correctif complet, à substituer au bloc de script actuel du snippet #62
(celui qui commence par `(function(){ var b=document.body, hdr=document.querySelector('.as-site-header'), terr=…`) :

```js
/* HEADER HOME — un seul bandeau, identique au repos et au scroll (2026-08).
   Avant : le masthead était DANS le panneau collant, donc il fallait l'écraser au
   scroll (229px -> 101px) ; et sur desktop les deux lignes étaient fixées
   séparément avec un top:49px codé en dur, d'où l'arrivée décalée.
   Après : le masthead sort du panneau et défile normalement ; le panneau est fixe
   dès le premier pixel, à hauteur constante. */
(function () {
  var panel = document.querySelector('.as-home-sticky-panel');
  if (panel) {
    var masthead = panel.querySelector('.as-masthead-block');
    if (masthead) { panel.parentNode.insertBefore(masthead, panel); }   // (1) le masthead sort

    document.body.classList.add('cs-hdr-min', 'cs-hdr-always');          // (2) toujours compact

    var spacer = document.createElement('div');                          // (3) cale permanente
    spacer.setAttribute('aria-hidden', 'true');
    panel.parentNode.insertBefore(spacer, panel.nextSibling);
    var size = function () { spacer.style.height = panel.getBoundingClientRect().height + 'px'; };
    size();
    window.addEventListener('resize', size);
    if (window.ResizeObserver) { new ResizeObserver(size).observe(panel); }
  }

  /* DESKTOP : les deux lignes sont fixes dès le départ, et le décalage de la 2e
     ligne est MESURÉ sur la 1re au lieu d'être codé en dur (49px). */
  var dNav  = document.querySelector('.as-home-desktop__nav');
  var dTerr = document.querySelector('.as-home-desktop .as-terr-bar-inline');
  if (dNav && dTerr) {
    var dSpacer = document.createElement('div');
    dSpacer.setAttribute('aria-hidden', 'true');
    dTerr.parentNode.insertBefore(dSpacer, dTerr.nextSibling);
    var syncDesk = function () {
      if (window.innerWidth < 900) { dSpacer.style.height = '0px'; dTerr.style.top = ''; return; }
      var h = dNav.getBoundingClientRect().height;
      dTerr.style.top = Math.round(h) + 'px';
      dSpacer.style.height = Math.round(h + dTerr.getBoundingClientRect().height) + 'px';
    };
    syncDesk();
    window.addEventListener('resize', syncDesk);
  }
})();
```

CSS d'accompagnement (même snippet #62) :

```css
/* le masthead, désormais HORS du panneau collant, reste déployé en permanence :
   il annule le repli hérité de cs-hdr-min. */
body.cs-hdr-always .as-masthead-block{
  max-height: none !important; opacity: 1 !important;
}
/* le nav desktop n'est plus jamais sticky (sticky est cassé par body{overflow-x:hidden}) :
   il est fixe dès le chargement, comme la ligne territoire juste dessous. */
@media (min-width: 900px){
  body.cs-home .as-home-desktop__nav{ position: fixed !important; top: 0; left: 0; right: 0; z-index: 41; margin: 0 !important; }
  body.cs-home .as-home-desktop .as-terr-bar-inline{ position: fixed !important; left: 0; right: 0; z-index: 41; margin: 0 !important; }
  /* plus de top:49px codé en dur : il est posé en JS depuis la hauteur mesurée. */
}
```

**Où le poser :** snippet **#62 (« header compact »)** exclusivement — c'est lui qui contient à la
fois le CSS `cs-hdr-compact` et la logique de seuil. Éclater ce correctif entre le snippet et le CSS
du thème rendrait le comportement impossible à relire.

**Degré de certitude :** le **diagnostic** est certain (mesures ci-dessus). Le **correctif** est
une proposition d'architecture : il change la mise en page haute de la home et **doit être vérifié
visuellement** sur mobile, tablette et desktop avant d'être laissé en place.

**Risque : moyen — le plus élevé des cinq.** Il touche le premier écran de toutes les home
(y compris `/explore/…` et `/choisir/…`, qui servent la même page 928) et déplace un nœud du DOM.
À déployer en dernier, et avec Franck devant l'écran.

---

## Bug 3 — Section « Les 7 prochains jours » blanche

### Ce qui a été observé

**Le constat de Franck est exact et vérifié** : entre le titre `Les 7 prochains jours` (offset
289006 du HTML de la home) et le titre `Nouveautés sur Agenda Sabauda` (offset 318929), le HTML
servi contient bien **8 cartes** — précisément 8 `div.jet-listing-grid__item.jet-listing-dynamic-post-…`
(posts 588, 590, 799, 6254, 599, 2269, 2281, 6801) dans
`<div class="wp-block-group as-home-desktop as-desktop-grid-4">`. (Il y a en tout 12 liens
`/evenement/` dans cet intervalle : les 8 cartes + les 4 de « Ça vaut le déplacement ».)

**La structure réelle**, mesurée dans le navigateur, est la suivante — un conteneur
`div.as-home-desktop`, enfant de `.as-home-root`, contient dans cet ordre :

| Enfant | Contenu | `display` en 390 px |
|---|---|---|
| `div` (sans classe) | « Voir tous les événements du week-end → » | **none** |
| `div` (sans classe) | **« Les 7 prochains jours · Voir tout → »** | **none** |
| `.as-home-desktop.as-desktop-grid-4` | **les 8 cartes** | **none** |
| `.as-home-desktop` | « Ça vaut le déplacement » (version desktop) | **none** |
| `.as-desktop-cols3` | Nouveautés / En évidence / L'agenda à venir | **grid** ✅ |

Le masquage vient d'une seule règle, ajoutée aujourd'hui dans `cs-composants-styles` :

```css
@media (max-width: 899px) {
  .as-home-desktop:has(> .as-desktop-cols3) > *:not(.as-desktop-cols3){ display: none !important; }
}
```

**Et il existe une version mobile propre de la section**, plus haut dans la page (offset 186189) :

```html
<!-- EVENEMENTS DU JOUR (rail horizontal) -->
<div class="as-day-rail" …>
  <div …>Les 7 prochains jours</div>
</div>
<div class="wp-block-group as-home as-day-rail" …><… id="jour" …>
```

**État actuel constaté : la section n'est plus blanche.** En rendu réel mobile 390 px, sur `/` comme
sur `/explore/savoie/`, le rail mobile est visible et **peuplé** (4 cartes visibles, limitées par
`.as-home #jour .jet-listing-grid__item:nth-child(n+5){display:none}`), et le doublon desktop est
correctement masqué (0 carte visible sur 8). En desktop 1366 px, c'est l'inverse : rail mobile
masqué, grille de 8 cartes visible. Je n'ai **pas** réussi à reproduire la section blanche
aujourd'hui.

### Cause la plus probable

**Le bug est celui qui vient d'être corrigé, et sa dernière rustine repose sur `:has()`.**
Démonstration faite : j'ai **supprimé cette seule règle du CSSOM** en direct, dans le navigateur
mobile, sans rien toucher d'autre. Résultat immédiat :

- le titre « Les 7 prochains jours » apparaît **deux fois** (y = 2394 pour le rail mobile,
  y = 3627 pour le doublon desktop) ;
- la grille des 8 cartes reste `display:none` (`.as-desktop-grid-4{display:none}` hors ≥ 900 px),
  hauteur **0** ;
- on obtient donc, à l'écran, **le titre « LES 7 PROCHAINS JOURS · Voir tout → » suivi de rien**,
  immédiatement collé à « NOUVEAUTÉS SUR AGENDA SABAUDA » — capture d'écran à l'appui.

C'est **exactement** la section blanche décrite, et aussi le « bloc en double, 1ʳᵉ occurrence vide »
noté dans `docs/site_issues.json` #3.

**Deux explications possibles à ce que Franck voit encore, et une seule information manque pour
trancher :**

- **(a) il a regardé avant le déploiement de la règle** (elle est datée du jour dans le CSS) — dans
  ce cas il n'y a plus rien à faire que vider le cache et revérifier ;
- **(b) son navigateur ne supporte pas `:has()`** (Safari < 15.4, Chrome < 105, Firefox < 121, et
  toutes les WebView Android anciennes) — la règle est alors ignorée **en silence** et le bug est
  toujours là chez lui, et chez tous les visiteurs dans le même cas.

**Information manquante et comment l'obtenir :** demander à Franck la version de son navigateur
(iOS Réglages → Général → Informations, ou `chrome://version`). Ou, plus rapide : lui faire ouvrir
la home sur son téléphone et taper dans la barre d'adresse
`javascript:alert(CSS.supports('selector(:has(*))'))` — `true` = cas (a), `false` = cas (b).
**Dans le doute, appliquer le correctif ci-dessous : il rend la question sans objet.**

### Correctif proposé (prêt à coller)

Remplacer la règle à `:has()` par une règle qui n'en dépend pas. Les trois éléments à masquer sur
mobile sont identifiables sans remonter au parent :

```css
/* Doublons desktop sur mobile — version sans :has() (2026-08).
   La règle précédente utilisait .as-home-desktop:has(> .as-desktop-cols3) > *:not(…),
   ignorée en silence par Safari < 15.4 / Chrome < 105 : chez ces visiteurs le titre
   « Les 7 prochains jours » du bloc desktop restait visible AVEC sa grille masquée,
   soit une section blanche. On cible désormais les blocs eux-mêmes. */
@media (max-width: 899px) {
  /* les grilles desktop sont déjà masquées par .as-desktop-grid-3/-4 ; ici on masque
     les TITRES et boutons desktop, qui n'ont pas de classe propre. */
  .as-home-root > .as-home-desktop > div:not([class]),
  .as-home-root > .as-home-desktop > .as-home-desktop{ display: none !important; }
  .as-home-root > .as-home-desktop > .as-desktop-cols3{ display: grid !important; }
}
```

> ⚠️ Ce sélecteur repose sur le fait, **vérifié dans le HTML servi**, que les titres desktop
> « Voir tous les événements du week-end → » et « Les 7 prochains jours » sont des `<div>` **sans
> attribut `class`**, enfants directs du conteneur `.as-home-desktop`. Si un jour un de ces blocs
> reçoit une classe, il réapparaîtra. La solution durable est de **leur donner une classe explicite**
> (par ex. `as-desktop-only`) dans le contenu de la page 928, et de masquer `.as-desktop-only` sous
> 900 px — 3 minutes dans l'éditeur Gutenberg, et plus aucun sélecteur acrobatique.

**Où le poser :** snippet **CS · Composants (styles)**, en **remplacement** du bloc actuel
« Doublons desktop sur mobile » (dernières lignes du snippet). Ne pas ajouter la nouvelle règle
à côté de l'ancienne : deux formulations concurrentes du même masquage sont ingérables.

**Certitude :** mécanisme **certain** (démontré en supprimant la règle). Le fait que Franck le voie
*encore* est une **hypothèse** tant que (a) ou (b) n'est pas tranché.

**Risque : faible.** La nouvelle règle est plus restrictive que l'ancienne (elle cible les enfants
directs d'un conteneur précis). À vérifier après pose : que la section « Ça vaut le déplacement »
mobile est toujours là (elle vient d'un autre bloc, dans `.as-home`) et que les 3 colonnes du bas
sont toujours affichées.

---

## Bug 4 — Formats de tuiles hétérogènes

### Ce qui a été observé

Mesure de **toutes les vignettes visibles** de la home en 390 px, après déclenchement complet du
lazy-loading :

| Section (id du listing) | Classe de la vignette | Largeur | Hauteur | Ratio |
|---|---|---|---|---|
| À la une / Ce week-end / 7 prochains jours (`#ala-une`, `#weekend`, `#jour`) | `.ala-une-card__image.cs-card-thumb` | 150 · 155 · **165** | 113 · 116 · 124 | 4:3 |
| Ça vaut le déplacement | `.cs-cvld-thumb` (variante `--row`) | **110** | 83 | 4:3 |
| **Nouveautés** (`#nouveautes`) | `.venir-row__image.cs-card-thumb` | **90** | 68 | 4:3 |
| En évidence (`#evidence`) | `.evidence-card__image.cs-card-thumb` | **330** (pleine largeur) | 248 | 4:3 |
| L'agenda à venir (`#venir`) | `.venir-row__image.cs-card-thumb` | 90 | 68 | 4:3 |

**Bonne nouvelle mesurée :** le ratio est **déjà unifié à 4:3 partout** (règle
`.cs-card-thumb{ aspect-ratio: 4/3 !important }`), et **toutes les tailles de titre sont à
15 px / 600** (`.cs-card-title`, `.cs-cvld-title`, `.evidence-card__title`, `.venir-row__title`,
`.ala-une-card__title`). Le travail d'unification typographique de la journée a bien pris.

**Ce qui reste hétérogène, c'est la LARGEUR des vignettes : 90, 110, 150–165, 330 px** — quatre
gabarits sur un même écran. La section « Nouveautés » a la plus petite (90 px), là où Franck
la veut grande.

### Cause — **certain**

Chaque gabarit fixe sa largeur dans sa propre règle, et rien ne les relie :

```css
.venir-row__image { width: 90px; flex-shrink: 0; aspect-ratio: 3/2; … }   /* Nouveautés + agenda à venir */
.cs-cvld-card--row .cs-cvld-thumb{ width:110px; flex-shrink:0; … }         /* Ça vaut le déplacement */
.as-day-rail .ala-une-card { width: 150px; flex-shrink: 0; }               /* rails horizontaux */
```

La classe partagée `.cs-card-thumb` gouverne le **ratio** et le **cadrage** (`object-position: top center`),
mais **pas la largeur ni la disposition** (photo à gauche vs photo au-dessus).

### Correctif proposé (prêt à coller)

Le format visé par Franck (« comme celui de Ça vaut le déplacement », c'est-à-dire la grande photo)
est en réalité, sur mobile, le format de **« En évidence » : photo pleine largeur au-dessus du
texte**. Voici la bascule, ciblée sur les sections concernées :

```css
/* MOBILE — un seul gabarit de carte : photo pleine largeur au-dessus du texte.
   Mesuré avant correction sur la home mobile : 4 largeurs de vignette (90 / 110 /
   150-165 / 330 px) sur un même écran. Le ratio (4:3) et la typo (15px/600) étaient
   déjà unifiés ; il ne restait que la disposition. On aligne « Nouveautés » et
   « Ça vaut le déplacement » sur « En évidence », qui est déjà en grand format. */
@media (max-width: 899px) {

  /* 1. Nouveautés : de « vignette 90px à gauche » à « photo pleine largeur au-dessus » */
  #nouveautes .venir-row,
  #nouveautes .venir-row > .wp-block-group__inner-container{ display: block !important; }
  #nouveautes .venir-row__image{
    width: 100% !important; margin-bottom: 9px !important; border-radius: 3px;
  }

  /* 2. Ça vaut le déplacement : même chose, la variante --row repasse en colonne */
  .cs-cvld-card--row{ display: block !important; }
  .cs-cvld-card--row .cs-cvld-thumb{
    width: 100% !important; margin-bottom: 9px !important;
  }
}
```

Et, si Franck veut **aussi** « L'agenda à venir » au même format (recommandé, sinon il restera
un 5ᵉ gabarit sur la page) — sinon, ne pas coller ce bloc :

```css
@media (max-width: 899px) {
  #venir .venir-row,
  #venir .venir-row > .wp-block-group__inner-container{ display: block !important; }
  #venir .venir-row__image{ width: 100% !important; margin-bottom: 9px !important; }
}
```

**Où le poser :** snippet **CS · Composants (styles)**, à la suite du bloc
« SYSTEME DE CARTE UNIFIE — 2026-08-02 » : c'est la suite logique du même chantier, écrite au
même endroit et avec la même justification chiffrée. **Surtout pas dans le CSS additionnel du
thème** — le système de carte serait alors décrit à deux endroits, et c'est précisément la cause
racine que le bloc « SYSTEME DE CARTE UNIFIE » dit avoir voulu supprimer.

**Certitude : certain** sur le diagnostic (largeurs mesurées) ; **le rendu final est un choix de
design** qu'il faut valider à l'œil — une carte pleine largeur par événement allonge nettement la
page (« Nouveautés » passe de 3 lignes compactes à 3 blocs de ~330 px).

**Risque : faible à modéré.** Purement visuel, borné à ≤ 899 px et à trois identifiants de listing.
À contrôler après pose : la longueur totale de la home mobile (elle fait 11 106 px aujourd'hui ;
elle augmentera de ~600 px), et le fait que les 3 colonnes desktop ne sont pas touchées
(la media query s'en charge).

---

## Bug 5 — Filtre territoire non transmis aux tuiles catégorie

### Ce qui a été observé — **CERTAIN**

> ⚠️ **Correction en cours d'enquête.** Ma première conclusion était « le territoire n'est mémorisé
> nulle part ». **C'est faux, et je l'ai vérifié avant de l'écrire** : il existe un cookie
> `as_territoire`. Le vrai défaut est plus précis, et le correctif n'est pas le même.

1. **Choisir « Savoie » sur la home = changer de page.** Le sélecteur de territoire n'est pas un
   filtre, ce sont quatre liens en dur :

   ```html
   <div class="as-terr-dropdown">
     <a href="https://agendasabauda.eu/explore/savoie/">Savoie</a>
     <a href="https://agendasabauda.eu/choisir/piemont/">Piémont</a>
     <a href="https://agendasabauda.eu/choisir/vallee-d-aoste/">Vallée d'Aoste</a>
     <a href="https://agendasabauda.eu/explore/comte-de-nice/">Comté de Nice</a>
   </div>
   ```

2. **`/explore/savoie/` est bien la home filtrée**, côté serveur : `<body class="home … page-id-928 …">`,
   canonique `https://agendasabauda.eu/`, et la barre affiche
   `Vous regardez <strong>Savoie</strong>` / « Changer de territoire ».

3. **Le choix EST mémorisé, dans un cookie posé par le serveur.** En-têtes de réponse de
   `/explore/savoie/` :

   ```
   set-cookie: as_territoire=savoie; expires=Mon, 31-Aug-2026 …; Max-Age=2592000; path=/
   ```

   (30 jours, tout le site.) Le mécanisme de remise à zéro existe aussi : `/?as_territoire=tous`
   répond `set-cookie: as_territoire=deleted; Max-Age=0`. Rien n'est écrit en `localStorage`
   (vérifié : `localStorage` vide, `sessionStorage` ne contient que `wpEmojiSettingsSupports`).

4. **Les tuiles catégorie ne portent aucun paramètre** — toutes de la forme
   `<a href="https://agendasabauda.eu/evenements/categorie/jeune-public-famille/">`.

5. **Le hub catégorie LIT le cookie, mais il ne s'en sert que pour trier, pas pour filtrer.**
   C'est le cœur du bug. Trois requêtes sur la même URL, événements uniques comptés et territoire
   de chaque carte relevé :

   | Requête | Nb d'événements | Territoires listés |
   |---|---|---|
   | sans cookie | **17** | Nice ×8, Savoie ×1, V. d'Aoste ×1, non étiquetés ×7 |
   | **avec `Cookie: as_territoire=savoie`** | **8** | **Savoie ×1 puis Nice ×3, V. d'Aoste ×1, autres** |
   | avec `?filtre2=savoie` | **2** | **Savoie uniquement** |

   Avec le cookie, les deux événements savoyards (`lete-au-centre-socioculturel`,
   `dinosaures-le-voyage-de-bumpy…`) **remontent en tête** et la liste est raccourcie à 8 — mais
   **les autres territoires sont toujours là**. Et le `<select name="filtre2">` reste sur
   « Territoire » : aucun `selected='selected'`. Du point de vue du visiteur : « j'ai choisi la
   Savoie et j'obtiens tous les territoires ». **La plainte de Franck est exacte.**

6. **Le vrai filtre existe et fonctionne**, par un paramètre GET. La barre de filtres du hub n'est
   **pas** JetSmartFilters mais un formulaire `method="get"` classique :

   ```html
   <form method="get">
     <input type="date" name="jour" …>
     <select name="ville">…</select>
     <select name="filtre2">
       <option value="">Territoire</option>
       <option value="comte-de-nice">Comté de Nice</option>
       <option value="piemont">Piémont</option>
       <option value="savoie">Savoie</option>
       <option value="vallee-d-aoste">Vallée d'Aoste</option>
     </select>
     <button type="submit">Appliquer</button>
   </form>
   ```

   | URL | Événements | `<option value="savoie">` |
   |---|---|---|
   | `/evenements/categorie/jeune-public-famille/` | 17 | non sélectionné |
   | `/evenements/categorie/jeune-public-famille/?filtre2=savoie` | **2** | `selected='selected'` |
   | `/evenements/categorie/jeune-public-famille/?filtre2=comte-de-nice` | 11 | non sélectionné |
   | `/type-de-lieu/musee/` | 9 | — |
   | `/type-de-lieu/musee/?filtre2=savoie` | **1** | `selected='selected'` |

   Le slug attendu par `filtre2` est **exactement** celui déjà présent dans l'URL de territoire et
   dans le cookie (`savoie`, `piemont`, `vallee-d-aoste`, `comte-de-nice`).

   ⚠️ `/tout-l-agenda/?filtre2=savoie` **ne filtre pas** (50 événements avant comme après) : cette
   page n'a que les filtres `ville` et `categorie`. Le correctif ne doit pas toucher ce lien.

### Cause — **certain**

Le hub connaît le territoire du visiteur (cookie) et **choisit de ne pas l'appliquer comme filtre** :
il ne s'en sert que pour un tri de priorité. Le seul mécanisme filtrant, `filtre2`, n'est alimenté
que par le formulaire, jamais par le cookie ni par les liens entrants.

### Correctif proposé — deux voies, la première recommandée

**Voie A (la plus propre, côté serveur) : faire que `filtre2` prenne par défaut la valeur du cookie.**
Le code qui rend le hub lit déjà `$_COOKIE['as_territoire']` (c'est lui qui trie) et lit déjà
`$_GET['filtre2']`. Il suffit que la valeur par défaut de `filtre2` soit le cookie :

```php
// Dans le snippet Code Snippets qui rend les hubs (le retrouver en cherchant
// « filtre2 » dans Code Snippets — c'est lui qui définit le nom du paramètre).
// AVANT : $terr = isset($_GET['filtre2']) ? sanitize_title($_GET['filtre2']) : '';
// APRÈS :
$terr = isset($_GET['filtre2'])
    ? sanitize_title($_GET['filtre2'])                       // le formulaire gagne toujours
    : ( isset($_COOKIE['as_territoire']) && $_COOKIE['as_territoire'] !== 'tous'
        ? sanitize_title($_COOKIE['as_territoire'])          // sinon, le territoire choisi
        : '' );
```

Avantages : marche depuis **n'importe quel lien** (menu, footer, recherche, lien partagé), et pas
seulement depuis les tuiles de la home ; le `<select>` se met tout seul sur la bonne valeur (il est
déjà construit à partir de `$terr`) ; le visiteur garde l'échappatoire existante
(« Tous les territoires » → `/?as_territoire=tous`, qui supprime le cookie).
Réserve : **c'est du PHP, donc du contenu servi** — à tester sur une catégorie avant de généraliser,
et à surveiller côté cache (une page mise en cache pour un territoire ne doit pas être resservie à
un visiteur d'un autre territoire ; vérifier la configuration de cache de l'hébergeur, ou exclure
les hubs du cache page).

**Voie B (sans PHP, sans risque de cache) : réécrire les liens en JS depuis la home de territoire.**

```js
/* TERRITOIRE PERSISTANT VERS LES HUBS (2026-08).
   Le hub catégorie lit bien le cookie as_territoire, mais il ne s'en sert que pour
   TRIER (17 -> 8 événements, tous territoires confondus) ; le seul filtre réel est
   ?filtre2=<slug> (17 -> 2, Savoie uniquement). On l'ajoute donc aux liens sortants
   des home de territoire. Volontairement PAS /tout-l-agenda/ ni /ce-week-end/ :
   ces pages ignorent filtre2. */
(function () {
  var TERR = ['savoie', 'piemont', 'vallee-d-aoste', 'comte-de-nice'];
  var m = location.pathname.match(/\/(?:explore|choisir|territoire)\/([a-z0-9-]+)\/?$/);
  var slug = m && TERR.indexOf(m[1]) !== -1 ? m[1] : null;

  // repli : si on n'est pas sur une home de territoire, on utilise le cookie
  if (!slug) {
    var c = document.cookie.match(/(?:^|;\s*)as_territoire=([a-z0-9-]+)/);
    if (c && TERR.indexOf(c[1]) !== -1) { slug = c[1]; }
  }
  if (!slug) { return; }

  document.querySelectorAll('a[href*="/evenements/categorie/"], a[href*="/type-de-lieu/"]')
    .forEach(function (a) {
      var u;
      try { u = new URL(a.href, location.origin); } catch (e) { return; }
      if (u.origin !== location.origin) { return; }
      if (u.searchParams.has('filtre2')) { return; }
      u.searchParams.set('filtre2', slug);
      a.href = u.toString();
    });
})();
```

**Où le poser :**
- Voie A : dans le snippet PHP **existant** qui rend les hubs. Ne pas créer un second endroit qui
  décide du territoire — c'est ce qui a produit la situation actuelle (un cookie qui trie d'un côté,
  un paramètre qui filtre de l'autre, sans lien entre les deux).
- Voie B : **nouveau snippet** Code Snippets, scope « front-end », émis en pied de page
  (`wp_footer`) pour que les tuiles soient dans le DOM. Un snippet séparé pour pouvoir le
  désactiver seul pendant un test.

**Recommandation :** commencer par la **voie B** (zéro risque, réversible en un clic, couvre le
scénario exact décrit par Franck), et garder la **voie A** pour la version définitive une fois la
question du cache tranchée.

**Risque :** voie B **très faible** (ne modifie que des `href` internes, n'écrase jamais un
`filtre2` existant, sans effet SEO : les robots voient les URL canoniques sans paramètre).
Voie A **faible à modéré**, entièrement porté par la question du cache page.

> 🐛 **Trouvaille annexe, à ne pas ignorer si vous implémentez ce correctif.**
> `/evenements/categorie/<n'importe quelle catégorie>/?territoire=savoie` répond
> **HTTP 200 avec 0 octet** — une page totalement blanche. Reproduit 2 fois sur
> `jeune-public-famille` et sur `concerts-musique` ; `?zzz=1` et `?utm_source=test` sur la même URL
> renvoient les 368 087 octets normaux, et `?territoire=nimportequoi` renvoie un 404 propre.
> `territoire` est le nom de la **taxonomie** : WordPress l'enregistre comme query var, et la
> combinaison « archive de catégorie + terme de territoire » casse silencieusement le rendu.
> Deux conséquences : (1) **n'utilisez jamais `?territoire=` comme nom de paramètre** pour le
> correctif ci-dessus — c'est pourtant le premier réflexe ; (2) c'est une URL publique qui renvoie
> une réponse vide en 200, donc une erreur douce indexable. À ouvrir comme une issue à part.

---

## Ordre de traitement recommandé

| # | Correctif | Pourquoi à ce rang | Effort | Risque |
|---|---|---|---|---|
| **1** | **2a — carrousel (+20 px)** | 3 lignes de CSS, cause certaine et chiffrée, effet visible **dès la 1ʳᵉ seconde sur toutes les pages à carrousel**. Meilleur rapport gain/risque du lot. | 5 min | très faible |
| **2** | **3 — section blanche sans `:has()`** | Remplace une rustine posée aujourd'hui par une règle qui marche aussi sur les navigateurs anciens. Ferme un bug que Franck voit peut-être **encore**, sans avoir à attendre la réponse sur sa version de navigateur. | 10 min | faible |
| **3** | **5 — territoire transmis aux hubs** | Le seul bug **fonctionnel** de la liste (les autres sont visuels) : aujourd'hui le visiteur qui choisit la Savoie reçoit du Piémont. Snippet isolé, désactivable seul. | 15 min | très faible |
| **4** | **1 — menu recouvert par le header (`z-index`) + verrou anti-régression** | Le recouvrement est un **défaut réel constaté aujourd'hui** (croix de fermeture inaccessible après scroll) ; le verrou immunise contre le retour du menu vide. Deux lignes de CSS. | 5 min | nul |
| **5** | **4 — uniformisation des tuiles** | Purement esthétique, et c'est un **choix** : à faire quand Franck peut regarder le résultat et arbitrer. | 20 min + validation | faible/modéré |
| **6** | **2b — header unifié initial/scrollé** | Le plus structurant : déplacement d'un nœud du DOM, panneau fixe permanent, premier écran de toutes les home. À faire en dernier, avec Franck devant l'écran, et sur un seul snippet pour pouvoir revenir en arrière d'un clic. | 45 min + validation | **moyen** |

### Récapitulatif des risques sur le reste du site

- **2a (carrousel)** — porte sur `.jet-listing-grid__items.swiper-wrapper`, donc sur tous les
  carrousels JetEngine du site (hero home mobile, hero home desktop, sélections). Elle leur impose
  la largeur que `swiper.min.css` finit de toute façon par leur donner : pas de nouvel état possible.
- **3 (doublons desktop)** — le nouveau sélecteur est **plus étroit** que celui qu'il remplace
  (enfants directs de `.as-home-root > .as-home-desktop`). Risque : qu'un `<div>` desktop reçoive
  un jour une classe et réapparaisse sur mobile. Parade durable proposée dans la section.
- **5 (territoire), voie B (JS)** — n'écrit que des `href` internes vers deux familles d'archives,
  n'écrase jamais un `filtre2` déjà présent. Aucun effet SEO (réécriture côté client, après rendu ;
  les robots voient les URL canoniques sans paramètre).
- **5 (territoire), voie A (PHP)** — le seul point à surveiller est le **cache page** : le contenu
  du hub dépendrait alors d'un cookie. Si l'hébergeur sert du cache anonyme, une page « Savoie »
  pourrait être resservie à un visiteur « Piémont ». À vérifier avant de basculer sur cette voie.
- **1 (menu)** — une exception à une règle de masquage, dans le même bloc que la règle, plus une
  valeur de `z-index`. Le passage de l'overlay à 60 le place au-dessus de tout le chrome de page ;
  vérifier seulement qu'il reste **sous** le bandeau cookies Complianz si celui-ci doit rester
  prioritaire (sinon, 60 convient : rien d'autre ne dépasse 41).
- **4 (tuiles)** — bornée par `@media (max-width: 899px)` et par trois `id` de listing ; les 3
  colonnes desktop et les pages hub ne sont pas touchées. Effet de bord attendu : home mobile plus
  longue d'environ 600 px.
- **2b (header)** — le seul qui touche la structure. Il concerne **toutes les home** (`/`, `/it/`,
  `/explore/*`, `/choisir/*` : elles servent toutes la page 928), pas les pages internes qui
  utilisent `.as-site-header`. Points à revérifier après pose : le panneau ne recouvre pas le H1,
  la cale de compensation garde le contenu immobile. **Attention :** le panneau devenant fixe
  **en permanence**, le recouvrement du menu décrit au bug 1 ne se produira plus seulement après
  scroll mais **dès le chargement**. Le correctif `z-index` du bug 1 est donc un **prérequis** de
  celui-ci, pas une option.

---

## Annexe — questions ouvertes à faire trancher par Franck

1. **Bug 3 :** son navigateur supporte-t-il `:has()` ? (`javascript:alert(CSS.supports('selector(:has(*))'))`
   dans la barre d'adresse du téléphone.) Répond à « bug déjà corrigé » vs « bug encore actif chez
   une partie des visiteurs ».
2. **Bug 4 :** valide-t-il que « Nouveautés » ET « L'agenda à venir » passent en grande photo, ou
   seulement « Nouveautés » ? (Le laisser à moitié = conserver un gabarit de plus.)
3. **Bug 5 :** veut-il que le territoire suive aussi sur `/tout-l-agenda/` et `/ce-week-end/` ?
   Si oui, il faut d'abord ajouter un filtre territoire à ces deux pages (snippet PHP qui génère
   les hubs — chercher `filtre2` dans Code Snippets).
4. **Bug 5 (suite) :** le hub doit-il **filtrer** sur le territoire mémorisé (voie A), ou seulement
   quand on y arrive par une tuile de la home (voie B) ? La question de fond : un visiteur qui a
   choisi la Savoie il y a trois semaines (le cookie dure 30 jours) et qui arrive par Google sur
   une page « Concerts » doit-il voir uniquement la Savoie ? Mon avis : **non** — d'où la
   recommandation de commencer par la voie B.
5. **Dette de dépôt :** `wordpress/design-system/components.css` (31 Ko) est en retard de ~40 Ko sur
   le snippet en production (70 875 caractères). Tant que ce n'est pas resynchronisé,
   `apply-components.mjs` est une arme chargée. À traiter hors de ce lot de bugs.
6. **Page blanche `?territoire=` :** ouvrir une issue à part (cf. encadré du bug 5) — une URL
   publique qui répond 200 avec 0 octet.

---

## Note de traçabilité

Aucun fichier du dépôt n'a été modifié en dehors de ce document, et je n'ai lancé ni `git commit`
ni `git push`. Si l'historique montre un commit portant ce fichier, il ne vient pas de cette
investigation.
