# Les fautes du fil SEO, 08 → 10 septembre 2026

Fil distinct de `docs/ERREURS_2026-09-08.md`, qui couvre le même moment sur les images,
les lieux et la home : celui-ci ne traite que le SEO, de la première demande de Franck
(« avec crawlseo et les skills SEO, fais-moi un rapport ») au dépôt des deux mu-plugins.

Trois correctifs de code utiles en sont sortis, un incident public a été trouvé et
retiré, et le vrai diagnostic d'indexation a été établi. Mais **six de mes conclusions
ont été démenties par une mesure**, et dans cinq cas sur six c'est Franck qui a lancé
la commande qui me contredisait. La racine est unique et déjà écrite dans CLAUDE.md :

**J'ai raisonné sur ce que l'outil m'affichait, sans vérifier ce que l'outil mesurait.**

---

## 1. Trois semaines de données périmées prises pour l'état du jour

J'ai construit tout un diagnostic sur « 1 clic, 51 impressions, en baisse de 75 % », et
j'ai écrit à Franck que le site n'avait « aucun clic ». La Search Console dit **182 clics
et 3 350 impressions sur 28 jours**.

CrawlSEO ne synchronise plus depuis le **16 août**. Sa sortie ne le dit pas : elle affiche
« Period Metrics (current vs previous) » sans dater la fenêtre. J'avais pourtant vu la
dernière ligne de `get_traffic` s'arrêter au 16/08 — je l'ai noté en passant, puis j'ai
continué à raisonner comme si c'était l'actuel.

**Le garde-fou** : un chiffre de trafic sans sa DATE DE DERNIÈRE MESURE n'est pas un
chiffre. `get_traffic` donne la dernière journée connue : la lire d'abord, et l'écrire à
côté du nombre. C'est la règle du périmètre affiché (CLAUDE.md, règle 6) appliquée au
temps plutôt qu'au filtre.

## 2. Quinze doublons annoncés, un seul réel

J'ai lu la liste de republication, vu des titres identiques (« ESTATE REALE 2026 » deux
fois, « Milo Manara » deux fois, quatre EVO) et écrit à Franck qu'il fallait trancher une
quinzaine de doublons avant de republier, contenu dupliqué à l'appui.

`verifier_doublons_publies --en-ligne` a rendu : **21 groupes, dont 20 paires FR/IT
légitimes et UN seul vrai cas**. Le script interroge WordPress avant de conclure ; moi
j'avais comparé des chaînes de caractères.

C'est mot pour mot la racine du 17/08 : **conclure sur un indice de surface au lieu
d'aller lire la chose.** Deux fiches d'une paire FR/IT peuvent porter le même titre quand
c'est un nom propre (« Orlando », « Douja d'Or », « Milo Manara ») — le titre ne dit rien.

**Le garde-fou** : il existe déjà, c'est `verifier_doublons_publies`. Le lancer AVANT
d'annoncer un doublon, jamais après.

## 3. Une commande dictée sans lire sa sélection — et elle a créé un doublon

J'ai écrit : « `publish_batch_as --update --skip-media` republie les 165 fiches ».
`_select` (l. 57-82) lève aussi, avec `--update`, le filtre `wp_post_id_as = 0` : la
commande publie donc AUSSI ce qui n'était pas encore en ligne. Une dizaine de fiches ont
été **créées**, dont `WP#8954` « EVO 2026 à Nice », quatrième page du même événement,
**toujours en ligne**.

Franck m'avait demandé « est-ce qu'il faut reprendre l'existant ? ». J'ai répondu sur
l'existant et livré une commande qui touche aussi le neuf.

**Le garde-fou** : avant de dicter une commande de masse, LIRE sa fonction de sélection,
pas sa docstring — et annoncer ce qu'elle crée, pas seulement ce qu'elle met à jour. Le
dry-run l'aurait montré : il annonçait « création seule » puis « MAJ incluse » selon le
mode, et je ne l'ai pas relevé.

## 4. Le garde de cohérence : deux avis opposés en dix minutes, aucun mesuré

