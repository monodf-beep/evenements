# Correctifs prêts à coller — agendasabauda.eu

**Date des mesures : 2026-08-03, 06 h 20 – 07 h 10 UTC.**
**Périmètre : préparation et vérification. Rien n'a été écrit sur le site. Aucun snippet créé,
modifié ou activé. Aucun PHP exécuté. Le déploiement est la décision de Franck.**

Ce document reprend `docs/DIAGNOSTIC_BUGS_SITE.md` (2026-08-01) et le confronte aux pages
réellement servies aujourd'hui. **Il confirme trois causes, en corrige une, et écarte un correctif
qui ne fait pas ce qu'il annonce.**

---

## 0. Méthode, et où passe la frontière entre MESURÉ et SUPPOSÉ

### Ce qui a été fait

1. **Téléchargement direct** (`curl`, User-Agent iPhone) de `/`, `/explore/savoie/`,
   `/explore/comte-de-nice/`, `/choisir/piemont/`, `/choisir/vallee-d-aoste/`, `/it/home-it/`,
   `/tout-l-agenda/`, `/ce-week-end/`, `/evenements/categorie/jeune-public-famille/`,
   `/evenements/categorie/concerts-musique/`, `/evenements/categorie/cinema/`,
   `/type-de-lieu/musee/`, une fiche événement.
2. **Rendu réel dans Chromium headless** (Playwright 1.56, Chromium 1194), viewports 390×844
   (iPhone) et 1366×860, avec `getComputedStyle`, `getBoundingClientRect`, `elementFromPoint`,
   et enregistrement image par image (`requestAnimationFrame`, ~1 000 relevés par run).
3. **Relais réseau.** Chromium ne joint pas le site directement depuis cet environnement (le proxy
   sortant réinitialise le tunnel TLS du navigateur). Chaque requête du navigateur est donc rejouée
   telle quelle par le client HTTP de Playwright — qui, lui, passe — puis servie au navigateur avec
   ses en-têtes d'origine, **et mise en cache disque pour que les runs « avant » et « après »
   portent sur des octets strictement identiques**.
4. **A/B réel de chaque correctif.** Le CSS candidat est injecté **dans le HTML servi, juste avant
   `</head>`** — exactement ce que fait un snippet Code Snippets émis en ligne dans le `<head>`.
   Chaque correctif ci-dessous a donc une mesure *avant* et une mesure *après*, sur la même page.

### Ce que ces mesures ne peuvent pas prouver

- **Je n'ai pas d'accès admin.** Je vois les blocs `<style id="cs-…">` que le site émet, pas les
  numéros de snippet dans Code Snippets. Quand j'écris « snippet #77 », je reprends le numéro du
  diagnostic du 1ᵉʳ août : **c'est une reprise, pas une vérification.** Le repère fiable est
  l'attribut `id` du bloc `<style>`, visible dans le code source de n'importe quelle page.
- **Je n'ai testé que Chromium 1194 (moteur récent).** Tout ce qui concerne les navigateurs anciens
  (§ 4) est mesuré par *émulation* — en retirant du CSSOM les règles qu'un vieux moteur rejetterait
  —, pas sur un vrai vieux Safari. C'est dit à chaque fois.
