# Sortir de `:has()` — bas de la home mobile

**Date des mesures : 2026-08-03, 07 h 05 – 08 h 00 UTC.**
**Périmètre : préparation et vérification. Rien n'a été écrit sur le site. Aucun snippet créé,
modifié ou activé. Aucune page ni aucun bloc Gutenberg touché. Aucun appel d'écriture WordPress.
Le déploiement est la décision de Franck.**

Ce document répond aux deux questions laissées ouvertes par
`docs/CORRECTIFS_CSS_PRETS.md` § 5 :

- **Volet A** — « combien de visiteurs n'ont pas `:has()` ? » → où Franck peut lire ce chiffre.
- **Volet B** — la parade durable annoncée en fin de § 5 : **une classe explicite, plus aucun
  `:has()`**. Conçue, chiffrée, et mesurée dans les trois états.

**Conclusion en une ligne : le volet B rend le volet A sans objet, et il est le seul des deux
correctifs qui soit vérifiable depuis un poste à jour.**

---

## 1. VOLET A — combien de visiteurs sont concernés ?

### 1.1 Ce qui est réellement en place (mesuré sur la page servie)

Relevé sur le HTML de `/` téléchargé le 2026-08-03 (639 361 caractères) :

| Outil | Présent ? | Preuve |
|---|---|---|
| **Google Analytics 4** | ✅ **oui**, `G-HWRKPM4F7J` | `<script async data-category="functional" src="https://www.googletagmanager.com/gtag/js?id=G-HWRKPM4F7J">` à l'offset 543 810, puis `gtag('config', 'G-HWRKPM4F7J', …)` |
| Matomo | ❌ non | aucune occurrence |
| Plausible / Fathom / Umami | ❌ non | aucune occurrence |
| Jetpack Stats (`stats.wp.com`) | ❌ non | aucune occurrence |
| WP-Statistics / Burst / Independent Analytics / Slimstat | ❌ non | aucune occurrence |

Recensement des extensions qui émettent des ressources sur `/` (comptage des chemins
`wp-content/plugins/<nom>` dans le HTML servi) :

```
complianz-gdpr   elementor   jet-blocks   jet-elements   jet-engine
jet-menu   jet-popup   jet-smart-filters   jet-theme-core   jet-tricks
the-events-calendar
```

**Aucune extension de statistiques.** Le référencement est assuré par Yoast SEO (2 occurrences
`yoast` dans le HTML servi) — et non par RankMath, contrairement à ce qu'indique
`docs/MARKETING_ET_PILOTAGE_AGENDA_SABAUDO.md` ; il n'y a donc pas de module « RankMath
Analytics » à ouvrir.

### 1.2 Et les journaux serveur ? — non, pas par le dépôt

`nginx.conf`, à la racine du dépôt, **ne concerne pas agendasabauda.eu**. Son propre en-tête le
dit : le VPS est derrière **Traefik**, pas nginx, et le `server_name` du fichier est
`agenda.culturasabauda.eu` avec un `proxy_pass` vers `http://127.0.0.1:5001` — c'est le
**backoffice Flask** de la chaîne de collecte, pas le site public.

Le site WordPress, lui, répond (mesuré, en-têtes HTTP du 2026-08-03) :

```
server: Apache
x-powered-by: PHP/8.0
```

C'est un hébergement mutualisé distinct. Le dépôt mentionne un accès **FTP/SFTP OVH**
(`docs/TODO_LANCEMENT.md` l. 54, `wordpress/README.md` l. 17) — **supposé, non vérifié** : je n'ai
pas d'accès à l'espace client. **Rien dans ce dépôt ne sert ni ne collecte les journaux d'accès de
agendasabauda.eu.**

### 1.3 Le chemin exact pour lire le chiffre : GA4

C'est le **seul** outil en place qui puisse répondre.

1. Ouvrir **analytics.google.com**, choisir la propriété dont l'identifiant de mesure est
   **`G-HWRKPM4F7J`**.
2. Menu de gauche → **Explorer**.
3. **Exploration au format libre** (la première vignette, « Blank » / « Format libre »).
4. Colonne **Variables**, ligne **Dimensions** → bouton **+** → chercher « navigateur » →
   cocher **Navigateur** *et* **Version du navigateur** → **Importer**.
5. Même colonne, ligne **Statistiques** → **+** → cocher **Utilisateurs actifs** → **Importer**.
6. Colonne **Paramètres** : glisser **Navigateur** dans **Lignes**, puis **Version du navigateur**
   dans **Lignes** juste en dessous ; glisser **Utilisateurs actifs** dans **Valeurs**.
7. En haut à droite, mettre la **plage de dates la plus large possible** (le site est récent :
   prendre « depuis le début » plutôt que 28 jours).
8. **Lire le tableau.** Additionner les utilisateurs des lignes :
   - **Safari**, version **strictement inférieure à 15.4**
   - **Chrome** et **Edge**, version **strictement inférieure à 105**
   - **Firefox**, version **strictement inférieure à 121**
   - **Samsung Internet**, version **strictement inférieure à 20**
   Diviser par le total de la colonne. **C'est le chiffre.**

Raccourci si l'exploration rebute : **Rapports → Technologie → Détails techniques**, puis le
bouton **+** à droite de l'en-tête de la première colonne pour ajouter **Version du navigateur**
en dimension secondaire. Même donnée, moins de réglages.

### 1.4 Trois réserves à connaître avant de croire ce chiffre

1. **Le consentement.** Le script gtag est posé dans la catégorie Complianz **`functional`**
   (mesuré : `data-category="functional"`), donc il se charge pour tout le monde ; mais
   `analytics_storage` reste `denied` tant que le visiteur n'a pas accepté la catégorie
   « statistics ». Les visiteurs qui refusent sont comptés en mode sans cookie / modélisé.
   **Le chiffre est un ordre de grandeur, pas un décompte.**
