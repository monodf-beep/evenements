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
| `15-cs-gabarit-hub-territoire-categorie.php` | #15 · CS · Gabarit Hub territoire/catégorie | front-end | oui | `ce606305fbcdec57b65e8e5ae354aa4b` (2026-09-06) |
| `23-cs-gabarit-recherche.php` | #23 · CS · Gabarit Recherche | front-end | oui | `a7fd40535f7ea92989f05484b75454e7` (2026-09-06) |
| `26-cs-gabarit-nos-articles-listing.php` | #26 · CS · Gabarit Le Fil (listing) — page « Nos articles » | front-end | oui | `639f5093ef22060fdc9f984d6cd2161a` (2026-09-06, soir) |
| `24-cs-gabarit-proposer-un-evenement.php` | #24 · CS · Gabarit Proposer un événement | front-end | oui | `3f7709b3b29d998cc12e6bc9d7004f5d` (2026-09-06) |
| `148-cs-plan-du-site-et-villes-du-territoire.php` | #148 · CS - Plan du site généré et villes du territoire | front-end | oui | `ea7b320ce60d4cead610fdbb8d1520b9` (2026-09-06) |
| `62-cs-header-compact-scroll.php` | #62 · CS · Header compact (scroll) | global | oui | `b899480a238c41ad673bc7b37d9f6ba2` (2026-09-07) |
| `134-cs-bloc-a-lire.php` | #134 · CS - Bloc A lire (rendu PHP) | front-end | oui | `7627ff584e34d66256334990f2e81e39` (2026-09-06, soir) |
| `44-cs-home-allocateur-centralise.php` | #44 · CS - Home allocateur centralisé (dedup fiable + langue + territoire) | front-end | oui | `5c017ab3fca0044c5fcd16544e13b794` (2026-09-06, soir) |

