# Skin publicitaire (bloc 4) — note de passation

**Écrit le 2026-08-05, à l'issue d'une session qui a produit dix versions du même fichier
sans jamais aboutir.** À lire en entier avant de toucher à `deploy/wordpress/cs-regie.php` :
la plupart des impasses ci-dessous ont l'air d'être de bonnes idées quand on arrive dessus.

**Pourquoi cette note existe** : la session qui a écrit ces dix versions n'avait pas d'accès
navigateur (proxy bloquant), donc aucun moyen de scroller la page, de mesurer une position
ou de vérifier un rendu. Chaque diagnostic a été inféré depuis des captures d'écran envoyées
à la main. Plusieurs versions ont corrigé un symptôme en fabriquant le suivant. **Ne pas
reprendre ce travail sans pouvoir observer la page en vrai.**

---

## 1. État actuel

- Fichier : `deploy/wordpress/cs-regie.php`, **v1.9**, commit `1e69289`.
- **Déployé en production** dans `wp-content/mu-plugins/cs-regie.php` (md5 vérifié identique
  au fichier git : `d4cb3c190fb21cb019c038e88990bb75`).
- Campagne de test active : bloc 4, « Spazio Sabaudo », GIF animé 1920×1080 (4 images),
  `https://agendasabauda.eu/wp-content/uploads/2026/08/spaziosabaudofrv3.gif`.
  Elle se termine le 2026-08-06 — après cette date la skin ne s'affiche plus du tout et il
  faudra réactiver ou recréer une campagne dans le backoffice pour tester.

**Le défaut ouvert : la skin saute pendant le défilement.** Non résolu après quatre
tentatives distinctes (v1.4, v1.5, v1.6, v1.9). **Cause mesurée depuis** — cf. §2 et §4
piège n°6 : elle ne se corrige pas par un réglage, elle impose de sortir la skin du flux.

### Comment c'est construit aujourd'hui

| Élément | Rôle |
|---|---|
| `#cs-skin` | Un seul élément portant toute la créative en `background`, `position:sticky` |
| `#cs-skin-track` | Le rail dans lequel la skin colle — un élément sticky ne peut pas sortir de son parent |
| `#cs-skin-spacer` | Une cale insérée en JS après la pile menu + barre territoire, pour dégager le bandeau |
| `--cs-skin-h` / `--cs-skin-band` | Hauteur de l'image et hauteur de son bandeau, liées par la géométrie (bandeau = 2/9 de l'image) |

Comportement visé : la skin défile avec la page, puis se fige quand le bas du bandeau
atteint le haut de la fenêtre — le bandeau se range au-dessus du bord, les gouttières
restent affichées, le menu opaque recouvre leur haut. Le rail s'arrête au haut du pied de
page pour que la skin se décolle à son arrivée.

---

## 2. Diagnostic — FAIT, la cause est mesurée

Ces vérifications ont été menées au navigateur le 2026-08-05 depuis une session locale.
**Résultat en §4, piège n°6** : la page raccourcit de 89 px en cours de défilement quand
l'en-tête compact sort du flux, et la skin est ancrée à la page. Cause close.

Deux détails de méthode, s'il faut remesurer :

- `scroll-behavior:smooth` fausse toute mesure synchrone — le désactiver avant de mesurer ;
- `body` est lui-même un conteneur de défilement (`overflow-x:hidden` du thème force
  `overflow-y:auto`). Ce n'est pas une règle de la skin, ne pas partir sur cette piste.

---

## 3. La recommandation de fond : le format est mal découpé

