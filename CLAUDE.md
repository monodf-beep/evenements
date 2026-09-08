# Agenda Sabauda — règles de travail

Agenda culturel bilingue FR/IT. Chaîne : scraping → dédoublonnage → dates → lieux →
évaluation → enrichissement → publication WordPress. Base SQLite `data/events.db` (WAL),
site `agendasabauda.eu`, 14 crons quotidiens/hebdomadaires (`crontab.txt`).

**Ce dépôt tourne EN PRODUCTION.** La base contient plusieurs milliers de fiches dont
plusieurs centaines sont publiées et visibles du public. Il n'y a pas d'environnement de
test.

---

## Les six règles, tirées d'incidents réels

### 1. Un identifiant en base ne prouve RIEN sur le site

`wp_post_id_as` renseigné ne veut pas dire « en ligne ». Il survit à une mise à la
corbeille. Deux fausses alertes en sont nées :

- « 61 posts supprimés » (2026-08-02) — aucun ne l'était, tous étaient à la corbeille ;
- « 21 fiches à dépublier » (2026-08-03) — 10 sur 21 étaient déjà retirées.

**Ne jamais conclure sur l'état du site sans avoir interrogé WordPress.** Et pas le
front-end : `/?p=<id>` répond 404 pour tout `tribe_events`, vivant ou mort. Seule l'API
REST sépare les trois états (public / corbeille / supprimé) — voir
`reconcile_wp_deleted._etat`.

### 2. Un inventaire WordPress est INCOMPLET

The Events Calendar exclut les événements **passés** de ses collections REST. Une fiche
terminée reste publiée et accessible par son adresse, mais n'apparaît dans aucune liste.
`audit_wp_ghosts` a annoncé « 0 anomalie » alors que onze fiches rejetées étaient en
ligne, pour cette seule raison.

**Pour savoir si un post précis est en ligne, l'interroger par son numéro.** Les listes
servent à explorer, jamais à prouver une absence.

### 3. Tout état terminal doit avoir quelqu'un qui le rouvre

C'est le défaut structurel de ce dépôt : un script pose un état qui écarte une fiche
d'une file, et aucun autre ne sait l'en sortir. Six culs-de-sac trouvés le 2026-08-03,
dont un créé le jour même en corrigeant les autres.

Avant d'ajouter un tel état, répondre à `docs/ETATS_TERMINAUX.md` : **qui le rouvre, à
quelle condition, et où se voit le nombre de fiches garées ?** « Un humain qui tape une
commande » n'est pas une réponse — 823 fiches ont dormi dans `venue_source='llm_none'`
alors que l'option `--retry` existait depuis le premier jour.

**Un refus qui se rejoue sur la MÊME entrée n'est pas un rouvreur.** Ajouté le
2026-08-08, après l'avoir refait une fois de plus. Un portillon posé le 06/08 refusait
une traduction dont le titre semblait non traduit ; son commentaire affirmait « le coût
d'un faux refus est un jour de retard, la fiche se représente au run suivant ». La
première moitié est vraie, la seconde ne l'est pas : la fiche se represente avec la même
matière, le LLM produit un titre équivalent, le portillon refuse à l'identique — tous les
jours, en brûlant deux appels API à chaque passage. Constaté en production sur la fiche
3588 (« La Rencontre Valdôtaine »), dont la traduction était en fait correcte : le
marqueur « français » venait du NOM PROPRE de l'événement.

Donc, pour tout portillon, deux exigences :

- **écrire pourquoi le prochain passage donnerait un AUTRE résultat.** Si la réponse
  repose sur « le LLM est stochastique », c'est une hypothèse — la tester ou renoncer ;
- **la fixture doit contenir un cas qui doit PASSER, choisi près de la frontière.** Celle
  du 06/08 n'avait que des cas qui confirmaient le design : elle est passée au vert sur un
  portillon faux. Un test qui ne cherche qu'à se donner raison ne prouve rien.

### 4. Dry-run d'abord, toujours

Tous les scripts destructifs sont en dry-run par défaut et demandent `--apply` ou
`--execute`. **Lire la sortie du dry-run avant d'appliquer**, même quand on croit savoir.
Le dry-run de `relink_wp_ids_as` du 2026-08-03 proposait six corrections dont trois
fabriquaient un doublon.

