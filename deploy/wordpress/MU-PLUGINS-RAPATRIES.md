# Mu-plugins : dépôt aligné sur la production le 2026-09-05

## Pourquoi

En cherchant quel code générait la barre de territoires, le fichier responsable
(`cs-territoire-persistant.php`) s'est révélé absent du dépôt. Mesure faite dans la foulée :

> **33 mu-plugins `cs-*` tournaient en production. DIX seulement avaient leur double ici.
> 23 n'étaient versionnés nulle part.**

Le CLAUDE.md annonçait « 34 en ligne, dont 18 seulement ont leur double ici ». Le chiffre réel
était 10 sur 33 : l'écart s'était creusé sans que personne le remesure.

C'est la configuration exacte de l'incident du 8 au 10 août 2026, où une faute de syntaxe dans
un mu-plugin écrit directement sur le serveur a rendu le site injoignable deux jours. Ce ne sont
pas la faute de frappe qui a coûté ces deux jours, c'est l'absence de version antérieure à
remettre : il a fallu du FTP.

**Les 33 sont désormais ici, identiques à la production à l'octet près**, donc couverts par
`tests/test_php_syntax.py` (qui lit `deploy/wordpress/*.php`, **à plat** — d'où le rangement à
plat plutôt qu'en sous-dossier : un sous-dossier serait passé à côté du contrôle, ce qui aurait
annulé tout l'intérêt de l'opération).

---

## Le vrai enseignement : 4 des 10 déjà versionnés DIVERGEAIENT

Le contrôle MD5 des 10 fichiers qu'on croyait à jour a donné **6 identiques, 4 divergents**.
Un fichier présent dans `deploy/wordpress/` ne prouvait donc ni qu'il était déployé, ni qu'il
était à jour, ni qu'il était la référence. C'est la règle 1 du CLAUDE.md, transposée au code.

Analyse fichier par fichier, en comparant le **code seul** (commentaires et espaces retirés via
`token_get_all`), parce que « les fichiers diffèrent » ne dit pas *en quoi* :

| Fichier | Nature de l'écart | Décision |
|---|---|---|
| `cs-notranslate-fr-it.php` | commentaires seulement. La production porte la version **corrigée le 06/08**, qui signale qu'une justification invoquait un `cs-cache-control-home.php` inexistant. Le dépôt gardait l'ancienne. | production |
| `cs-menu-it.php` | commentaires seulement (dépôt plus bavard, production condensée) | production |
| `cs-pub-slots-vides.php` | commentaires seulement : le dépôt portait une note « récupéré de la production le 2026-08-04 », absente en ligne | production |
| **`cs-taxo-it.php`** | **écart de CODE réel** | **production** |

### `cs-taxo-it.php` : le dépôt avait tort, et le déployer aurait cassé quelque chose

`cs_taxo_it_map()` associe chaque terme FR de la taxonomie `territoire` à sa traduction IT, en
retrouvant le terme FR **par son slug**. Les deux versions ne cherchaient pas les mêmes :

| | Savoie | Comté de Nice |
|---|---|---|
| dépôt | `savoie-haute-savoie` | `nice-alpes-maritimes` |
| production | `savoie` | `comte-de-nice` |

Vérification faite sur les termes réels :

```
get_term_by(slug='savoie-haute-savoie')  -> INTROUVABLE
get_term_by(slug='nice-alpes-maritimes') -> INTROUVABLE
get_term_by(slug='savoie')               -> #3  Savoie          (48 événements)
get_term_by(slug='comte-de-nice')        -> #10 Comté de Nice   (30 événements)
```

Les slugs du dépôt sont ceux du **plan du site**, jamais ceux qui ont été créés. Le code fait
`continue` sur un terme introuvable : déployer la version du dépôt aurait donc **arrêté en
silence la création et le rattachement des traductions IT pour la Savoie et le Comté de Nice**.
Pas d'erreur, pas de message, juste deux territoires qui cessent d'exister côté italien.

C'est mot pour mot la leçon `cs-publish.php` du CLAUDE.md : *« la version en ligne contenait
deux morceaux de code absents du dépôt — l'écraser aurait été une régression, pas un
correctif. »*

**Conséquence pour la suite : `deploy/wordpress/` n'est PAS une source à pousser aveuglément
vers la production.** C'est un miroir. Avant tout déploiement d'un de ces fichiers, comparer.

---

## Vérifier que le dépôt est encore fidèle

Côté serveur (Novamira, `novamira/execute-php`) :

```php
$d = ABSPATH . 'wp-content/mu-plugins/';
$out = [];
foreach (glob($d . 'cs-*.php') as $f) { $out[] = md5_file($f) . '  ' . basename($f); }
sort($out); return implode("\n", $out);
```

Côté dépôt :

```bash
cd deploy/wordpress && md5sum cs-*.php | sort
```

Toute ligne qui diffère signale soit une modification en production non redescendue ici, soit un
fichier d'ici jamais déployé. Les deux méritent qu'on aille lire, et le contrôle
« commentaires seuls ou code réel ? » se fait ainsi :

```bash
php -r 'foreach (token_get_all(file_get_contents($argv[1])) as $t) {
  if (is_array($t)) { if (in_array($t[0], [T_COMMENT, T_DOC_COMMENT, T_WHITESPACE], true)) continue; echo $t[1]; }
  else echo $t; }' fichier.php | md5sum
```

---

## État au 2026-09-05 : 33 fichiers, dépôt == production

Contrôle passé : **33 / 33 identiques**. Empreintes de référence dans l'historique git de ce
fichier (commit du 05/09) ; les régénérer avec la commande ci-dessus plutôt que de les recopier.

**Les fichiers ne sont PAS annotés.** La convention d'août ajoutait une note « récupéré depuis la
production le … » dans l'en-tête ; on s'en abstient délibérément, pour que les copies restent
identiques à l'octet près et que le contrôle MD5 garde son sens. C'est d'ailleurs cette
annotation qui faisait diverger `cs-pub-slots-vides.php`. La provenance vit ici et dans git.

## Comment ils ont été transférés

Archive ZIP créée côté serveur dans `wp-content/uploads/` sous un nom aléatoire, téléchargée,
**puis supprimée immédiatement** (suppression vérifiée, aucune archive restante). Deux passes de
recherche de secrets, côté serveur puis en local, avant tout commit : clés d'API, jetons, mots de
passe, URL avec identifiants, mots de passe d'application WordPress. Aucune occurrence. Les 33
fichiers passent `php -l` (PHP 8.4.19) et le test du dépôt.
