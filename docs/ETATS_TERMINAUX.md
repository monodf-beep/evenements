# Les états terminaux — recensement, et qui sait les rouvrir

**Balayage systématique du 2026-08-03.** Méthode : inventaire de toutes les valeurs
écrites dans les champs d'état (`grep` sur les `UPDATE`), puis recherche, pour chacune,
d'un chemin qui la remette en jeu. Un champ qu'aucun script ne remet jamais à zéro est un
**cul-de-sac** : la fiche y entre et n'en sort plus, quoi qu'il arrive ensuite.

## Pourquoi ce document

Le 2026-08-03 a été passé à réparer à la main des fiches bloquées. Cinq causes distinctes
ont été trouvées **par accident**, en cherchant autre chose :

- une fiche rejetée éditorialement restait en ligne, et rien ne savait la re-classer ;
- une fiche corbeillée gardait un lien mort que rien ne nettoyait ;
- un archivage « passé » posé sur une date FAUSSE n'était jamais rouvert quand la date
  était corrigée ;
- 823 fiches dormaient dans `venue_source='llm_none'` depuis des semaines ;
- et le portillon écrit ce jour-là a créé, en une heure, un sixième cul-de-sac.

Le motif n'est jamais de la négligence. Chaque état terminal a une bonne raison d'exister
— on ne veut pas re-payer indéfiniment un échec, ni re-poser une question tranchée. **Ce
qui manque à chaque fois, c'est la question suivante : qui rouvrira ?**

D'où ce balayage, fait exprès plutôt qu'au hasard.

## Le recensement

| État | Posé par | Rouvert par | Verdict |
|---|---|---|---|
| `enrich_status='api_error'` | `enrich` | `enrich`, dès le run suivant | ✅ fermé le 2026-08-03 |
| `enrich_status='error'` | `enrich` | `enrich`, après `ENRICH_RETRY_DAYS` | ✅ fermé le 2026-08-03 |
| `enrich_status='matiere_polluee'` | `enrich` | `repair_polluted_descriptions` | ✅ fermé le 2026-08-03 |
| `venue_source` ∈ `llm_none`/`novenue` | `venues` | `venues`, après `VENUE_COOLDOWN_DAYS` | ✅ fermé le 2026-08-03 |
| `date_source` ∈ `nodate`/`llm_none` | `dates` | `dates`, après `DATE_COOLDOWN_DAYS` | ✅ fermé le 2026-08-03 |
| `url_officiel` (verrou) | `enrich` | `enrich`, test de pertinence à la lecture | ✅ fermé le 2026-08-03 |
| `wp_deleted_at` | `reconcile_wp_deleted` | `reconcile_wp_deleted` (déshorodate) | ✅ déjà fermé |
| `translation_of` | `translate_events` | `unlink_bad_translations` | ✅ déjà fermé |
| `statut='rejected'` | `evaluator`, `purge_*`, back-office | `unreject_wp_online`, `reconcile_catalogue`, back-office | 🟡 partiel, **volontaire** |
| `wp_post_id_as=NULL` après corbeille | `trash_by_ids`, `trash_wp_ids` | `relink_wp_ids_as` (par titre) | 🟡 partiel, **assumé** |
| `statut='merged'` + `duplicate_of` | `dedupe` | `unmerge` (à la main, jamais en cron) | ✅ fermé le 2026-08-03 |
| `home_override='excluded'` | back-office | back-office + republication, **rappelé par `weekly_digest`** | ✅ fermé le 2026-08-04, **corrigé le soir même** |

### `home_override='excluded'` — réversible, mais invisible

Ajouté au recensement le 2026-08-04, après en avoir posé un soi-même. Cet état écarte une
fiche de la vitrine et se lève d'un bouton : la première question de la règle (« qui le
rouvre ? ») avait donc une réponse. Mais **la troisième n'en avait aucune** — rien ne
disait combien de fiches y dormaient, ni depuis quand.

Le cas : `[2153]` « Une semaine pas plus » a été exclue parce que sa description était
celle d'un autre événement (la Fête du lac d'Annecy, héritée d'une fusion) et qu'aucune
source ne permettait de récupérer la vraie — domaine source en 403 sur tout le domaine,
dix sauvegardes déjà polluées, aucune fiche sœur. Décision juste.

Mais **le motif peut cesser** : `autocomplete` peut la re-remplir un jour depuis une autre
source, et personne ne se souviendrait alors de lever l'exclusion. La fiche resterait
invisible pour une raison disparue — la forme la plus discrète du cul-de-sac, puisque rien
n'est cassé.