2. **Un vieux navigateur exécute quand même le JS**, donc il est bien compté — mais un navigateur
   assez vieux pour ne pas avoir `:has()` peut aussi échouer sur le bandeau Complianz ou sur
   `gtag`. **Le biais joue dans le sens de la sous-estimation.**
3. **Version ≠ moteur.** Sur iOS, tous les navigateurs sont WebKit : « Safari 15.1 » veut dire
   « iOS 15.1 », ce qui est bien le bon critère. En revanche les navigateurs intégrés aux
   applications (Facebook, Instagram) remontent en « Android Webview » avec leur propre numéro.

### 1.5 Sur la statistique publique — ce que je ne ferai pas

Le § 5 de `CORRECTIFS_CSS_PRETS.md` avance « probablement de l'ordre de 1 % ». **C'est une
estimation, pas une mesure, et ce n'est pas le trafic de Franck.**

Je ne cite aucun chiffre de part de marché. Si Franck veut une référence publique, elle se lit sur
**caniuse.com/css-has** (ligne « Global »), et **c'est une moyenne mondiale tous sites confondus** :
un agenda culturel savoyard, alpin, avec une part de mobile iOS élevée, n'a aucune raison d'y
ressembler. Cette moyenne ne peut pas décider à la place de son GA4.

### 1.6 La façon la plus légère d'obtenir la réponse *directe*

La mesure vraiment exacte serait un événement GA4 déclenché quand
`CSS.supports('selector(:has(*))')` vaut `false`. **Mais c'est un snippet à poser sur le site** —
donc une écriture, et l'attente de plusieurs semaines de trafic avant de pouvoir trancher.

**Le volet B coûte moins cher que cette mesure, et il rend la mesure inutile.** C'est la vraie
réponse au volet A.

---

## 2. VOLET B — la solution sans `:has()`

### 2.0 Méthode

Reprise intégrale du montage du § 0 de `CORRECTIFS_CSS_PRETS.md` :

1. **Relais réseau.** Chromium ne joint pas le site directement depuis cet environnement. Chaque
   requête du navigateur est rejouée par le client HTTP de Playwright (qui, lui, passe le proxy),
   puis servie au navigateur avec ses en-têtes d'origine, **et mise en cache disque** : les runs
   « avant » et « après » portent sur des **octets strictement identiques**. Cache partagé avec les
   mesures du 2026-08-03 matin — d'où des hauteurs de page rigoureusement reproductibles
   (10 928 px, à la page près).
2. **Chromium 1194, Playwright 1.56.1**, viewports 360 / 390 / 899 / 900 / 1366, UA iPhone.
3. **Simulation de la modification de contenu.** La classe est ajoutée par **réécriture littérale
   du HTML servi** dans la copie locale — exactement l'octet que Franck ajouterait dans l'éditeur.
   Vérifié : la chaîne cible apparaît **exactement 1 fois** dans la page.
4. **Émulation d'un navigateur sans `:has()`** : toutes les règles dont le sélecteur contient
   `:has(` sont retirées du CSSOM après chargement (**15 règles**, ce qu'un vieux moteur fait à la
   lecture).

**Les deux pièges signalés par le document source ont été évités**, et c'était nécessaire :

- `CSSStyleRule` expose aujourd'hui une propriété `cssRules` (vide) à cause du CSS imbriqué. Le
  parcours récursif **ne fait donc pas `continue` sur les règles de style** : il teste
  `selectorText` **puis** descend dans `cssRules` si elle est non vide.
- Chromium **normalise** les sélecteurs : `> *:not(.as-desktop-cols3)` s'y relit
  `> :not(.as-desktop-cols3)`, sans l'astérisque. Le filtre ne cherche donc **jamais** une chaîne
  d'origine, seulement la sous-chaîne `:has(`. Le relevé le confirme, première ligne de la liste
  des 15 règles supprimées :
  `.as-home-desktop:has(> .as-desktop-cols3) > :not(.as-desktop-cols3)` — **sans astérisque.**

**Ce que cette méthode ne peut pas prouver :** je n'ai testé qu'un moteur récent. Le comportement
d'un vrai Safari 15.0 est **émulé**, pas observé. C'est dit à chaque fois. *(Voir § 2.7 : c'est
précisément le point sur lequel la solution proposée ici est meilleure que le repli `@supports`.)*

---

### 2.1 Les blocs concernés — mesurés, pas supposés

`.as-home-root` est émis par le gabarit de page (`homepage-template.php`), pas par Gutenberg :
**chaque enfant direct de `.as-home-root` est un bloc de premier niveau de la page 928.** Elle en a
**15**. Cinq portent `as-home-desktop` — le document source disait 5, **c'est confirmé** :

```
--- .as-home-root > .as-home-desktop (5) — viewport 390 px, état actuel ---

  #0 (enfant nº 9 de root)  DIV class="as-home-desktop"                                   display=none  h=0
     masthead desktop, nav, barre territoire, tuiles, titre « À la une »
  #1 (enfant nº 10)         DIV class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  h=0
  #2 (enfant nº 11)         DIV class="as-home-desktop"                                   display=none  h=0
     titre « Ce week-end »
  #3 (enfant nº 12)         DIV class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  h=0
  #4 (enfant nº 13)         DIV class="as-home-desktop"                                   display=block h=6810   ← LE SEUL EN JEU
```

**Quatre de ces cinq blocs sont purement desktop et restent `display:none` sous 900 px de
toute façon** — sans `:has()`, avec `:has()`, dans tous les cas. *Ils ne sont pour rien dans le
problème.*

Le problème tient tout entier au **bloc #4**, qui est **mixte** : il contient à la fois des
éléments de mise en page desktop *et* le seul bloc qui doit rester visible sur mobile. Ses
12 enfants directs, mesurés :

