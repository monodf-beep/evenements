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