Avant tout `--apply` de masse : `.venv/bin/python scripts/backup_db.py`.

### 5. On ne travaille que sur ce qui est encore devant nous

Trois familles méritent qu'on s'en occupe, et elles seules :

- les événements **à venir** ;
- les événements **en cours** — une exposition de mai à septembre compte tout l'été,
  donc c'est `date_event_end` qui décide, jamais `date_event_start` seule ;
- les événements **récurrents** (`utils.completeness.is_recurring`), qui n'ont pas de
  date unique et ne sont donc jamais « passés ».

**Tout le reste est mort.** Réparer une fiche dont l'événement a eu lieu ne sert
personne : elle ne sera pas republiée, plus aucun visiteur ne la cherche. Un audit, un
rapport ou une liste de correctifs qui mélange passé et à-venir **fabrique du travail au
lieu d'en désigner** — c'est le reproche que Franck a fait le 2026-08-03 à
`audit_dedupe_damage`, qui présentait 94 cas comme s'ils comptaient tous alors que la
fiche concentrant le tiers d'entre eux était datée du 10 juillet, passée depuis trois
semaines.

Deux précautions quand on applique cette règle :

- **une fiche sans date ne se classe PAS en « passé »** — c'est une donnée manquante, pas
  un événement terminé, et `dates.py` la remplira peut-être demain ;
- **la date lue vient de la base, et une mauvaise fusion peut l'avoir corrompue** —
  WP#6798 portait la date d'un autre événement. Donc écarter le passé d'un rapport, oui ;
  le supprimer de la base sur ce seul motif, non.

### 6. Rapporter le RÉSULTAT, jamais l'intention

Un bilan qui annonce ce qui a été demandé plutôt que ce qui s'est produit ferme la
question au lieu de l'ouvrir. Recompter en base après une écriture ; ne jamais écrire
« N fiches traitées » sur la foi de la longueur d'une liste.

Et un état qui sort une fiche d'une file la sort aussi de tous les bilans : le compter
explicitement, sinon on le découvre des semaines plus tard.

**Un compteur doit dire ce qu'il compte, et une file ne doit contenir que ce qu'un humain
peut faire.** Ajouté le 2026-08-11, après une matinée entière passée à démonter des
chiffres que j'avais moi-même produits. Franck : « 548 tâches ! c'est ingérable. »

Trois compteurs décrivaient l'état du site, les trois étaient gonflés, et aucun ne
mentait sur ses données — ils mentaient sur leur PÉRIMÈTRE :

- « 793 points à vérifier » — la file n'avait aucun filtre de date : elle affichait les
  points d'événements terminés depuis des mois ;
- « 108 fiches publiées trop maigres » — passé et à-venir mélangés ; il y en avait SEIZE
  encore devant nous ;
- « 454 points à contrôler » — dont 315 n'étaient pas des faits douteux mais des
  informations que la source ne publie pas. Personne ne peut vérifier la capacité
  d'accueil d'une sortie au lac : ni Franck, ni le modèle. Une file pareille n'est pas un
  garde-fou, c'est l'inventaire des silences de la source.

Deux exigences, donc, pour tout chiffre destiné à un humain :

- **écrire son périmètre à côté de lui.** Deux compteurs qui portent le même nom et
  comptent deux choses se contrediront un jour, et c'est le plus gros qu'on croira ;
- **avant d'ajouter une ligne à une file, se demander ce que le lecteur en FERA.** S'il
  n'y a pas de geste au bout, ce n'est pas une tâche : c'est du bruit qui décourage, et
  qui cache les vraies. Sur ces 454 points, le seul qui comptait — « l'organisateur
  annoncé semble être la journaliste, pas l'organisatrice » — était noyé sous trois cents
  « tarifs non publiés ».

---

## Le journal des erreurs

`docs/ERREURS_2026-08-11.md` liste les quinze fautes d'une seule journée, avec pour chacune
le garde-fou qui l'empêche de revenir. `docs/ERREURS_2026-08-17.md` fait de même pour six
autres, dont trois récidives — et elles ont une racine commune qui mérite d'être ici :