```
  [0]  DIV (sans classe)                                    display=none   « Voir tous les événements du week-end → »
  [1]  DIV (sans classe)                                    display=none   « Les 7 prochains jours   Voir tout → »
  [2]  DIV .wp-block-group.as-home-desktop.as-desktop-grid-4 display=none
  [3]  DIV .as-home-desktop                                 display=none   « Ça vaut le déplacement … »
  [4]  P  (sans classe)                                     display=none
  [5]  DIV .wp-block-group.as-home-desktop.as-desktop-cols3 display=grid  h=6810   ← CE QU'IL FAUT GARDER
  [6]  DIV .as-desktop-newsletter-band                      display=none
  [7]  INPUT#as-desktop-adbar-toggle                        display=none
  [8]  DIV .as-desktop-sticky-ad                            display=none
  [9]  P .wp-block-paragraph                                display=none
  [10] P .wp-block-paragraph                                display=none
  [11] P .wp-block-paragraph                                display=none
```

Et les trois sections du bas de home vivent **toutes les trois** dans l'enfant `[5]` :

```
#nouveautes      → .jet-listing-grid--blocks ⊂ .wp-block-group__inner-container ⊂ .as-desktop-col
                     ⊂ .wp-block-group__inner-container ⊂ .as-desktop-cols3
#evidence        → même chaîne
#venir           → même chaîne
(+ #evidence-bottom et #venir-bottom, même chaîne)
```

**Conséquence, et c'est le point de conception :** la parade proposée en fin de § 5 était de
« donner une classe `as-desktop-only` à ces blocs ». **Ce n'est pas là qu'il faut la poser.** Les
blocs desktop-only sont déjà correctement masqués. Ce qu'il faut, c'est **dire au bloc #4 qu'il
n'est PAS desktop-only** — c'est-à-dire lui donner une classe à lui, et une seule.

**Une classe. Un bloc. Un caractère de contenu changé.**

---

### 2.2 Les trois règles `:has()` à remplacer — relevées dans le CSS servi

| # | Bloc | Règle exacte | Rôle |
|---|---|---|---|
| 1 | `cs-no-hide-empty-cols` | `.as-home-desktop:has(> .as-desktop-cols3){ display: block !important; }` | **RÉVÈLE** le bloc #4 |
| 2 | `cs-no-hide-empty-cols`, dans `@media (max-width:899px)` | `.as-home-desktop:has(> .as-desktop-cols3){ max-width:480px !important; margin-left:auto !important; margin-right:auto !important; }` | **CENTRE** le bloc #4 sur mobile |
| 3 | `cs-composants-styles` l. 1179, dans `@media (max-width:899px)` | `.as-home-desktop:has(> .as-desktop-cols3) > *:not(.as-desktop-cols3){ display:none !important; }` | **MASQUE** ses 11 autres enfants |

Le document source en annonçait deux ; **il y en a trois** — la deuxième (le centrage à 480 px)
n'avait pas été relevée. Sans elle, le bas de home mobile s'étalerait sur toute la largeur.

Règle de base qui rend tout cela nécessaire, `cs-composants-styles` l. 440-441 :

```css
.as-home-desktop { display: none; }
@media (min-width: 900px) { .as-home-desktop { display: block; } }
```

---

### 2.3 Le CSS de remplacement — aucun `:has()`

```css
/* ═══ DÉBUT sortie de :has() — bas de home mobile (2026-08-03) ═══ */
/* POURQUOI : l'affichage de Nouveautés / En évidence / L'agenda à venir sous
   900 px reposait sur TROIS règles :has() (révéler, centrer, masquer les
   doublons). Un navigateur sans :has() (Safari < 15.4, Chrome < 105,
   Firefox < 121) les rejette toutes les trois : le conteneur reste
   display:none et ces trois sections DISPARAISSENT — la home mobile tombe de
   10 928 px à 4 118 px (mesuré le 2026-08-03 par émulation).
   Ici, plus aucun sélecteur acrobatique : le conteneur mixte porte désormais
   une classe explicite, .as-home-tail, posée dans l'éditeur de la page 928.
   Ces règles marchent sur TOUS les navigateurs, anciens comme récents — donc
   elles sont vérifiables depuis un poste à jour, ce que n'était pas le repli
   @supports. */
@media (max-width: 899px) {
  /* 1. le conteneur mixte redevient visible (remplace la règle :has() nº 1)
        et reste centré à 480 px (remplace la règle :has() nº 2) */
  .as-home-root > .as-home-tail{
    display: block !important;
    max-width: 480px !important;
    margin-left: auto !important;
    margin-right: auto !important;
  }
  /* 2. dans ce conteneur, tout est desktop-seulement… (remplace la nº 3)
        Formule volontairement générique, comme l'était le :not() d'origine :
        tout élément ajouté plus tard au conteneur restera masqué sur mobile
        par défaut, au lieu de réapparaître en doublon sans prévenir. */
  .as-home-root > .as-home-tail > *{ display: none !important; }
  /* 3. …sauf le bloc 3 colonnes, qui porte les trois sections. */
  .as-home-root > .as-home-tail > .as-desktop-cols3{ display: grid !important; }
}

/* COMPLÉMENT, indépendant du bas de home. JetEngine pose lui-même, dans
   jet-engine/assets/css/frontend.css :
       .jet-listing-grid:has(.swiper){ position: relative }
   Sans :has(), les flèches du carrousel (position:absolute) s'ancrent sur un
   autre bloc conteneur et descendent de 159 px — mesuré : next-arrow passe de
   (320, 438) à (340, 597). Cette ligne fait la même chose sans :has().
   Vérifié inerte sur navigateur récent : 0 différence sur les 2 699 éléments
   de la page, en 390 px comme en 1366 px. */
.jet-listing-grid{ position: relative; }
/* ═══ FIN sortie de :has() ═══ */
```

**Où le poser :** dans le snippet qui émet **`<style id="cs-no-hide-empty-cols">`**, *à la fin*.
Trois raisons :

1. C'est **le dernier `<style>` du `<head>`** (offset 106 805) : la règle gagne la cascade sans
   dépendre de la spécificité.
