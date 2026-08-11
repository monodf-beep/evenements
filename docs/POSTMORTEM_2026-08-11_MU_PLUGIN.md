# Post-mortem : agendasabauda.eu hors ligne, 2026-08-11

Vingt minutes de HTTP 500 sur l'ensemble du site, admin et API comprises, provoquées par un
fichier que j'ai écrit. Ce document raconte l'incident, puis fait l'inventaire de toutes les
erreurs de la session, parce que l'incident n'est pas isolé : il est l'aboutissement d'un
travers présent depuis le début.

## 1. L'incident

### Ce qui s'est passé

Je venais de retirer 22 sources proscrites des fiches en ligne. Pour empêcher le pipeline de les
réécrire, j'ai généré un mu-plugin `cs-source-garde.php` filtrant `update_post_metadata` sur la
clé `as_source_officielle_url`.

Le fichier était produit par concaténation de lignes PHP. L'une d'elles était écrite en **doubles
quotes** et contenait `$hote` :

```php
$l[] = "    if ($hote === '') { return false; }";
```

PHP a interpolé `$hote` au moment de la génération. La variable était vide. Le fichier déposé sur
le serveur contenait donc :

```php
    if ( === '') { return false; }
```

Une erreur de syntaxe. Les mu-plugins sont chargés avant tout le reste de WordPress : chaque
requête a fatalé. Le site public, l'administration, l'API REST et **le connecteur MCP par lequel
je travaillais** sont tombés ensemble.

### Pourquoi je n'ai pas pu réparer

Mon unique canal d'écriture passait par le site que je venais de casser. Les appels suivants ont
tous échoué. Il a fallu un accès humain en SFTP pour renommer le fichier.

Le chemin de réparation a lui-même perdu du temps, pour deux raisons qui méritent d'être notées.
J'ai transmis le chemin `/home/ohcqqjv/agendasabauda/...` tel que WordPress me le renvoyait, sans
vérifier d'abord sur quelle machine il se trouvait : Franck l'a exécuté sur le VPS du pipeline,
où il n'existe pas. Et une autre session, en parallèle, a désigné par élimination un fichier
différent, `cs-notranslate-fr-it.php`, sans savoir qu'un fichier plus récent avait été écrit.
Supprimer celui-là n'aurait rien réparé et aurait cassé autre chose.

### Le signal que j'avais et que je n'ai pas lu

L'appel qui a déposé le fichier a renvoyé, dans son champ `errors[]` :

```
Warning: Undefined variable $hote
```

**L'outil m'a dit ce qui n'allait pas.** J'ai lu `return_value`, qui annonçait
« ecrit : ... (1922 octets) », j'en ai conclu que c'était fait, et je suis passé à l'appel
suivant. Le bug était nommé, dans le résultat, à la seconde où il a été créé.

### Ce qui aurait suffi à l'éviter

Par ordre de coût croissant, chacune de ces mesures prise isolément aurait suffi :

1. Lire `errors[]`.
2. Générer le PHP en simples quotes uniquement.
3. Écrire dans `sys_get_temp_dir()`, valider par un `include` sous `catch (ParseError)`, puis
   déplacer.
4. Utiliser un snippet Code Snippets plutôt qu'un mu-plugin : un snippet se désactive depuis
   l'admin, un mu-plugin emporte l'admin avec lui.

La règle générale qui les résume : **avant d'écrire un fichier qui s'exécute au démarrage, se
demander par où on le retirera s'il est fautif.** Quand la réponse est « par le site que je suis
en train de modifier », la prudence doit monter d'un cran, pas rester la même.

---

## 2. Inventaire des erreurs de la session

Douze erreurs, dont sept que j'ai rattrapées moi-même et cinq qui ont produit un effet visible.
Elles se rangent en trois familles, et c'est le rangement qui est instructif, pas la liste.

### Famille A : j'ai cru mon instrument sans le vérifier

| Erreur | Effet | Rattrapée ? |
|---|---|---|
| Détecteur de langue comptant « la » et « per » comme français, alors que les deux mots existent en italien | 5 fiches italiennes signalées à tort comme françaises | Oui, avant d'agir |
| Requête cherchant une clé `bloquants` alors que le champ s'appelle `bloquant` | J'ai annoncé « 0 fiche bloquée » au lieu de 74 | Oui, l'incohérence m'a alerté |
| Extraction du JSON-LD cherchant `<script type="application/ld+json">` exactement, sans l'attribut de classe ajouté par Yoast | J'ai conclu que le site n'émettait **aucune** donnée structurée | Oui, au deuxième essai |
| `.{55}` au lieu de `.{0,55}` dans un contexte de regex (session du 08/08) | 3 fiches fautives invisibles dans l'audit | Oui |

