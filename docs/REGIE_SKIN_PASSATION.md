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
tentatives distinctes (v1.4, v1.5, v1.6, v1.9).

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

## 2. Ce qu'il faut vérifier EN PREMIER avec un navigateur

Dans l'ordre, parce que la réponse à la première question rend peut-être les suivantes
inutiles :

1. **Mesurer si `#cs-skin-spacer` change de position pendant le défilement.**
   `getBoundingClientRect().top + scrollY` doit être **constant**. S'il ne l'est pas, c'est
   la cause du saut, et c'est la piste principale (cf. §4, piège n°6).
2. **Vérifier si `.as-site-header` (l'en-tête compact de l'accueil) est en `position:fixed`
   ou dans le flux.** S'il est dans le flux et qu'il apparaît au défilement, il pousse tout
   le contenu vers le bas en cours de route — auquel cas **aucune** approche ancrée sur la
   page ne peut être stable, et il faut soit le sortir du flux, soit passer au fond fixe.
3. **Filmer le saut au ralenti** (DevTools → Performance, ou capture vidéo) pour savoir s'il
   se produit à un seuil précis (bascule d'état) ou en continu (retard de peinture).

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

C'est l'option à privilégier si Franck accepte de faire produire une seconde créative.

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

### 6. Le bas du menu n'est pas un repère stable (v1.4 → v1.5, et probablement le défaut restant)

Sur l'accueil, la barre territoire s'en va en défilant pendant que l'en-tête compact
apparaît : `headBottom()` **change en cours de défilement**. Tout ce qui s'y ancre se déplace
donc en cours de route.

- v1.4 accrochait la skin à « bas du menu − hauteur du bandeau » → elle sautait.
- v1.5 a remplacé ça par une constante → mieux, mais le rail restait calé une fois pour
  toutes, donc en remontant le bandeau revenait tronqué (il fallait recharger).
- v1.9 revérifie le rail au défilement en n'écrivant que si la valeur a changé → **et le saut
  est revenu**, ce qui suggère que la position de la cale change bel et bien en cours de
  défilement (à confirmer, cf. §2 point 1).

**C'est la piste la plus probable pour le défaut restant.** Un fond `position:fixed` y serait
insensible par construction : il ne dépend d'aucun repère de la page.

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