2. C'est **déjà lui qui porte la règle qui révèle** le bloc #4 (`:has()` nº 1) : tout ce qui
   concerne ce conteneur reste au même endroit, et se relit ensemble.
3. **C'est la position dans laquelle j'ai mesuré** (le CSS candidat est injecté juste avant
   `</head>`, donc après `cs-no-hide-empty-cols`). Le poser ailleurs, c'est déployer autre chose
   que ce qui a été vérifié.

**Vérifié : le nom `as-home-tail` n'existe nulle part** — 0 occurrence dans le HTML servi de `/`,
0 dans les six blocs `cs-*`, 0 dans `jet-engine/frontend.css`. Aucune collision possible.

---

### 2.4 La modification de contenu — mode opératoire

C'est la partie qui demande d'ouvrir l'éditeur. Elle est courte, mais elle est réelle.

#### Quelle page

| Page WordPress | Titre | ID | URL servies |
|---|---|---|---|
| **Accueil** | « Accueil » | **928** | `/`, `/explore/savoie/`, `/explore/comte-de-nice/`, `/choisir/piemont/`, `/choisir/vallee-d-aoste/` |
| **Home (IT)** | « Home (IT) » | **1717** | `/it/home-it/` |

Mesuré : les cinq URL françaises servent toutes `body class="… page-id-928 …"`. **Une seule
modification couvre les cinq.** La home italienne est une page distincte et demande **la même
modification, à l'identique** — la chaîne cible y est présente **exactement 1 fois** aussi
(vérifié sur `/it/home-it/`).

#### Quel bloc

Un **bloc « HTML personnalisé »** (Custom HTML). Ce n'est **pas** un bloc Groupe : le conteneur
sort dans la page en `<div class="as-home-desktop">` *sans* la classe `wp-block-group` que
Gutenberg ajoute aux Groupes. Il n'y a donc **pas** de champ « Classe(s) CSS additionnelle(s) » à
remplir dans le panneau Avancé — **la classe se pose dans le code du bloc.**

Ce bloc **ouvre un `<div>` qu'il ne referme pas** : les blocs suivants de la page (la grille 4
colonnes, « Ça vaut le déplacement », le groupe 3 colonnes, la bande newsletter…) se retrouvent
*à l'intérieur* dans le rendu. C'est pour cela qu'il commande l'affichage de tout le bas de page.

#### Le geste, pas à pas

1. **wp-admin → Pages → « Accueil »** (ID 928) → **Modifier**.
2. En haut à droite, menu **⋮ (Options)** → **Éditeur de code** *(raccourci
   `Ctrl` + `Maj` + `Alt` + `M`)*. C'est plus sûr que la vue visuelle : le bloc visé est un bloc de
   code, et l'éditeur de code permet de chercher.
3. `Ctrl` + `F` et chercher :

   ```
   justify-content:center
   ```

   Il y a **4 occurrences** dans la page. **La bonne est la seule qui soit précédée, sur la ligne
   juste au-dessus, de `<div class="as-home-desktop">`.** Les deux lignes se suivent exactement
   ainsi — cette paire de lignes n'apparaît **qu'une seule fois** dans toute la page (vérifié) :

   ```html
   <div class="as-home-desktop">
   <div style="display:flex;justify-content:center">
     <a href="https://agendasabauda.eu/ce-week-end/" style="display:inline-block;text-align:center;…
   ```

   Repère supplémentaire : dans les lignes qui suivent immédiatement, on lit
   `Voir tous les événements du week-end&nbsp;→`, puis le commentaire
   `<!-- EVENEMENTS DU JOUR -->`, puis `Les 7 prochains jours`. **Si ces trois repères n'y sont
   pas, ce n'est pas le bon bloc — ne rien changer.**

4. **Modifier uniquement la première de ces deux lignes**, en ajoutant un espace et un mot :

   ```diff
   - <div class="as-home-desktop">
   + <div class="as-home-desktop as-home-tail">
   ```

   **Ne rien toucher d'autre. Ne pas retirer `as-home-desktop`** : c'est elle qui pilote la mise
   en page desktop (largeur 950 px, marges auto, padding 20 px, `cs-composants-styles` l. 584).
5. **⋮ → Éditeur visuel** pour revenir, puis **Mettre à jour**.
6. Recommencer à l'identique sur **Pages → « Home (IT) »** (ID 1717).

