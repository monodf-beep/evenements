# Déploiement pas à pas — 3 correctifs pour agendasabauda.eu

**Pour Franck. À suivre de haut en bas. Vous n'avez pas besoin d'ouvrir
`docs/CORRECTIFS_CSS_PRETS.md` : tout ce qu'il faut est ici.**

Date : 2026-08-03. Rédigé après relecture intégrale du document de mesures, et après
**revérification en direct** du site (en lecture seule) le 2026-08-03 vers 07 h 10 UTC.

Trois étapes, dans cet ordre :

| Étape | Ce que ça répare | Où | Durée |
|---|---|---|---|
| **1** | Le carrousel de la home qui se décale de 20 px au chargement | snippet existant | 5 min |
| **2** | Le menu mobile qui s'ouvre **derrière** le header : croix de fermeture inaccessible | snippet existant | 5 min |
| **3** | Le territoire choisi qui n'est pas transmis aux pages catégorie | **nouveau** snippet | 15 min |

Les étapes 1 et 2 sont indépendantes l'une de l'autre. Vous pouvez faire l'étape 1,
vérifier, puis l'étape 2. C'est même recommandé : si quelque chose bouge, vous savez
immédiatement quoi.

---

## 0. AVERTISSEMENT — à lire avant de toucher quoi que ce soit

### Ces correctifs sont des AJOUTS, jamais des remplacements

Chaque bloc ci-dessous est encadré par deux marqueurs :

```
/* === DEBUT correctif … === */
        … le correctif …
/* === FIN correctif … === */
```

**Vous ajoutez ce bloc. Vous ne remplacez rien, vous n'effacez rien, vous ne
« mettez à jour » rien.** Si à un moment vous vous apprêtez à sélectionner du texte
existant pour le remplacer, c'est que vous avez mal lu : arrêtez-vous.

### Pourquoi c'est vital

Le snippet de production `cs-composants-styles` fait aujourd'hui **71 235 caractères**,
alors que le fichier correspondant dans le dépôt Git,
`wordpress/design-system/components.css`, n'en fait que **31 050** : la production a
dérivé de 40 Ko, et ces 40 Ko de CSS n'existent **nulle part ailleurs** — ni dans le
dépôt, ni dans aucune sauvegarde de code.

Autrement dit : **écraser ou remplacer un bloc existant détruirait définitivement du CSS
irrécupérable**, et le site perdrait une partie de son habillage sans qu'on puisse le
reconstruire. C'est pour cette raison, et pour elle seule, que tout ce document ne fait
qu'ajouter du texte à la fin de blocs existants.

*(Les deux chiffres ci-dessus ont été remesurés aujourd'hui, pas recopiés : 71 235
caractères relevés dans le HTML servi par le site, 31 050 octets relevés sur le fichier
du dépôt.)*

---

## 0 bis. Avant de commencer — 5 minutes qui vous éviteront une soirée

### a) Sauvegardez le snippet AVANT de le modifier

Pour chaque snippet que vous ouvrez aux étapes 1 et 2 :

1. Cliquez dans la zone de code, faites **Ctrl + A** (tout sélectionner) puis **Ctrl + C**.
2. Collez dans un fichier texte sur votre ordinateur, nommé par exemple
   `sauvegarde-cs-hdr-compact-2026-08-03.txt`.
3. **Puis seulement** faites la modification.

Ce n'est pas de la prudence excessive : ces snippets n'existent **pas** dans le dépôt Git
(vérifié aujourd'hui — `cs-hdr-compact` et `cs-no-hide-empty-cols` n'apparaissent dans
aucun fichier du dépôt). Votre copier-coller est la seule sauvegarde qui existera.

### b) Ne vous fiez pas aux numéros de snippet

Vous verrez peut-être ailleurs les mentions « snippet #77 » ou « snippet #62 ». **Ces
numéros n'ont jamais été vérifiés.** Le seul repère fiable est le **nom technique** qui
apparaît dans le code du snippet : `cs-no-hide-empty-cols`, `cs-hdr-compact`. C'est ce
nom-là que vous cherchez, pas un numéro.

### c) La règle de l'apostrophe — importante

Les deux snippets des étapes 1 et 2 ne sont pas de simples fichiers CSS : ce sont des
snippets **PHP** qui assemblent le CSS sous forme de texte. L'un d'eux porte d'ailleurs,
écrit à l'intérieur, cet avertissement laissé par une intervention précédente :

> *« ce fichier concatène des chaînes PHP entre apostrophes — ne JAMAIS mettre une
> apostrophe dans ces commentaires, elle ferme la chaîne et casse tout le snippet »*