**Le cas #44 (2026-09-06) : « je ne veux plus autoriser 2x le même article ».** Franck,
capture de `/explore/savoie/` (via l'ancien /explore/) : la Foire de Savoie apparaissait
deux fois. Deux causes distinctes, et un premier correctif trop large corrigé le même jour :

1. Persistant, réel : « À la une » et « Jour » sont chacune rendues par **deux widgets
   JetEngine distincts** (plein format + compact) partageant le MÊME `_element_id` —
   l'allocateur dédoublonne ENTRE sections du plan, jamais entre deux widgets de la MÊME
   section, donc les deux montraient l'item nº1. Corrigé par un registre statique **PAR
   SECTION** (`$deja_par_section[$eid]`) dans le filtre
   `jet-engine/listing/grid/posts-query-args` lui-même : un id déjà rendu dans CETTE
   section ne s'y représente plus, quel que soit le widget.
2. Premier correctif (annulé le même jour) : j'avais aussi mis à 0 le budget de repli
   entre SECTIONS différentes (`$reuse_budget`, décision du 23/07 : jusqu'à 2
   répétitions tolérées sur toute la home plutôt qu'une section vide). Constaté après
   coup : ça vidait « À la une » sur les petits territoires (Savoie : « Aucun événement
   pour le moment ») au lieu de viser le vrai bug. Franck a précisé la règle : **jamais
   2x dans la MÊME section, mais jusqu'à 2 fois au total sur toute la home reste
   accepté** — c'est exactement le budget du 23/07, remis à sa valeur d'origine (2, et
   4 pour `venir`/`venir-bottom`).

Vérifié après le second correctif, section par section (regroupement des `data-post-id`
par `_element_id` sur la page rendue) : zéro doublon DANS chaque section sur les 4
territoires, et « À la une » n'est plus vide sur la Savoie.

**Troisième correctif, le soir même — le registre par section est ANNULÉ.** Franck,
captures desktop de Nice et de « les 4 » : « on a toujours pas retrouvé d'articles à la
une ! ». Mesuré : pour un visiteur anonyme le HTML contenait bien 727 et 7495… dans le
widget MOBILE (listing 1696, bloc `.as-home`, `display:none` à partir de 900 px). Le widget
DESKTOP (1695, `.as-home-desktop`, masqué en dessous) rendait `jet-listing-not-found` sur
TOUS les territoires. Les « deux widgets d'une même section » du point 1 ne sont donc pas
concurrents mais alternatifs — jamais visibles ensemble — et le registre faisait exactement
l'inverse de ce qu'il promettait : le mobile, rendu en premier, consommait les ids, le
desktop recevait `[0]`. Ma vérification du point 1 comptait les `data-post-id` sans
regarder lequel des deux blocs est affiché — un doublon mobile+desktop dans le HTML n'est
pas un doublon à l'écran, et c'est ce que j'avais pris pour le bug. Le plan de
l'allocateur garantit déjà qu'un id n'apparaît qu'une fois PAR section ; chaque widget
reçoit le plan entier, comme avant le 06/09. Vérifié en ligne après écriture, widget par
widget : desktop = mobile sur Nice (727, 7495), Savoie (8150, 754), Piémont (6386), VdA
(4113), « les 4 » FR (8096, 7495, 6386). Sauvegarde :
`novamira-sandbox/backups/snippet-44-20260906-203543.txt`.

**Quatrième passe (même soir) : le VRAI doublon, enfin mesuré.** En faisant calculer les
plans par l'allocateur lui-même, territoire par territoire : Savoie `evidence=[1925]` et
`evidence-bottom=[1925]` — la Foire de Savoie deux fois de suite dans la même colonne,
exactement la capture du matin ; Nice `venir` et `venir-bottom` partageaient 909. Cause :
les moitiés basses complètent leur manque par réemploi (`$reuse_budget` / `max_reuse`), et
le réservoir de réemploi contenait les ids de la moitié HAUTE de la même colonne. Le
closure `$take` accepte désormais un 5ᵉ argument `$exclure_reemploi` ; `evidence-bottom`
reçoit les ids d'`evidence`, `venir-bottom` ceux de `venir` (le plan est construit
séquentiellement pour pouvoir s'y référer). Remesuré après écriture : intersection vide sur
Savoie, Nice, « les 4 » ; page Savoie rendue conforme (`evidence-bottom` vide plutôt que
redondant). Sauvegarde : `novamira-sandbox/backups/snippet-44-20260906-211554.txt`.

Et une réserve honnête sur le manque de matière : côté FR il n'y a que 76 événements à
venir, dont 12 avec `as_une_now` > 0 (Nice 3, Savoie 3, Piémont 5, VdA 1) — et « À la
une » est servie APRÈS « Ce week-end » (6) et « Les 7 jours » (8) sans droit de réemploi
(`max_reuse = 0` sur cette ligne du plan). Une ou deux fiches par territoire, c'est le stock
réel, pas un bug d'affichage.

Vérifié après écriture (comptage des `data-post-id` sur la page rendue) : **zéro doublon**
sur les 4 pages territoire, la home FR, la home IT et une page catégorie IT — contre 1 à
11 doublons par page avant les deux correctifs.

**Le cas #62 (2026-09-07) : « un espace en trop en haut de page » en mobile.** Franck,
capture d'écran de la home FR sur téléphone, chevrons dessinés autour d'une bande vide
au-dessus du logo. **Mesuré avant de conclure** (Chromium headless, viewport 412 × 915,
sur une copie locale de la page réellement servie) : le panneau home commençait à
**25,5 px** du haut au lieu de 0, et le logo à **41,5 px** au lieu de 16.

La cause n'était ni une marge du panneau (`margin-top: 0`) ni un padding du conteneur
(`.site` et `.as-home-root` à 0) : **six `<p>` sans contenu visible**, chacun portant sa
marge basse par défaut (1.5 em = 25,5 px à 17 px de fonte). Le premier, placé juste avant
`.as-home`, poussait tout le haut de la page ; un deuxième ajoutait le même décalage au
milieu (top 3342 px), les quatre autres vivaient dans `.as-home-desktop`.

**Ils ne viennent pas du contenu, ils sont fabriqués au rendu** : `wpautop` enveloppe dans
un `<p>` les commentaires HTML isolés du contenu des pages 928/1717. La preuve tient à la
page italienne — son `post_content` n'en contient **aucun** (`<p></p>` : 0, `<p><!--…--></p>` :
0) et son HTML servi en montre pourtant **trois**, exactement comme la française. Nettoyer
le contenu n'aurait donc rien tenu : la prochaine édition de la page les aurait ramenés.
(La home FR portait en plus trois blocs `wp:paragraph` vides en fin de contenu, laissés par
l'éditeur — même effet, autre origine.)

Correctif : `.as-home-root p:empty{ display:none !important; }`, ciblé sur le conteneur de
la home et non site-wide. `:empty` matche bien un `<p>` ne contenant qu'un commentaire (la
spec ignore les commentaires) — **vérifié en direct, 6 sur 6**, pas supposé. Remesure sur la
page réellement servie après écriture : panneau à **0**, logo à **16 px** (le seul padding
voulu du masthead), zéro `<p>` vide encore affiché, et la règle est servie dans les deux
langues. Sauvegarde d'avant :
`novamira-sandbox/backups/snippet-62-20260907-074143.txt` (md5 `c26c99d3322c5721e9a96ec0ed6f059d`).

**Le cas #134 (2026-09-06) : réécriture complète des règles de « À lire ».** Franck,
capture de la Vallée d'Aoste : « je ne sais pas si on mélange des territoires ». Discussion
en session (maquette « Le moteur d'À lire », voir conversation) tranchée ainsi : territoire
actif d'abord (4 places), saison (`cs_guide_saison_debut`/`cs_guide_saison_fin`, Custom
Fields facultatifs — hors saison EXCLU, pas relégué, règle 5), diversité de sujet
(`cs_guide_cat_term`), rotation quotidienne des ex æquo (même défaut déjà corrigé sur
« À la une »), et une place voisine réservée par proximité (Savoie↔Piémont/VdA,
Piémont↔VdA/Savoie/Nice, VdA↔Savoie/Piémont, Nice↔Piémont) — jamais mélangée aux locaux :
sous un bandeau « Ailleurs dans l'espace sabaudo », comme « Ça vaut le déplacement » le
fait déjà.

Un bug trouvé PAR le test avant écriture (vue « les 4 territoires » sans `_motif` — les
fonctions internes testées en isolation via `eval()` d'un fichier déposé en sandbox,
snippet réel non touché tant que le bug n'était pas corrigé) : corrigé, retesté propre.
Débogage réservé aux comptes `edit_posts` : `?cs_a_lire_debug=1` sur une page — liste les
places et LEUR MOTIF (règle 6, jamais deviner pourquoi une section montre ce qu'elle
montre), vérifié absent pour un visiteur anonyme. Vérifié en ligne après écriture sur
Savoie, Comté de Nice, Piémont IT et la home : bandeau présent sur les pages territoire,
absent sur la home (« les 4 » — rien n'est « chez soi », rien à séparer). Pas de filtre par
sujet seul : avec 6 guides au total, croiser sujet + territoire viderait la section — à
revoir si le stock grossit.

Deuxième passe le soir même — Franck : « le à lire a été travaillé sur Savoie mais pas
sur le reste des homepages ! […] il faut que ça soit comme sur Savoie mais adapté aux
territoires sélectionnés ». Sur la vue « les 4 territoires » (`?as_territoire=tous`, home
FR et IT), la première version rendait une liste plate de 5 articles étiquetés — rien de
comparable au bandeau de la page Savoie. Choix de Franck (question posée) : **un bandeau
par territoire**, même dessin que « Ailleurs dans l'espace sabaudo » mais à la couleur du
territoire, les articles groupés dessous dans l'ordre de la rotation du jour, sans
étiquette de territoire sur les cartes (le bandeau la porte). Deux cartes (premier
article des deux premiers groupes) + lignes, comme partout. Testé en isolation via
`eval()` (préfixe `cs_test3_`) en FR et IT, page Savoie recontrôlée inchangée (1 local +
3 ailleurs), puis vérifié en ligne : 4 bandeaux sur `/?as_territoire=tous` et sur
`/it/home-it/?as_territoire=tous`, bandeau « Ailleurs » toujours présent sur
`/explore/savoie/`. Sauvegarde de l'ancien code :
`novamira-sandbox/backups/snippet-134-20260906-201736.txt`.

Troisième passe, sur capture : « on peut pas avoir d'autres choses que ces séparateurs ?
ça fait trop de séparateurs similaires, on en a un au-dessus et en dessous de Comté de
Nice ». Le trait noir de 2 px du bandeau doublait celui du titre « À lire », et revenait
à chaque territoire. Supprimé : chaque territoire est marqué par son nom en couleur
souligné d'un court tiret (28 × 3 px) de la même couleur, un simple espace entre les
groupes. Vérifié en ligne : plus aucun `border-top:2px solid #1D1D1B` dans « À lire » (les
deux restants sur la page sont les tuiles « Ce week-end » / « Tout l'agenda »), quatre
tirets aux quatre couleurs. Sauvegarde :
`novamira-sandbox/backups/snippet-134-20260906-202256.txt`.

**Le cas #26, archives de catégorie (2026-09-06, soir).** Franck : « /category/curiosites/
ne correspond pas au template des pages ». Mesuré : la page était l'archive par défaut de
GeneratePress (`body.archive.category`, colonne latérale, 5 articles) — le seul endroit du
site rendu hors gabarit maison ; aucun snippet ne traitait `is_category()`. Quatre
catégories d'articles existent (curiosites/curiosita 5, guides/guide-it 7, plus deux vides
« non classé »). Le `template_redirect` du #26 prend désormais aussi les archives de
catégorie : même liste, filtrée par `cat`, nom de la catégorie en H1, et un rappel « Nos
articles › » vers 994/3186. Vérifié en ligne : `/category/curiosites/`, `/category/guides/`,
`/it/category/curiosita/` sans colonne latérale, `/le-fil/` (« Nos articles ») inchangé (10
articles, pas de rappel). Sauvegarde :
`novamira-sandbox/backups/snippet-26-20260906-211139.txt`.

**Le cas #148 et le menu footer (2026-09-06) : « Autres villes » dans le footer.** Franck,
capture du footer FR : les colonnes territoire n'affichent que 3-4 villes chacune, sur 17
pages « ville » réellement publiées — en Savoie, 7 (Sallanches, Cluses, Albertville,
Annemasse, Thonon-les-Bains, Moûtiers, Saint-Jean-de-Maurienne) n'apparaissent dans aucun
menu. Vérifié avant d'agir : ces pages sont indexables et déjà dans le sitemap, donc ce
n'est pas un problème d'indexation — mais elles ne sont liées que depuis le hub territoire
(`[cs_villes_du_territoire]`, shortcode déjà existant, jamais depuis le footer, présent lui
sur TOUTE page du site) : gain de maillage interne et de profondeur de clic, pas de
découvrabilité.

Ajout d'un ancrage `id="villes-et-zones"` sur le conteneur que rend ce shortcode (#148),
puis un item « Autres villes » / « Altre città » sous chaque groupe territoire des menus
`footer-territoires` (281) et `footer-territoires-it` (521), pointant vers
`<hub-territoire>#villes-et-zones` — la liste que le shortcode affiche déjà, jamais une
page dupliquée. Vérifié après écriture : ancre présente et liste (« Sallanches » incluse)
sur `/que-faire-en-savoie/`, 8 nouveaux liens détectés sur les deux accueils (la home
rend le footer deux fois, comme le reste du menu — cf. commentaire du snippet #19).

**Le cas #24 (2026-09-06) : proposer une SOURCE, pas seulement un événement.** Demande de
Franck : « il faut aussi pouvoir proposer un flux RSS ou un lien d'inscription à une
newsletter, il faut que je reçoive sur Slack ». Second formulaire sous le premier, sur
les pages 934 (FR) et 3183 (IT) : type (RSS / newsletter / autre), adresse, organisme,
e-mail, consentement, pot de miel, nonce propre. Chaque envoi est rangé dans l'option
`cs_sources_proposees` (tableau : `at, type, url, org, email, lang`) et annoncé par
`cs_slack_notify_form` — donc dans le **récapitulatif quotidien de 11h45**, pas en message
immédiat : c'est la règle de Franck (« un seul message Slack par jour »), la même que pour
les propositions d'événement. Testé de bout en bout par un POST réel (deux envois de test,
retirés ensuite de l'option et de la boîte Slack du jour). Pour lire ce qui attend :
`maybe_unserialize($wpdb->get_var("SELECT option_value FROM wp_options WHERE option_name='cs_sources_proposees'"))`.
Rien n'ajoute encore ces sources à la veille du VPS : c'est un geste humain, après lecture.

**Les cas #15 et #23 (2026-09-06) : le passé s'affichait.** Constat de Franck, capture de
`/evenements/categorie/sport/` en main : 12 cartes, 9 terminées. Mesure en SQL direct
(les requêtes WP ne comptent pas le passé, TEC le filtre — règle 2) : 141 fiches
terminées sur 263 publiées ; la requête du gabarit Sport en rendait 13 dont 10 passées.
Les deux gabarits n'avaient aucun plancher de date — le hub ville (#61) et la liste
partagée (`mu-plugins/cs-agenda-list-shared.php`) en avaient un depuis le début. Ajout
d'un `_EventEndDate >= now` (la date de FIN décide, une exposition en cours reste) sur
la requête de base de #15 et sur les quatre requêtes événements de #23. Contrôle après
écriture : Sport 3 cartes (toutes à venir), recherche « Nice » plus rien avant septembre.
Sauvegardes d'avant sur le serveur : `wp-content/novamira-sandbox/backups/snippet-{15,23,26}-20260906-085950.php`.
Le mirroir `wordpress/design-system/taxonomy-archive-template.php` (86 lignes, 07/2026)
n'est PAS la référence : la version en ligne fait 22 ko.

**Même jour, second passage sur #15 et #23 : l'ordre ne se voyait pas.** Franck, capture
de Concerts & Musique : « j'ai l'impression qu'il n'y a pas d'ordre ». L'ordre était bien
start ASC, mais rendu à plat, sans en-tête de jour, et une fiche commencée en juillet
(« Jusqu'au 16/10 ») ouvrait la liste devant le 06/09. Les deux gabarits passent par le
rendu partagé `cs_render_day_groups` (#21) déjà utilisé par Ce week-end et les hubs ville :
en-têtes par jour, et les déjà-commencés à la fin sous « Ne ratez pas » (décision Franck
2026-08-02). Sur #23, l'ordre vient toujours de `$cs_tri_ponctuels` (03/08) — le rendu ne
fait que le montrer. Relevé après écriture : Concerts « Aujourd'hui / Vendredi 11 septembre
/ … / Ne ratez pas ». Sauvegardes : `snippet-15-20260906-092620.php`, `snippet-23-20260906-092651.php`.
Vu au passage, hors périmètre : #729 et #2231 (MITO, 11/09) sont le même événement, deux
fois en français — un doublon à fusionner côté base.

**Le cas #26 :** « Le fil » renommé « Nos articles » / « I nostri articoli » (H1 du
gabarit et titre des pages 994 / 3186 ; les slugs `/le-fil/` et `/it/il-filo/` sont
inchangés, aucun lien ne casse). L'agencement des articles (saison en cours d'abord)
est une décision éditoriale en attente — voir la note #138 ci-dessous, la question
annoncée comme devant « porter sur la FRAÎCHEUR » est revenue le 2026-09-06.

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