**Conclure sur un indice de SURFACE, au lieu d'aller lire la chose.** Ce jour-là : quatre
audits WordPress déclarés « redondants » sur la seule ressemblance de leurs titres (aucun ne
l'était, et j'ai proposé de les supprimer) ; quarante minutes de recherche dans ce dépôt
pour un code qui vivait dans la base WordPress, alors que l'ABSENCE D'ACCENTS des messages
désignait leur provenance dès le premier coup d'œil ; une baisse de 7 à 6 attribuée à mon
correctif quand elle venait d'un `array_slice(…, 0, 6)` d'affichage. Les deux fois où j'ai
lu — le code des audits, la sortie réelle du filtre — la conclusion s'est INVERSÉE.

`docs/ERREURS_2026-08-18.md` ajoute sept fautes, et **quatre d'entre elles sont la MÊME
faute que ci-dessus** — commise le lendemain du jour où je l'ai écrite. Un dépôt HTTPS
échouait ; j'ai annoncé quatre causes successives comme établies (l'en-tête HTTP, une
limite de l'hébergeur, une IPv4 disparue, puis l'hébergeur à nouveau), et j'ai failli
faire demander à OVH le déblocage d'une IP sur la foi de la deuxième. Ce qui a tranché
tenait en quatre commandes qu'il fallait taper à la première minute : ping, port 80,
port 443, et un hôte de contrôle.

D'où la formulation la plus utile de cette racine, celle à relire avant de répondre :

**Ne jamais présenter une INFÉRENCE comme un FAIT.** Les deux sont acceptables — mesurer,
ou dire « c'est une hypothèse ». Les confondre coûte une demi-journée et use la confiance
dans tout le reste. Ce jour-là, cinq affirmations pour cinq mesures disponibles que
personne n'avait demandées : `ifconfig.me` répondait depuis toujours, `parsed=175` était
en base depuis des semaines, la sortie du filtre était à une commande.

Corollaire pour tout diagnostic : **un diagnostic qui pose une alternative sans la
trancher n'est pas un diagnostic.** « Réessayer plus tard dira lequel des deux » rendait à
un humain une question que la machine règle en trois secondes.

Trois corollaires opérationnels :

- **une liste tronquée doit annoncer son total.** Sans ça elle fabrique de fausses causes,
  y compris pour celui qui l'a écrite. Le 18/08, le chiffre que Franck attendait depuis le
  matin était calculé puis jeté par un `[:2000]`, trois fois de suite ;
- **avant de diagnostiquer une panne, LIRE #agendasabauda.** Le 18/08, le bilan
  automatique de 11h05 portait déjà le bon diagnostic — heure de début (09h58), preuve que
  le réseau du VPS allait bien, et la conséquence « 0 fiche publiée aujourd'hui, pas 8 ».
  J'ai passé l'après-midi à le retrouver, avec quatre hypothèses fausses au passage.
  L'accès en lecture existait ; je ne l'avais pas ouvert ;
- **un dispositif fait pour rendre autonome ne peut pas ressembler à une panne pendant
  qu'il travaille.** Cinq minutes de silence entre deux tentatives, et une commande donnée
  avec `| tail`, qui retient tout jusqu'à la fin : Franck a cru le script mort. Annoncer
  chaque étape, et donner les commandes longues SANS `tail` ;
- **un fichier poussé sur une branche ne prouve pas qu'il est déployé** (règle 1
  transposée) : `deploy/update.sh` remet le dépôt sur `claude/quirky-davinci-jvqrnw`, donc
  du travail poussé ailleurs n'arrive pas — et sera EFFACÉ au déploiement suivant. Vérifier
  la branche que vise le script avant de dicter la commande, et la donner avec son
  répertoire.

**Neuf des quinze fautes du 11/08 étaient des récidives d'une règle
déjà écrite ici.** Écrire la règle ne suffit donc pas ; c'est la fixture, le dry-run et le
périmètre affiché à côté du nombre qui tiennent, parce qu'eux se déclenchent tout seuls.

Deux enseignements de ce journal valent pour toute session future :