Dans les quatre cas, le résultat était plausible et faux. C'est ce qui les rend dangereuses :
rien dans la sortie ne signale l'erreur, seule une invraisemblance de fond peut alerter.

**Ce que j'en ai fait :** j'ai adopté en cours de session la règle « vérifier l'instrument avant
de croire la mesure », et je l'ai appliquée systématiquement aux audits qui ont suivi. C'est ce
qui m'a fait revérifier moi-même deux sources proposées par les agents, dont une qui décrivait
l'édition 2026 d'un festival là où la fiche annonçait 2025.

### Famille B : j'ai appliqué la leçon aux données, jamais au code

C'est la famille qui a causé la panne. Une heure après avoir formulé « vérifier l'instrument
avant de croire la mesure », j'ai écrit du code non validé sur la production. La règle ne s'était
pas étendue de ce que je lisais à ce que j'écrivais.

Même schéma pour une consigne que j'avais pourtant rédigée moi-même : le brief de doctrine
imposait aux agents de ne rien inventer, mais ne leur interdisait pas d'écrire « cette
information n'a pas pu être vérifiée » **dans le texte publié**. Neuf fiches sont revenues avec
du langage d'atelier destiné au lecteur. Je l'ai corrigé, et j'ai ajouté l'interdiction explicite
au second lot.

### Famille C : j'ai conclu avant d'aller voir

| Erreur | Conséquence |
|---|---|
| Lancer la rédaction de 50 fiches **avant** d'en chercher les sources | 718 000 tokens pour 10 fiches réellement étoffées. La substance vient de la source ouverte : 22 sources lues, 10 textes corrects, la corrélation était totale. Le second lot, lancé après recherche des sources, a produit un bien meilleur résultat pour moitié moins de jetons |
| Juger le bloc « Nouveautés » sur son rendu chez nous et conclure que le composant était inutile | Faux. Chez Guida Torino, ce bloc liste leurs **articles**, pas des fiches d'événement, d'où l'absence de doublon. C'est Franck qui m'a donné la référence, et elle a renversé ma conclusion |
| Me fier à l'horloge du serveur (9 août) plutôt qu'à la date réelle (11 août) | Diagnostic faux : j'ai présenté comme une question de seuil ce qui était un vrai retard de trois jours |
| Affirmer que je n'avais accès à aucun dépôt du projet | Faux : `monodf-beep/evenements` est dans mes répertoires de travail depuis le début. C'est la raison pour laquelle rien n'a été documenté au bon endroit pendant toute la session |
| Transmettre un chemin serveur sans vérifier de quelle machine il s'agissait | Une tentative de réparation perdue sur le mauvais serveur, pendant la panne |

---

## 3. Ce qui en est tiré

**Documents créés :** `docs/MCP_NOVAMIRA.md`, qui n'existait pas alors que tout le travail sur le
site passe par ce connecteur depuis des semaines. Ce document consigne les limites de transport,
la sémantique des messages d'erreur, le moyen de distinguer une panne du site d'une panne du
connecteur, et les règles d'écriture de fichiers.

**Journal ajouté** dans `docs/BACKLOG.md`, avec la répartition habituelle entre ce qui se corrige
dans WordPress et ce qui doit l'être dans le pipeline. Le point le plus coûteux y figure : tant
que la passe amont laisse passer les sources proscrites, les reports en double et les verdicts de
panel sans motif, tout ce qui est réparé côté site est réécrit à la republication suivante.

**Une constatation d'ordre général**, qui vaut au-delà de cet incident. Sur douze erreurs, une
seule a produit une panne, et c'est la seule qui portait sur du **code exécuté au démarrage**.
Les onze autres portaient sur des données, des mesures ou des jugements, et toutes étaient
rattrapables. La conclusion n'est pas qu'il faut se tromper moins, c'est qu'il faut réserver la
prudence maximale au très petit nombre d'actions dont l'échec supprime le moyen de se corriger.