`weekly_digest` liste désormais ces fiches, **nommées et datées**, en écartant celles dont
l'événement est passé (règle 5). Nommées et datées et non seulement comptées : « 3 fiches
exclues » se lit et s'oublie, « exclue depuis le 4 août » se rouvre.

**⚠️ Et cette ligne a été cochée « fermée » à tort, le jour même.** Le recensement du soir
l'a montré : `set_home_override` n'écrivait qu'en BASE. La méta `as_home_override` n'est
posée que par `publish_to_as`, donc à la publication — sur une fiche déjà en ligne, seul
cas où l'on songe à cliquer « exclure », le bouton confirmait et **la home ne bougeait
pas**. C'est mot pour mot le défaut d'`as_deplacement_now` réparé la veille : une valeur
calculée en base, publiée une seule fois, jamais remise à jour. Deux jours de suite, deux
endroits différents. Le clic republie désormais la fiche (texte seul), et dit franchement
si la republication a échoué.

**La leçon dépasse le cas.** Les trois questions de ce document — qui rouvre, à quelle
condition, où se voit le compte — ne suffisent pas : elles supposent que le rouvreur est
ATTEIGNABLE. Il en faut une quatrième.

## Les trois délais, et pourquoi ils sont identiques

`WEB_COOLDOWN_DAYS`, `VENUE_COOLDOWN_DAYS`, `DATE_COOLDOWN_DAYS`, `ENRICH_RETRY_DAYS` :
même valeur par défaut (7 jours), et les trois derniers lisent `WEB_COOLDOWN_DAYS` en
repli. Quatre délais réglables séparément pour la même idée — « re-tenter un échec quand
la matière a eu le temps de changer » — seraient un piège de réglage : on en changerait un
en croyant les changer tous.

Un délai, et pas un ré-armement à chaque run : re-tenter tous les jours des centaines de
fiches re-paierait tous les jours les mêmes échecs. Une page sans date hier n'en a pas
davantage aujourd'hui ; elle peut en avoir dans une semaine.

**`NULL` compte comme « ancien ».** Chaque colonne d'horodatage est arrivée après les
fiches qu'elle doit débloquer : si l'absence de date valait « jamais essayé, donc
récent », le correctif oublierait exactement les fiches pour lesquelles il est écrit.

## Les deux cas volontaires