Vérification faite aujourd'hui : ces deux snippets ne contiennent **aucun caractère
accenté**, pas un seul, alors que `cs-composants-styles` en contient 282. Ce n'est pas un
hasard.

**Conséquence pratique : les blocs à coller aux étapes 1 et 2 ont été écrits sans aucun
accent et sans aucune apostrophe.** Ils sont un peu moins jolis à lire — c'est voulu.
**Copiez-les tels quels, ne les « corrigez » pas, n'y remettez pas les accents.**

### d) Comment ouvrir le bon snippet

1. Connectez-vous à `https://agendasabauda.eu/wp-admin/`.
2. Dans le menu de gauche, cliquez sur **« Snippets »**, puis **« Tous les snippets »**.
3. En haut à droite de la liste, dans le champ de recherche, tapez le nom technique
   (`cs-no-hide-empty-cols` ou `cs-hdr-compact`) et validez.
4. Ouvrez le snippet trouvé et **vérifiez** que son code contient bien ce nom technique.
   Si ce n'est pas le cas, ce n'est pas le bon : ne le modifiez pas.

*Si la recherche ne trouve rien (certaines versions ne cherchent que dans les titres) :
les snippets de ce site sont nommés selon le modèle « CS · quelque chose ». Ouvrez-les un
par un et cherchez le nom technique dans le code avec Ctrl + F.*

### e) Le test d'arrêt : à quoi doit ressembler le code du snippet

Quand vous ouvrez le snippet, regardez la zone de code :

- **Vous voyez du CSS lisible** (des noms de classes, des accolades `{ }`, la balise
  `</style>` quelque part) → **c'est bon, continuez.**
- **Vous voyez un pavé illisible** de plusieurs milliers de lettres et chiffres collés
  sans espaces → **ARRÊTEZ-VOUS.** Ce snippet est encodé et n'est pas modifiable à la
  main. Ne touchez à rien, fermez sans enregistrer, et demandez de l'aide.

---

## ÉTAPE 1 — Le carrousel décalé au chargement

### Ce que vous réparez

Sur la home, au chargement, le carrousel d'images est trop large de 20 px et décalé vers
la droite, puis « se recale vers la gauche » une fraction de seconde plus tard. Sur un
téléphone en 4G, ce défaut dure environ une seconde. C'est le premier écran du site.

**La cause**, lue dans le fichier fautif : une feuille de style du plugin JetEngine annule
les marges du carrousel mais oublie d'annuler sa largeur. La feuille qui répare
(`swiper.min.css`) existe, mais elle est chargée beaucoup trop tard — remesuré
aujourd'hui : elle arrive plus de **340 Ko** après la fin de l'en-tête de la page.

### Où aller

1. `https://agendasabauda.eu/wp-admin/` → menu **« Snippets »** → **« Tous les snippets »**.
2. Ouvrez le snippet dont le code contient **`cs-no-hide-empty-cols`**.
3. **Sauvegardez-le d'abord** (voir § 0 bis a).

### Où coller exactement

Dans la zone de code, cherchez avec **Ctrl + F** la chaîne **`</style>`**.

- **Vous la trouvez** → placez le curseur **juste avant** ce `</style>` et collez le bloc
  ci-dessous. (C'est important : dans un snippet PHP, coller tout en bas du code, après le
  `</style>`, mettrait le CSS en dehors de la balise de style — il ne servirait à rien, et
  pourrait casser le snippet.)
- **Vous ne la trouvez pas** → c'est un snippet de CSS pur : collez alors tout à la fin du
  code.

Vous collez **à la fin du CSS**, après tout le reste, notamment après le bloc
« Anti-flash Swiper pre-init » qui s'y trouve déjà.

### Le bloc à coller

```css
/* === DEBUT correctif carrousel - largeur du wrapper (2026-08-03) === */
/* POURQUOI : la feuille jet-engine/frontend.css v3.8.11.2 pose
     .jet-listing-grid__items{ width:calc(100% + 20px); margin:0 -10px }
   puis, pour la variante carrousel :
     .jet-listing-grid__items.swiper-wrapper{ ...; margin-left:0; margin-right:0 }
   Les marges negatives sont annulees, mais PAS la largeur. Resultat : le bloc
   qui contient les cartes deborde de 20 px vers la droite pendant tout le debut
   du chargement, jusqu au moment ou la feuille swiper.min.css est enfin lue. Or
   cette feuille arrive tres tard : dans le corps de page, plus de 340 Ko apres
   la fin du head (mesure le 2026-08-03).
   MESURE le 2026-08-03 : bloc de 370 px dans un conteneur de 350 px en mobile
   390, et 930 dans 910 en desktop 1366, pendant toute la premiere seconde en
   4G. On impose ici, des le premier octet, la largeur que swiper.min.css finit
   de toute facon par imposer une seconde plus tard : on ne cree aucun etat
   nouveau, on supprime seulement un etat transitoire faux.
   NB : commentaire volontairement sans accent et sans apostrophe. Ce snippet
   assemble des chaines PHP ; il porte lui-meme cet avertissement plus haut. */
.jet-listing-grid__slider .jet-listing-grid__items.swiper-wrapper{
  width: 100% !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}
/* === FIN correctif carrousel === */
```