La [spec du format Page Skin (IQD/IAB)](https://techspecs.iqd-ao.de/en/index.php?title=Page_Skin)
prévoit **deux créatives séparées** :

- un **fond** 1920×1080 qui reste **fixe dans la fenêtre**, en permanence, et ne bouge jamais ;
- un **bandeau** distinct (1000×333 ou 1000×250) qui vit dans le flux et défile naturellement.

La créative de test fusionne les deux dans un seul fichier. Elle enfreint en plus deux
recommandations explicites de cette même spec : ne pas mettre de **texte** dans le motif de
fond (« L'atmosfera sabauda » y est), et ne pas y ménager de **zone creuse ou blanche** (la
fenêtre crème centrale, pensée pour coïncider avec la colonne de contenu — coïncidence que
le format ne garantit pas, puisque la visibilité dépend de la résolution et de la mise en
page).

**Conséquence directe** : tout le code de `cs-regie.php` essaie de faire faire deux métiers
contradictoires à une seule image — défiler *et* rester collée — avec un raccord au pixel.
C'est la source de toute la difficulté.

**Avec deux créatives séparées, il n'y a plus de problème à résoudre** : le fond est
`position:fixed` (il ne bouge jamais, donc il est insensible à tout ce qui remue dans la
page), le bandeau est un bloc normal dans le flux (il défile tout seul). Ni sticky, ni rail,
ni cale, ni JavaScript. Zéro calcul, donc zéro saut possible.

**Le fond fixe ne demande AUCUNE nouvelle créative** : il fonctionne avec le fichier
actuel, c'est ce que faisait la v0.3. La seconde créative sert uniquement à récupérer le
bandeau défilant — c'est un gain de confort, pas une condition.

À savoir avant d'arbitrer : en fond fixe, la bande titre de la créative actuelle
(« L'atmosfera sabauda ») sera **largement masquée par l'en-tête**. Sur l'accueil au
chargement la pile d'en-têtes fait ~450 px et cette bande ~150 px : elle sera entièrement
derrière ; une fois défilé, l'en-tête compact ne fait plus que ~130 px et elle réapparaîtra
en partie. C'est exactement ce que la spec anticipe en déconseillant le texte dans le fond.
Autrement dit : le fond fixe supprime le bug tout de suite, mais transforme le message de
l'annonceur en ambiance. Pour qu'il reste lisible, il faut le bandeau séparé.

**Ordre recommandé** : passer en fond fixe maintenant (le site cesse de sauter, sans rien
attendre de personne), et demander le bandeau 970×250 pour la campagne suivante — ajout
indépendant qui ne remet rien en cause.

---

## 4. Les pièges, et ce que chaque version a coûté

Numérotés pour pouvoir s'y référer. **Chacun a l'air d'une bonne idée quand on arrive
dessus** — c'est exactement pour ça qu'ils sont écrits.

### 1. Le découpage en plusieurs éléments fabrique des trous (v0.4 → v0.7, quatre versions)

Bandeau + deux bandes latérales, chacun affichant une zone du fichier via
`background-position`. Le bandeau était en `background-size:1920px auto` **centré** : sur un
écran de 1477px il montrait donc les 1477px du **milieu** d'une image de 1920, pendant que
les bandes en montraient les **bords extrêmes**. Entre les deux, ~220px de créative de
chaque côté n'étaient affichés nulle part.

> « On a des trous de partout, ça ne fait pas une skin, c'est n'importe quoi. »

Trois versions (v0.5, v0.6, v0.7) ont corrigé des **symptômes** de ce découpage — seuil du
bandeau, ancrage des colonnes, largeur des colonnes — sans voir que le découpage lui-même
était le défaut.

**Règle** : si plusieurs éléments affichent la même image, ils doivent partager **exactement
la même mise à l'échelle** (`background-size` identique et exprimé dans la même unité), et
se partager ses colonnes sans trou ni recouvrement. Sinon le raccord ne peut pas tomber juste.

### 2. Plusieurs éléments affichant le HAUT de l'image le montrent en double (v1.3)

Correction du piège n°1 : faire partir les bandes latérales de la ligne 0 pour que le
raccord tombe juste en haut de page. Ça marche — jusqu'au premier défilement, où le bandeau
glisse par-dessus des bandes qui montrent toujours ce même haut d'image. Le titre de
l'annonceur apparaissait alors **deux fois**, à deux hauteurs.

> « C'est comme si tu avais superposé deux gifs. »

### 3. Le navigateur peint le défilement AVANT d'exécuter le JS (v1.0, v1.4, v1.5)

Le piège le plus coûteux — trois versions.

Repositionner un élément dans un écouteur `scroll` ne peut pas suivre : le compositeur peint
en continu, l'événement JS arrive après coup. Deux manifestations :

- **repositionnement à chaque pixel** (v1.0) → l'élément traîne derrière le contenu, ce que
  Franck a décrit comme « un effet de parallaxe », « trop saccadé » ;
- **bascule d'état sur seuil** (v1.4, v1.5) → à chaque cran de molette (~100px d'un coup)
  l'élément est d'abord peint trop loin, puis remis en place au tour suivant : saut
  d'exactement un cran.

**Règle** : tout ce qui doit bouger avec le défilement se fait en CSS (`position:sticky`,
`position:fixed`, `background-attachment:fixed`) — jamais dans un écouteur `scroll`.
Corollaire : j'ai cherché deux fois du côté des **valeurs** calculées alors que le défaut
tenait à l'**instant** du calcul.

### 4. `offsetParent === null` ne veut pas dire « masqué » (v1.1 → v1.2)

Il vaut aussi `null` pour **tout élément en `position:fixed`**. Utilisé pour écarter les
en-têtes masqués, il les a tous écartés — plus aucun repère, la cale retombait en haut de
page et la créative repassait au-dessus du menu.

**Utiliser `getClientRects().length === 0`**, qui ne répond vide que si l'élément n'est
vraiment pas rendu.

### 5. Sur l'accueil, le menu est DANS le contenu (v0.8 → v0.9)

`.as-site-header` y est masqué (snippet 62) et le menu est baké dans le contenu de la page,
donc **à l'intérieur de `.site`**. Un `padding-top` sur `.site` pousse donc le menu vers le
bas lui aussi, et la bande s'affiche **au-dessus** de lui.

D'où la cale insérée en JS après la pile d'en-têtes : elle tombe au bon endroit sur les deux
types de page sans les distinguer. **L'accueil et les pages intérieures n'ont pas la même
structure d'en-tête — toujours tester les deux.**

### 6. La page RACCOURCIT de 89 px en cours de défilement — cause mesurée du saut

**Mesuré au navigateur le 2026-08-05** (session locale), après avoir été supposé ici. Ce
n'est plus une piste, c'est la cause.

Sur l'accueil, entre `y=250` et `y=300`, trois choses basculent ensemble :

| | avant le seuil | après |
|---|---|---|
| `body.cs-hdr-min` | absent | présent |
| `.as-home-sticky-panel` | `position:static` | `position:fixed` |
| haut du rail `#cs-skin-track` | 339,3 px | **250,3 px** |

L'en-tête compact fait passer le panneau en `position:fixed` : il **sort du flux**, et tout
ce qui est ancré en dessous remonte de **89 px instantanément**. Pas progressivement — d'un
coup, au franchissement du seuil. Le mouvement est réversible et se rejoue à l'identique en
remontant. Les pages intérieures sautent aussi, plus discrètement : ~11 px en deux paliers.

**Conséquence, et c'est la conclusion importante : aucun ancrage dans le flux ne peut être
stable.** Ce n'est pas un réglage à trouver, c'est une propriété du thème. Une fois la skin
ancrée dans la page, il n'y a que deux comportements possibles, et les deux ont été essayés :

- **elle suit le mouvement** (v1.4, v1.9) → le contenu remonte de 89 px, elle aussi : c'est
  le saut, inévitable puisque le déplacement lui-même est instantané ;
- **elle ne suit pas** (v1.5, ancrage sur une constante) → plus de saut, mais le contenu a
  bougé et pas elle : la fenêtre crème ne tombe plus en face de la colonne de contenu, ce
  qui est le décalage constaté à l'époque.

Il n'y a pas de troisième comportement. C'est un choix entre deux défauts.

Supprimer le mouvement de la page se mord la queue : ces 89 px, l'en-tête compact existe
précisément pour les récupérer. Lui demander de réserver la place qu'il libère annulerait sa
fonction. **À écarter.**

**Seul un fond `position:fixed` y est insensible**, parce qu'il ne dépend d'aucun repère de
la page. Le problème ne se pose plus, il disparaît.

### 6 bis. Sur l'accueil, la cale ne cale rien (jamais élucidé pendant la session aveugle)

Toujours mesuré : sur l'accueil, `#cs-skin-spacer` est inséré dans `.as-home-sticky-panel`,
**dont la hauteur rendue est 0**. Sa propre hauteur calculée est bien de ~205 px, mais elle
est absorbée par un ancêtre à hauteur nulle : elle ne dégage donc **aucun espace**. Sur les
pages intérieures, en revanche, elle est enfant direct de `body` et fait ses ~189 px réels.

C'est la vraie raison pour laquelle le bandeau n'avait jamais « la place » sur l'accueil
alors que la même mécanique fonctionnait ailleurs — mis à tort, pendant la session aveugle,
sur le compte du placement de la cale (piège n°5).

### 7. Une créative 16/9 est moins haute qu'une fenêtre courante (v1.8)

Mise à la largeur de l'écran elle fait `56.25vw` de haut ; bandeau rangé au-dessus du bord,
il n'en reste que `43.75vw` de visible — moins que la hauteur d'une fenêtre typique, d'où une
bande vide en bas.

Formule retenue : ce qui reste visible vaut 7/9 de la hauteur totale, donc il faut au moins
`9/7 × 100vh`. `background-size:cover` remplit la boîte au prix d'un léger rognage latéral,
ce que la spec prévoit explicitement.

### 8. Deux valeurs censées être identiques, calculées à deux endroits

Source récurrente de décalages (cale vs. décalage de la skin). Depuis la v1.8 elles passent
par les **mêmes variables CSS** (`--cs-skin-band`). **Ne pas les redédoubler.**

---

## 5. Déploiement et vérification

`deploy/wordpress/cs-regie.php` est la source ; le fichier vivant est
`wp-content/mu-plugins/cs-regie.php`. Il n'y a pas de synchronisation automatique.

**Ne jamais recopier le contenu du fichier à la main dans un appel d'outil** : la première
tentative de cette session a produit une corruption d'un octet, silencieuse. Méthode fiable,
qui ne fait jamais transiter le fichier par le modèle :

```php
// via MCP novamira/execute-php
$url  = 'https://raw.githubusercontent.com/monodf-beep/evenements/<COMMIT>/deploy/wordpress/cs-regie.php';
$body = wp_remote_retrieve_body(wp_remote_get($url, array('timeout' => 10)));
if (strlen($body) !== <TAILLE> || md5($body) !== '<MD5>') { echo 'ABORT'; }   // md5 du fichier git LOCAL
else { file_put_contents(WPMU_PLUGIN_DIR . '/cs-regie.php', $body); }
```

Puis vérifier `md5_file()` côté serveur, et charger la home pour confirmer l'absence de
`Fatal error`. **Vérifier sur `/` ET sur `/explore/savoie/`** (piège n°5) — noter que
`/explore/savoie/` a pour URL canonique la home : c'est le gabarit d'accueil filtré, pas une
page intérieure. Pour une vraie page intérieure, prendre une fiche événement.

Rappel : le site n'a **pas de cache** (`cache-control: no-cache`, aucune couche CDN), donc
un rechargement suffit à voir le déploiement.

## 6. Revenir en arrière

L'état « fond plein écran » d'avant cette session est le commit `0da1858` (v0.3). Un
`git show 0da1858:deploy/wordpress/cs-regie.php` le restitue. C'était une skin simple, sans
bandeau ni sticky — elle s'affichait dès 1280px et ne sautait pas, mais le bandeau
chevauchait le menu et les bandes latérales continuaient sous le pied de page, ce qui est ce
qui a lancé tout ce chantier.

---

## 7. Contexte d'usage, pour l'arbitrage éditorial

Les guides métier recommandent de **ne pas laisser un habillage en permanence** : une à deux
campagnes par mois maximum, en alternance avec le fond normal, sous peine de lasser les
visiteurs et de voir s'effondrer le revenu du format. À prendre en compte avant d'investir
davantage dans ce bloc.