> ⚠️ **Ordre de déploiement.** Poser **d'abord le CSS** (§ 2.3), **ensuite la classe**. Dans cet
> ordre, aucun état intermédiaire n'est visible : le CSS seul ne s'accroche à rien (la classe
> n'existe pas encore), et la classe arrive dans un CSS déjà prêt. Dans l'ordre inverse aussi, en
> réalité, rien ne casse — les règles `:has()` restent en place et continuent de tout piloter —
> mais autant ne pas avoir à y penser.

---

### 2.5 Les mesures — relevé brut

Trois états, même page, **mêmes octets** (cache disque), viewport 390 px.

#### Relevé verbatim

```
############ CSS=actuel  MOTEUR=moderne  viewport=390px ############
CSS.supports('selector(:has(*))') dans la page : true

.as-home-root > .as-home-desktop :
   [0] class="as-home-desktop"  display=none  hauteur=0 px
   [1] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [2] class="as-home-desktop"  display=none  hauteur=0 px
   [3] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [4] class="as-home-desktop"  display=block  hauteur=6810 px

sections du bas de home :
   Nouveautés (#nouveautes)     → visible, 355 px
   En évidence (#evidence)      → visible, 1143 px
   L'agenda à venir (#venir)    → visible, 449 px
   #evidence-bottom             → visible, 1162 px
   #venir-bottom                → visible, 516 px

doublons potentiels :
   VISIBLE  « Voir tous les événements du week-end → »
   VISIBLE  « Les 7 prochains jours »
    caché   « Voir tous les événements du week-end → »
    caché   « Les 7 prochains jours »

HAUTEUR TOTALE DE PAGE : 10928 px
largeur de défilement du document : 390 px (viewport 390)

############ CSS=actuel  MOTEUR=sans-has  viewport=390px ############
règles :has() retirées du CSSOM : 15
CSS.supports('selector(:has(*))') dans la page : true

.as-home-root > .as-home-desktop :
   [0] class="as-home-desktop"  display=none  hauteur=0 px
   [1] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [2] class="as-home-desktop"  display=none  hauteur=0 px
   [3] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [4] class="as-home-desktop"  display=none  hauteur=0 px

sections du bas de home :
   Nouveautés (#nouveautes)     → PRÉSENTE MAIS INVISIBLE (0 px)
   En évidence (#evidence)      → PRÉSENTE MAIS INVISIBLE (0 px)
   L'agenda à venir (#venir)    → PRÉSENTE MAIS INVISIBLE (0 px)
   #evidence-bottom             → PRÉSENTE MAIS INVISIBLE (0 px)
   #venir-bottom                → PRÉSENTE MAIS INVISIBLE (0 px)

doublons potentiels :
   VISIBLE  « Voir tous les événements du week-end → »
   VISIBLE  « Les 7 prochains jours »
    caché   « Voir tous les événements du week-end → »
    caché   « Les 7 prochains jours »

HAUTEUR TOTALE DE PAGE : 4118 px
largeur de défilement du document : 390 px (viewport 390)

############ CSS=classe  MOTEUR=moderne  viewport=390px ############
CSS.supports('selector(:has(*))') dans la page : true

.as-home-root > .as-home-desktop :
   [0] class="as-home-desktop"  display=none  hauteur=0 px
   [1] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [2] class="as-home-desktop"  display=none  hauteur=0 px
   [3] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [4] class="as-home-desktop as-home-tail"  display=block  hauteur=6810 px

sections du bas de home :
   Nouveautés (#nouveautes)     → visible, 355 px
   En évidence (#evidence)      → visible, 1143 px
   L'agenda à venir (#venir)    → visible, 449 px
   #evidence-bottom             → visible, 1162 px
   #venir-bottom                → visible, 516 px

doublons potentiels :
   VISIBLE  « Voir tous les événements du week-end → »
   VISIBLE  « Les 7 prochains jours »
    caché   « Voir tous les événements du week-end → »
    caché   « Les 7 prochains jours »

HAUTEUR TOTALE DE PAGE : 10928 px
largeur de défilement du document : 390 px (viewport 390)

############ CSS=classe  MOTEUR=sans-has  viewport=390px ############
règles :has() retirées du CSSOM : 15
CSS.supports('selector(:has(*))') dans la page : true

.as-home-root > .as-home-desktop :
   [0] class="as-home-desktop"  display=none  hauteur=0 px
   [1] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [2] class="as-home-desktop"  display=none  hauteur=0 px
   [3] class="wp-block-group as-home-desktop as-desktop-grid-3"  display=none  hauteur=0 px
   [4] class="as-home-desktop as-home-tail"  display=block  hauteur=6810 px

sections du bas de home :
   Nouveautés (#nouveautes)     → visible, 355 px
   En évidence (#evidence)      → visible, 1143 px
   L'agenda à venir (#venir)    → visible, 449 px
   #evidence-bottom             → visible, 1162 px
   #venir-bottom                → visible, 516 px

doublons potentiels :
   VISIBLE  « Voir tous les événements du week-end → »
   VISIBLE  « Les 7 prochains jours »
    caché   « Voir tous les événements du week-end → »
    caché   « Les 7 prochains jours »

HAUTEUR TOTALE DE PAGE : 10928 px
largeur de défilement du document : 390 px (viewport 390)
```

#### Le même relevé en tableau

| | Navigateur récent | **Sans `:has()`** |
|---|---|---|
| **État actuel** | 10 928 px, 3 sections visibles ✅ | **4 118 px (−62 %), 3 sections à 0 px** ❌ |
| **Avec la solution** | **10 928 px, 3 sections visibles** ✅ | **10 928 px, 3 sections visibles** ✅ |

**Les trois cas donnent le même rendu.** C'était l'exigence.

Et le doublon que le § 5 d'origine surveillait : dans les quatre relevés, « Les 7 prochains jours »
et « Voir tous les événements du week-end » apparaissent **une fois visibles, une fois cachés**.
Aucun doublon n'est créé dans aucun état.

#### La preuve dure : empreinte géométrique de la page entière

Le relevé ci-dessus regarde cinq sections. Pour ne rien manquer, j'ai relevé pour **chacun des
2 699 éléments du DOM** son tag, son id, ses classes, sa position absolue, sa taille et son
`display`, puis comparé les états ligne à ligne (les identifiants tirés au hasard à chaque
chargement — `menu-item-…-sub-menu`, `swiper-wrapper-…` — et l'ordre d'insertion des iframes
AdSense sont normalisés ; ce sont du bruit, pas du rendu).

**Viewport 390 px**

```
   0 différence(s)   actuel/moderne  ↔  solution/moderne
   0 différence(s)   actuel/moderne  ↔  solution/SANS :has
   0 différence(s)   solution/moderne  ↔  solution/SANS :has

 905 différence(s)   actuel/moderne  ↔  actuel/SANS :has        ← le bug, aujourd'hui
```

**Viewport 1366 px** (contrôle de non-régression desktop)

```
   0 différence(s)   actuel/moderne  ↔  solution/moderne
   0 différence(s)   actuel/moderne  ↔  solution/SANS :has
   0 différence(s)   solution/moderne  ↔  solution/SANS :has
```

**Zéro différence sur 2 699 éléments, dans les deux viewports.** La solution est **strictement
invisible** sur un navigateur à jour, et rend **strictement pareil** sur un navigateur ancien.

*Note d'honnêteté : sans la ligne de complément `.jet-listing-grid{ position: relative; }`, il
restait exactement 12 lignes de différence entre « solution/moderne » et « solution/SANS `:has()` »,
toutes portées par 6 éléments : les flèches du carrousel (`next-arrow` / `prev-arrow` + leur `svg`
+ leur `path`), qui descendaient de 159 px. La cause n'était pas notre correctif mais la règle
`:has()` de JetEngine lui-même. C'est ce que cette ligne répare, et elle a été mesurée séparément.*

#### Autres largeurs

| Viewport | Actuel / moderne | Solution / moderne | Solution / sans `:has()` |
|---|---|---|---|
| 360 px | 10 956 px | **10 956 px** | **10 956 px** |
| 390 px | 10 928 px | **10 928 px** | **10 928 px** |
| 899 px *(dernier px du mode mobile)* | 11 528 px | **11 528 px** | **11 528 px** |
| 900 px *(premier px du mode desktop)* | 7 100 px | **7 100 px** | **7 100 px** |
| 1366 px | 7 220 px | **7 220 px** | **7 220 px** |

La bascule à 899/900 px est franche et intacte : ni glissement de seuil, ni zone morte.

#### Phase 2 : et si on retire vraiment les `:has()` ?

Une fois la classe et le CSS en place, les trois règles `:has(> .as-desktop-cols3)` ne servent plus
à rien. Mesure de leur retrait (uniquement celles-là — celles de JetEngine, Elementor et des
listings vides restent), sur navigateur récent :

```
viewport 390  : 0 différence(s) entre « état actuel » et « phase 2 », navigateur récent  — hauteur 10928 px
viewport 1366 : 0 différence(s) entre « état actuel » et « phase 2 », navigateur récent  — hauteur 7220 px
```

**Le nettoyage est sûr.** Mais il n'est pas urgent : laisser les `:has()` en place ne coûte rien
(elles disent la même chose que les nouvelles règles). *Recommandation : faire la phase 2 plus
tard, séparément, une fois la solution en production depuis quelques jours.*

---

### 2.6 Ce que cette solution coûte — franchement

| | Repli `@supports` (§ 5 du doc source) | **Cette solution** |
|---|---|---|
| Nature | 100 % CSS, un bloc à coller | CSS **+ une classe dans l'éditeur Gutenberg** |
| Pages à modifier | 0 | **2** (928 et 1717) |
| Effort | 10 min | **20 min** |
| Annulation | supprimer un bloc CSS | supprimer un bloc CSS **+ retirer ` as-home-tail` dans 2 pages** |
| Bénéfice sur navigateur récent | aucun (inerte par construction) | aucun (mesuré : 0 différence) |
| Bénéfice sur navigateur ancien | **théorique** — invérifiable depuis un poste à jour | **mesuré** |
| **Vérifiable après pose ?** | **non** | **oui** — voir § 2.7 |

**Les trois vraies objections, dites franchement :**

1. **C'est une modification de contenu.** Un bloc CSS vit dans Code Snippets, dans un bloc balisé
   par des marqueurs `DÉBUT`/`FIN` : on le supprime en trente secondes sans rien risquer d'autre.
   Une classe dans un bloc HTML personnalisé vit dans le contenu d'une page. **On l'annule en
   retirant ` as-home-tail` de la même ligne** — c'est simple, mais ça se fait dans l'éditeur de
   page, pas dans un panneau de snippets, et **ça passe par une révision de page.**
2. **Le bloc à modifier n'est pas trivial à trouver.** C'est un bloc HTML personnalisé, dans une
   page qui en compte plusieurs, et qui ouvre un `<div>` sans le refermer. Le § 2.4 donne trois
   repères pour l'identifier sans ambiguïté, mais ça reste plus engageant que coller du CSS.
   *Recommandation : Franck fait cette manipulation quand il a dix minutes tranquilles, pas entre
   deux choses.*
3. **Deux pages, pas une.** La home italienne (1717) demande le même geste. Si Franck ne fait que
   la française, **`/it/home-it/` restera dans l'état actuel** — pas cassée, juste toujours
   dépendante de `:has()`.

**Et une objection qui n'en est pas une :** cette solution ne rend pas la page « plus fragile aux
ajouts de contenu ». La règle `> *{ display:none }` a exactement la même sémantique générique que
le `> *:not(.as-desktop-cols3)` d'aujourd'hui — dont le commentaire dans `cs-composants-styles`
dit qu'elle a été écrite **volontairement** ainsi, pour que tout nouvel élément ajouté au conteneur
desktop reste masqué sur mobile par défaut. Ce comportement est conservé à l'identique.

---

### 2.7 Le vrai argument : ça se vérifie

C'est le point sur lequel cette solution ne se compare pas au repli `@supports` — elle joue dans
une autre catégorie.

Le § 5 disait de son repli : *« c'est le point faible de ce correctif :
`@supports not selector(:has(*))` est faux sur tout navigateur moderne, donc on ne peut pas le
vérifier depuis un poste à jour. »* C'est exact, et c'est même un peu pire que ça, comme mon
propre relevé le montre : dans les quatre runs ci-dessus, y compris ceux en mode « sans `:has()` »,
la page rapporte

```
CSS.supports('selector(:has(*))') dans la page : true
```

**L'émulation retire l'effet des règles `:has()`, elle ne peut pas retirer la capacité du
moteur.** Autrement dit : **la garde `@supports` du repli du § 5 n'a jamais pu être testée, ni par
moi ni par l'agent précédent** — seul son *contenu* l'a été, injecté sans sa garde. On ne sait donc
pas mesurer que le repli s'active vraiment là où il devrait. On le croit, parce que la spécification
le dit.

**La solution de ce document ne contient aucune garde conditionnelle.** Ses règles s'appliquent
partout, tout le temps, à tous les moteurs. Donc :

> **Une fois posée, elle est vérifiable en trente secondes sur le téléphone de Franck** — et si
> elle marche là, elle marche aussi sur un Safari 15.0, parce que c'est exactement le même CSS qui
> s'exécute, sans branche conditionnelle nulle part.

C'est une propriété que le repli `@supports` ne pourra jamais avoir.

---

### 2.8 Comment vérifier que ça a marché — protocole exact, sans rien écrire

1. Chrome, `https://agendasabauda.eu/`, **F12**, mode appareil, **largeur 390 px**, recharger.
2. Console, coller (lecture seule) :

   ```js
   const c = document.querySelector('.as-home-root > .as-home-tail');
   console.log('classe posée :', c ? 'OUI ✅' : 'NON ❌');
   if (c) console.log('display :', getComputedStyle(c).display,
                      '| hauteur :', Math.round(c.getBoundingClientRect().height));
   ['nouveautes','evidence','venir'].forEach(id => {
     const e = document.getElementById(id);
     const h = e ? Math.round(e.getBoundingClientRect().height) : -1;
     console.log(id.padEnd(12), h > 0 ? h + ' px ✅' : 'INVISIBLE ❌');
   });
   console.log('hauteur de page :', document.documentElement.scrollHeight);
   ```

   **Attendu : `classe posée : OUI ✅`, `display : block`, hauteur `6810`,
   `nouveautes 355 px ✅`, `evidence 1143 px ✅`, `venir 449 px ✅`,
   `hauteur de page : 10928`** (± la variation du catalogue, qui bouge tous les jours).

3. **Le test qui compte vraiment — et qui n'existait pas pour le repli `@supports`.** Toujours en
   390 px, coller ceci : il neutralise **toutes** les règles `:has()` de la page, exactement ce que
   fait un Safari 15.0 à la lecture.

   ```js
   let n = 0;
   const scrub = (o, rs) => { for (let i = rs.length - 1; i >= 0; i--) { const r = rs[i];
     if (r.selectorText !== undefined && r.style !== undefined && /:has\(/.test(r.selectorText)) { o.deleteRule(i); n++; continue; }
     if (r.cssRules && r.cssRules.length) scrub(r, r.cssRules); } };
   for (const s of document.styleSheets) { try { scrub(s, s.cssRules); } catch (e) {} }
   console.log(n + ' règles :has() neutralisées — hauteur :', document.documentElement.scrollHeight);
   ```

   **Avant la pose : `15 règles :has() neutralisées — hauteur : 4118`** et les trois sections
   disparaissent à l'œil.
   **Après la pose : `15 règles :has() neutralisées — hauteur : 10928`** et **rien ne bouge**.

   *Recharger la page ensuite : la manipulation ne modifie que le CSSOM de l'onglet courant, elle
   ne touche ni le site ni le cache.*

4. **Contrôle desktop :** repasser en 1366 px, recharger. La home doit être **exactement** comme
   avant (mesuré : 7 220 px, 0 différence sur 2 699 éléments).
5. **Contrôle sur la home italienne :** refaire les points 1 à 4 sur `https://agendasabauda.eu/it/home-it/`.
6. **Le test final, à l'œil, sur un vrai téléphone :** faire défiler la home jusqu'en bas.
   « Nouveautés », « En évidence » et « L'agenda à venir » doivent être là, et il ne doit y avoir
   **qu'un seul** « Les 7 prochains jours ».

### 2.9 Comment annuler

- **Le CSS :** Code Snippets → snippet `cs-no-hide-empty-cols` → supprimer tout ce qui est entre
  `/* ═══ DÉBUT sortie de :has()` et `/* ═══ FIN sortie de :has() ═══ */` → Enregistrer.
- **La classe :** Pages → « Accueil » (928) → Éditeur de code → chercher `as-home-tail` (1 seule
  occurrence) → **retirer ` as-home-tail`**, en gardant `as-home-desktop` → Mettre à jour.
  Recommencer sur « Home (IT) » (1717).
- **Filet de sécurité :** WordPress conserve une **révision** de la page à chaque mise à jour.
  En cas de doute, wp-admin → Pages → Accueil → panneau de droite → **Révisions** → revenir à la
  version d'avant.

**Important :** tant que la phase 2 (§ 2.5) n'est pas faite, **les trois règles `:has()` sont
toujours là**. Annuler la solution remet donc simplement le site dans son état actuel, sans aucun
état intermédiaire cassé. **C'est ce qui rend ce déploiement peu risqué : les deux mécanismes
coexistent, et le nouveau ne prend le relais que là où l'ancien tombait.**

---

### 2.10 Risque de régression — nommé et vérifié

| Risque | Vérification | Verdict |
|---|---|---|
| Le sélecteur touche d'autres éléments | `.as-home-root > .as-home-tail` ne peut correspondre qu'aux blocs portant la classe, posée **1 fois par page** sur **2 pages** | **nul** |
| Collision de nom de classe | 0 occurrence de `as-home-tail` dans le HTML servi, les 6 blocs `cs-*`, et `jet-engine/frontend.css` | **nul** |
| Régression desktop | 0 différence sur 2 699 éléments en 1366 px et en 900 px | **nul (mesuré)** |
| Régression mobile sur navigateur récent | 0 différence sur 2 699 éléments en 360, 390 et 899 px | **nul (mesuré)** |
| Débordement horizontal | largeur de défilement = viewport dans tous les états et tous les viewports | **nul (mesuré)** |
| Doublon « Les 7 prochains jours » | 1 visible / 1 caché dans les 4 états | **nul (mesuré)** |
| `.jet-listing-grid{position:relative}` casse un positionnement ailleurs | 0 différence sur 2 699 éléments, 390 px et 1366 px | **nul sur la home** — *non testé sur les hubs et les fiches* ⚠️ |
| Les 4 autres blocs `as-home-desktop` | non touchés : ni la classe, ni les sélecteurs ne les atteignent ; mesurés `display:none` h=0 dans les 4 états | **nul** |
| L'éditeur Gutenberg reformate le bloc | **non vérifié** — je n'ai pas d'accès admin ⚠️ | voir ci-dessous |

**Les deux réserves, en clair :**

- **`.jet-listing-grid{ position: relative; }` n'a été mesurée que sur la home.** C'est une
  déclaration bénigne (`position:relative` sur un bloc statique ne déplace rien par lui-même), mais
  `.jet-listing-grid` existe sur tous les hubs et toutes les fiches. **Si Franck préfère la
  prudence, cette ligne est facultative** : sans elle, tout le bas de home fonctionne pareil, seules
  les flèches du carrousel restent décalées de 159 px sur un vieux navigateur. À arbitrer.
- **Je n'ai pas ouvert l'éditeur.** J'ai lu le HTML **rendu**, où le bloc HTML personnalisé sort
  verbatim. La ligne source devrait donc être identique à celle du § 2.4 — mais **c'est une
  déduction, pas une observation.** Si Franck ne retrouve pas exactement ces deux lignes dans
  l'éditeur de code, **il ne faut rien modifier** et me le dire.

---

## 3. Avis franc : faut-il faire ça ?

**Oui — mais pas pour la raison que le § 5 mettait en avant, et pas dans l'ordre qu'il suggérait.**

### Ce qu'il ne faut pas faire

**Ne pas déployer le repli `@supports` du § 5.** Non parce qu'il est faux — il est correct — mais
parce qu'il achète un bénéfice invérifiable au prix d'un bloc CSS de plus, et qu'il **laisse le
problème de fond en place** : le bas de la home continue de dépendre de deux règles acrobatiques
qui vont en sens contraire, plus une troisième que personne n'avait relevée. Le jour où quelqu'un
touche à l'une des trois, la page retombe. Et si le repli s'activait mal chez un vrai vieux
navigateur, **personne ne le saurait jamais** (§ 2.7).

**Et surtout : ne pas attendre le chiffre GA4 pour décider.** Le site est récent. Sur un petit
volume, la proportion de visiteurs sans `:has()` sera un bruit à deux ou trois visiteurs près, et
la décision qu'on en tirera sera arbitraire dans les deux sens. **Le § 5 disait « c'est cette
proportion qui doit décider ». Je pense que c'est une mauvaise règle de décision ici** — pas parce
que le chiffre est sans intérêt, mais parce qu'il ne sera pas assez solide pour porter le poids
qu'on veut lui faire porter. Franck peut aller le lire (§ 1.3, c'est cinq minutes) par curiosité,
et pour le savoir. Pas pour arbitrer.

