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
| `statut='merged'` + `duplicate_of` | `dedupe` | **RIEN** | ⛔ **OUVERT** |

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

## Le seul cul-de-sac encore ouvert

### `statut='merged'` + `duplicate_of` — aucun chemin de retour

`dedupe.merge_group` absorbe une fiche dans une autre : la perdante passe `merged`, son
`duplicate_of` pointe la gagnante, et sa matière est agrégée vers elle. **Aucun script du
dépôt ne remet jamais `duplicate_of` à NULL.** Le seul démêlage existant,
`unlink_bad_translations`, ne traite que l'appariement FR/IT, pas la fusion.

Ce n'est pas théorique : `audit_dedupe_damage` a compté **1105 fusions douteuses sur
1835**. Elles ne se réparent pas en re-téléchargeant une page — quand c'est l'APPARIEMENT
qui était faux, une fiche légitime a été absorbée par une autre qui n'a rien à voir.

**Pourquoi ce n'est pas corrigé ici** : défaire une fusion n'est pas un geste mécanique.
Il faut rendre à la fiche absorbée son statut d'avant — qu'aucune colonne ne conserve —,
décider si la gagnante garde la matière héritée, et trancher si les deux fiches doivent
exister séparément. C'est un arbitrage éditorial, pas une réouverture automatique. Le
mettre en cron serait exactement l'erreur inverse de celles corrigées ci-dessus.

**Ce qu'il faudrait, dans l'ordre :**

1. passer `audit_dedupe_damage --published-only` sur la base réelle (lecture seule) ;
2. sur les cas classés « certain », vérifier à la main quelques exemples pour juger de la
   fiabilité du classement ;
3. seulement ensuite, écrire un `unmerge` — en conservant, à la fusion suivante, le statut
   d'origine de la perdante dans une colonne, faute de quoi aucun retour ne sera propre.

Le point 3 est la vraie leçon : **une fusion qui n'enregistre pas ce qu'elle écrase ne
peut pas être défaite.** C'est le même défaut que ceux corrigés aujourd'hui, un cran plus
profond — non pas « personne ne rouvre », mais « il n'y a plus rien à rouvrir ».

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