- **Le comportement du cache de l'hébergeur n'a pas été testé.** Aucun des correctifs retenus n'en
  dépend (aucun n'est du PHP servi).

### Un faux négatif rencontré et corrigé en cours de route — à connaître

Mon premier sondage « quelle règle masque ce bloc ? » a répondu **« aucune »**, ce qui était faux.
Deux causes, toutes deux instructives :

- `CSSStyleRule` expose aujourd'hui une propriété `cssRules` (vide) à cause du CSS imbriqué. Mon
  parcours récursif faisait donc `continue` sur **toutes** les règles de style et n'en examinait
  aucune.
- Chromium **normalise** les sélecteurs dans le CSSOM : la règle écrite
  `:has(> .as-desktop-cols3) > *:not(.as-desktop-cols3)` s'y relit
  `:has(> .as-desktop-cols3) > :not(.as-desktop-cols3)` — **sans l'astérisque**. Chercher la chaîne
  d'origine ne trouve rien.

Si j'avais gardé la première réponse, j'aurais écrit « le masquage ne vient pas du CSS » et bâti un
correctif dessus. C'est exactement la classe d'erreur que ce document doit éviter : **une mesure qui
répond « rien » mérite d'être suspectée avant d'être crue.**

---

## 1. État réel de la production au 2026-08-03

### Les blocs de style que le site émet lui-même

Relevé sur le HTML servi de `/` (offsets = position dans le document, donc **ordre de cascade**) :

| Offset | Bloc | Taille | Rôle |
|---|---|---|---|
| 5 366 | `<style id="cs-design-tokens">` | 5 036 c. | variables |
| 10 660 | `<style id="cs-composants-styles">` | **71 235 c.** | l'essentiel du design |
| 86 870 | `<link>` **jet-engine/assets/css/frontend.css** v3.8.11.2 | — | ← la règle fautive du carrousel |
| 95 990 | `<link>` `generatepress-child/style.css` | — | CSS additionnel du thème |
| 98 886 | `<style id="cs-nav-logo-reveal">` | 178 c. | |
| 99 112 | `<style id="cs-cat-empty-hide">` | 159 c. | |
| 99 314 | `<style id="cs-hdr-compact">` | 6 896 c. | header compact (« #62 ») |
| 106 805 | `<style id="cs-no-hide-empty-cols">` | 4 540 c. | anti-flash carrousel (« #77 », priorité 999) |
| **112 482** | `</head>` | | |
| **462 645** | `<link>` **elementor/…/swiper/v8/css/swiper.min.css** | — | **dans le corps de page, très tard** |

Deux conséquences directes, toutes deux mesurées :

- **`swiper.min.css` arrive à l'offset 462 645, soit 350 Ko après la fin du `<head>`.** C'est la
  cause matérielle du défaut du carrousel : la feuille qui répare arrive bien après celle qui casse.
- **`cs-no-hide-empty-cols` est le dernier bloc du `<head>`, et il est émis après
  `jet-engine/frontend.css`.** Une règle posée là gagne la cascade sur JetEngine **même sans
  `!important`** (vérifié par mesure, § 2).

### Le piège de déploiement est toujours ouvert

`docs/site_issues.json` #9 tient : `wordpress/design-system/components.css` fait 31 Ko dans le
dépôt, le bloc `cs-composants-styles` en production en fait **71 235 caractères** (il en faisait
70 875 le 1ᵉʳ août : **+360 c. en deux jours**, la production continue de bouger sous le dépôt).

**Conséquence pour tout ce qui suit : aucun correctif de ce document ne remplace un bloc existant.**
Ce sont tous des **ajouts autonomes**, encadrés par des marqueurs de début et de fin, posés à la
suite d'un snippet existant. `apply-components.mjs` reste à ne pas lancer.

### Ce que le diagnostic du 1ᵉʳ août dit encore juste — revérifié aujourd'hui

| Mesure du diagnostic | État au 2026-08-03 |
|---|---|
| Wrapper de carrousel 370 px dans un conteneur de 350 (mobile) | ✅ **identique** |
| Wrapper 930 dans 910 (desktop) | ✅ **identique** |
| Overlay de menu z-index 40, panneau de header z-index 41, hauteur 101 px | ✅ **identique** |
| Croix de fermeture et 1ʳᵉ entrée inaccessibles après scroll | ✅ **identique** |
| Desktop : nav sorti à y = −10 pendant que la barre territoire est encore dans le flux | ✅ **identique** (mesuré y = −10 à 260 px, y = −30 à 280 px) |
| Mobile : panneau 229 px → 101 px, masthead 136 → 0, contenu immobile (1ʳᵉ carte à y = 271) | ✅ **identique** |
| Cookie `as_territoire` posé 30 jours par `/explore/savoie/` | ✅ **identique** |
| Hub catégorie : le cookie trie mais ne filtre pas ; seul `?filtre2=` filtre | ✅ **identique** (volumes différents, catalogue mis à jour : 11 sans cookie → 8 avec cookie → **2** avec `?filtre2=savoie`) |
| `/tout-l-agenda/?filtre2=savoie` ne filtre pas | ✅ **identique** (50 avant, 50 après) |
| `?territoire=savoie` → HTTP 200 avec **0 octet** | ✅ **identique**, reproduit sur 2 catégories |
| 4 largeurs de vignette sur un même écran mobile | ✅ **identique** (90 / 110 / 150-155-165 / 330 px) |
| Ratio 4:3 et titres 15 px/600 partout | ✅ **identique** |
| **La section blanche vient de `:has()`, et un vieux navigateur voit un titre suivi de rien** | ❌ **FAUX — voir § 4** |

---

## 2. CORRECTIF 1 — Carrousel décalé au chargement
### ✅ à déployer en premier

### Ce qui est mesuré

Enregistrement image par image du chargement de `/`, `swiper.min.css` volontairement retardée de
3 s pour rendre la fenêtre du défaut observable de façon déterministe (sur une connexion rapide
elle dure quelques dizaines de millisecondes ; sur un téléphone en 4G moyenne, ~1 s) :

| Viewport | Instant | Conteneur `.jet-listing-grid__slider` | `.swiper-wrapper` | Image |
|---|---|---|---|---|
| 390 px | t = 1 035 ms | largeur **350** | largeur **370** *(calculée : `370px`)* | **350** |
| 390 px | t = 5 034 ms *(swiper.min.css arrivée)* | 350 | **350** | **330** |
| 1366 px | t = 98 ms | largeur **910** | largeur **930** | **910** |
| 1366 px | t = 3 106 ms *(swiper.min.css arrivée)* | 910 | **910** | **890** |

Marges mesurées pendant le défaut : `margin-left: 0px`, `margin-right: 0px`. **Débordement de
+20 px exactement, à droite, sur les deux viewports.**

### La cause, lue dans le fichier servi

`jet-engine/assets/css/frontend.css?ver=3.8.11.2`, téléchargé et lu aujourd'hui :

```css
.jet-listing-grid__items{ display:flex; flex-wrap:wrap; margin:0 -10px; width:calc(100% + 20px) }
.jet-listing-grid__items.swiper-wrapper{ flex-wrap:nowrap; --column-gap:0px!important;
  column-gap:0!important; gap:0!important; margin-left:0; margin-right:0 }
```

La seconde règle remet **les marges** à 0 et **oublie la largeur**. Le wrapper garde
`calc(100% + 20px)` sans le `-10px` de gauche qui la compensait : il déborde de 20 px à droite.
`swiper.min.css` (`.swiper-wrapper{ …; width:100%; … }`) répare — mais elle est chargée à l'offset
462 645, dans le corps de page.

Le conteneur étant en `overflow:hidden`, le visiteur voit une image trop grande et décalée à
droite, qui « se recale vers la gauche » quand la feuille arrive. **Mot pour mot la description de
Franck.**

### Le CSS, prêt à coller

```css
/* ═══ DÉBUT correctif carrousel — largeur du wrapper (2026-08-03) ═══ */
/* POURQUOI : jet-engine/frontend.css v3.8.11.2 pose
     .jet-listing-grid__items{ width:calc(100% + 20px); margin:0 -10px }
   puis, pour la variante slider :
     .jet-listing-grid__items.swiper-wrapper{ …; margin-left:0; margin-right:0 }
   — les marges négatives sont annulées, PAS la largeur. Le wrapper déborde donc
   de 20 px à droite jusqu'à l'arrivée de swiper.min.css, qui n'est chargée qu'à
   l'offset 462 645 du HTML (dans le corps de page, pas dans le head).
   MESURÉ le 2026-08-03 : wrapper 370 px dans un conteneur de 350 px en mobile
   390, 930 dans 910 en desktop 1366, pendant toute la première seconde d'un
   chargement 4G. On impose ici, dès le premier octet, la largeur que
   swiper.min.css finit de toute façon par imposer : aucun état nouveau n'est
   créé, on ne fait que supprimer un état transitoire faux. */
.jet-listing-grid__slider .jet-listing-grid__items.swiper-wrapper{
  width: 100% !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
/* ═══ FIN correctif carrousel ═══ */
```

### Résultat mesuré, même page, mêmes octets

| | Avant | Après |
|---|---|---|
| Mobile 390, dès t = 129 ms | wrapper **370** / conteneur 350, image **350** | wrapper **350** / conteneur 350, image **330** ✅ |
| Desktop 1366, dès t = 111 ms | wrapper **930** / conteneur 910, image **910** | wrapper **910** / conteneur 910, image **890** ✅ |
| Durée du débordement | 100 ms → arrivée de swiper.min.css | **aucune frame en débordement** ✅ |
| Après init de Swiper | wrapper 350, x = −330 (mobile) | **identique**, x = −330 ✅ |

Le dernier point est le plus important pour le risque : **après initialisation, Swiper pilote la
position par `transform`, pas par la largeur du wrapper.** Le correctif ne change rien à cet état.

### Où le poser, et pourquoi là

**Dans le snippet qui émet `<style id="cs-no-hide-empty-cols">`** (le diagnostic l'appelle #77,
priorité 999 — *numéro non vérifié faute d'accès admin*), **à la suite du bloc
« Anti-flash Swiper pre-init »**, qui traite déjà exactement le même instant de vie du carrousel.
Les deux règles se relisent alors ensemble.

Trois raisons mesurées :

1. Ce bloc est **le dernier `<style>` du `<head>`** (offset 106 805) : il est présent dès le premier
   rendu, avant toute feuille externe du corps de page.
2. Il est émis **après** `jet-engine/frontend.css` (offset 86 870) : la règle gagne la cascade.
   *Mesure complémentaire : la variante **sans `!important`** fonctionne aussi depuis cette
   position (wrapper 350/350 dès t = 164 ms). Le `!important` est conservé pour que le correctif
   survive à un changement de priorité ou d'ordre des snippets.*
3. **Ne pas le mettre dans le CSS additionnel du thème** (`generatepress-child/style.css`,
   offset 95 990) : c'est un fichier externe, qui peut arriver après le premier rendu — le
   correctif serait en retard sur le problème qu'il corrige.

> ⚠️ Le mettre dans `cs-composants-styles` fonctionnerait aussi (grâce au `!important`), mais c'est
> le bloc de 71 Ko en retard de 40 Ko sur le dépôt : moins on y touche, mieux c'est.

### Le sélecteur est-il le plus étroit possible ? — vérifié, pas supposé

`.jet-listing-grid__slider .jet-listing-grid__items.swiper-wrapper` exige **trois conditions
simultanées** : être un conteneur d'items JetEngine, porter la classe `swiper-wrapper`, et être
descendant d'un slider JetEngine.

Recensement de **tous** les éléments correspondants sur le site (comptage dans le HTML servi, pas
dans le CSS) :

| Page | `div.jet-listing-grid__items…swiper-wrapper` |
|---|---|
| `/` | **2** (carrousel mobile n° 1721, carrousel desktop n° 1722) |
| `/explore/savoie/`, `/explore/comte-de-nice/` | 2 |
| `/it/home-it/` | 2 |
| `/choisir/piemont/`, `/choisir/vallee-d-aoste/` | **0** (le listing « sélections » est vide pour ces territoires) |
| `/tout-l-agenda/`, `/ce-week-end/` | **0** |
| `/evenements/categorie/*`, `/type-de-lieu/*` | **0** |
| fiche `/evenement/…` | **0** |

**Le correctif touche donc au maximum deux éléments par page, et uniquement sur les home.** Les
« 11 à 17 occurrences de `jet-listing-grid__slider` » que donne un `grep` brut sur ces pages sont du
**texte CSS** (les règles du snippet #77 et du snippet composants), pas des éléments — c'est un piège
de comptage, il est signalé ici pour qu'il ne reserve pas.

### Comment vérifier que ça a marché — protocole exact, sans rien écrire

1. Chrome, ouvrir `https://agendasabauda.eu/`, DevTools (F12), mode appareil, **largeur 390 px**.
2. Onglet **Réseau** → recharger → repérer la ligne `swiper.min.css` → **clic droit → « Bloquer
   l'URL de la requête »** (`Block request URL`). Recharger.
   *Cela fige indéfiniment l'état transitoire fautif : plus besoin de brider le réseau.*
3. Console, coller (lecture seule) :

   ```js
   document.querySelectorAll('.jet-listing-grid__slider').forEach(c => {
     const w = c.querySelector('.jet-listing-grid__items');
     const a = Math.round(c.getBoundingClientRect().width);
     const b = Math.round(w.getBoundingClientRect().width);
     if (a) console.log('conteneur', a, '| wrapper', b, '| écart', b - a);
   });
   ```

   **Avant le correctif : `conteneur 350 | wrapper 370 | écart 20`.**
   **Après le correctif : `conteneur 350 | wrapper 350 | écart 0`.**
4. Répéter en 1366 px : `910 / 930 / 20` avant, `910 / 910 / 0` après.
5. Retirer le blocage réseau, recharger, faire défiler le carrousel à la main sur mobile et desktop :
   le défilement, les points de pagination et la hauteur doivent être inchangés.

### Comment annuler en trente secondes

Code Snippets → le snippet `cs-no-hide-empty-cols` → sélectionner **tout ce qui est entre
`/* ═══ DÉBUT correctif carrousel` et `/* ═══ FIN correctif carrousel ═══ */`** → supprimer →
Enregistrer. Le reste du snippet n'est pas touché.
*Repli plus radical si le snippet entier pose problème : le désactiver (interrupteur) — mais
attention, cela emporte aussi l'anti-flash Swiper et les colonnes mobiles.*

### Risque de régression — nommé et vérifié

- **Autres carrousels du site :** il n'y en a pas d'autres. Recensement exhaustif ci-dessus :
  2 éléments, sur les home uniquement.
- **Grilles JetEngine non-carrousel** (toutes les listes de `#ala-une`, `#weekend`, `#jour`,
  `#nouveautes`, `#evidence`, `#venir`, les hubs) : **hors périmètre**, elles n'ont pas la classe
  `swiper-wrapper`. Leur `width: calc(100% + 20px)` avec `margin: 0 -10px` reste intact — c'est le
  fonctionnement normal de la gouttière JetEngine, et le correctif ne le touche pas.
- **Après initialisation de Swiper :** mesuré identique avec et sans correctif.
- **Anti-flash existant du snippet #77** (`.jet-listing-grid__slider.swiper:not(.swiper-initialized)
  .jet-listing-grid__item{ flex:0 0 100%!important; width:100%!important }`) : il cible les
  **items**, le correctif cible le **wrapper**. Aucune collision.

**Risque résiduel : très faible.** Le correctif impose une valeur que le navigateur finit de toute
façon par appliquer, sur deux éléments identifiés.

---

## 3. CORRECTIF 2 — Menu mobile recouvert par le header
### ✅ à déployer en second

### Ce qui est mesuré

Home mobile 390 px, défilement de 600 px, ouverture réelle du menu (bascule de la case
`.as-menu-toggle`) :

```
.as-menu-overlay       → position:fixed, z-index: 40, rect [0, 0, 390, 844], 24 liens
.as-home-sticky-panel  → position:fixed, z-index: 41, y = 0, hauteur = 101 px
elementFromPoint(195, y) pour y = 10, 30, 50, 80, 101  → un DIV du header, HORS de l'overlay
elementFromPoint(195, y) pour y = 110, 150             → un lien A, DANS l'overlay
croix de fermeture      → rect [350, 16, 20, 20], cliquable : NON (interceptée par le header)
1re entrée « Aujourd'hui » → y = 62, cliquable : NON
```

**Les 101 premiers pixels du menu ouvert sont recouverts. La croix de fermeture est inaccessible.**
Le visiteur qui ouvre le menu après avoir fait défiler la page ne peut plus le refermer autrement
qu'en rechargeant ou en utilisant le bouton retour.

### Le défaut est-il partout ? — non, et c'est vérifié

| Famille de pages | Panneau ouvert | z-index | Header concurrent | Croix cliquable |
|---|---|---|---|---|
| Home (`/`, `/explore/*`, `/choisir/*`, `/it/home-it/`) | `.as-menu-overlay` | **40** | `.as-home-sticky-panel` **41** | ❌ **non** |
| Pages internes (`/evenements/categorie/*`, `/type-de-lieu/*`) | `.as-site-header__mobile-menu` | **50** | `.as-site-header` 40 | ✅ oui |

**Le bug est strictement limité aux home.** Les pages internes sont saines (mesuré sur deux pages) :
inutile d'y toucher.

### Le CSS, prêt à coller

```css
/* ═══ DÉBUT correctif menu mobile — z-index de l'overlay (2026-08-03) ═══ */
/* POURQUOI : sur la home, le panneau de header devient position:fixed au-delà
   d'un seuil de défilement, avec z-index:41 et 101 px de haut
   (.as-home-sticky-panel, réglé dans cs-composants-styles). L'overlay de menu,
   lui, est à z-index:40 — il s'ouvre DERRIÈRE. MESURÉ le 2026-08-03, home
   mobile 390 px après 600 px de défilement : elementFromPoint(195, 30) renvoie
   un DIV du header, la croix de fermeture (rect 350,16,20,20) n'est pas
   cliquable, et la 1re entrée « Aujourd'hui » (y = 62) non plus.
   Un panneau ouvert passe DEVANT le chrome de page, jamais dessous.
   60 et non 42 : ça laisse la place au dropdown territoire (z-index 95, mais
   enfermé dans le contexte d'empilement du panneau, donc sans effet ici) et ça
   reste très loin sous le bandeau cookies Complianz (z-index 99 999), qui doit
   rester prioritaire. */
.as-menu-overlay{ z-index: 60 !important; }
/* ═══ FIN correctif menu mobile ═══ */
```

### Résultat mesuré, même page, mêmes octets

| | Avant | Après |
|---|---|---|
| `z-index` de l'overlay | 40 | **60** |
| `elementFromPoint(195, 10 / 30 / 50 / 80 / 101)` | header, **hors overlay** | **dans l'overlay** ✅ |
| Croix de fermeture cliquable | **non** | **oui** (elle reçoit bien le `<line>` du SVG) ✅ |
| 1ʳᵉ entrée « Aujourd'hui » cliquable | **non** | **oui** ✅ |
| Menu **fermé** : l'overlay intercepte-t-il des clics ? | non | **non** (rect x = 390, hors écran ; 5 points sondés, aucun ne tombe dedans) ✅ |
| Largeur de défilement du document, menu fermé | 390 = 390 | **390 = 390**, pas de débordement horizontal créé ✅ |
| Bandeau cookies Complianz | z-index 99 999, au-dessus | **inchangé, toujours au-dessus** ✅ |

La ligne « menu fermé » est celle qui répondait au vrai risque de ce correctif : monter le `z-index`
d'un élément `position:fixed; inset:0` peut le faire intercepter tous les clics de la page. **Ce
n'est pas le cas** : l'overlay fermé est translaté hors écran (`translateX(100%)`, x = 390), et les
cinq points sondés (dont le bord droit, x = 389) tombent sur le contenu de la page.

### Où le poser, et pourquoi là

**Dans le snippet qui émet `<style id="cs-hdr-compact">`** (le diagnostic l'appelle #62 — *numéro non
vérifié*), **à la fin**, à la suite des règles `.as-menu-overlay .as-site-header__menu{…}` qui s'y
trouvent déjà.

> 📌 **Correction au diagnostic du 1ᵉʳ août.** Il dit de poser ce correctif dans #62 « juste à côté
> de la règle qui pose `z-index:41` sur `.as-home-sticky-panel` ». **Cette règle n'est pas dans
> #62** : elle est à la ligne 731 de `cs-composants-styles`
> (`.as-home-sticky-panel { position: static; z-index: 41; background: #FBF7F0; }`). #62 reste
> néanmoins le bon endroit, mais pour une autre raison : **c'est déjà lui qui rattrape le menu
> overlay** (il contient `.as-menu-overlay .as-site-header__menu{ display:block !important }` et
> quatre autres règles `.as-menu-overlay …`). Tout ce qui concerne ce panneau est donc au même
> endroit.

Vérification de cascade : `cs-hdr-compact` est émis à l'offset 99 314, `cs-composants-styles` à
10 660. Le correctif gagne donc **même sans `!important`** ; le `!important` est gardé pour
survivre à un réordonnancement.

### Comment vérifier que ça a marché

1. Chrome, `https://agendasabauda.eu/`, DevTools, mode appareil, **390 px**.
2. Faire défiler de ~600 px (le header doit être devenu compact et collé en haut).
3. Ouvrir le menu (hamburger).
4. Console, coller :

   ```js
   const o = document.querySelector('.as-menu-overlay');
   const e = document.elementFromPoint(195, 30);
   console.log('z-index :', getComputedStyle(o).zIndex,
               '| à y=30 :', e.tagName, o.contains(e) ? 'DANS le menu ✅' : 'HORS du menu ❌');
   ```

   **Avant : `z-index : 40 | à y=30 : DIV HORS du menu ❌`.**
   **Après : `z-index : 60 | à y=30 : DIV DANS le menu ✅`.**
5. **Test à la main, le seul qui compte vraiment :** cliquer la croix en haut à droite. Le menu doit
   se fermer. Faire l'essai sur un vrai téléphone.
6. **Contrôle de non-régression sur place :** menu fermé, vérifier que la page défile normalement et
   que les liens du haut de page restent cliquables ; puis vérifier que le bandeau cookies (s'il
   n'a pas encore été accepté) reste **au-dessus** du menu ouvert.

### Comment annuler en trente secondes

Code Snippets → snippet `cs-hdr-compact` → supprimer les lignes entre `/* ═══ DÉBUT correctif menu
mobile` et `/* ═══ FIN correctif menu mobile ═══ */` → Enregistrer.

### Risque de régression — nommé et vérifié

Inventaire de **tous** les `z-index ≥ 30` réellement appliqués sur la home mobile (relevé dans le
navigateur, sur les éléments existants, pas dans le CSS) :

| z-index | Élément | Passe-t-il sous l'overlay à 60 ? |
|---|---|---|
| 99 999 | `.cmplz-cookiebanner` (Complianz) | **non**, reste au-dessus — voulu |
| 99 999 | `ul.sub-menu` (sous-menus GeneratePress, `position:absolute`) | non, mais ils sont dans le header, donc enfermés dans son contexte d'empilement |
| 9 998 | `.cmplz-btn` (bouton « gérer le consentement ») | non, reste au-dessus |
| 95 | `.as-terr-dropdown` | **enfermé dans `.as-home-sticky-panel`** (z-index 41, `position:fixed` → contexte d'empilement). Il passe donc bien sous l'overlay. |
| 50 | `.as-site-header__mobile-menu` | oui — sans effet : les deux panneaux ne coexistent jamais (l'un est sur les home, l'autre sur les pages internes) |
| 41 | `.as-home-sticky-panel` | **oui — c'est le but** |
| 40 | `.as-site-header`, `.as-desktop-sticky-ad` | oui |
| 30 | `.as-sticky-ad`, `.as-home-desktop__nav` | oui |

**Un seul élément change de position relative : le panneau de header, qui passe derrière le menu
ouvert.** C'est précisément l'effet recherché. **Risque : très faible.**

> 🔗 **Dépendance à retenir.** Si le correctif « header unifié » (§ 6, bug 2b du diagnostic) est un
> jour déployé, le panneau devient `fixed` **en permanence** — le recouvrement ne se produirait plus
> seulement après défilement mais **dès le chargement**. Ce correctif-ci en est alors un
> **prérequis**, pas une option.

---

## 4. CORRECTIF 3 — Territoire transmis aux hubs (voie B, JS)
### ✅ déployable, validé de bout en bout

### Ce qui est mesuré (revérifié aujourd'hui)

1. `/explore/savoie/` pose bien `set-cookie: as_territoire=savoie; Max-Age=2592000; path=/`.
2. Sur `/evenements/categorie/jeune-public-famille/`, nombre d'événements **uniques** :

   | Requête | Événements | `<option value="savoie">` |
   |---|---|---|
   | sans cookie | **11** | non sélectionné |
   | avec `Cookie: as_territoire=savoie` | **8** *(tous territoires confondus)* | **non sélectionné** |
   | `?filtre2=savoie` | **2** *(Savoie uniquement)* | **`selected='selected'`** |
   | `?filtre2=comte-de-nice` | 6 | — |

   Sur `/type-de-lieu/musee/` : 8 sans filtre, **1** avec `?filtre2=savoie`.
3. **Le cookie trie et raccourcit, il ne filtre pas.** Le visiteur qui a choisi la Savoie reçoit du
   Comté de Nice et de la Vallée d'Aoste. **La plainte de Franck est exacte.**
4. `/tout-l-agenda/?filtre2=savoie` : **50 événements avant, 50 après** — cette page ignore
   `filtre2`. Le correctif ne doit pas toucher ce lien.

### Le JS, prêt à coller

```js
/* ═══ DÉBUT correctif territoire → hubs (2026-08-03) ═══ */
/* POURQUOI : le hub catégorie LIT le cookie as_territoire, mais il ne s'en sert
   que pour TRIER et raccourcir la liste (11 → 8 événements, tous territoires
   confondus). Le seul mécanisme qui FILTRE réellement est le paramètre GET
   ?filtre2=<slug> (11 → 2, Savoie uniquement — mesuré le 2026-08-03). On ajoute
   donc ce paramètre aux liens sortants vers les hubs, depuis les pages de
   territoire (et, à défaut, depuis le cookie).
   VOLONTAIREMENT PAS /tout-l-agenda/ NI /ce-week-end/ : ces deux pages ignorent
   filtre2 (50 événements avant comme après), le paramètre y serait un mensonge.
   NE JAMAIS UTILISER ?territoire= À LA PLACE : c'est le nom de la taxonomie, et
   /evenements/categorie/<x>/?territoire=savoie répond HTTP 200 avec 0 octet
   (page totalement blanche, reproduit sur 2 catégories le 2026-08-03). */
(function () {
  var TERR = ['savoie', 'piemont', 'vallee-d-aoste', 'comte-de-nice'];
  var m = location.pathname.match(/\/(?:explore|choisir|territoire)\/([a-z0-9-]+)\/?$/);
  var slug = m && TERR.indexOf(m[1]) !== -1 ? m[1] : null;

  /* repli : hors home de territoire, on relit le choix mémorisé dans le cookie */
  if (!slug) {
    var c = document.cookie.match(/(?:^|;\s*)as_territoire=([a-z0-9-]+)/);
    if (c && TERR.indexOf(c[1]) !== -1) { slug = c[1]; }
  }
  if (!slug) { return; }

  document.querySelectorAll('a[href*="/evenements/categorie/"], a[href*="/type-de-lieu/"]')
    .forEach(function (a) {
      var u;
      try { u = new URL(a.href, location.origin); } catch (e) { return; }
      if (u.origin !== location.origin) { return; }   /* jamais un lien externe */
      if (u.searchParams.has('filtre2')) { return; }  /* jamais écraser un choix explicite */
      u.searchParams.set('filtre2', slug);
      a.href = u.toString();
    });
})();
/* ═══ FIN correctif territoire → hubs ═══ */
```

### Résultat mesuré, de bout en bout, sur `/explore/savoie/`

| | Avant | Après |
|---|---|---|
| Liens vers `/evenements/categorie/` ou `/type-de-lieu/` sur la page | 78 | 78 |
| … dont porteurs de `filtre2` | **0** | **78** ✅ |
| Liens `/tout-l-agenda/` et `/ce-week-end/` modifiés | 0 | **0** ✅ |
| Autres liens du site ayant reçu un `filtre2` (fuite) | 0 | **0** ✅ |
| **Navigation réelle sur la 1ʳᵉ tuile (« Cinéma »)** | `/…/cinema/` → **5 événements**, `<select filtre2>` vide | `/…/cinema/?filtre2=savoie` → **2 événements**, `<select filtre2>` = **`savoie`** ✅ |

Le `<select>` de la barre de filtres se positionne tout seul sur « Savoie » : le visiteur **voit**
le filtre qui s'applique, et peut le retirer.

### Où le poser, et pourquoi là

**Dans un NOUVEAU snippet Code Snippets**, de type JavaScript, portée « Site front-end », émis en
pied de page (`wp_footer`) — les tuiles doivent être dans le DOM au moment de l'exécution.

Un snippet à part, et pas un ajout à un snippet existant, pour une seule raison : **c'est le seul
correctif du lot qui change le comportement de navigation.** Le mettre seul permet de l'éteindre
d'un clic sans rien emporter d'autre.

### Comment vérifier que ça a marché

1. Ouvrir `https://agendasabauda.eu/explore/savoie/`.
2. Console, coller :

   ```js
   const a = [...document.querySelectorAll('a[href*="/evenements/categorie/"], a[href*="/type-de-lieu/"]')];
   console.log(a.filter(x => x.href.includes('filtre2=')).length + ' / ' + a.length + ' liens réécrits');
   console.log('tout-l-agenda touché ?',
     [...document.querySelectorAll('a[href*="tout-l-agenda"], a[href*="ce-week-end"]')]
       .some(x => x.href.includes('filtre2=')) ? 'OUI ❌' : 'non ✅');
   ```

   **Avant : `0 / 78`. Après : `78 / 78`, et `tout-l-agenda touché ? non ✅`.**
3. **Le test qui compte :** cliquer une tuile catégorie. Sur la page d'arrivée, la liste déroulante
   « Territoire » doit afficher **Savoie**, et la liste ne doit contenir **que** des événements de
   Savoie. Compter à l'œil, ou :

   ```js
   console.log([...new Set([...document.querySelectorAll('a[href*="/evenement/"]')]
     .map(a => a.getAttribute('href')))].length + ' événements');
   ```
4. **Contrôle de l'échappatoire :** depuis la page d'arrivée, remettre la liste « Territoire » sur
   « Territoire » et cliquer « Appliquer » → tous les territoires doivent revenir.

### Comment annuler en trente secondes

Code Snippets → le snippet → **interrupteur sur « Désactivé »**. Un clic, effet immédiat sur la
requête suivante. C'est le correctif le plus facile à annuler du lot.

### Risque de régression — nommé et vérifié

- **Portée :** deux familles d'URL seulement (`/evenements/categorie/`, `/type-de-lieu/`), et
  uniquement des liens de même origine (`u.origin !== location.origin` → sortie). Vérifié : 0 fuite
  sur les autres liens de la page.
- **N'écrase jamais un choix explicite :** `if (u.searchParams.has('filtre2')) return;`.
- **`/tout-l-agenda/` et `/ce-week-end/` :** hors sélecteur, vérifié à 0.
- **SEO :** les URL filtrées portent un `<link rel="canonical">` vers l'URL **sans paramètre**
  (vérifié par téléchargement : `/…/cinema/?filtre2=savoie` → canonical `/…/cinema/`). Le
  `robots.txt` n'interdit rien, donc un robot exécutant JS peut suivre ces liens — mais la
  canonique consolide. Risque faible, non nul : à surveiller dans la Search Console
  (« pages non indexées → autre page avec balise canonique correcte »).
- **Ce que ce correctif ne fait pas :** il ne mémorise rien de nouveau et ne touche à aucun cookie.
  Un visiteur qui arrive par Google directement sur `/evenements/categorie/concerts-musique/` avec
  un vieux cookie `as_territoire` vieux de trois semaines **verra sa liste filtrée**, à cause du
  repli sur cookie. **C'est un arbitrage, pas un effet secondaire :** si Franck ne le veut pas,
  supprimer les cinq lignes du bloc « repli » — le correctif ne marchera plus que depuis
  `/explore/*` et `/choisir/*`, ce qui couvre le scénario exact qu'il a décrit.

> 🐛 **À ouvrir comme issue séparée (revérifié aujourd'hui, toujours vrai) :**
> `/evenements/categorie/<n'importe laquelle>/?territoire=savoie` répond **HTTP 200 avec 0 octet**.
> Reproduit sur `jeune-public-famille` et `concerts-musique`. Pour comparaison, sur la même URL :
> `?zzz=1` et `?utm_source=test` → 357 692 octets normaux ; `?territoire=nimportequoi` → 404 propre
> de 335 266 octets. C'est une URL publique qui renvoie une réponse vide en 200 — une erreur douce
> indexable. Sans rapport avec les correctifs ci-dessus, mais à ne pas perdre.

---

## 5. CORRECTIF 4 — Section blanche / `:has()`
### ⚠️ le correctif du diagnostic ne fait PAS ce qu'il annonce — ne pas le déployer tel quel

C'est la seule conclusion du 1ᵉʳ août que ces mesures **infirment**. Elle mérite d'être lue en
entier avant toute décision.

### Ce que dit le diagnostic

> « Sur un navigateur sans `:has()` (Safari < 15.4, Chrome < 105, Firefox < 121), la règle est
> ignorée en silence : le titre "Les 7 prochains jours" du bloc desktop reste visible AVEC sa grille
> masquée, soit une section blanche. »

Et il propose de **remplacer** la règle à `:has()` par une règle sans `:has()`.

### Ce qui est réellement mesuré

Le masquage ne repose pas sur **une** règle `:has()` mais sur **deux, qui vont en sens contraire** :

| Règle | Bloc | Effet |
|---|---|---|
| `.as-home-desktop:has(> .as-desktop-cols3){ display:block !important }` | `cs-no-hide-empty-cols` (#77) | **RÉVÈLE** le conteneur desktop sur mobile (sans elle, il reste `display:none`) |
| `@media (max-width:899px){ .as-home-desktop:has(> .as-desktop-cols3) > *:not(.as-desktop-cols3){ display:none !important } }` | `cs-composants-styles` | **MASQUE** ses doublons |

Or la règle de base, ligne 440 de `cs-composants-styles`, est
`.as-home-desktop { display: none; }` — le conteneur desktop est **invisible par défaut sous
900 px**. C'est la première règle `:has()` qui le fait apparaître.

**Émulation d'un navigateur sans `:has()`** — on retire du CSSOM **toutes** les règles dont le
sélecteur contient `:has()` (15 règles), ce qu'un vieux moteur fait à la lecture :

| | Navigateur récent (référence) | **Sans `:has()`** |
|---|---|---|
| Conteneur desktop | `display:block`, 6 810 px | **`display:none`, 0 px** |
| Section « Nouveautés » | visible | **absente** |
| Section « En évidence » | visible | **absente** |
| Section « L'agenda à venir » | visible | **absente** |
| Titre « Les 7 prochains jours » | 1 fois, visible (rail mobile) | **1 fois, visible** — pas de doublon |
| Hauteur totale de la home mobile | **10 928 px** | **4 118 px (−62 %)** |

**Il n'y a donc pas de section blanche chez ces visiteurs. Il y a un tiers de la page qui manque.**
Le diagnostic avait produit la section blanche en retirant **seulement** la règle qui masque, en
laissant en place celle qui révèle : un état artificiel dans lequel aucun navigateur réel ne se
trouve.

### Et le correctif proposé ? — mesuré, il ne répare rien

Le CSS proposé le 1ᵉʳ août, appliqué dans les deux mondes :

| | Navigateur récent | Sans `:has()` |
|---|---|---|
| Sans le correctif | 10 928 px, tout correct | 4 118 px, 3 sections absentes |
| **Avec le correctif du diagnostic** | 10 954 px (**+26 px** : trois `<p>` vides et un `<p>` sans classe réapparaissent, non couverts par `div:not([class])`) | **4 118 px — strictement rien ne change** ❌ |

Il ne répare pas le cas ancien (la règle qui *révèle* utilise elle aussi `:has()`, et tombe aussi) et
il ajoute 26 px de vide dans le cas courant. **À ne pas déployer.**

### Le candidat corrigé, si Franck veut couvrir les vieux navigateurs

```css
/* ═══ DÉBUT repli sans :has() — bas de home mobile (2026-08-03) ═══ */
/* POURQUOI : l'affichage du bas de la home mobile (Nouveautés / En évidence /
   L'agenda à venir) repose sur DEUX règles :has() — l'une révèle le conteneur
   desktop sous 900 px, l'autre masque ses doublons. Un navigateur sans :has()
   (Safari < 15.4, Chrome < 105, Firefox < 121) rejette les deux : le conteneur
   reste display:none et ces trois sections DISPARAISSENT. Mesuré le 2026-08-03
   par émulation : la home mobile tombe de 10 928 px à 4 118 px.
   @supports garantit que ce bloc est TOTALEMENT INERTE sur un navigateur
   récent : il ne s'applique que là où :has() n'existe pas. */
@supports not selector(:has(*)) {
  @media (max-width: 899px) {
    .as-home-root > .as-home-desktop{
      display: block !important; max-width: 480px !important;
      margin-left: auto !important; margin-right: auto !important;
    }
    .as-home-root > .as-home-desktop > *{ display: none !important; }
    .as-home-root > .as-home-desktop > .as-desktop-cols3{ display: grid !important; }
  }
}
/* ═══ FIN repli sans :has() ═══ */
```

**Mesures de ce candidat :**

| | Navigateur récent | Sans `:has()` |
|---|---|---|
| Sans le candidat | 10 928 px ✅ | 4 118 px, 3 sections absentes ❌ |
| **Avec le candidat** | **10 928 px, aucun pixel de différence** ✅ | **10 928 px, les 3 sections reviennent, un seul titre « 7 prochains jours »** ✅ |

L'inertie sur navigateur récent est vérifiée deux fois : `CSS.supports('not selector(:has(*))')`
renvoie `false`, et l'injection du bloc ne change **aucune** des valeurs relevées (hauteur de page,
`display` et hauteur des 5 conteneurs `.as-home-root > .as-home-desktop`).

**Où le poser :** dans le snippet `cs-composants-styles`, **en ajout à la fin**, à la suite du bloc
« Doublons desktop sur mobile » — surtout **pas en remplacement** de ce bloc, qui reste la règle
active pour 98 % des visiteurs.

**Comment vérifier :** c'est le point faible de ce correctif. `@supports not selector(:has(*))` est
faux sur tout navigateur moderne, donc **on ne peut pas le vérifier depuis un poste à jour**. Deux
protocoles possibles, à la charge de Franck :

- **Contrôle négatif (30 s, faisable tout de suite) :** après pose, ouvrir la home mobile 390 px et
  vérifier que `document.documentElement.scrollHeight` vaut toujours **10 928** (± la variation du
  catalogue) et que rien n'a bougé à l'œil. C'est ce que garantit `@supports` ; c'est ce qu'il faut
  confirmer.
- **Contrôle positif :** un vrai Safari 15.0–15.3 ou Chrome 90–104. En pratique : BrowserStack,
  ou un vieil iPad/iPhone bloqué sur iOS 15.0–15.3. Sans ça, **le bénéfice reste théorique** — je
  le dis franchement plutôt que de l'affirmer.

**Comment annuler :** supprimer le bloc entre les marqueurs. Comme il est inerte sur navigateur
récent, son retrait n'a par construction aucun effet visible sur un poste à jour.

**Risque : très faible mais non nul.** Le sélecteur `.as-home-root > .as-home-desktop` correspond à
**5 éléments** (vérifié), pas un seul — les quatre autres sont `display:none` par défaut sous 900 px
et le restent puisque `> *{display:none}` masque tous leurs enfants ; mesuré : hauteur de page
inchangée au pixel. La parade durable reste celle que proposait le diagnostic, et elle est bonne :
**donner une classe explicite** (par ex. `as-desktop-only`) à ces blocs dans l'éditeur Gutenberg de
la page 928, et masquer `.as-desktop-only` sous 900 px. Plus aucun `:has()`, plus aucun sélecteur
acrobatique.

**Question à trancher avant de déployer quoi que ce soit ici : combien de visiteurs sont concernés ?**
`:has()` est disponible depuis mars 2022 (Safari 15.4), août 2022 (Chrome 105) et décembre 2023
(Firefox 121). En août 2026, la part de trafic concernée est probablement de l'ordre de 1 %.
**Cette proportion est vérifiable dans les statistiques du site ; je ne l'ai pas.** C'est elle qui
doit décider, pas ce document.

---

## 6. Ce qui n'est PAS prêt à coller

### Bug 4 — Uniformisation des tuiles : diagnostic confirmé, correctif = choix de design

Mesure refaite aujourd'hui, home mobile 390 px, après déclenchement complet du lazy-loading :

| Section | Classe de vignette | Dimensions |
|---|---|---|
| `#ala-une` | `.ala-une-card__image.cs-card-thumb` | **165** × 124 |
| `#jour` | idem | **150** × 113 |
| `#cat-concerts`, `#cat-expositions`, `#cat-gastronomie` | idem | **155** × 116 |
| « Ça vaut le déplacement » | `.cs-cvld-thumb` | **110** × 83 |
| `#nouveautes`, `#venir`, `#venir-bottom` | `.venir-row__image.cs-card-thumb` | **90** × 68 |
| `#evidence`, `#evidence-bottom` | `.evidence-card__image.cs-card-thumb` | **330** × 248 |

**Confirmé :** ratio 4:3 partout, titres 15 px/600 partout — le travail d'unification a pris. Il
reste **quatre gabarits de largeur** sur un même écran.

Le CSS proposé par le diagnostic est cohérent avec ces mesures, **mais son résultat est un choix
esthétique** : passer « Nouveautés » de 90 px à pleine largeur allonge la home mobile de plusieurs
centaines de pixels. Je ne le reprends pas ici comme « prêt à coller » parce que **je ne peux pas
valider un arbitrage de design par une mesure.** À reprendre quand Franck peut regarder le résultat.

### Bug 2b — Header unifié initial/scrollé : diagnostic confirmé, correctif hors périmètre

Mesures refaites, identiques au 1ᵉʳ août :

```
DESKTOP 1366   scroll=240  nav sticky y=+10   | barre territoire static y=59
               scroll=260  nav sticky y=−10   | barre territoire static y=39   ← désynchronisation
               scroll=280  nav sticky y=−30   | barre territoire static y=19
               scroll=300  nav FIXED  y=0     | barre territoire FIXED y=49    ← les deux ressautent
MOBILE 390     scroll=0    panneau static, hauteur 229, masthead 136
               scroll=300  panneau fixed,  hauteur 101, masthead 0
               (1re carte à y=271 avant comme après : la cale JS fait son travail)
```

Le correctif proposé **déplace un nœud du DOM en JavaScript** et remplace un bloc de script
existant. Ce n'est ni un ajout autonome ni quelque chose que je peux valider sans écrire en
production et regarder trois viewports à l'œil. **À traiter en dernier, avec Franck devant
l'écran**, et après le correctif menu (§ 3), qui en est le prérequis.

---

## 7. Classement bénéfice / risque

| Rang | Correctif | Bénéfice | Risque | Effort | Réversibilité |
|---|---|---|---|---|---|
| **1** | **Carrousel (+20 px)** — § 2 | Élimine un défaut visible **à chaque chargement de la home**, sur mobile et desktop, mesuré à +20 px pendant ~1 s en 4G. C'est le premier écran du site. | **très faible** : 3 déclarations, 2 éléments recensés sur tout le site, valeur identique à celle que le navigateur applique de toute façon | 5 min | supprimer un bloc balisé |
| **2** | **Menu mobile (z-index)** — § 3 | Répare une **impasse de navigation** : croix de fermeture inaccessible après défilement. Une ligne. | **très faible** : 1 élément, 1 déclaration ; inventaire complet des z-index fait ; menu fermé vérifié sans effet | 5 min | supprimer une ligne |
| **3** | **Territoire → hubs (JS)** — § 4 | Le seul bug **fonctionnel** du lot : le visiteur qui choisit la Savoie reçoit du Piémont. Validé de bout en bout (11 → 2 événements). | **faible** : 78 liens réécrits, 0 fuite, canonique vérifiée ; un arbitrage à confirmer (repli sur cookie) | 15 min | **désactiver le snippet, 1 clic** |
| **4** | **Repli sans `:has()`** — § 5 | Rend le bas de la home visible aux ~1 % de visiteurs sur navigateur ancien. Inerte ailleurs, mesuré. | **très faible** mais **bénéfice non vérifiable** sans un vrai vieux navigateur | 10 min | supprimer un bloc balisé |
| **5** | Uniformisation des tuiles — § 6 | Cohérence visuelle. | faible à modéré, **et c'est un choix de design** | 20 min + validation à l'œil | — |
| **6** | Header unifié — § 6 | Supprime la saccade du premier écran. | **moyen — le plus élevé** : déplacement d'un nœud du DOM, toutes les home | 45 min + validation | — |

### À déployer en premier : **le correctif carrousel (§ 2).**

Trois raisons : la cause est lue dans le fichier fautif et l'effet est chiffré avant/après sur deux
viewports ; le périmètre est exhaustivement recensé (deux éléments sur tout le site) ; et le
correctif impose une valeur que le navigateur finit de toute façon par appliquer une seconde plus
tard — il ne crée aucun état qui n'existe pas déjà.

**Puis le menu (§ 3), qui est une ligne et répare une impasse.** Les deux peuvent partir ensemble :
ils ne touchent ni les mêmes snippets, ni les mêmes sélecteurs, ni les mêmes pages.

---

## 8. Ce qui reste à faire trancher par Franck

1. **§ 4 — repli sur cookie ?** Un visiteur arrivé par Google sur « Concerts » avec un cookie
   `as_territoire` vieux de trois semaines doit-il voir sa liste filtrée sur ce territoire ?
   *Mon avis : non.* Si Franck est d'accord, supprimer les cinq lignes du bloc « repli » : le
   correctif ne s'appliquera plus que depuis `/explore/*` et `/choisir/*`.
2. **§ 4 — voie A (PHP) plus tard ?** Faire lire le cookie par défaut à `filtre2` côté serveur est
   plus propre et couvre tous les liens entrants, mais rend le contenu du hub dépendant d'un cookie :
   **il faut d'abord savoir si l'hébergeur sert du cache anonyme sur ces pages.** Non testé.
3. **§ 5 — quelle part du trafic n'a pas `:has()` ?** Cette proportion, lisible dans les statistiques
   du site, décide si le correctif 4 vaut la peine.
4. **§ 6 — tuiles :** « Nouveautés » seule, ou « Nouveautés » + « L'agenda à venir » ? À moitié =
   un gabarit de plus, pas un de moins.
5. **`?territoire=` → page blanche en HTTP 200.** Toujours reproductible. À ouvrir comme issue
   séparée (erreur douce indexable).
6. **Dette de dépôt (issue #9).** `cs-composants-styles` est passé de 70 875 à **71 235 caractères**
   en deux jours pendant que `wordpress/design-system/components.css` reste à 31 Ko.
   **Resynchroniser production → dépôt** avant toute idée de lancer `apply-components.mjs`.

---

## Note de traçabilité

Aucune écriture sur le site : ni snippet créé, modifié ou activé, ni PHP exécuté, ni appel
d'écriture WordPress. Tous les correctifs ont été éprouvés **dans un navigateur local**, en injectant
le CSS/JS candidat dans une copie de la page servie, jamais dans la page réelle.

Dans le dépôt, **ce fichier est le seul écrit**. Aucun `git add`, `git commit` ni `git push`.