### Ce qu'il faut faire

**Poser la solution du volet B — après les correctifs 1 et 2 du document source, pas avant.**

Le vrai argument n'est pas les vieux navigateurs. C'est celui-ci : **aujourd'hui, un tiers de la
page d'accueil tient à un mécanisme que personne ne peut ni voir ni tester.** Le § 5 a montré que
le diagnostic du 1ᵉʳ août s'était trompé dessus (« section blanche » au lieu de « sections
absentes »), et le présent document montre qu'il manquait encore une troisième règle au tableau.
**C'est un point du site que deux passes d'analyse successives n'ont pas décrit correctement.**
Ça, c'est un coût permanent, indépendant de tout navigateur.

La solution le remplace par trois règles qu'on lit à voix haute sans effort : *ce conteneur-ci est
visible sur mobile, tout ce qu'il contient est caché, sauf ce bloc-là.* Elle est mesurée à
**0 différence sur 2 699 éléments** dans les deux mondes, elle se vérifie en trente secondes après
la pose, et elle s'annule en retirant un mot dans deux pages.

### L'ordre que je recommande

1. **Correctif carrousel** (§ 2 du doc source) — le défaut le plus visible, le risque le plus bas.
2. **Correctif menu mobile** (§ 3) — une ligne, répare une impasse de navigation.
3. **Cette solution** — CSS d'abord, puis la classe sur 928, puis sur 1717.
4. **Vérifier** avec le § 2.8, y compris le point 3 (neutralisation des `:has()`), sur les deux
   home.
