# Les snippets Code Snippets — copies versionnées, PAS la référence

Ces fichiers sont la copie du code qui vit **dans la base WordPress**, table `wp_snippets`,
gérée par le plugin *Code Snippets*. Aucun dépôt de fichier ne les atteint : les déposer
sur le serveur ne les déploie pas.

## Ce que cette copie prouve, et ce qu'elle ne prouve pas

Elle prouve qu'on peut **relire** et **restaurer** ce code. Elle ne prouve **ni** qu'il est
en ligne, **ni** qu'il est à jour : c'est la règle 1 de `CLAUDE.md` transposée au code.
Le 2026-08-12, trois heures ont été perdues à livrer par quatre transports successifs un
fichier que WordPress n'exécutait pas, et la version en ligne contenait **deux morceaux de
code absents du dépôt** — dont le méta de tri qui fait apparaître la Foire de la Saint-Ours
en page d'accueil. L'écraser aurait été une régression, pas un correctif.

**Donc, avant toute écriture : lire ce qui est en ligne et comparer.** L'empreinte md5 en
tête de chaque section ci-dessous est celle du jour où la copie a été prise.

## L'inventaire

| Fichier | Snippet | Portée | Actif | md5 au 2026-08-17 |
|---|---|---|---|---|
| `130-audit-doctrine-editoriale.php` | #130 · Audit doctrine editoriale | front-end | oui | `ed75042bf2b81194c55473df5367ec37` |
| `135-garde-fous-dates-et-sources.php` | #135 · Garde-fous dates et sources | front-end | oui | `daafdd83a310978e18eae9b41ae6151a` |
| `136-garde-fous-panel-formes-lieux.php` | #136 · Garde-fous 2 : panel, formes, lieux | front-end | oui | `59582f3cbccf3c03c089ac740cd41f8d` |

Les copies **d'avant** les modifications du 2026-08-17 sont sur le serveur, dans
`wp-content/uploads/cs-snippets-sauvegarde-2026-08-17/` (`130-avant.txt`, `135-avant.txt`,
`136-avant.txt`). C'est le retour arrière.

Un quatrième audit existe, **#138 « fraîcheur des guides »** : il est **désactivé** et son
cron n'est plus programmé — donc personne ne surveille la péremption des guides. Il n'est
pas copié ici tant que son sort n'est pas tranché (le réactiver ou le supprimer).

## Le format, et le contrôle de syntaxe

Ces fichiers sont au format de Code Snippets : **pas de `<?php`** en tête, pour qu'ils
soient copiables tels quels dans l'éditeur du plugin. `tests/test_php_syntax.py` les
préfixe avant de les passer à `php -l` — une copie de secours cassée ne se découvrirait
sinon qu'au moment de restaurer.

## Mettre à jour la copie après une modification en ligne

```sh
# 1. relire ce qui tourne (Novamira / execute-php) et comparer l'empreinte
#    SELECT md5(code) FROM wp_snippets WHERE id=135;
# 2. si elle diffère de ce README, la copie est PÉRIMÉE : la reprendre depuis la base,
#    jamais l'inverse ;
# 3. vérifier, puis committer :
.venv/bin/python -m tests.test_php_syntax
```

## Écrire dans la base, si c'est vraiment nécessaire

Le plugin exécute ce code sur le site public : une faute de syntaxe dans un snippet
**actif** casse les pages qui le chargent. La méthode suivie le 2026-08-17, et la seule
qui soit sûre :

1. **sauvegarder** le code actuel dans un fichier hors du dépôt WordPress ;
2. remplacer par **ancres exactes**, en refusant l'opération si une ancre n'apparaît pas
   exactement une fois (une ancre ambiguë est une faute, pas un détail) ;
3. **contrôler la syntaxe avant d'écrire**, sans binaire php :
   `token_get_all('<?php ' . $code, TOKEN_PARSE)` lève `ParseError` ;
4. écrire, puis **relire et faire tourner** la fonction concernée, et LIRE sa sortie.

Les charges de plus de quelques kilo-octets ne passent pas par l'argument d'un appel
(deux `502` de suite le 2026-08-17) : les déposer en fichier, puis les lire sur place.