**Un zéro ne dit pas s'il vient d'un échec ou d'une absence de cas.** Un pipeline qui ne
trouve rien ressemble EXACTEMENT à un monde où il n'y a rien à trouver. Trois fois le
2026-08-11 un « 0 » a semblé désigner une source pauvre ; les trois fois, c'était la
requête. Tout compteur qui peut valoir zéro doit dire combien de cas se sont présentés.

**Un défaut de forme ne se voit pas dans le code, il se voit dans les RÉSULTATS.** Le
détecteur de comptes rendus prenait « est présenté » (présent passif) pour un passé, et
lisait « à ciel ouvert » comme l'auxiliaire avoir. Aucune relecture ne l'aurait montré ;
la liste des vingt-cinq fiches signalées l'a montré en dix secondes. Avant de livrer un
portillon, le passer sur des données réelles et LIRE ce qu'il refuse.

---

## Périmètre éditorial

Quatre territoires : **Savoie / Haute-Savoie**, **Piémont**, **Vallée d'Aoste**, et le
**Comté de Nice** — qui est l'**arrondissement de Nice**, PAS le département. Les 62
communes de l'arrondissement de Grasse (Cannes, Antibes, Grasse, Vence, Cagnes,
Valbonne…) sont **hors périmètre**. Liste faisant foi :
`config/communes_comte_de_nice.json`.

Public **visé**, pas seulement public **admis** : un congrès, un colloque scientifique ou
un salon B2B n'a pas sa place, même ouvert à tous. Mais « Conférences & Rencontres » est
une des onze catégories : salon du livre, conférence de musée, café philo, dédicace y
restent pleinement. Le partage se fait sur **à qui ça s'adresse**, jamais sur le mot du
titre. Détail : `docs/CHARTE_EDITORIALE.md`.

---

## Autonomie : réversible = seul, irréversible = jamais

**Arbitrage de Franck du 2026-08-03 : le site doit se tenir à jour tout seul.** Les
permissions de `.claude/settings.json` ne demandent donc plus confirmation avant d'agir.
La frontière n'est plus « écrire ou lire », elle est **« réversible ou non »**.

**Se fait seul, sans demander** — parce que ça se défait :

- corbeille WordPress (`trash_by_ids`, `trash_wp_ids`, `reconcile_catalogue`) — un post
  corbeillé se restaure en un clic ;
- changements de `statut` (`purge_*`, `unreject_wp_online`) — une re-classification, pas
  une perte de donnée ;
- publication, enrichissement, dates, lieux, traduction — le pipeline normal ;
- `git commit`, `git push` sur la branche de travail, `crontab`.

**Interdit, et ça ne se négocie pas** — parce que ça ne se défait pas :

- `rm -rf`, `git reset --hard`, `git clean`, `git push --force` ;
- `--hard` sur les purges (il SUPPRIME les lignes au lieu de les rejeter) ;
- `DELETE FROM`, `DROP TABLE`, `TRUNCATE` en SQL direct ;
- `force=true` sur une route **`wp/v2/…`** — c'est le drapeau de suppression DÉFINITIVE
  de WordPress, qui court-circuite la corbeille. Idem `--force-delete`.
  ⚠️ **À ne pas confondre** (précisé le 2026-08-03, après que la question s'est posée en
  vrai) : `scripts/cleanup_as_trash.trash_one(..., force=True)` passe par la route MAISON
  `cs/v1/trash`, où `force` signifie « autoriser la corbeille sur un post déjà publié ».
  Rien à voir : ce chemin-là est **réversible** et c'est celui qu'utilisent `trash_by_ids`
  et `trash_wp_ids`. Vérifier la ROUTE avant de conclure, jamais le seul mot `force` ;
- lecture du `.env`.

**Demande encore** : `apt`, `pip install`, `systemctl`, `reboot` — hors du projet ; et la
modification de `.claude/settings.json` lui-même, pour qu'aucune session ne puisse élargir
ses propres droits en silence.

### Le filet, puisqu'il n'y a plus de confirmation

`scripts/backup_db.py` tourne à 3h (`crontab.txt`). **Avant toute opération de masse,
le relancer à la main** — la règle 4 reste valable, elle porte simplement sur soi-même
plutôt que sur Franck. Et la corbeille WordPress n'est jamais vidée automatiquement.