Puis **Enregistrer**. Ne changez rien d'autre : ni le titre, ni la priorité, ni la portée,
ni l'interrupteur d'activation.

### Vérification — en trois temps

**Temps 1 — est-ce que ça a seulement atteint le site ? (15 secondes)**

Ouvrez `https://agendasabauda.eu/`, faites **Ctrl + U** (afficher le code source), puis
**Ctrl + F** et cherchez `DEBUT correctif carrousel`.

- Trouvé → le correctif est bien servi aux visiteurs. Continuez.
- Pas trouvé → il n'est pas actif. Ne cherchez pas plus loin, revenez au snippet.

**Temps 2 — est-ce que ça répare ? (3 minutes)**

1. Dans Chrome, ouvrez `https://agendasabauda.eu/`, puis **F12** pour ouvrir les outils de
   développement, et activez le **mode appareil** (l'icône téléphone/tablette). Réglez la
   largeur sur **390 px**.
2. Onglet **Réseau** → rechargez la page → repérez la ligne `swiper.min.css` →
   **clic droit → « Bloquer l'URL de la requête »**. Rechargez.
   *Cela fige le défaut de façon permanente : plus besoin de le guetter.*
3. Onglet **Console**, collez ceci (c'est une simple lecture, ça n'écrit rien) :

   ```js
   document.querySelectorAll('.jet-listing-grid__slider').forEach(c => {
     const w = c.querySelector('.jet-listing-grid__items');
     const a = Math.round(c.getBoundingClientRect().width);
     const b = Math.round(w.getBoundingClientRect().width);
     if (a) console.log('conteneur', a, '| wrapper', b, '| écart', b - a);
   });
   ```

   **Ce que vous devez voir :** `conteneur 350 | wrapper 350 | écart 0`.
   *(Avant le correctif, c'était `conteneur 350 | wrapper 370 | écart 20`.)*

4. Repassez la largeur à **1366 px** et recollez la même commande.
   **Attendu : `conteneur 910 | wrapper 910 | écart 0`.** *(Avant : `910 / 930 / 20`.)*

**Temps 3 — est-ce que rien d'autre n'a bougé ? (2 minutes)**

Retirez le blocage réseau (clic droit sur la ligne → « Débloquer »), rechargez, puis
**faites défiler le carrousel à la main**, sur mobile et sur desktop. Le défilement, les
points de pagination et la hauteur des cartes doivent être **exactement comme avant**.

### Marche arrière en 30 secondes

Snippets → le snippet `cs-no-hide-empty-cols` → sélectionnez tout ce qui va de
`/* === DEBUT correctif carrousel` jusqu'à `/* === FIN correctif carrousel === */`
inclus → supprimez → **Enregistrer**. Le reste du snippet n'est pas touché.

*Repli plus radical, si le snippet entier pose problème : le désactiver avec son
interrupteur. Mais attention, cela emporte aussi l'anti-flash du carrousel et la mise en
colonne mobile — le site sera plus abîmé qu'avant. À ne faire qu'en dernier recours.*

### Le risque, nommé

Ce correctif ne touche que les blocs qui remplissent **trois conditions à la fois**.
Recensement refait aujourd'hui sur le HTML réellement servi : **2 éléments sur la home, et
zéro ailleurs** (zéro sur `/tout-l-agenda/`, `/ce-week-end/`, les pages catégorie, les
fiches événement). Les autres grilles JetEngine du site n'ont pas la classe concernée et
ne sont pas touchées. **Risque : très faible.**

> ⚠️ Attention à un piège de comptage : une recherche brute du mot
> `jet-listing-grid__slider` dans la page en trouve **17**. Ce sont des morceaux de texte
> CSS, pas des carrousels. Les vrais éléments sont bien **2**.

---

## ÉTAPE 2 — Le menu mobile recouvert par le header

### Ce que vous réparez

Sur la home, sur téléphone : si le visiteur fait défiler la page puis ouvre le menu, les
**101 premiers pixels du menu sont recouverts par le header**. La croix de fermeture est
inaccessible, la première entrée du menu aussi. Le visiteur ne peut plus refermer le menu
autrement qu'en rechargeant la page ou en utilisant le bouton retour. C'est une impasse.

**La cause :** le header passe devant (niveau 41), le menu reste derrière (niveau 40). On
fait passer le menu au niveau 60.

**Le défaut n'est PAS partout :** il est limité aux pages d'accueil (`/`, `/explore/*`,
`/choisir/*`, `/it/home-it/`). Les pages internes utilisent un autre menu, qui est déjà
au-dessus et fonctionne correctement. On n'y touche pas.

### Une correction à connaître

Un document antérieur disait de poser ce correctif « juste à côté de la règle qui pose
`z-index:41` ». **Cette règle n'est pas dans le snippet où vous allez coller.** Elle se
trouve à la **ligne 731 du snippet `cs-composants-styles`** — le gros snippet de 71 Ko, le
seul qu'il ne faut surtout pas toucher.

*Revérifié aujourd'hui, mot pour mot, à la ligne 731 :*
`.as-home-sticky-panel { position: static; z-index: 41; background: #FBF7F0; }`

**Vous ne modifiez pas cette ligne. Vous n'ouvrez pas ce snippet.** Le correctif va dans
`cs-hdr-compact`, pour une autre raison : c'est déjà ce snippet-là qui contient les cinq
règles qui s'occupent du menu de la home. Tout ce qui concerne ce panneau reste ainsi au
même endroit. Et comme `cs-hdr-compact` est servi **après** `cs-composants-styles`, notre
règle l'emporte.

### Où aller

1. `https://agendasabauda.eu/wp-admin/` → menu **« Snippets »** → **« Tous les snippets »**.
2. Ouvrez le snippet dont le code contient **`cs-hdr-compact`**.
3. **Sauvegardez-le d'abord** (voir § 0 bis a).

### Où coller exactement

Comme à l'étape 1 : cherchez **`</style>`** avec Ctrl + F et collez **juste avant**. Si
vous ne le trouvez pas, collez tout à la fin du code.

Vous collez donc après les règles qui commencent par `.as-menu-overlay .as-site-header__menu`,
qui sont déjà les dernières du snippet.

### Le bloc à coller

```css
/* === DEBUT correctif menu mobile - z-index du panneau (2026-08-03) === */
/* POURQUOI : sur la home, le panneau de header passe en position:fixed au-dela
   du seuil de defilement, avec z-index:41 et 101 px de hauteur. Cette valeur 41
   est posee par .as-home-sticky-panel, a la ligne 731 du snippet
   cs-composants-styles - PAS ici, et on ne va pas y toucher. Le panneau de menu,
   lui, reste a z-index:40 : il se deplie DERRIERE le header.
   MESURE le 2026-08-03, home mobile 390 px apres 600 px de defilement : le point
   situe a 30 px du haut de la fenetre renvoie un DIV du header et non un lien du
   menu ; la croix de fermeture (rectangle 350,16,20,20) ne repond pas ; la
   premiere entree du menu, a 62 px, ne repond pas non plus. Un panneau ouvert
   passe DEVANT le reste de la page, jamais dessous.
   60 et non 42 : cela laisse la place au menu deroulant territoire (z-index 95,
   mais enferme dans le contexte de superposition du panneau de header, donc sans
   effet ici) et cela reste tres loin sous le bandeau cookies Complianz
   (z-index 99 999), qui doit rester prioritaire.
   NB : commentaire volontairement sans accent et sans apostrophe. Ce snippet
   assemble des chaines PHP. */
.as-menu-overlay{ z-index: 60 !important; }
/* === FIN correctif menu mobile === */
```

Puis **Enregistrer**. Rien d'autre ne change.

### Vérification — en trois temps

**Temps 1 — est-ce que ça a atteint le site ? (15 secondes)**

`https://agendasabauda.eu/` → **Ctrl + U** → **Ctrl + F** → cherchez
`DEBUT correctif menu mobile`. Trouvé = c'est en ligne.

**Temps 2 — le test à la machine (2 minutes)**

1. Chrome, `https://agendasabauda.eu/`, **F12**, mode appareil, largeur **390 px**.
2. Faites défiler d'environ **600 px** (le header doit être devenu compact et collé en haut).
3. Ouvrez le menu (le bouton hamburger).
4. Onglet **Console**, collez :

   ```js
   const o = document.querySelector('.as-menu-overlay');
   const e = document.elementFromPoint(195, 30);
   console.log('z-index :', getComputedStyle(o).zIndex,
               '| à y=30 :', e.tagName, o.contains(e) ? 'DANS le menu ✅' : 'HORS du menu ❌');
   ```

   **Attendu : `z-index : 60 | à y=30 : DIV DANS le menu ✅`.**
   *(Avant le correctif : `z-index : 40 | à y=30 : DIV HORS du menu ❌`.)*

**Temps 3 — le test qui compte vraiment (3 minutes)**

**Sur un vrai téléphone**, pas seulement dans Chrome :

1. Ouvrez la home, faites défiler, ouvrez le menu, **cliquez la croix en haut à droite**.
   → Le menu doit se fermer. C'est tout l'objet du correctif.
2. Menu fermé : la page défile-t-elle normalement ? Les liens du haut de page
   répondent-ils toujours ? *(C'était le vrai risque de ce correctif — un panneau
   invisible qui intercepterait tous les clics. Mesuré : ce n'est pas le cas, le panneau
   fermé est envoyé hors écran.)*
3. Si le bandeau cookies n'a pas encore été accepté : ouvrez le menu et vérifiez que le
   **bandeau cookies reste bien au-dessus** du menu.

### Marche arrière en 30 secondes

Snippets → `cs-hdr-compact` → supprimez tout ce qui va de
`/* === DEBUT correctif menu mobile` jusqu'à `/* === FIN correctif menu mobile === */`
inclus → **Enregistrer**.

### Le risque, nommé

Un inventaire complet des niveaux de superposition de la home mobile a été fait. **Un seul
élément change de position relative : le panneau de header, qui passe derrière le menu
ouvert.** C'est exactement l'effet recherché. Le bandeau cookies (99 999) et le bouton de
consentement (9 998) restent au-dessus. **Risque : très faible.**

---

## ÉTAPE 3 — Le territoire transmis aux pages catégorie (JavaScript)

### Ce que vous réparez

Un visiteur choisit « Savoie », puis clique sur une tuile « Cinéma ». Il arrive sur la page
Cinéma… avec des événements du Piémont et du Comté de Nice. **Votre plainte était exacte.**

**Remesuré aujourd'hui**, sur la page catégorie « Jeune public / famille » :

| Situation | Nombre d'événements | Le menu « Territoire » affiche |
|---|---|---|
| Sans rien | **11** | rien de sélectionné |
| Avec le cookie « Savoie » | **8** *(tous territoires mélangés)* | rien de sélectionné |
| Avec `?filtre2=savoie` dans l'adresse | **2** *(Savoie uniquement)* | **Savoie** ✅ |

Conclusion : le cookie **trie et raccourcit**, il ne **filtre pas**. Le seul mécanisme qui
filtre vraiment est le paramètre `?filtre2=` dans l'adresse. Le correctif ajoute donc ce
paramètre aux liens sortants des pages de territoire.

Bonus vérifié : sur la page d'arrivée, la liste déroulante « Territoire » se positionne
toute seule sur « Savoie ». Le visiteur **voit** le filtre qui s'applique, et peut le retirer.

### Votre décision a été appliquée

Vous avez tranché : **pas de repli sur cookie.** Un visiteur arrivé par Google sur une page
« Concerts » avec un vieux cookie ne doit pas voir sa liste filtrée à son insu.

Le bloc « repli » a donc été **retiré** du code ci-dessous. Conséquence : le correctif ne
s'applique **que** depuis les pages `/explore/…` et `/choisir/…`, c'est-à-dire exactement le
parcours que vous avez décrit. Partout ailleurs, il ne fait strictement rien.

*Ce que j'ai vérifié moi-même après ce retrait, et non supposé :*

- **La syntaxe est valide** : le code a été passé à `node --check` (Node 22). Aucune erreur.
- **Aucune variable orpheline** : la variable `c`, qui servait uniquement à lire le cookie,
  a disparu partout — vérifié par comptage, elle apparaît **0 fois** dans le code final.
  Les autres variables (`TERR`, `m`, `slug`, `u`, `a`) sont toutes déclarées et toutes
  utilisées.
- **Les accolades et parenthèses sont équilibrées** : 7 `{` pour 7 `}`, 18 `(` pour 18 `)`.
- **Le comportement restant est intact** : le code a été exécuté sur cinq scénarios
  simulés. Depuis `/explore/savoie/` il réécrit bien les liens en `?filtre2=savoie` ;
  depuis `/choisir/piemont/`, en `?filtre2=piemont` ; **depuis une page « Concerts » avec un
  vieux cookie, il ne réécrit plus rien du tout** — ce qui est précisément votre décision ;
  et dans aucun scénario il ne touche `/tout-l-agenda/`, `/ce-week-end/`, les liens externes
  ou les fiches événement.

### ⚠️ Une correction importante par rapport au document de mesures

Le document d'origine dit de créer « un snippet de type **JavaScript** ». **Ne faites pas
ça.**

Le site tourne sur **Code Snippets version gratuite**, et il est déjà établi noir sur blanc
dans la documentation du projet (`wordpress/build-recipes/STATUS.md`) que les snippets de
type **CSS** de cette version gratuite **s'enregistrent, s'activent, n'affichent aucune
erreur — et ne sont jamais envoyés au visiteur.** Tout le CSS du chantier a été perdu
pendant des semaines à cause de ça. Le type **JavaScript** appartient à la même famille de
fonctionnalités payantes : il y a tout lieu de croire qu'il échouerait de la même manière
silencieuse.

**On utilise donc la méthode qui est prouvée sur ce site** : un snippet **PHP**, portée
« site public », qui envoie le JavaScript en pied de page.

### Où aller

1. `https://agendasabauda.eu/wp-admin/` → menu **« Snippets »** → **« Ajouter »**.
2. **Titre** : `CS · Territoire vers hubs (filtre2)`
3. **Type** : **Fonctions PHP** (l'onglet par défaut). *Pas* CSS, *pas* JavaScript.
4. **Portée / exécution** : **« Exécuter uniquement sur le site public »**
   (« Run snippet everywhere » convient aussi, mais le site public est plus propre).
5. Collez le code ci-dessous dans la zone de code, **en entier**, tel quel.
6. **Enregistrer et activer.**

### Le code à coller

Copiez tout, **sans rien réindenter** — en particulier, la ligne
`AS_TERRITOIRE_HUBS;` doit rester **collée à gauche**, sans espace devant.

```php
add_action('wp_footer', function () {
    echo <<<'AS_TERRITOIRE_HUBS'
<script>
/* ═══ DÉBUT correctif territoire → hubs (2026-08-03) ═══ */
/* POURQUOI : le hub catégorie LIT le cookie as_territoire, mais il ne s'en sert
   que pour TRIER et raccourcir la liste (11 → 8 événements, tous territoires
   confondus). Le seul mécanisme qui FILTRE réellement est le paramètre GET
   ?filtre2=<slug> (11 → 2, Savoie uniquement — mesuré le 2026-08-03). On ajoute
   donc ce paramètre aux liens sortants vers les hubs, depuis les pages de
   territoire UNIQUEMENT.
   PAS DE REPLI SUR COOKIE (décision de Franck, 2026-08-03) : un visiteur arrivé
   par Google sur une page « Concerts » avec un vieux cookie ne doit pas voir sa
   liste filtrée à son insu. Le correctif ne s'applique donc que depuis
   /explore/<slug>/ et /choisir/<slug>/.
   VOLONTAIREMENT PAS /tout-l-agenda/ NI /ce-week-end/ : ces deux pages ignorent
   filtre2 (50 événements avant comme après), le paramètre y serait un mensonge.
   NE JAMAIS UTILISER ?territoire= À LA PLACE : c'est le nom de la taxonomie, et
   /evenements/categorie/<x>/?territoire=savoie répond HTTP 200 avec 0 octet
   (page totalement blanche, reproduit sur 2 catégories le 2026-08-03). */
(function () {
  var TERR = ['savoie', 'piemont', 'vallee-d-aoste', 'comte-de-nice'];
  var m = location.pathname.match(/\/(?:explore|choisir|territoire)\/([a-z0-9-]+)\/?$/);
  var slug = m && TERR.indexOf(m[1]) !== -1 ? m[1] : null;

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
</script>
AS_TERRITOIRE_HUBS;
}, 99);
```

*Ici les accents et les apostrophes sont autorisés, contrairement aux étapes 1 et 2 : la
construction utilisée (`<<<'AS_TERRITOIRE_HUBS'`) transmet le texte tel quel, sans aucune
interprétation. Vérifié en exécutant réellement ce code : le JavaScript produit est
identique, caractère pour caractère, à celui qui a été validé par `node --check`.*

### Vérification — en trois temps

**Temps 1 — est-ce que ça a atteint le site ? (15 secondes)**

C'est **le test le plus important de cette étape**, parce qu'il attrape précisément le mode
de panne silencieuse décrit plus haut.

Ouvrez `https://agendasabauda.eu/explore/savoie/`, faites **Ctrl + U**, puis **Ctrl + F** et
cherchez `DÉBUT correctif territoire`.

- **Trouvé** → le script est bien envoyé aux visiteurs. Continuez.
- **Pas trouvé** → le snippet ne sort pas. Inutile de tester la suite : vérifiez que le
  snippet est bien **activé**, de type **Fonctions PHP**, et en portée **site public**.

**Temps 2 — le test à la machine (2 minutes)**

Sur `https://agendasabauda.eu/explore/savoie/`, ouvrez la Console (**F12**) et collez :

```js
const a = [...document.querySelectorAll('a[href*="/evenements/categorie/"], a[href*="/type-de-lieu/"]')];
console.log(a.filter(x => x.href.includes('filtre2=')).length + ' / ' + a.length + ' liens réécrits');
console.log('tout-l-agenda touché ?',
  [...document.querySelectorAll('a[href*="tout-l-agenda"], a[href*="ce-week-end"]')]
    .some(x => x.href.includes('filtre2=')) ? 'OUI ❌' : 'non ✅');
```

**Attendu : tous les liens réécrits (« 78 / 78 » ou un nombre voisin selon le catalogue du
jour), et `tout-l-agenda touché ? non ✅`.**

**Temps 3 — le test qui compte vraiment (3 minutes)**

1. Depuis `/explore/savoie/`, **cliquez une tuile de catégorie** (par exemple « Cinéma »).
2. Sur la page d'arrivée, la liste déroulante « Territoire » doit afficher **Savoie**, et la
   liste ne doit contenir **que** des événements de Savoie.
3. **Test de l'échappatoire** — indispensable : sur cette même page, remettez la liste
   « Territoire » sur « Territoire » et cliquez « Appliquer ». **Tous les territoires
   doivent revenir.** Le visiteur ne doit jamais être enfermé dans un filtre.
4. **Test de votre décision** : ouvrez un onglet de navigation privée, allez sur
   `/explore/savoie/` (pour poser le cookie), puis tapez directement dans la barre
   d'adresse `https://agendasabauda.eu/evenements/categorie/concerts-musique/`.
   **La liste ne doit PAS être filtrée sur la Savoie.** C'est exactement ce que vous avez
   demandé, et c'est ce que le retrait du bloc « repli » garantit.

### Marche arrière en 5 secondes

Snippets → le snippet `CS · Territoire vers hubs (filtre2)` → **interrupteur sur
« Désactivé »**. Un clic, effet immédiat au rechargement suivant. **C'est le correctif le
plus facile à annuler des trois** — c'est précisément pour cela qu'il est dans un snippet
à part, et pas ajouté à un snippet existant.

### Ce que ce correctif ne couvre pas — à savoir

- Il ne s'applique **que** depuis `/explore/…` et `/choisir/…`. C'est votre décision.
- **Point relevé aujourd'hui** : la page `/que-faire-en-savoie/` existe, répond
  normalement, et contient 51 liens vers des pages catégorie — mais elle **ne sera pas
  couverte** par ce correctif, car son adresse ne suit pas le modèle `/explore/…` ou
  `/choisir/…`. Ce n'est pas un défaut du correctif, c'est une limite connue. Si ces pages
  « que-faire-en-… » deviennent importantes, il faudra les ajouter — à traiter plus tard,
  après avoir vérifié quelles adresses de ce type existent réellement.
- Côté référencement : les adresses filtrées portent une balise « canonique » qui renvoie
  vers l'adresse sans paramètre. Le risque est faible mais non nul — à surveiller dans la
  Search Console, rubrique « pages non indexées → autre page avec balise canonique
  correcte ».

---

## CE QU'IL NE FAUT PAS DÉPLOYER

### Le correctif `:has()` proposé le 1er août — à laisser de côté

Ce correctif visait une « section blanche » censée apparaître sur les navigateurs anciens.
**Les mesures montrent que cette section blanche n'existe pas** : sur un vieux navigateur,
ce n'est pas un blanc qui apparaît, c'est un tiers de la page d'accueil mobile qui
disparaît purement et simplement — trois sections entières (« Nouveautés », « En
évidence », « L'agenda à venir »). Le diagnostic s'était trompé de symptôme.

**Et le correctif proposé ne répare pas ce vrai problème.** Mesuré dans les deux mondes :
sur un vieux navigateur, il ne change **strictement rien** ; sur un navigateur récent — donc
chez la quasi-totalité de vos visiteurs — il **ajoute 26 px de vide** en faisant réapparaître
des paragraphes vides. Il dégrade le cas courant sans réparer le cas rare.

**Conclusion : ne le déployez pas.** Une version corrigée existe (dans `CORRECTIFS_CSS_PRETS.md`
§ 5), mais elle devrait aller dans `cs-composants-styles`, le gros snippet de 71 Ko — et
avant même de l'envisager, il faut répondre à une question qui n'a pas de réponse
aujourd'hui : **quelle part de vos visiteurs utilise un navigateur si ancien ?** Ce chiffre
est dans vos statistiques de fréquentation. Tant qu'on ne l'a pas, ce correctif n'a aucune
priorité — l'estimation est de l'ordre de 1 %.

---

## APRÈS DÉPLOIEMENT — ce qu'il faut resynchroniser

Ces trois correctifs ne créent pas de dette nouvelle, mais ils sont l'occasion de solder
celle qui existe. Rien d'urgent, rien à faire dans la minute — mais rien à oublier non plus.

### 1. La dette principale : issue #9, production → dépôt

`wordpress/design-system/components.css` (**31 050 octets** dans le dépôt) est en retard de
**40 Ko** sur le snippet `cs-composants-styles` de la production (**71 235 caractères**,
remesuré aujourd'hui ; il en faisait 70 875 le 1er août — **la production continue de bouger
sous le dépôt**).

**Le sens de la réconciliation est : production → dépôt. Jamais l'inverse.**

- Récupérer le contenu réel du snippet de production.
- Le comparer au fichier du dépôt et fusionner **en gardant la production comme référence**.
- **Ne surtout pas lancer `wordpress/scripts/apply-components.mjs`** tant que ce n'est pas
  fait : ce script écraserait le snippet de production par la version courte du dépôt, et
  détruirait les 40 Ko — sans retour arrière.

### 2. Une dette voisine, découverte aujourd'hui

Quatre snippets tournent en production **sans aucune trace dans le dépôt** — ils n'ont
jamais été versionnés, et n'existent que dans WordPress :

| Snippet | Taille | Dans le dépôt ? |
|---|---|---|
| `cs-hdr-compact` | 6 896 c. | **non** |
| `cs-no-hide-empty-cols` | 4 540 c. | **non** |
| `cs-nav-logo-reveal` | 178 c. | **non** |
| `cs-cat-empty-hide` | 159 c. | **non** |

Ce sont précisément les deux premiers que vous modifiez aux étapes 1 et 2. **À verser au
dépôt une fois le déploiement stabilisé** (par exemple dans
`wordpress/design-system/`), avec les correctifs dedans. C'est la seule façon de ne pas
refaire le même diagnostic dans six mois.

### 3. Le nouveau snippet de l'étape 3

À verser lui aussi au dépôt, avec un script `apply-` si vous voulez pouvoir le
redéployer — c'est la règle du projet : « toute modif du site passe par un script versionné ».

### 4. Une issue à ouvrir, sans rapport avec ces correctifs

`/evenements/categorie/<n'importe laquelle>/?territoire=savoie` répond **HTTP 200 avec
0 octet** — une page totalement vide, mais annoncée comme valide. **Revérifié aujourd'hui,
toujours vrai** (0 octet, alors que la même page avec `?zzz=1` renvoie 413 988 octets
normaux). C'est une adresse publique qui renvoie une réponse vide en disant « tout va
bien » : Google peut l'indexer. À ouvrir comme issue séparée dans `docs/site_issues.json`.

---

## Traçabilité

**Aucune écriture n'a été faite sur le site pour produire ce document.** Ni snippet créé,
ni modifié, ni activé. Le site n'a été consulté qu'en lecture (téléchargement de pages
publiques). Le déploiement est votre geste, et le vôtre seul.

Dans le dépôt, **ce fichier est le seul écrit**. Aucun `git add`, `git commit`, `git push`.

**Remesuré en direct le 2026-08-03 pour ce document** (et non recopié) : les tailles et
positions des six blocs de style de la home ; les 71 235 caractères de `cs-composants-styles` ;
les 31 050 octets de `components.css` ; la ligne 731 et la ligne 440 de `cs-composants-styles` ;
les deux règles fautives de `jet-engine/frontend.css` ; le nombre réel de carrousels (2) ;
le cookie posé par `/explore/savoie/` ; les comptages 11 / 8 / 2 événements et le
positionnement du menu déroulant ; la réponse vide en HTTP 200 de `?territoire=`.

**Validé mécaniquement** : le JavaScript de l'étape 3, amputé du bloc « repli », passe
`node --check` ; il a été exécuté sur cinq scénarios ; et le code PHP qui l'enveloppe passe
`php -l` et produit un JavaScript identique caractère pour caractère.

**Repris du document de mesures sans revérification** (mesures faites au navigateur, que je
ne pouvais pas refaire ici) : les largeurs 370/350 et 930/910 pendant le chargement ; les
relevés de clics sur le menu ouvert ; les tableaux avant/après ; l'inventaire des niveaux de
superposition ; les chiffres du § « ce qu'il ne faut pas déployer ».
