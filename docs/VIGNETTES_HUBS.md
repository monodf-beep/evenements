# Vignettes des pages hub — ce qui a été mesuré le 2026-09-21

Procédure de pose de l'encart de période sur les 192 pages hub. Première
application : les six pages de Chambéry. **Lire les trois pièges avant de faire
les 186 suivantes** — deux d'entre eux ont mordu dès le premier passage.

## L'état de départ, recompté en base

| | mesure |
|---|---|
| pages hub (`cs_hub_quand`) | **192** — 64 `aujourdhui`, 64 `weekend`, 64 `semaine`, toutes publiées |
| pages hub avec image mise en avant | **0** |
| pages « guide de ville » (`que-faire-a-*`, `cosa-fare-a-*`) | **28**, aucune avec image |
| `cs_hub_image` renseigné | 42 pages seulement |

La photo de fond par ville vient de `cs_hub_image`, **hérité du hub parent**
(snippet 61, ligne 353). Exemple : 2458 = « Château des Ducs de Savoie, Chambéry ».

Deux gains d'un seul geste : le visiteur distingue enfin les trois fenêtres, et
une image mise en avant vaut **+7 points Yoast** sur ces pages (mesuré le 19/09).

## Les trois pièges

### 1. Polylang recopie l'image française sur la page italienne

`get_option('polylang')['sync']` vaut **`["_thumbnail_id"]`** — la seule méta
synchronisée est justement celle-là. Conséquence constatée en vrai : après avoir
posé les trois vignettes FR, les trois pages IT portaient `9838/9839/9840`, donc
« CE WEEK-END » et un `alt` français sur `/it/`.

`set_post_thumbnail()` passe par `update_post_meta()`, donc par la synchro. Pour
poser une image DIFFÉRENTE sur la traduction, écrire la méta directement :

```php
$wpdb->delete($wpdb->postmeta, array('post_id'=>$id, 'meta_key'=>'_thumbnail_id'));
$wpdb->insert($wpdb->postmeta, array('post_id'=>$id, 'meta_key'=>'_thumbnail_id',
                                     'meta_value'=>$att));
clean_post_cache($id);
wp_cache_delete($id, 'post_meta');
```

> ⚠️ **Ce n'est pas durable.** Le réglage Polylang est toujours actif : un
> enregistrement futur de la page FR depuis wp-admin repoussera l'image FR sur
> la page IT. Deux issues, et c'est un arbitrage de Franck, pas une décision
> technique : retirer `_thumbnail_id` de la liste de synchro (mais les
> événements perdent alors le partage de photo entre leurs deux versions), ou
> accepter la fragilité et prévoir une commande de réparation.

### 2. Le garde-fou anti-doublon par `guid` NE MARCHE PAS

Écrit pour éviter le défaut de septembre (2 016 médias en trop), il interrogeait
`guid LIKE '%<nom>.jpg'`. **Testé : il ne retrouve rien.** Le `guid` d'une pièce
jointe n'est pas l'adresse du fichier mais un permalien :

```
9844  guid = https://agendasabauda.eu/it/cosa-fare-a-chambery/oggi/cosa-fare-a-chambery-oggi/
```

Un second passage redéposerait donc les six images. Le bon critère est le chemin
réel du fichier, et **sans l'extension** (voir piège 3) :

```php
$existant = $wpdb->get_var($wpdb->prepare(
  "SELECT post_id FROM {$wpdb->postmeta}
    WHERE meta_key='_wp_attached_file' AND meta_value LIKE %s",
  '%' . $wpdb->esc_like(pathinfo($nom, PATHINFO_FILENAME)) . '.%'));
```

Et le second garde-fou — « la page a déjà une vignette » — est faux lui aussi :
il a sauté les trois pages italiennes, qui portaient une vignette, mais **la
mauvaise** (piège 1). Comparer à l'image ATTENDUE, jamais à la simple présence
d'une image.

### 3. Les fichiers déposés en `.jpg` ressortent en `.webp`

Constaté sur les six : `wp_upload_bits()` reçoit `agenda-sabauda-chambery-oggi.jpg`,
`get_attached_file()` rend `agenda-sabauda-chambery-oggi.webp`. Une conversion
tourne à l'arrivée. Le NOM est conservé, donc le levier SEO tient ; seule
l'extension change. Toute recherche de fichier doit ignorer l'extension.

## Ce qui reste ouvert

- **`og:image` est figé pour tout le site** : `og-agenda-sabauda-fr.png` (et `-it`),
  déposé en 2026/07. Les six pages servent bien leur vignette DANS la page
  (3 occurrences dans le HTML, vérifié), mais un partage Facebook, LinkedIn ou
  WhatsApp affiche toujours l'image générique — le problème du « on dirait la
  même page », transposé au partage. À trancher séparément.
- Les 28 pages « guide de ville » n'ont toujours aucune image.

## La commande

```
python3 scripts/vignette_hub.py --photo <fichier|url> --fenetre weekend \
    --ville "Chambéry" --langue fr --sortie <chemin.jpg>
```

Elle tourne dans le conteneur de session (Chromium), **pas sur le VPS** : rien
ne dit qu'un navigateur y soit installé, et personne ne l'a vérifié. C'est
cohérent avec la consigne : la vignette se fabrique en même temps que la
rédaction, page par page.

## Le résultat du premier passage