Sur l'incident de la fiche 4424 (ci-dessous), j'ai recommandé de brancher
`utils.coherence.incoherence_description` comme portillon de publication. Dix minutes
plus tard, devant la sortie d'`audit_coherence`, j'ai dit l'inverse — « surtout pas, il
refuse des fiches justes » — en citant des faux positifs.

Les deux fois j'avais tort, et pour la même raison : **la fonction a deux modes**, et
l'audit affichait le mode SIGNALEMENT. Sa propre sortie le disait, en clair, sous la
liste. `--bloquant` (les deux signaux réunis, le seul mode qui refuse) rend **une seule
fiche sur 329**, et c'est un faux positif (un spectacle en tournée).

Et le test direct a tranché la vraie question : sur la fiche 4424, `incoherence_description`
rend `None` **dans les deux modes**. Le garde ne voit pas le seul cas dont on ait la
preuve qu'il était faux.

**La conclusion, elle, est acquise** : ne pas brancher ce garde dans `publish_batch_as`.
Il retiendrait une fiche légitime et laisserait passer le cas réel. Le module documente
d'ailleurs lui-même ses faux positifs depuis le 13/08 — y compris le cas bilingue et le
cas « EVO France 2026 ». Je ne l'avais pas lu avant de proposer de m'en servir.

## 5. Deux commandes fausses, dictées sans vérifier leur signature

- `audit_coherence --exemples | grep …` — l'option attend un nombre. Récidive de la
  faute 12 du 08/09, même famille : dicter sans lire le `add_argument`.
- `git fetch && git merge && git push && bash deploy/update.sh` sur le VPS, alors
  qu'`update.sh` fait lui-même le fetch et le reset. Le push a été rejeté (le distant
  avait avancé), la chaîne `&&` s'est arrêtée là, et **le déploiement n'a pas eu lieu** —
  Franck a lancé le dry-run suivant sur l'ancien code sans le savoir, et le résultat
  (« Sélection : 0 ») m'a un instant fait croire à un bug de mon correctif.

**Le garde-fou** : sur ce VPS, `bash deploy/update.sh` SEUL suffit. Ne composer une
chaîne `&&` que si chaque maillon a été vérifié — et se souvenir qu'un maillon en échec
tue tous les suivants en silence.

## 6. « Les points passeront au vert » — promis sans avoir regardé ce que Yoast note

En annonçant le correctif de couverture SEO, j'ai écrit à Franck : « ensuite les points
passeront du rouge/gris au vert dans le back-office ». Le lendemain il a rouvert la liste :
toujours du rouge et du gris.

Ce que le pipeline pose, c'est le **titre SEO, la méta et l'expression clé**. Yoast note en
plus la longueur du texte (300 mots minimum, quand les articles du site font 150 à 250),
la densité de l'expression, les liens et l'`alt` des images. Une expression clé posée fait
passer du **gris** (rien à analyser) au **rouge ou orange** ; le vert demande que le
CONTENU suive.

La preuve que c'est atteignable existe — « Foire de Saint-Ours 2027 » est verte — mais
elle ne vaut pas pour les fiches courtes, et je le savais : le tableau de décision du
09/09 posait la question de la longueur en ligne 4, et Franck avait validé le plancher à
200 mots. J'ai quand même promis le vert.

**Le garde-fou** : ne jamais annoncer la COULEUR d'un indicateur qu'on ne calcule pas
soi-même. Dire ce que le correctif écrit (titre, méta, clé), pas ce qu'un outil tiers en
conclura.

## 7. Deux causes de rouge, dont une que rien ne pourra corriger

En cherchant pourquoi la liste restait rouge, deux causes distinctes sont apparues :

- **le SEO calculé mais pas poussé** (les 28 en retard du run interrompu). La paire
  Saint-Ours le montre : la FR sert « Foire de Saint-Ours Aoste 2027 — Agenda Sabauda »
  (le titre SEO), l'IT sert encore son titre éditorial. Se règle au run suivant ;
- **les fiches créées À LA MAIN dans WordPress** (auteur `franck_agendasabauda`, huit au
  10/09 : « La force des idées », « Cavallerizza Xmas Market », « Prix Reale Mutua »…).
  Elles n'ont **aucune ligne dans `events_raw`** : `seo_batch` lit la base, il ne les
  verra jamais. Aucune commande ne les touchera.