**`statut='rejected'`** — un rejet éditorial est une décision, pas un échec technique. Le
rouvrir automatiquement effacerait un jugement humain. Trois chemins de réouverture
existent, chacun pour un cas nommé : `unreject_wp_online` (le post est resté en ligne),
`reconcile_catalogue` (l'archivage « passé » portait sur une date devenue à venir), et le
bouton du back-office. Tout le reste demande un humain, **et c'est le but**.

**`wp_post_id_as` effacé après mise à la corbeille** — asymétrie assumée entre deux
scripts. `reconcile_wp_deleted` GARDE le lien (un post corbeillé se restaure en un clic,
couper le lien détruirait de l'information), tandis que `trash_by_ids`/`trash_wp_ids` le
coupent (on retire volontairement, on ne compte pas revenir). `relink_wp_ids_as` sait
recoller par titre, avec le garde-fou anti-collision du 2026-08-03. Divergence connue, à
unifier si elle gêne un jour.

## Le dernier fermé, et le plus long à l'être

### `statut='merged'` + `duplicate_of`

`dedupe.merge_group` absorbe une fiche dans une autre : la perdante passe `merged`, son
`duplicate_of` pointe la gagnante, et sa matière est agrégée vers elle. Jusqu'au
2026-08-03, **aucun script du dépôt ne remettait jamais `duplicate_of` à NULL** — le seul
démêlage existant, `unlink_bad_translations`, ne traite que l'appariement FR/IT.
`scripts/unmerge.py` comble ce manque, avec la réserve importante décrite plus bas : il
RESTAURE les fusions récentes et se contente de RECONSTITUER les anciennes.

Ce n'est pas théorique, mais c'est plus petit qu'annoncé. **Chiffre corrigé le
2026-08-03** : `audit_dedupe_damage --published-only` compte **94 fusions suspectes sur
1857**, dont **zéro « certain »**, 13 « probable » et 81 « à vérifier ». Le « 1105 sur
1835 » cité toute la journée provenait d'un passage sans `--published-only` — il comptait
des fiches jamais publiées, donc sans conséquence pour le visiteur.

**Un tiers des 94 tient à UNE fiche.** `[1789]` « Torino crocevia di sonorità | Incanto »
a absorbé une trentaine de perdantes sans rapport : Vermeer, Hokusai, le Torino Jazz
Festival, la Festa di San Giovanni, un article sur un restaurant, un communiqué sur le
PNRR. Défusionner celle-là seule règle l'essentiel du problème.

**Et `[2153]` « Une semaine pas plus » ← `[2762]` « Fête du lac 2026 » est toujours en
base** : c'est la fusion à l'origine de WP#6798, celle qui a mis la traduction en pause.
C'est aussi, à elle seule, la condition C5 de `docs/GO_NOGO_TRADUCTION.md`.

Ces cas ne se réparent pas en re-téléchargeant une page — quand c'est l'APPARIEMENT qui
était faux, une fiche légitime a été absorbée par une autre qui n'a rien à voir.

**Pourquoi ce n'est pas corrigé ici** : défaire une fusion n'est pas un geste mécanique.
Il faut rendre à la fiche absorbée son statut d'avant — qu'aucune colonne ne conserve —,
décider si la gagnante garde la matière héritée, et trancher si les deux fiches doivent
exister séparément. C'est un arbitrage éditorial, pas une réouverture automatique. Le
mettre en cron serait exactement l'erreur inverse de celles corrigées ci-dessus.

**La marche à suivre :**

1. `audit_dedupe_damage --published-only` sur la base réelle — il écarte désormais les
   événements passés, donc il ne liste que ce qui compte encore ;
2. sur les cas retenus, en vérifier quelques-uns à la main pour juger de la fiabilité du
   classement avant de faire confiance au reste ;
3. `scripts/unmerge.py <ids des perdantes>` en dry-run, puis `--apply`.

**Ce que `unmerge` fait, et ce qu'il refuse de faire.** Il ne décide JAMAIS quelles
fusions défaire : départager deux fiches homonymes demande de regarder les dates, le lieu
et le contenu. `audit_dedupe_damage` liste, un humain choisit, `unmerge` exécute. Le
mettre en cron serait l'erreur inverse de toutes celles corrigées ce jour-là.

Il refuse aussi une fusion dont la perdante est **encore en ligne** : la défusionner
laisserait deux fiches revendiquer la même page — on ne répare pas un désordre en en
créant un autre.

**Et il distingue deux cas qui ne se valent pas**, en le disant fiche par fiche :

- **fusion récente** — l'instantané existe, on RESTAURE le statut d'avant à l'identique ;
- **fusion antérieure au 2026-08-03** — rien n'a été enregistré, le statut d'avant
  n'existe nulle part. On ne peut que RECONSTITUER : couper le lien et rendre la fiche à
  la file d'évaluation. Elle sera re-jugée, ce qui coûte un appel LLM et peut donner un
  verdict différent de celui qu'un humain avait validé à l'époque.

C'est là que se paie, concrètement, le fait de n'avoir rien enregistré pendant des mois.

Le point 3 est la vraie leçon : **une fusion qui n'enregistre pas ce qu'elle écrase ne
peut pas être défaite.** C'est le même défaut que ceux corrigés aujourd'hui, un cran plus
profond — non pas « personne ne rouvre », mais « il n'y a plus rien à rouvrir ».

### ✅ L'hémorragie est arrêtée (2026-08-03), le passif reste

`dedupe.merge_group` enregistre désormais, dans une colonne `unmerge_data`, ce que chaque
fusion écrase :

- **côté perdant** : son `statut` d'avant. C'est la seule chose qu'aucune autre source ne
  peut rendre — `pending`, `evaluated` ou `published_sub` ne se devinent pas après coup, et
  sans lui défusionner obligerait à re-évaluer la fiche, donc à re-payer un appel LLM et à
  risquer un verdict différent de celui qu'un humain avait déjà validé ;
- **côté gagnant** : les champs remplacés, et en pratique surtout `description` — le seul
  cas où une valeur existante est écrasée. C'est celui qui a détruit des descriptions
  légitimes (« Charlie Winston ■ 7 juillet » a écrasé « Charlie Winston ») et qui a obligé
  à écrire `repair_polluted_descriptions.py` pour re-télécharger ce qu'on avait soi-même
  effacé. Le noter coûte une ligne ; le reconstituer a coûté un script entier.

`unmerge_data` est une **liste**, pas un objet : une fiche peut absorber plusieurs groupes
au fil des semaines, et écraser l'instantané précédent reproduirait exactement le défaut
qu'on répare. Vérifié sur fixture — après deux fusions successives, on remonte jusqu'à la
description **d'origine**, pas seulement à l'avant-dernière.

**Ce que ça ne fait pas** : rien de rétroactif. Les 94 fusions suspectes déjà en base
n'ont pas d'instantané et resteront à trancher à la main. Le correctif ne répare pas le
passé, il garantit que le passif ne grossit plus.

## Le diagnostic sans issue — vu, décrit, et irréparable

Troisième forme du même motif, trouvée le 2026-08-03 : ni un état qu'on ne rouvre pas, ni
une valeur qu'on ne recalcule pas, mais **un problème que l'outil censé le réparer ne peut
pas voir**.

`audit_wp_ghosts` signalait depuis toujours qu'un post WordPress était revendiqué par
plusieurs lignes locales, en renvoyant vers `relink_wp_ids_as`. Or ce script **valide
chaque ligne par le titre du post qu'elle vise** : il regarde `ligne → post`, jamais
`post → lignes`. Les deux prétendantes portant le même titre que le post, chacune est
« déjà bonne » prise isolément. Un doublon de lien lui est invisible **par construction** —
vérifié sur WP#6365, dont son dry-run ne mentionne ni le post ni aucune des deux fiches.

Le renvoi était donc une impasse polie : le rapport indiquait quoi faire, et l'outil
indiqué ne faisait rien. On relisait la ligne chaque semaine sans jamais pouvoir la
refermer.

**Le dommage est mesurable.** Sur WP#6365 « Percorso in Rosso 2026 », les deux fiches ont
été poussées vers le même post à trois secondes d'intervalle. La dernière a gagné, et
c'était la MOINS complète : la page porte son score de 4 et n'a pas d'`article_title`,
tandis que la fiche mieux notée et pourvue de son article a été écrasée. **La dernière
arrivée gagne, pas la meilleure.** Sept autres conflits identiques attendaient le même
arbitrage.

`scripts/resolve_wp_collision.py` construit l'**index inverse** qui manquait (post →
lignes), garde la plus complète sur des critères observables, détache les autres, et
enregistre leur statut d'avant dans `unmerge_data` — poser un `merged` sans instantané
recréerait, en une ligne d'inattention, le cul-de-sac fermé le matin même. Il refuse deux
cas : dates incompatibles (deux événements différents sur une même page, pas deux copies)
et complétude strictement égale (trancher à pile ou face une fiche publiée serait pire
que ne rien faire). `--forcer` sert quand un humain a regardé.

**La leçon** : quand un rapport renvoie vers un outil, vérifier que l'outil voit le cas.
Un renvoi qui n'aboutit pas coûte plus cher qu'une absence de renvoi — il donne
l'impression que la question est traitée.

## La même question, posée aux VALEURS

Le 2026-08-03, le motif est réapparu sous une forme qui n'entrait dans aucune ligne du
tableau : non pas « un état que personne ne rouvre », mais **une valeur que personne ne
recalcule**.

`as_deplacement_now` trie la section « Ça vaut le déplacement ». Il relève le score
intrinsèque (0-8) par le **temps qui reste pour y aller** — il dépend donc du calendrier,
pas de la fiche. Or `publisher_as` le calcule au moment de la publication et WordPress le
GÈLE. Une fiche publiée avec le bonus « dans 4 jours » garde 11 en octobre ; un événement
terminé, que `deplacement_now` sort du classement (règle 5), continue d'y trôner. Le
classement dérive dans les deux sens, sans que rien ne le signale — la section affiche
toujours quelque chose, seulement ce quelque chose vieillit.

Le défaut a été introduit le jour même de la mise en service du tri. Il n'a pas été trouvé
en cherchant un bug, mais en se posant la question de la règle 3 sur autre chose qu'un
statut.

`scripts/refresh_deplacement.py` (cron 10h50) recalcule et republie **les seules fiches
dont la valeur a changé** — la colonne `deplacement_now_publie` retient ce qui a réellement
été envoyé. Il vérifie chaque post par son numéro avant de le pousser : sur les 123 fiches
republiées à la main ce jour-là, **16 étaient à la corbeille** alors que la base les croyait
publiées (règle 1). Et il est inscrit dans `watchdog_crons` — sinon son arrêt serait
invisible, ce qui est exactement le défaut qu'il corrige.

**Le même script répare aussi un oubli de copie.** Le score dérive de `llm_score_detail`,
que l'évaluateur écrit sur la fiche d'origine et jamais sur sa traduction — et
`translate_events` ne copiait pas cette colonne. Les 14 fiches Savoie + Comté de Nice
traduites en italien avaient donc un score VIDE, et la section italienne retombait sur
`as_score`, c'est-à-dire le tri qu'on venait précisément de quitter. La copie est faite à
la création depuis le 2026-08-03 ; la propagation quotidienne rattrape les traductions
déjà en base et reste en place comme filet — une réponse à « qui rouvre ? » plutôt qu'une
commande que personne ne lancera. C'est le même oubli, dans la même requête, que celui qui
avait laissé `date_source` à NULL et fait re-dater les traductions italiennes avec un
parseur français.

**À retenir pour la suite** : une valeur qui dépend de la date d'aujourd'hui et qu'on écrit
ailleurs qu'en base doit avoir, dès sa première ligne, quelqu'un qui la recalcule.

## Le cas qui n'EST PAS un état terminal — et pourquoi il fallait le dire

Ajouté le 2026-08-05, en construisant le **portillon éditorial** de `publish_batch_as`
(règle d'exclusion `config/excluded_event_keywords.txt`, puis arrondissement de Grasse).
Une fiche retenue à ce portillon n'est **pas garée** : rien n'est écrit, son `statut` ne
bouge pas, elle se represente au lot suivant. Il n'y a donc pas d'état à rouvrir — et
c'est délibéré : la rétention ne fait que retarder, la SORTIE de file reste un geste
explicite (`audit_excluded_events --apply`, `purge_out_of_zone --apply`), tous deux
branchés dans `weekly_audits`.

La tentation était l'inverse : poser `statut='rejected'` au moment de la rétention, pour
« ne pas y revenir ». C'eût été un septième cul-de-sac, posé par un script de
publication qui n'a aucun titre à trancher l'éditorial — et sur la foi d'une règle
déterministe qui, le jour même, avait déjà produit un faux positif (le Salone Auto
Torino, salon grand public attrapé par « btob » dans sa description).

**La leçon générale : quand un garde-fou doit empêcher quelque chose, retenir sans
écrire coûte un log répété, tandis qu'écrire coûte un état à rouvrir.** Le premier prix
est presque toujours le bon, à une condition — que le message nomme la commande de
sortie, ce que font les deux messages du portillon.

## La règle à suivre

Avant d'ajouter un état qui écarte une fiche d'une file, répondre par écrit à :

1. **Qui le rouvre ?** Si la réponse est « un humain qui tape une commande », ce n'est pas
   une réponse — personne ne tape une commande dont il ignore l'existence. Les 823 fiches
   de `venues.py` avaient leur `--retry` depuis le premier jour.
2. **À quelle condition ?** Un délai (la matière peut changer) ou un événement (la cause a
   disparu). Le second est meilleur quand il existe : `repair_polluted_descriptions`
   rouvre `matiere_polluee` au moment précis où il supprime la pollution.
3. **Où se voit le nombre de fiches garées ?** Un état qui sort une fiche de sa file la
   sort aussi de tous les bilans. S'il n'est compté nulle part, on le découvre des
   semaines plus tard en cherchant autre chose.
4. **Le rouvreur est-il BRANCHÉ, et qu'est-ce qui prouve qu'il tourne ?** Question ajoutée
   le 2026-08-04, après un balayage qui a trouvé six trous dont **cinq ont la même
   origine** : on avait vérifié qu'un chemin de retour EXISTE, jamais qu'il est
   ATTEIGNABLE. Un rouvreur absent du `crontab.txt` et de `weekly_audits` ne rouvre rien —
   c'est le cas de `repair_polluted_descriptions`, parfaitement écrit et lancé par
   personne. Un rouvreur dont la docstring promet qu'un autre script reprendra la fiche
   sans que ce script la sélectionne (`unlink_bad_translations` → `translate_events`, qui
   filtre sur `translated_at=''`) est un renvoi mort, exactement comme celui
   d'`audit_wp_ghosts` vers `relink_wp_ids_as`. Et un état posé en base qui n'atteint pas
   le site (`home_override`) ne rouvre rien de ce que voit le visiteur.