5. **Plus tard, séparément : phase 2** — retirer les trois règles `:has(> .as-desktop-cols3)`
   devenues inutiles. Mesuré sans effet, mais rien ne presse.

**Le repli `@supports` du § 5 devient alors inutile, et le classement bénéfice/risque du § 7 du
document source peut retirer sa ligne 4.**

### Si Franck ne veut pas toucher au contenu

C'est un choix défendable, et il faut le dire sans le regretter à moitié. Dans ce cas :
**vivre avec `:has()`, et ne rien coller du tout.** Les trois règles fonctionnent parfaitement pour
la quasi-totalité des visiteurs, et un correctif invérifiable posé « au cas où » ajoute de la
complexité à un CSS qui en a déjà beaucoup. **Entre « le repli `@supports` » et « ne rien faire »,
je choisis « ne rien faire ».** Le vrai choix est entre **ne rien faire** et **la solution du
volet B** — pas entre trois options.

---

## Note de traçabilité

Aucune écriture sur le site : ni snippet créé, modifié ou activé, ni page ou bloc Gutenberg touché,
ni PHP exécuté, ni appel d'écriture WordPress. La classe `as-home-tail` et le CSS candidat ont été
éprouvés **dans un navigateur local**, en réécrivant une **copie** de la page servie (relais réseau
+ cache disque), jamais la page réelle.

Les seules requêtes émises vers agendasabauda.eu sont des **lectures** : `GET /`,
`GET /explore/savoie/`, `GET /explore/comte-de-nice/`, `GET /choisir/piemont/`,
`GET /choisir/vallee-d-aoste/`, `GET /it/home-it/`, `GET /wp-json/wp/v2/pages/928`,
`GET /wp-json/wp/v2/pages/1717`, plus les sous-ressources chargées par le navigateur.

Dans le dépôt, **ce fichier est le seul écrit**. Aucun `git add`, `git commit` ni `git push`.