### Ce qui reste un arbitrage humain, même sans blocage technique

Défusionner, re-classer une fiche que Franck a rejetée lui-même, trancher un orphelin,
déployer du CSS sur le site : le harnais ne les empêche plus, **le jugement doit le
faire**. Dans le doute sur une décision ÉDITORIALE — pas technique — proposer plutôt
qu'agir.

---

## Développement

Branche de travail : `claude/quirky-davinci-jvqrnw`. **Ne jamais pousser sur la branche
par défaut.**

Commits en français, au présent, expliquant **pourquoi** et pas seulement quoi — avec la
mesure ou l'incident qui a motivé le changement quand il y en a un. Les commentaires de
ce dépôt sont sa vraie documentation : les garder.

Vérifier sur fixture avant de committer un correctif — construire une base jetable avec
`scripts.scraper_events.init_db`, jamais sur `data/events.db`.

**Déployer sur le VPS, c'est `bash deploy/update.sh`** — une commande, qui fait le fetch,
le reset sur la branche, les dépendances et le redémarrage du service. Ne PAS dicter à
Franck une suite de `git pull` / `pip install` / `systemctl` : il n'est pas développeur,
c'est lui qui tape, et ce script existe précisément pour ça. Rappel écrit le 2026-08-08
parce que je le lui ai fait retaper à la main pendant toute une session, alors qu'il
avait lui-même utilisé `deploy/update.sh` la veille.

**Aucun PHP ne part sur WordPress sans `php -l`, et sans passer par `deploy/wordpress/`.**
Écrit le 2026-08-10, après deux jours de site injoignable — front, wp-admin et API REST
en 500 en même temps — pour une seule ligne :

```
Parse error: syntax error, unexpected token "===" in
  .../wp-content/mu-plugins/cs-source-garde.php on line 20
```

Un mu-plugin se charge AVANT tout le reste de WordPress : une faute de syntaxe y tue
aussi la porte qui permettrait de la réparer. Le retour arrière a demandé du FTP, que
Franck n'avait pas sous la main — c'est ça qui a coûté les deux jours, pas la faute
elle-même. Et `cs-source-garde.php` n'était PAS dans le dépôt : écrit directement sur le
serveur, sans relecture ni copie versionnée. Il reste **34 mu-plugins `cs-*` en ligne
dans ces conditions**, dont 18 seulement ont leur double ici.

Donc : le fichier vit dans `deploy/wordpress/`, `tests/test_php_syntax.py` le passe au
`php -l` (avec une contre-épreuve : un fichier cassé DOIT être refusé), et
`deploy/push-wordpress.sh` refuse d'envoyer ce qui ne compile pas.

**Mais AVANT tout ça, établir OÙ le code vit.** Ajouté le 2026-08-12, après trois heures
passées à réparer quatre transports successifs pour livrer un fichier que WordPress
n'exécute pas : `cs-publish.php` n'est pas un mu-plugin, il est collé dans **Code
Snippets**, en base. Aucun dépôt de fichier ne l'atteint. Son en-tête proposait les deux
installations depuis le premier jour — personne n'avait vérifié laquelle avait été retenue.

C'est la règle 1 transposée au code : un fichier dans `deploy/wordpress/` ne prouve ni
qu'il est déployé, ni qu'il est à jour, ni même qu'il est la référence. Ce jour-là les
trois étaient faux, et la version en ligne contenait **deux morceaux de code absents du
dépôt** — dont le méta de tri qui fait apparaître la Foire de la Saint-Ours en page
d'accueil. L'écraser aurait été une régression, pas un correctif.

Le détail vérifié — où vit chaque chose, quels transports OVH répondent quoi, comment
contrôler la syntaxe sans binaire `php`, et où est la sauvegarde d'avant — est dans
`docs/DEPLOIEMENT_WORDPRESS.md`. Le canal qui marche est **Novamira**. La route
`GET /wp-json/cs/v1/version` répond ce que la version EN LIGNE dit d'elle-même : tant
qu'elle renvoie 404, le correctif n'est pas passé.
