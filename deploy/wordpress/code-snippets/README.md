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

| Fichier | Snippet | Portée | Actif | md5 (date de relevé) |
|---|---|---|---|---|
| `130-audit-doctrine-editoriale.php` | #130 · Audit doctrine editoriale | front-end | oui | `9d1437c9851c0d311a49ad673319fdc4` (2026-08-19) |
| `135-garde-fous-dates-et-sources.php` | #135 · Garde-fous dates et sources | front-end | oui | `daafdd83a310978e18eae9b41ae6151a` |
| `136-garde-fous-panel-formes-lieux.php` | #136 · Garde-fous 2 : panel, formes, lieux | front-end | oui | `59582f3cbccf3c03c089ac740cd41f8d` |
| `10-cs-trash.php` | #10 · CS Trash (routes `cs/v1/trash` et `cs/v1/list`) | global | oui | `d882c18b020ddb1686fb0ee171612812` |

**Le cas #10 mérite d'être lu avant de toucher à quoi que ce soit.** Le dépôt contenait
déjà `deploy/wordpress/cs-trash.php` — et il n'y a **aucun** `mu-plugins/cs-trash.php` sur
le serveur : ces routes sont servies par le snippet, en base. Le 2026-08-18, j'ai modifié
le fichier du dépôt en croyant corriger le site ; il ne se passait rien. C'est exactement
la faute du 12/08, refaite malgré la règle écrite. Le fichier d'origine porte désormais un
avertissement en tête, et la copie fidèle est ici.

**Le cas #130 rappelle la même leçon.** La copie du 17/08 était PÉRIMÉE : entre le 17 et
le 19, huit termes ont été ajoutés en base (`versant`, `transalpin`, `cote national`,
`de part et autre`, `franco-italien`, `neo-savoyard`, `aostois`, `irredentisme` — l'écart
mesuré le 18/08 après la fuite « versant » sur quatre articles) sans que la copie ici ne
soit remise à jour. Le 19/08, avant d'ajouter le terme « surnom touristique », le code
réellement en base a été relu et comparé (empreinte différente : `62afa37a…` vs
`ed75042b…`), l'ajout a été fait par ANCRE EXACTE sur le code LIVE — jamais en réécrivant
depuis ce fichier — puis la copie ici a été resynchronisée depuis la base. Procédure
suivie à la lettre plus bas dans ce document.

Les copies **d'avant** les modifications du 2026-08-17 sont sur le serveur, dans
`wp-content/uploads/cs-snippets-sauvegarde-2026-08-17/` (`130-avant.txt`, `135-avant.txt`,
`136-avant.txt`). C'est le retour arrière.

### #138 « fraîcheur des guides » — ABANDONNÉ, décision de Franck du 2026-08-17

Un quatrième audit a existé une journée. Il est **désactivé**, son cron est **déprogrammé**,
et il doit **rester** ainsi. Franck : « les guides, ça doit être rédigé une fois et c'est
tout. Il n'y a pas d'autre chose. La seule chose que je demande, c'est que le guide puisse
être lu par le panel de personas pour vérifier si ça correspond bien à ce qu'on fait avec le
reste du site, mais c'est tout. »

**Ne pas le ressusciter en croyant combler un trou.** Ce qu'il faisait — signaler les guides
citant une date passée et ceux qui périment sous 21 jours — est un choix éditorial qui a été
tranché contre. Ce qui le remplace est à la demande et sans cron :

```sh
.venv/bin/python -m scripts.panel_site --guides 2422   # un guide, après l'avoir écrit
.venv/bin/python -m scripts.panel_site --guides        # les douze guides publiés
```

L'objection écartée reste vraie et est notée pour que personne ne la redécouvre comme une
nouveauté : « Festivals de l'été en Savoie 2026 » annonce des dates passées et il est servi
en premier sur l'accueil pour la Savoie. Si la question revient, elle portera sur la
FRAÎCHEUR — pas sur ce panel-là.

Le code du snippet n'est pas copié ici : il est abandonné, pas maintenu. Il reste lisible
dans la base (`SELECT code FROM wp_snippets WHERE id=138`), inactif.

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
