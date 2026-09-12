# Déployer du code sur WordPress — ce qui est vrai, vérifié le 2026-08-12

Écrit après une matinée entière passée à essayer de livrer trente lignes de PHP. Le
problème n'était aucun de ceux qu'on cherchait.

## 1. `cs-publish.php` n'est PAS un fichier sur le serveur

Il est collé dans **Code Snippets**, entrée **n° 6, « CS Publish — Endpoint TEC
(cs/v1/event) »**, active, 15 897 octets. Le dossier `wp-content/mu-plugins/` contient
33 fichiers `cs-*.php` — et `cs-publish.php` n'en fait pas partie.

Conséquence immédiate : **aucun dépôt de fichier ne peut le mettre à jour.** Ni SFTP, ni
FTP, ni `deploy/push-wordpress.sh`. On a passé la matinée à réparer un transport pour
livrer un fichier que WordPress n'exécute pas.

Le fichier lui-même le disait depuis toujours, dans son propre en-tête :

```
INSTALLATION (au choix) :
 A) Code Snippets : coller tout le code SANS la ligne « <?php », « Run everywhere ».
 B) mu-plugin : déposer dans wp-content/mu-plugins/cs-publish.php.
```

Personne n'avait vérifié LEQUEL des deux avait été choisi. C'est la règle 1 : un fichier
dans le dépôt ne prouve rien sur ce que le site exécute.

## 2. Les transports de fichiers, un par un

| Chemin | Résultat, 2026-08-12 |
|---|---|
| SFTP `ohcqqjv@ftp.cluster100…:22` | `Connection closed by 54.36.142.132 port 22` |
| SFTP `ohcqqjv@ssh.cluster100…:22` | `Connection closed by 54.36.142.133 port 22` |
| FTPS explicite, `AUTH TLS` | `500 This security scheme is not implemented` |
| FTPS explicite, `AUTH SSL` | idem |
| FTP en clair, port 21 | non essayé — le mot de passe ouvre tout le site |

Cet hébergement mutualisé n'expose que du FTP en clair. SSH n'y est pas désactivé : il
n'est pas fourni.

## 3. Ce qui marche : Novamira

Le plugin **Novamira** (actif) expose un point MCP authentifié qui donne accès au système
de fichiers, à WP-CLI et à l'exécution de PHP sur le serveur. C'est par là que passe toute
modification de code WordPress — y compris les snippets, qui vivent en base
(`wp_snippets`) et qu'aucun transport de fichiers n'atteindrait de toute façon.

Contrainte à connaître : `novamira/write-file` refuse d'écrire un `.php` ailleurs que dans
`wp-content/novamira-sandbox/`. Pour un mu-plugin ou un snippet, passer par
`novamira/execute-php`.

**Contrôle de syntaxe sans binaire `php`** — `token_get_all('<?php ' . $code, TOKEN_PARSE)`
lève une `ParseError` sur un code invalide. C'est un vrai `php -l`, exécutable côté
serveur, et il doit tourner AVANT d'écrire : un snippet fautif casse le site comme un
mu-plugin.

**Sauvegarde avant écriture.** L'état du 12/08 au matin est dans l'option
`cs_publish_backup_20260812` (sha1 `bfda649c28dc5d58871751d42f2c29fc48ff644d`, 15 897 o).
Retour arrière :

```php
$wpdb->update($wpdb->prefix . 'snippets',
              array('code' => get_option('cs_publish_backup_20260812')),
              array('id' => 6));
```

## 4. Le dépôt et la production avaient divergé DANS LES DEUX SENS

C'est la vraie découverte de la journée, et elle valait mieux que le correctif qu'on
voulait livrer. Écraser le snippet avec `deploy/wordpress/cs-publish.php` aurait **retiré
du code qui tourne** :

| | Production | Dépôt (avant le 12/08) |
|---|---|---|
| `province` — terme territoire enfant (Piémont) | ✅ | ❌ |
| `as_deplacement_now` — tri de la section « ça vaut le déplacement » | ✅ | ❌ |
| `start_time` — heure réelle, Schema.org Event | ❌ | ✅ |