| page | id | média | fichier | alt |
|---|---|---|---|---|
| `/que-faire-a-chambery/aujourdhui/` | 2595 | 9838 | `…-chambery-aujourdhui.webp` | Que faire à Chambéry aujourd'hui |
| `/que-faire-a-chambery/ce-week-end/` | 2596 | 9839 | `…-chambery-ce-week-end.webp` | Que faire à Chambéry ce week-end |
| `/que-faire-a-chambery/cette-semaine/` | 2597 | 9840 | `…-chambery-cette-semaine.webp` | Que faire à Chambéry cette semaine |
| `/it/cosa-fare-a-chambery/oggi/` | 2598 | 9844 | `…-chambery-oggi.webp` | Cosa fare a Chambéry oggi |
| `/it/cosa-fare-a-chambery/questo-weekend/` | 2599 | 9845 | `…-chambery-questo-weekend.webp` | Cosa fare a Chambéry questo weekend |
| `/it/cosa-fare-a-chambery/questa-settimana/` | 2600 | 9846 | `…-chambery-questa-settimana.webp` | Cosa fare a Chambéry questa settimana |

Six images servies en 200 (53 à 63 ko après conversion), six `alt` distincts,
recomptés en base après écriture.

## La hauteur d'affichage — correctif du 2026-09-21

Franck, le jour même de la pose : « prend trop de hauteur de page et on a un
bandeau blanc ». Mesuré avant de conclure, en rejouant la page servie dans
Chromium (scripts retirés, image chargée en local, sinon on mesure une image
cassée) :

| | au départ | 1re passe | après alignement |
|---|---|---|---|
| image affichée | 1200 × **630** | 1200 × 460 | **900 × 345** |
| largeur vs colonne de contenu (900 px) | déborde de 300 | déborde de 300 | **alignée** |
| blanc entre l'image et le fil d'Ariane | **0 px** | 0 px | **0 px** |

Du haut de l'image au bas du H1 : **416 px**, contre 630 px pour la seule image
au départ.

**La hauteur était bien le défaut**, et c'est le thème qui la produit :
GeneratePress rend l'image mise en avant à sa taille native dans
`<div class="featured-image page-header-image">`, sans marge ni padding.

**Le bandeau blanc, lui, ne se reproduit pas.** L'écart entre le bas de l'image
et le fil d'Ariane mesure zéro pixel, avant comme après. Je ne lui donne donc
aucune cause — c'est une hypothèse ouverte, pas un diagnostic.

Le correctif est un `<style>` posé par le gabarit hub lui-même (snippet 61),
donc **limité aux 192 pages hub** — aucun CSS global :

```css
.featured-image.page-header-image{line-height:0}
.featured-image.page-header-image img{display:block;margin:0 auto;
  max-width:1200px;width:100%;height:auto;aspect-ratio:1200/460;
  object-fit:cover;object-position:center}
```

**Largeur : 900 px, pas 1200.** Franck : « on peut réduire la largeur pour avoir
900px c'est ça la largeur du site ? » — oui, c'est le `max-width:900px` du
gabarit hub. L'image débordait de la colonne de 300 px. Alignée, elle tombe
mécaniquement à 345 px de haut, le rapport de recadrage étant inchangé.

**Pourquoi le rapport 1200/460 et pas moins.** Le recadrage est centré : 460/630 conserve de
y=85 à y=545 dans l'image source. Le plus haut des encarts (« aujourd'hui »,
384 px, centré) occupe y=123 à y=507, languette comprise jusqu'à ~526. Il passe
avec 19 px de marge. **Descendre sous 460 rognerait la carte** : il faudrait
alors refabriquer les 192 images avec un encart plus petit.

Sauvegarde du gabarit avant modification : option `cs_snippet61_sauvegarde_20260921c`.
md5 `9d9275f9c87cac2eb24889a86889e0c4` → `7a68c89565155a2560671b95de2f2db7` (+256 octets).

Retour arrière :

```php
global $wpdb;
$wpdb->update($wpdb->prefix.'snippets',
  array('code' => get_option('cs_snippet61_sauvegarde_20260921c')),
  array('id' => 61));
```

> Dette assumée : le snippet 61 n'est toujours pas miroité à l'octet près dans
> `deploy/wordpress/`. Elle date d'avant ce chantier, elle n'est pas réglée ici.

## Le bandeau de 180 px du gabarit faisait doublon

Franck, à la vue de la page : « on a 2 fois l'image ». Exact : le gabarit hub
affiche sous le H1 un bandeau de 180 px avec la photo de la ville — utile tant
que ces pages n'avaient AUCUNE image, redondant depuis que la vignette porte la
même photo avec l'encart par-dessus.

Il est désormais **conditionnel** : il ne s'affiche que si la page n'a pas de
vignette. Vérifié en ligne — Chambéry ne l'a plus, Annecy (pas encore traitée)
l'a toujours. Les 186 pages restantes gardent donc leur photo jusqu'à leur tour.

Le **crédit photo n'est pas conditionné** : c'est la même photo, l'attribution
reste due.

### Contrôler la syntaxe PHP sans binaire `php`

Première tentative refusée par mon propre garde-fou : `exec('php -l')` a répondu
`sh: php: command not found` — l'hébergement OVH n'expose pas le binaire. Le
refus était bon, la raison était mauvaise. Le contrôle équivalent depuis PHP :

```php
try { token_get_all("<?php \n" . $code, TOKEN_PARSE); }
catch (ParseError $e) { /* refuser l'ecriture */ }
```

md5 `7a68c89565155a2560671b95de2f2db7` → `5cfd753fd43b2ef1dd81b1a7cec61ba2`.
Sauvegarde : option `cs_snippet61_sauvegarde_20260921d`.