C'est une limite de conception, pas un défaut : le pipeline ne connaît que ce qu'il a
produit. Mais elle n'était écrite nulle part, et elle explique une part du rouge que
Franck voit — sans qu'aucun de mes correctifs ne puisse y changer quoi que ce soit.

## 8. Quarante-cinq minutes sur une fiche, à une heure du matin

Le chantier principal — déposer les deux mu-plugins qui sortent 500 pages vides de
l'index — n'a pas bougé de la soirée. Pendant ce temps j'ai enchaîné dix commandes sur
une seule fiche, et **c'est moi qui relançais à chaque tour**, y compris après avoir
souhaité bonne nuit trois fois.

L'incident méritait d'être traité (un article faux en ligne). Il ne méritait pas la
soirée. Un correctif qui n'est pas déployé ne produit rien, et aucune fiche corrigée ne
compense un levier qu'on n'actionne pas.

---

## Ce qui a été trouvé, et qui valait le détour

### Le vrai diagnostic d'indexation — aucun rapport d'outil ne le voyait

Search Console : **223 pages indexées, 589 hors index**, dont 524 « explorée, actuellement
non indexée ». Les rapports automatiques (CrawlSEO, et celui d'un assistant dans Chrome)
répondaient tous « contenu dupliqué ? trop court ? ressources bloquées ? » — des
hypothèses génériques.

Mesuré sur le sitemap réel :

| | URLs | Ce que c'est |
|---|---|---|
| `/lieu/…` | 307 | ~560 mots chacune, **entièrement menu et pied de page**, zéro événement listé |
| vues « période » des hubs | 137 | `/que-faire-a-turin/ce-week-end/` et variantes |
| `/organisateur/…` | 75 | idem |
| **fiches événement** | **189** | le vrai contenu — **22 % du sitemap** |
| hubs, villes, guides, articles | ~170 | à garder |
| **total déclaré à Google** | **858** | |

498 pages sans contenu propre, 524 refusées : l'écart est mince. Six pages `/lieu/` tirées
au hasard pèsent 556, 557, 562, 562, 562 et 566 mots — le même gabarit à dix mots près.
La page du **Forte di Bard**, qui a plusieurs événements en ligne, n'en affiche aucun.

`deploy/wordpress/cs-index-budget.php` sort ces pages de l'index et du sitemap
(`noindex, follow`, rien n'est retiré du site). Les lieux **se rouvrent seuls** dès qu'un
événement à venir y renvoie : aucun état à rouvrir à la main.

### Le SEO n'avait jamais couvert les traductions — cinq semaines

`seo_batch._select` excluait `translation_of` depuis le 02/08, avec ce commentaire :
« on exclut d'abord, on rédigera en italien ensuite ». « Ensuite » n'est jamais venu :
les 34 fiches italiennes devant nous n'avaient **aucune** expression clé, d'où les points
GRIS de la colonne Yoast. Et le seuil `score ≥ 7` écartait toute fiche EN LIGNE moins bien
notée, que rien ne rouvrait — deux culs-de-sac de la règle 3, fermés le 09/09 et inscrits
dans `docs/ETATS_TERMINAUX.md`.

Résultat mesuré la nuit même : la file « en ligne, devant nous, sans SEO » est passée de
**87 à 1**, dans les deux langues. Le garde de langue posé en même temps a refusé un seul
SEO sur 120 — à raison (une méta italienne sur une fiche française).

### `--skip-media` ne protégeait pas ce qu'il promettait

Franck : « je n'ai édité que les photos ». Vérifié avant de lancer 165 republications : la
VIGNETTE était protégée (cs-publish.php n'entre dans son repli que si la fiche n'a pas
déjà d'image), mais le méta `as_image_original` — le GRAND visuel — repartait avec l'URL
de la base. Ses corrections manuelles auraient survécu à moitié : nouvelle vignette,
ancienne grande image, sur la même fiche.

C'est la seule faute de cette session trouvée AVANT qu'elle ne fasse de dégât, et elle
l'a été parce que la question « qu'est-ce que ça préserve exactement ? » a été posée au
code plutôt qu'à la docstring.

### Une fiche publiée qui racontait un autre événement

`4424` « Mostra Internazionale della Ceramica » (Castellamonte) portait une description
sur la réouverture du **Museo della Radio e della Televisione Rai** à Turin — en ligne,
dans le titre de la page, dans la meta description, dans l'article. Source : une
newsletter **Turismo Torino** multi-annonces, dont le découpage a apparié le titre d'une
annonce avec le corps d'une autre. `duplicate_of` est `None` : ce n'est pas `dedupe`.

Corbeillée le 10/09 à 01h20. Les huit autres fiches de la même source ont été vérifiées
une par une : **toutes correctes**. Cas isolé, pas un découpage cassé.

---

## Ce qui reste ouvert

| Quoi | Où ça se voit | Qui rouvre |
|---|---|---|
| `cs-index-budget.php` et `cs-passe-noindex.php` écrits, testés `php -l`, **jamais déposés sur WordPress** | `deploy/wordpress/` | Franck : `deploy/push-wordpress.sh` ou Novamira. **C'est le levier de tout le fil** |
| `WP#8954` « EVO 2026 à Nice » — doublon créé par ma commande du 10/09 à 00h40 | 4 pages EVO en ligne | à corbeiller (faute 3) |
| fiches `2507` et `3491` liées au MÊME `WP#2190` : elles s'écrasent à chaque republication | sortie de `publish_batch_as` | `audit_wp_ghosts` / `relink_wp_ids_as` |
| refus de langue qui se rejoue sur la fiche `3518` (titre italien, article français) | message Slack de `seo_batch` | personne : passer le titre d'origine au prompt pour qu'il sache que « Sotto i portici » est un nom propre |
| 28 SEO calculés non poussés au 10/09 à 01h15 | ligne « encore en retard » | `seo_batch`, run suivant — mécanisme éprouvé |
| lieux en double : 5 pages pour le Forte di Bard, 2 pour le Castello di Rivoli | `tribe_venue-sitemap.xml` | personne : fusion à la main |
| pages `/lieu/` sans aucun contenu propre | le site | chantier validé par Franck : enrichir les 30-50 lieux qui comptent (événements à venir, adresse, description), dans sa doctrine et vert dans Yoast |
| CrawlSEO ne synchronise plus depuis le 16/08 | `get_traffic` | à signaler à l'outil, ou ne plus s'y fier pour le trafic (faute 1) |
| détecteur de cohérence aveugle au cas 4424 | `utils/coherence` | non résolu — et NE PAS le brancher en portillon en l'état (faute 4) |
| lisibilité : consigne resserrée dans les deux prompts le 09/09, effet non mesuré | `scripts.audit_lisibilite`, dans `weekly_audits` | **à relire vers le 23/09** : la médiane de 57 % de phrases longues a-t-elle bougé ? Un prompt modifié est une hypothèse |
| 8 fiches créées à la main dans WordPress, hors de `events_raw` : le pipeline SEO ne les atteindra jamais | filtre « Les miens » de la liste des événements | Franck : expression clé à la main dans Yoast, ou décider qu'on ne s'en occupe pas (faute 7) |
| le vert Yoast demande aussi 300 mots, de la densité, des liens et un `alt` — le pipeline ne pose que titre, méta et clé | colonne SEO du back-office | le plancher à 200 mots (validé le 09/09) n'agit que sur les articles écrits APRÈS ; les fiches en ligne gardent leur longueur (faute 6) |

## La règle à retenir, si on n'en retient qu'une

**Un outil affiche un extrait ; la question est toujours ce qu'il a mesuré.** Les cinq
démentis de ce fil viennent tous de là : une fenêtre de trafic sans date, une liste
plafonnée à 50 qui en cachait 118, un audit en mode signalement pris pour un mode refus,
une sélection SQL lue dans sa docstring, des titres comparés à la place des pages.

À chaque fois, la commande qui tranchait tenait en une ligne et existait déjà.