Le deuxième cas est le plus parlant : `publisher_as.py` **envoie** `as_deplacement_now`
depuis le 03/08, et la liste `$allowed` du dépôt ne le connaissait pas. Déployer le dépôt
aurait donc silencieusement jeté ce méta et rendu à la home le défaut qu'on avait mis une
journée à corriger — la Foire de la Saint-Ours qui n'apparaît jamais derrière deux
expositions de 365 jours.

Les deux blocs de production sont désormais recopiés dans le dépôt, avec un `⚠️` qui dit
d'où ils viennent.

**Reste `start_time`, qui est un arbitrage et pas un oubli.** Le dépôt sait extraire
l'heure de début et la poser dans `EventStartDate` ; la production l'ignore et publie tout
en journée entière. Le remettre améliore les données structurées (c'était l'objet de
l'audit SEO du 29/07) mais change ce que le site AFFICHE sur les fiches déjà en ligne, au
prochain `--update`. À trancher, pas à glisser dans un correctif de lieu.

## 5. La règle qui en sort

**Avant de modifier du code WordPress, établir OÙ il vit.** Un fichier dans
`deploy/wordpress/` ne prouve ni qu'il est déployé, ni qu'il est à jour, ni même qu'il est
la référence — trois choses qu'on a crues ce matin, et qui étaient fausses toutes les
trois.

La route `GET /wp-json/cs/v1/version` existe pour ça : elle répond ce que la version en
ligne dit d'elle-même. Tant qu'elle renvoie 404, le correctif n'est pas passé.

---

## 6. Ce qui a été ajouté le 2026-08-17, et par quel chemin

Journée d'un seul sujet : « les messages ne doivent arriver uniquement dans la chaîne
#agendasabauda et non pas dans formulaire ». Elle a produit deux mu-plugins, une route,
trois snippets modifiés — et elle confirme la règle du § 5 dans les deux sens.

### Où vit quoi, maintenant

| Chose | Où elle vit | Copie versionnée |
|---|---|---|
| `cs_slack_notify()` / `cs_slack_notify_form()`, boîte du jour, route REST | mu-plugin `wp-content/mu-plugins/cs-slack-formulaires.php` | `deploy/wordpress/cs-slack-formulaires.php` |
| Filtre de périmètre des audits (règle 5) | mu-plugin `wp-content/mu-plugins/cs-audit-perimetre.php` | `deploy/wordpress/cs-audit-perimetre.php` |
| Audits quotidiens #130, #135, #136 | **base WordPress**, table `wp_snippets` | `deploy/wordpress/code-snippets/` (copies, pas la référence) |
| Rapatriement des rapports vers Slack | VPS, `scripts/rapports_wordpress.py`, appelé par `scripts/slack_digest.py` | le dépôt EST la référence |

Sauvegardes d'avant la journée, sur le serveur :
`wp-content/mu-plugins/cs-slack-formulaires.php.bak-2026-08-17` et
`wp-content/uploads/cs-snippets-sauvegarde-2026-08-17/{130,135,136}-avant.txt`.

### La route `cs/v1/slack-boite`

WordPress ne poste plus rien sur Slack de lui-même : il TIENT ses rapports, et le
récapitulatif de 11h45 du VPS vient les chercher. Motif, donné par Franck le jour même
(« tu publies déjà dans ce canal, pourquoi je devrais te redonner le webhook ? ») : le
webhook de #agendasabauda reste dans le seul `.env` du VPS, au lieu d'exister en double
dans la base d'un site public.

```
GET    /?rest_route=/cs/v1/slack-boite         → {count, messages:[{id, at, heure, texte}]}
DELETE /?rest_route=/cs/v1/slack-boite&ids=…   → retire EXACTEMENT ces identifiants
```

Authentification : celle de la publication quotidienne (`X-CS-Auth` ou Application
Password), capacité `edit_posts`. Vérifié en ligne : **401** sans authentification, **200**
avec.

Deux points à ne pas rouvrir :

- **la purge se fait par identifiants, jamais par borne d'horodatage.** La première version
  bornait « jusqu'à la seconde lue » et détruisait un rapport écrit après la lecture dans
  la même seconde — les horloges WordPress sont à la seconde et les audits partent du même
  cron. Fixture : `tests/test_slack_boite_wordpress.py`, avec contre-épreuve ;
- **le GET vaut preuve de vie**, pas seulement le DELETE : les jours sans rapport il n'y a
  rien à supprimer, et sans cette marque WordPress croirait le pipeline mort au bout de
  26 h et reprendrait la parole dans le mauvais canal.

Si plus personne ne vient vider la réserve pendant 26 h, WordPress **reprend la parole tout
seul** sur son propre webhook (donc #formulaire, faute d'autre). C'est voulu : un message
mal rangé se voit, une file silencieuse non. Voir `docs/ETATS_TERMINAUX.md`.

### Le transport qui a marché, et ses limites

Même canal qu'au § 3 (Novamira), avec deux précisions apprises ce jour-là :

1. **`novamira/write-file` refuse le PHP hors du bac à sable.** Pour un mu-plugin :
   `novamira/create-upload-link` sur un chemin en `.nouveau`, `curl -X PUT --data-binary`,
   puis un `execute-php` qui (a) compare le **md5** au fichier local, (b) **sauvegarde**
   l'ancienne version, (c) contrôle la syntaxe par `token_get_all(…, TOKEN_PARSE)` — il n'y
   a pas de binaire `php` sur l'hébergement —, (d) fait un `rename()` **atomique**. Un
   mu-plugin se charge avant tout le reste : la moitié d'un fichier écrit tue le site.
2. **Les grosses charges ne passent pas par l'argument d'un appel** : deux `502 Bad
   gateway` de suite sur ~5 ko de patch. Les déposer en fichier et les lire sur place. Et
   après un échec de transport, **vérifier l'état avant de retenter** — c'est ce qui a
   montré que le patch n'était pas passé, donc qu'il n'y avait rien à défaire.


## 7. 2026-09-08 — `cs-taxo-it.php` : les termes suivent la langue du post dans les deux sens

Constat de Franck : dans la grille française, des cartes étiquetées « Piemonte » à côté de
cartes « Piémont ». Mesuré sur WordPress (Novamira, lecture seule) : **26 fiches en
français** portaient un terme territoire ET une catégorie en italien (21 « Piemonte »,
4 « Valle d'Aosta », 1 « Savoia ») ; aucune fiche italienne ne portait de terme français.

**Cause, établie par un test réversible et non par lecture seule.** Polylang
(`PLL_CRUD_Posts::set_object_terms`, accroché à l'action `set_object_terms`) convertit tout
terme posé sur un post vers la langue que le post a *à cet instant* : sur WP#8163 (post
`it`), poser le terme 6 « Piémont » donne 321 « Piemonte ». Or `cs-publish` pose ses termes
AVANT que le snippet Polylang (priorité 20) ne pose la langue. Une fiche poussée une
première fois en `it` (titre italien — c'était la règle de `publisher_as._lang` avant le
07/09), puis re-poussée en `fr`, gardait donc ses termes italiens : le filtre (B) de
`cs-taxo-it.php` rendait la main dès que le post était français.

**Correctif.** (B) réaffecte désormais chaque terme vers sa traduction dans la langue du
post, quelle que soit la langue. Déployé par le canal du § 3 : `write-file` sur
`cs-taxo-it.php.nouveau` (extension non-PHP, donc autorisée hors bac à sable), puis un
`execute-php` qui compare le md5 au fichier du dépôt (`f0ea2333…`), sauvegarde l'ancien
(`cs-taxo-it.php.bak-2026-09-08`, md5 `a7e81f40…`, identique au miroir d'avant), contrôle
la syntaxe par `token_get_all(…, TOKEN_PARSE)` et fait un `rename()` atomique. Front,
`/it/` et l'API REST répondaient 200 après.

**Réparation.** Les 26 fiches (52 affectations : territoire + catégorie) ont été
réaffectées par `execute-php` après un dry-run listant chaque paire terme → traduction ;
recompte après écriture : 0 terme dans une autre langue que celle de son post. Le terme
« Piémont » compte 64 fiches (42 avant), « Piemonte » 52 (74 avant). Réversible : c'est une
réaffectation de termes, la liste est dans le message du commit.

Retour arrière du mu-plugin : `rename(cs-taxo-it.php.bak-2026-09-08 → cs-taxo-it.php)`.

## 8. 2026-09-08 (suite) — `cs-cvld-dynamique.php` et `cs-territoire-persistant.php`

Trois changements déployés le même après-midi, par le canal du § 3, avec une précision de
transport apprise ce jour-là : **ne jamais retaper un fichier de 13 ko dans l'argument d'un
appel** — une coquille s'y est glissée (« Voir dans les altri territori ») et seul le
contrôle md5 avant `rename()` l'a arrêtée. `create-upload-link` + `curl --data-binary`
depuis le fichier local, puis `execute-php` (md5 attendu, sauvegarde, `token_get_all`,
`rename`). Le `.nouveau` d'un envoi raté doit être supprimé avant le suivant
(`overwrite:false`).

- `cs-cvld-dynamique.php` : plancher `CS_CVLD_PLANCHER = 10` sur la note intrinsèque et
  la note temps-ajustée au premier passage, note seule au second (repli) ; bouton « Et
  ailleurs » sur `/espace-sabaudo/`. Sauvegardes `.bak-2026-09-08` (version du matin,
  md5 `99fc262e…`) et `.bak-2026-09-08b` (plancher strict, `82c06457…`). En ligne :
  `dc46ac66…`.
- `cs-territoire-persistant.php` : « Tous les territoires » de la barre sur
  `/espace-sabaudo/`. Sauvegarde `.bak-2026-09-08` (`1e9d5b07…`). En ligne : `6583e6a7…`.
- Données, pas code : `as_home_override=excluded` sur WP#8049 (carte noire, titre italien,
  finit le 09/09) ; `cs_guide_saison_debut/fin` = 2026-06-01 / 2026-08-31 sur le guide
  « Festivals de l'été en Savoie 2026 » (post 2422) — le mécanisme de saison de « À lire »
  existait depuis le 06/09, aucun des six guides ne le renseignait.

## 9. 2026-09-08 (soir) — modifier un Code Snippet EN BASE, sans casser le site

Le snippet 44 (allocateur de la home, « En évidence ») vit dans la table
`wp_snippets`, pas dans un fichier : ni `deploy/push-wordpress.sh`, ni `php -l` ne
l'atteignent. Deux retouches y ont été faites ce soir par `novamira/execute-php`, avec la
procédure ci-dessous — à reprendre telle quelle, parce qu'un snippet actif qui ne compile
pas est aussi mortel qu'un mu-plugin cassé :

1. lire le code (`SELECT code FROM wp_snippets WHERE id=44`) et cibler la retouche par une
   chaîne EXACTE dont on vérifie `substr_count(...) === 1` — zéro ou deux occurrences, on
   s'arrête sans écrire ;
2. copier l'ancien code dans `wp-content/uploads/cs-backups/snippet-<id>-<date>.php.txt`
   (`.txt` : le bac à sable n'écrit pas de `.php`, et un `.txt` ne s'exécute pas) ;
3. `token_get_all('<?php ' . $nouveau, TOKEN_PARSE)` dans un `try` — une exception, on
   s'arrête sans écrire ;
4. `$wpdb->update`, puis `wp_cache_flush()`, puis relire et comparer les md5 ;
5. vérifier dans une REQUÊTE SUIVANTE (le code déjà chargé ne change pas dans la requête
   qui l'a modifié) : appeler `cs_home_build_allocation()` avec
   `$_GET['as_territoire'] = '<slug FR du territoire>'` — le SLUG (`comte-de-nice`), pas la
   clé canonique (`nice`), sinon le filtre territoire est ignoré en silence — et
   `PLL()->curlang = PLL()->model->get_language('fr')`, sans quoi Polylang mélange les
   deux langues hors du front ; le cache statique du plan est par langue et par requête,
   donc UN territoire par appel ;
6. puis lire la page publique elle-même (`curl` de `/explore/<slug>/`), parce que l'étape
   5 mesure l'allocateur, pas le rendu.

Ce que les deux retouches font, et comment revenir en arrière, est écrit dans les
commentaires du snippet lui-même (datés 2026-09-08) et dans `docs/ERREURS_2026-09-08.md`
(§ « Ce qui a été changé sur WordPress ce soir »). Les snippets n'ont toujours pas de
double versionné ici — c'est un point ouvert, pas une règle.

## 10. 2026-09-10 — `cs-passe-noindex.php` et `cs-index-budget.php` : le budget d'exploration

Deux mu-plugins NEUFS (aucune version en ligne à écraser), déposés par le canal du § 3,
procédure du § 6 : `create-upload-link` sur un `.nouveau`, `curl --data-binary` depuis le
fichier local, `execute-php` qui compare le md5, contrôle la syntaxe par
`token_get_all(…, TOKEN_PARSE)`, refuse si la cible existe déjà, puis `rename()` atomique.
`php -l` local avant tout (les deux passent, `tests/test_php_syntax.py` les couvre).

| fichier | md5 en ligne | taille |
|---|---|---|
| `cs-passe-noindex.php` | `f3f8cd1d17b0c85b2397b19c89f28cde` | 4 216 o |
| `cs-index-budget.php`  | `b76ce6d0769c1c9a04e858e365862c45` | 11 965 o |

**Le dry-run a été LU avant le second dépôt, pas seulement compté** — c'est lui qui a
corrigé l'en-tête du fichier. Les chiffres qu'il portait venaient du SITEMAP, donc de ce
que le site déclare ; la mesure sur la base dit autre chose :

| famille | estimé au sitemap | mesuré sur la base |
|---|---|---|
| vues « période » | 137 | **192** sur 306 pages publiées |
| lieux sans événement à venir | 307 (tous les lieux) | **221** sur 313, 92 gardés |
| organisateurs | 75 | **83** |
| total hors index | 498 | **496** |

Les 92 lieux gardés sont les lieux vivants : Forte di Bard (7 événements à venir), Opéra
de Nice (5), Théâtre M. Novarina (5), Fondazione Merz (4). Aucune page hub n'était dans la
liste des exclues.

**Arbitrage laissé ouvert, délibérément** : les 8 pages « période × territoire »
(`/ce-week-end/piemont/`, `/it/questo-weekend/valle-d-aosta/`…) restent indexées. Leur
slug propre est un TERRITOIRE, pas une période, donc la règle ne les attrape pas — et
« que faire ce week-end en Piémont » est une intention de recherche réelle. On ne
désindexe pas ce qu'on n'a pas jugé.

### Contrôle après dépôt (fait, des DEUX côtés de chaque frontière)

| page | attendu | obtenu |
|---|---|---|
| WP#8049, terminé la veille à 23h59 | `noindex, follow` | ✅ `data-cs="cs-passe-noindex"` |
| WP#8741, se termine ce soir | rien | ✅ aucune balise |
| `/que-faire-a-turin/ce-week-end/` | `noindex` | ✅ `data-cs="cs-index-budget"` |
| `/que-faire-a-turin/` (hub) | rien | ✅ aucune balise |
| `/lieu/forte-di-bard/` (7 à venir) | rien | ✅ aucune balise |
| `/lieu/theatre-des-collines/` (0 à venir) | `noindex` | ✅ `data-cs="cs-index-budget"` |
| `/organisateur/cristinag/` | `noindex` | ✅ |
| accueil, `/wp-json/`, `/wp-admin/` | 200 / 200 / 302 | ✅ |

Sitemap déclaré, avant (mesuré le 09/09) et après :

    total          858  →  370
    lieux          307  →   92
    organisateurs   75  →    0   (le sitemap tribe_organizer a disparu de l'index)
    pages          137+ →  106
    événements     189  →  131   (les terminés sortent : cs-passe-noindex)

### Un « trou » annoncé, puis DÉMENTI par la mesure suivante — 2026-09-10

J'ai écrit ici, et dit à Franck, que `post-sitemap.xml` déclarait **0 URL** pour
**24 articles publiés**, et j'ai proposé d'en faire une urgence. C'était FAUX.

Ce qui a tranché, en trois appels : le fournisseur Yoast rendait bien
`get_sitemap_links('post', …)` → **24 liens** ; une lecture du même sitemap DEPUIS le
serveur → **24 `<loc>`** ; et une relecture depuis l'extérieur → **24** aussi. Le site
n'a jamais eu ce trou. C'est mon `curl` qui a compté zéro, une fois, et je n'ai pas
recompté avant d'annoncer.

**Ce que ça coûte, et le garde-fou.** C'est la faute-racine du dépôt à l'état pur : une
mesure UNIQUE présentée comme un fait, et une conclusion (« tes contenus les plus
durables sont invisibles de Google ») bâtie dessus. La règle existait déjà —
« ne jamais présenter une INFÉRENCE comme un FAIT » — mais il en manquait un cran :
**un zéro se recompte AVANT d'être annoncé, par un second chemin.** Un zéro est
justement la valeur qu'un défaut de mesure produit le plus volontiers, et il ressemble
exactement à un monde où il n'y a rien.

Le reste des chiffres de ce paragraphe tient : 24 articles publiés, aucun en noindex,
`noindex-post` à `false`. C'est la seule ligne qui comptait — « 0 URL » — qui était de
moi et pas du site.

### Retour arrière

Supprimer le fichier concerné dans `wp-content/mu-plugins/`. Rien n'est écrit en base,
aucun post n'est modifié : tout se calcule au rendu. Les lieux se rouvrent d'eux-mêmes dès
qu'un événement à venir y pointe (règle 3), et une fiche dont la date de fin repasse dans
l'avenir redevient indexable sans que personne n'y touche.

## 11. 2026-09-12 — le rouvreur de complétude ne voyait qu'un brouillon sur trois

**Snippet 150** (« CS - Completude : le rouvreur »), miroir versionné
`deploy/wordpress/code-snippets/137-cs-completude-rouvreur.php`. Ancien md5
`9af7fdf0a19e0f36f6b553b7e45d45ce`, nouveau `94518218d43222d8f6d0ee2028626f3e`.
Sauvegarde de la version d'avant dans l'option `cs_rouvreur_sauvegarde_2026_09_12`
(6 035 octets) — retour arrière : réécrire ce contenu dans `wp_snippets.code` pour l'id 150.

**Le cul-de-sac, fermé des DEUX côtés.** Le rouvreur n'examinait que les brouillons
portant `as_completude_refus`, c'est-à-dire ceux que le garde-fou avait lui-même
dépubliés. Mesuré ce jour-là : **16 fiches à venir en brouillon, dont 11 sans ce marqueur
et sans le moindre bloquant.** Publiables, et invisibles de tout le monde.

L'autre côté est écrit dans `cs-publish.php` (snippet 6, l.156) : « NE PAS dépublier au
re-push : on retire post_status pour préserver le statut existant ». Décision juste — une
fiche retirée à la main ne doit pas revenir toute seule — mais elle a un revers : une
fiche tombée en brouillon y RESTE, même quand `publish_batch_as` la repousse chaque
semaine. Le publieur ne la relève pas ; le rouvreur ne la voyait pas. Règle 3, exactement,
et un cran plus bas que là où elle avait déjà été réparée le 06/09.

**Le garde-fou du garde-fou : `as_score`.** Seul le pipeline le pose. Un brouillon sans
lui vient d'ailleurs — du formulaire public « Proposer un événement » (snippet 24) ou de
la main de quelqu'un — et ne doit jamais être publié par un automate. Mesuré AVANT
d'écrire la ligne : sur 44 brouillons, 2 n'avaient pas `as_score` ; aucun des onze.

**Dry-run lu ligne par ligne avant d'écrire** (la nouvelle requête, sans aucune écriture) :
16 candidats, 11 à republier, 5 à garder en brouillon avec leur motif. Puis exécution, et
recompte en base fiche par fiche (règle 6 — on ne croit pas la liste rendue) :

    garées 16 · sans marqueur 11 · rouvertes 11 · bloquées 5
    1938, 902, 606, 2311, 6288, 6382, 6435, 6438, 7552, 7558, 7639  → toutes `publish`
    restent en brouillon : 7686, 8626, 8669, 8682 (source_officielle) · 8707 (corps_indigent)
    total tribe_events publiés : 293 · brouillons à venir restants : 5

Trois pages tirées au hasard parmi les onze répondent 200 en public.

**Le compteur ajouté, et pourquoi.** Le relevé porte désormais `sans_marqueur` à côté de
`garees`. C'est le chiffre qui manquait : tant qu'il reste élevé, quelque chose met des
fiches en brouillon sans le dire, et il faudra trouver quoi. Ce qui a mis ces onze-là en
brouillon n'est PAS établi — le marqueur absent est précisément ce qui empêche de le
savoir, et je ne le devine pas.

**Ce qui reste ouvert** : les 4 fiches bloquées sur `source_officielle` et la 8707 sur
`corps_indigent` (c'est elle qui fait exploser le plafond de jetons à l'enrichissement).
