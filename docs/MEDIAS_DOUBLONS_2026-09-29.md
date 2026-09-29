# Les médias déposés en double — ce qui est mesuré, et ce qui ne l'est pas

Écrit le 2026-09-29, à la demande de Franck, avant d'archiver la session : cette mesure
n'existait que dans une conversation. Elle a coûté cinq requêtes, une hypothèse fausse
annoncée puis retirée, et un détecteur borgne qui a rendu un chiffre rassurant et faux.

**Point de départ.** Le 28/09, une republication de deux fiches (WP#2340, WP#3807) a
redéposé six médias sous mes yeux. Le journal des erreurs du 12/09 disait pourtant le
problème réglé : `_upload_featured_media` ne demandait jamais à WordPress si l'image y
était déjà, et une empreinte md5 avait été posée depuis pour l'en empêcher. Donc soit le
garde-fou ne marchait pas, soit il ne couvrait pas ce cas. C'est le second.

---

## Les chiffres, avec leur périmètre

Mesuré sur la base WordPress de production le 2026-09-28/29.

| Grandeur | Valeur | Périmètre |
|---|---|---|
| médias, tous confondus | **5 249** | tout `post_type='attachment'` |
| médias portant une empreinte | **1 288** | slug finissant par `-[0-9a-f]{10}` — donc déposés **depuis le 15/09**, date où l'empreinte a été introduite |
| empreintes présentes sous plusieurs noms | **274** | parmi ces 1 288 |
| copies en trop de ce seul fait | **499** | idem |
| copies de ces groupes encore référencées | **347** | vignette à la une, méta `as_image_original`, ou corps de fiche |
| copies orphelines | **426** | **sur WordPress seulement** — voir la réserve plus bas |

Et la répartition des 274 groupes, par nombre de fiches qui les référencent :

| Cause | Groupes |
|---|---|
| **plusieurs fiches** référencent les mêmes octets (affiche partagée) | **164** |
| une seule fiche (titre réécrit entre deux dépôts) | **10** |
| aucune copie référencée par quoi que ce soit | **100** |

L'exemple le plus net est la GAM de Turin, empreinte `ad73590c2f` : **8 copies pour
9 fiches** — l'exposition, ses visites guidées, ses performances, chacune ayant déposé la
sienne.

---

## Le mécanisme, établi en lisant le code

`scripts/publisher.py::_upload_featured_media` calcule bien une empreinte md5 des octets
envoyés, mais elle n'est qu'un **suffixe** : le nom de fichier est
`<titre>-<déclinaison>-<empreinte>`, et `_media_existant()` cherche ce **slug entier**.
Deux fiches différentes — ou une même fiche renommée — produisent donc deux noms
différents pour des octets identiques, et la recherche ne trouve rien.

Vérifié sur le cas du 28/09, les deux fichiers portant la même empreinte :

```
9322   2026-09-15   orlando-carte-c7e01d533d
12890  2026-09-28   amore-e-follia-nell-opera-di-haendel-orlando-carte-c7e01d533d
```

Le garde-fou du 15/09 fonctionne exactement comme il a été écrit. Il attrape la
republication d'une fiche dont rien n'a changé ; il ne peut rien contre un titre réécrit
ni contre deux fiches qui partagent une affiche.

---

## ⚠️ L'hypothèse que j'ai annoncée et qui était fausse

J'ai d'abord conclu, à partir du seul cas du 28/09 : « le titre est réécrit, donc la clé
change, donc ça redépose » — en citant la faute 20 du 14/09 (« un titre n'identifie rien
de durable dans ce dépôt »). C'était cohérent, c'était documenté, et **ça représente
10 groupes sur 274**. La cause dominante est le partage d'une affiche entre plusieurs
fiches, que ce raisonnement ne voyait pas.

Le correctif que j'en avais tiré — clé sur `(numéro de post, déclinaison, empreinte)` —
aurait donc réparé 10 groupes sur 274. **Un cas réel qui confirme une règle connue reste
un cas : il ne donne pas la proportion.**

## ⚠️ Et la mesure qui ne mesurait rien

Pour séparer les deux causes, j'ai d'abord regroupé les copies par `post_parent`. Réponse :
« 274 groupes sur une seule fiche, 0 réparti ». Elle contredisait un exemple que j'avais
sous les yeux (huit noms d'événements différents pour une seule empreinte), d'où la
vérification :

```
medias a empreinte : 1288   dont post_parent = 0 : 1288
```

**La colonne n'est jamais renseignée par nos dépôts** — le pipeline téléverse en
`wp/v2/media` sans parent. Le détecteur rendait donc un chiffre parfaitement net sur une
colonne vide. C'est la mesure refaite sur les vraies références (vignette, méta, corps)
qui a donné le tableau ci-dessus, et qui a **inversé** la conclusion.

---

## L'arbitrage, qui reste entier

Mutualiser les 164 groupes suppose de **partager un seul média entre plusieurs fiches**.
Or le texte alternatif vit sur le média, pas sur l'usage, et il porte l'expression clé —
une par fiche. Dans le groupe `ad73590c2f`, les huit copies portent huit `alt` différents
(« Song Dong. Soul Out », « Evolving Soundscapes », « Visite guidate alla mostra… »).
Le choix n'est donc pas contournable par un meilleur code :

1. **partager le média** — 164 groupes de doublons en moins, un seul `alt` pour toutes les
   fiches qui l'utilisent ;
2. **garder une copie par fiche** et accepter les doublons comme le prix de l'`alt` par
   fiche, en nettoyant périodiquement les orphelines. La voie la moins risquée, et rien ne
   dit que 5 249 médias gênent le site ;
3. **ne rien changer au dépôt**, ne traiter que les orphelines.

Franck n'avait pas tranché au moment d'écrire ces lignes.

---

## ⚠️ La réserve à ne pas perdre : un seul des TROIS mondes a été interrogé

Les 426 « orphelines » le sont **sur WordPress**. Les références vivent dans trois mondes
(journal des erreurs du 14/09), et deux n'ont pas été lus :

- **WordPress** — lu : `_thumbnail_id`, méta `as_image_original`, et les URL du corps ;
- **le dépôt** — `config/territory_category_images.txt`, où les 48 images de secours ne
  sont référencées QUE là ;
- **la base locale** — `wp_raw_image_url_as`, `url_image`, `url_image_wide`,
  `url_image_portrait`, écrites par `publish_batch_as.py`.

Donc **426 est un plafond de ce qui est supprimable, pas une liste de suppression.** Une
copie que la base locale désigne encore serait re-poussée au prochain `--update`, ou
casserait la vignette. Le recoupement se fait sur le VPS, et il précède toute suppression.

Au passage, deux formes vérifiées plutôt que supposées, parce qu'elles ont l'air
d'évidences et n'en sont pas : `as_image_original` contient **une URL** (le visuel 16:9,
déclinaison `-fiche-carte`), et `as_affiches` ne contient **aucune image** — c'est un
libellé de crédit (« photo officielle »).

---

## Les requêtes, pour refaire la mesure sans la reconstruire

Par Novamira (`novamira/execute-php`). Elles sont en lecture seule.

**Les doublons par empreinte :**

```php
$rows = $wpdb->get_results("SELECT ID, post_name, post_date FROM {$wpdb->posts}
    WHERE post_type='attachment' AND post_name REGEXP '-[0-9a-f]{10}$' ORDER BY ID", ARRAY_A);
$par = array();
foreach ($rows as $r) { $par[substr($r['post_name'], -10)][] = $r; }
// groupes de 2+ = mêmes octets déposés plusieurs fois
```

**Qui les référence vraiment** (les trois points WordPress, en trois passes groupées —
jamais un `LIKE` par média, c'est ce qui rend la mesure tenable en moins de 30 s) :

```php
// 1. vignette à la une, par id
SELECT post_id, meta_value FROM wp_postmeta WHERE meta_key='_thumbnail_id'
// 2. métas portant une URL d'image
SELECT post_id, meta_value FROM wp_postmeta
  WHERE meta_key IN ('as_image_original') AND meta_value LIKE '%/uploads/%'
// 3. corps des fiches : une seule passe, regex sur /uploads/AAAA/MM/<base>.<ext>
SELECT ID, post_content FROM wp_posts
  WHERE post_status NOT IN ('trash','auto-draft','inherit') AND post_content LIKE '%/uploads/%'
```

**Et ce qu'il NE faut pas faire** : regrouper par `post_parent`. Il vaut 0 pour les
1 288, et le regroupement rend alors un chiffre net et faux.
