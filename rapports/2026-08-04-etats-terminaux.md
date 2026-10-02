# Balayage des états terminaux — 2026-08-04

Refait de zéro, sans reprendre le recensement du 2026-08-03. Méthode identique à celle qui
l'a produit : inventaire MÉCANIQUE des `UPDATE … SET` de `scripts/*.py`, `app/*.py` et
`utils/*.py`, extraction des valeurs LITTÉRALES écrites dans chaque champ d'état, puis
recherche, pour chacune, d'un chemin qui la remette en jeu.

**Ce que je n'ai pas pu faire :** aucun accès au VPS, à `data/events.db` ni au site. Tous
les comptages de fiches réelles sont **invérifiables d'ici** et signalés comme tels. Les
vérifications exécutées l'ont été sur base jetable (`scripts.scraper_events.init_db`).

---

## 1. L'inventaire mécanique

154 `UPDATE … SET` trouvés. Les valeurs littérales écrites dans un champ d'état :

| Champ | Valeurs littérales écrites | Écrites par |
|---|---|---|
| `statut` | `pending`, `evaluated`, `merged`, `rejected`, `published_cs`, `published_sub` | evaluator, dedupe, enrich, purge_*, discard_uncompletable, cleanup_cinema, audit_non_events, audit_excluded_events, trash_by_ids, trash_wp_ids, **retirer_source**, **resolve_wp_collision**, reconcile_catalogue, unreject_wp_online, unmerge, scraper_events, app/app.py |
| `enrich_status` | `''`, `enriched`, `api_error`, `error`, `matiere_polluee` | enrich, repair_polluted_descriptions, translate_events, recover_clobbered_translations |
| `venue_source` | `''`, `none`, `source`, `page`, `llm`, `llm_none`, `novenue`, `web` | venues, venues_web |
| `date_source` | `''`, `none`, `parsed`, `page`, `llm`, `nodate`, `llm_none`, `web`, `copie-traduction` | dates, dates_web, gmail_relink, repair_translation_dates, translate_events |
| `duplicate_of` | `<id gagnante>`, `NULL` | dedupe, **resolve_wp_collision** / unmerge |
| `translation_of` | `<id original>`, `NULL` | translate_events, link_translations_as, recover_clobbered_translations / unlink_bad_translations, repair_translation_cycles |
| `translated_at` | `datetime('now')`, `NULL` | translate_events / repair_translation |
| `wp_deleted_at` | `<horodatage>`, `NULL` | reconcile_wp_deleted / reconcile_wp_deleted, publish_batch_as, unreject_wp_online |
| `home_override` | `''`, `featured`, `excluded` | app/app.py (`/set-home-override`) — **et personne d'autre** |
| `home_order` | `<rang>` | app/app.py (`/set-home-order`) |
| `wp_post_id_as` | `<id>`, `NULL` | publish_batch_as, autocomplete, app.py / cleanup_as_*, trash_*, reconcile_wp_deleted, resolve_wp_collision, relink_wp_ids_as |
| `deplacement_now_publie` | `<score>` ou `''` | **refresh_deplacement** — et personne d'autre |
| `url_officiel` | `<url>`, `NULL` | enrich / enrich |
| `autocomplete_state` | `ready`, `missing:<…>` | autocomplete / autocomplete |
| `llm_score` | `0` (posé avec tout rejet) | evaluator, purge_out_of_zone / unreject_wp_online `--score` seulement |
| `checks.status` | `pending`, `resolved` | audit_*, unlink_bad_translations |
| `ig_scheduled_posts.status` | `pending`, `done`, `error` | ig_scheduler |

`autocomplete_state` n'écarte d'aucune file (mémo anti-spam Slack) — écarté de la suite.
`checks` et `ig_scheduled_posts` ont chacun leur passe de résolution — écartés aussi.

---

## 2. Le tableau

| État | Posé par | Rouvert par | Verdict |
|---|---|---|---|
| `enrich_status='api_error'` | enrich | enrich, dès le run suivant (`enrich.py:1241`) | ✅ fermé — **revérifié** |
| `enrich_status='error'` | enrich | enrich, après `ENRICH_RETRY_DAYS` (`enrich.py:1242`) | ✅ fermé — **revérifié** |
| `enrich_status='matiere_polluee'` | enrich | `repair_polluted_descriptions`, **jamais en cron** | 🔴 **OUVERT (n° 3)** |
| `venue_source ∈ llm_none/novenue` | venues | venues, ré-armement AUTOMATIQUE `VENUE_COOLDOWN_DAYS` (`venues.py:255-268`) | ✅ fermé — **revérifié** |
| `date_source ∈ nodate/llm_none` | dates | dates, ré-armement AUTOMATIQUE `DATE_COOLDOWN_DAYS` (`dates.py:449-463`) | ✅ fermé — **revérifié** |
| `url_officiel` (verrou) | enrich | enrich, sur lecture réussie non pertinente (`enrich.py:941-949`) | ✅ fermé — **revérifié** |
| `wp_deleted_at` | reconcile_wp_deleted | reconcile_wp_deleted (déshorodate), publish_batch_as, unreject_wp_online | ✅ fermé — **revérifié** |
| `translation_of` | translate_events, link_translations_as | unlink_bad_translations, repair_translation_cycles | ✅ fermé |
| `translated_at` | translate_events | `repair_translation` **uniquement pour un cas très étroit** | 🟡 **partiel non déclaré (n° 5)** |
| `statut='rejected'` (évaluateur, purges, back-office) | evaluator, purge_*, app.py | unreject_wp_online, reconcile_catalogue, back-office | 🟡 partiel, volontaire |
| `statut='rejected'` (**retirer_source**, 2026-08-04) | retirer_source | **aucun des trois** — motif non inscrit | 🔴 **OUVERT (n° 4)** |
| `wp_post_id_as=NULL` après corbeille | trash_by_ids, trash_wp_ids | relink_wp_ids_as (par titre) | 🟡 partiel, assumé |
| `statut='merged'` + `duplicate_of` (dedupe) | dedupe | unmerge (instantané `unmerge_data`) | ✅ fermé |
| `statut='merged'` + `duplicate_of` (**resolve_wp_collision**) | resolve_wp_collision | unmerge — instantané bien empilé (`resolve_wp_collision.py:170-180`) | ✅ fermé — **le nouveau script n'a PAS recréé le cul-de-sac** |
| `deplacement_now_publie` | refresh_deplacement | refresh_deplacement, quotidien | ✅ fermé — nouveau et propre |
| `home_override='excluded'` / `'featured'`, `home_order` | back-office | back-office + `weekly_digest` **en base seulement** | 🔴 **OUVERT (n° 1)** |
| File de traduction bloquée par un refus permanent | translate_events (portillon `utils.coherence`) + dédup affiche | rien | 🔴 **OUVERT (n° 2)** |
| Post à la corbeille pendant que la base le croit publié | (WordPress / geste humain) | `reconcile_hors_ligne` — **non commité, non branché** | 🔴 **OUVERT (n° 6)** |

---

## 3. Les états OUVERTS, les trois questions

### n° 1 — `home_override` n'atteint JAMAIS le site

**C'est le plus sérieux, et le document le déclare fermé la veille de ce rapport.**

`app/app.py:set_home_override` (ligne 3985) écrit `home_override` **en base uniquement**.
Même chose pour `set_home_order` (ligne 4025). Or la valeur ne parvient à WordPress
(`as_home_override`, `as_home_order`) que par `publisher_as.publish_to_as`, lignes 245-247
— appelée à la **publication**. Aucune des deux routes ne l'appelle. Vérifié par grep
exhaustif : `as_home_override` n'apparaît que dans `publisher_as.py`.

Conséquence : sur une fiche **déjà publiée**, cliquer « 🚫 exclure » ne change rien pour le
visiteur. La méta reste à sa valeur du jour de la publication.

Les republieurs existants ne comblent pas le trou :
- `seo_batch` (10/jour, score ≥ 7) republie une partie du haut du panier — au hasard du
  passage, jamais parce qu'un override a changé ;
- `refresh_deplacement` ne republie **que** les fiches dont `as_deplacement_now` a changé.
  Une fiche hors de la section garde `''` d'un jour sur l'autre : elle n'est jamais
  republiée, donc son exclusion n'est jamais poussée.

1. **Qui le rouvre ?** La question ne se pose même pas encore : l'état n'est pas *posé* là
   où il agit. Et il n'y a personne non plus pour le pousser — c'est très exactement le
   défaut `as_deplacement_now` du 2026-08-03 (« une valeur que personne ne recalcule »),
   reproduit le lendemain sur un autre champ, y compris la leçon écrite en fin de section
   du document : « une valeur qu'on écrit ailleurs qu'en base doit avoir, dès sa première
   ligne, quelqu'un qui la propage ».
2. **À quelle condition ?** Un événement existe et il est parfait : le clic lui-même. Il
   suffirait que `set_home_override` appelle `publish_to_as` quand `wp_post_id_as > 0`
   (le back-office le fait déjà ailleurs, lignes 1341, 3670, 3815, 3925).
3. **Où se voit le nombre ?** `weekly_digest._garees` compte les fiches **en base**,
   nommées et datées — c'est la moitié qui a été faite le 2026-08-04. Rien ne compare la
   base à la méta WordPress. `site_audit` relit le JSON-LD public (dates, titre, lieu,
   image de partage) et **pas les métas** : l'écart lui est invisible par construction.

**Combien de fiches sont concernées : invérifiable d'ici.** En particulier, je ne peux pas
dire si `[2153]` « Une semaine pas plus », le cas fondateur de la ligne du document, est
réellement sortie de la vitrine ou seulement en base.

### n° 2 — un refus permanent de traduction occupe un créneau de `--cap` à vie

`translate_events` sélectionne `ORDER BY score DESC, id ASC`, coupe à `--cap` (5 depuis le
2026-08-04), puis applique le portillon `utils.coherence` **à l'intérieur du lot**. Une
fiche refusée ne reçoit aucune marque : `translated_at` reste vide, elle est re-sélectionnée
le lendemain, au même rang.

Le portillon dit de lui-même « Ce refus n'est PAS un état terminal : la fiche se represente
au run suivant ». C'est vrai de la FICHE. C'est faux de la FILE.

**Vérifié sur base jetable** (`init_db`, 3 fiches à description polluée score 10 + 4 fiches
saines score 7, cap 3, ordre réel du script) :

```
jour 1 : lot=[101, 102, 103]  refus=[101, 102, 103]  traduisibles=[]
jour 2 : lot=[101, 102, 103]  refus=[101, 102, 103]  traduisibles=[]
jour 3 : lot=[101, 102, 103]  refus=[101, 102, 103]  traduisibles=[]
restantes jamais traduites : [101, 102, 103, 201, 202, 203, 204]
```

Le scénario n'est pas théorique : c'est celui de WP#6798. **La pollution FAIT MONTER le
score** — l'évaluateur avait noté `[2153]` 10/10 sur le texte de la Fête du lac. Les fiches
que le portillon refuse sont donc mécaniquement celles qui trônent en tête du tri, c'est-à-
dire celles qui occupent les créneaux.

Le retour `skip` (dédup affiche, même image déjà présente dans la langue cible) a exactement
la même propriété : rien n'est écrit, la fiche revient tous les jours.

1. **Qui le rouvre ?** Personne — et ici « rouvrir » veut dire *débloquer la file*, pas la
   fiche.
2. **À quelle condition ?** Il n'y a rien à attendre : le correctif est de forme. Soit
   exclure les refus du plafond (les compter hors `--cap`), soit les renvoyer en fin de tri.
3. **Où se voit le nombre ?** Le message Slack quotidien nomme jusqu'à 5 refus — bien. Mais
   rien ne dit que ce sont **les mêmes depuis N jours**, et le compteur « à traduire » du
   digest hebdomadaire (`status_report._backlog_counts`, même prédicat que la sélection)
   stagnerait sans que sa stagnation soit signalée. Le motif du document (« un état qui sort
   une fiche d'une file la sort aussi de tous les bilans ») a ici sa variante : *un état qui
   BLOQUE une file ne se distingue pas d'une file vide*.

### n° 3 — `matiere_polluee` : le rouvreur existe, mais personne ne le lance

Le document le donne fermé, au motif que `repair_polluted_descriptions` le rouvre au moment
précis où il supprime la pollution. Le mécanisme est bon (`repair_polluted_descriptions.py:458`,
`CASE WHEN enrich_status='matiere_polluee' THEN NULL`). Le problème est ailleurs :

**`repair_polluted_descriptions` n'est ni dans `crontab.txt`, ni dans `weekly_audits.py`.**
C'est « un humain qui tape une commande » — ce que la règle 1 du document refuse
explicitement, avec l'exemple des 823 fiches de `venues.py` qui avaient leur `--retry`
depuis le premier jour.

1. **Qui le rouvre ?** Un humain, à la main. Non conforme.
2. **À quelle condition ?** La condition est la meilleure des deux (un événement, pas un
   délai) — mais depuis le 2026-08-04 il existe une classe qu'elle ne peut plus satisfaire :
   `repair_polluted_descriptions` re-télécharge la page source, et `audit_sources_bloquees`
   a établi que `agendaculturel.fr` répond 403 sur tous ses sous-domaines. Pour ces
   fiches-là, le rouvreur ne peut pas aboutir, quel que soit le nombre de fois qu'on le
   lance. (Elles sont depuis passées `rejected` par `retirer_source` — ce qui les sort de
   `select_events` par une autre porte, sans que le compteur `matiere_polluee` le sache.)
3. **Où se voit le nombre ?** Un `log.warning` à chaque run d'enrich (`enrich.py:1786`),
   donc **uniquement dans `logs/enrich.log`** — pas dans Slack, et surtout pas dans
   `_backlog_counts`, dont le compteur « à enrichir » exige `enrich_status IS NULL OR ''` et
   les **exclut par construction**. Le stock est donc invisible du digest hebdomadaire.

### n° 4 — `statut='rejected'` posé par `retirer_source` (créé le 2026-08-04, absent du recensement)

Aucun des trois chemins de réouverture nommés par le document ne s'applique :

- `reconcile_catalogue` ne rouvre **que** l'empreinte exacte
  `llm_justification = "Passé — archivé depuis À valider."`. `retirer_source` n'écrit
  **aucune** `llm_justification` (`retirer_source.py:122`) : le motif du rejet n'est inscrit
  nulle part sur la ligne ;
- `unreject_wp_online` exige des ids donnés à la main ;
- le bouton du back-office aussi.

Deux particularités que le document ne couvre pas :

**a) Il GARDE `wp_post_id_as`**, contrairement à `trash_by_ids`/`trash_wp_ids` qui le
coupent. C'est délibéré et bien argumenté (docstring, lignes 23-25), mais ça produit une
combinaison inédite : `rejected` + lien conservé + post corbeillé. Elle n'est nettoyée
qu'au passage hebdomadaire de `reconcile_wp_deleted` (dimanche 5h), qui posera
`wp_deleted_at`. Entre-temps, la fiche compte comme « publiée » dans tout ce qui sélectionne
sur `COALESCE(wp_post_id_as,0) > 0`.

**b) En cas d'échec de corbeille, deux outils du dépôt se contredisent.** `retirer_source`
le dit franchement (lignes 136-141) : statut `rejected` posé, post **encore en ligne**. Or
c'est très exactement la condition d'entrée d'`unreject_wp_online`, qui re-classerait ces
fiches `published_sub` et **défairait le retrait de la source**. Rien sur la ligne ne permet
de distinguer « rejetée parce que la source a été retirée » de « rejetée à tort ».

1. **Qui le rouvre ?** Personne, et c'est légitime — un retrait de source est une décision.
   Mais alors il doit porter son empreinte, comme `MOTIF_PERIMETRE` et `MOTIF_ARCHIVE`, pour
   qu'`unreject_wp_online` puisse refuser d'y toucher.
2. **À quelle condition ?** Le motif peut cesser : un 403 peut être temporaire, et
   `audit_sources_bloquees` le dit lui-même (« un 403 peut être temporaire, ou tomber le
   jour où le domaine change d'hébergeur »). Le jour où le domaine répond de nouveau,
   **rien** ne ramène les 338 fiches.
3. **Où se voit le nombre ?** Nulle part. `audit_sources_bloquees` compte les fiches
   *encore devant nous* d'un domaine bloqué — pas les fiches retirées. Une fois passées
   `rejected`, elles sortent de tous les compteurs. Nombre réel : invérifiable d'ici.

### n° 6 — le cas que le code déclare ouvert et que le document ne mentionne pas

`refresh_deplacement` (lignes 260-273) écrit noir sur blanc :

> « ces N post(s) sont à la CORBEILLE alors que la base les croit publiés (règle 1).
> **AUCUN script ne referme ce cas tout seul, et c'est voulu** »

et propose deux gestes manuels (rejeter, ou vider `wp_post_id_as`). Le commit d7e4741 chiffre
le stock au 2026-08-04 : **22 fiches refusées, 21 encore devant nous**, note de section gelée.

**Une réserve importante, trouvée en fin de balayage.** L'arbre de travail contient un
fichier **non suivi par git** : `scripts/reconcile_hors_ligne.py`. Il traite exactement ce
cas, en quatre familles (lien mort / lien périmé / retrait voulu / retrait subi), répond
explicitement aux trois questions dans sa docstring, emprunte à `resolve_wp_collision` sa
parade « dates incompatibles », et chiffre le stock réel : **85 fiches portent un
`wp_post_id_as` dont le post n'est pas public, dont 28 encore devant nous**.

Mais au 2026-08-04, il **n'est pas commité**, n'apparaît ni dans `crontab.txt` ni dans
`weekly_audits.py`, et **aucun autre fichier du dépôt ne le mentionne** (grep exhaustif).
En l'état de la branche, le cas reste donc ouvert : le remède existe, il n'est branché nulle
part. Je le signale sans y toucher — ce n'est pas mon fichier, et cette session n'écrit que
ce rapport.

1. **Qui le rouvre ?** Personne à ce jour. L'argument de `refresh_deplacement` (« on ne peut
   pas deviner si le post a été retiré exprès ou par accident ») est juste ;
   `reconcile_hors_ligne` y répond par une heuristique explicitement présentée comme un
   pari, avec deux options séparées `--voulus`/`--subis` et rien d'automatique.
2. **À quelle condition ?** Aucune ne peut être automatique, admis.
3. **Où se voit le nombre ?** **C'est là que ça manque.** `refresh_deplacement` n'importe ni
   `utils.slack` ni `utils.pipeline_status` (vérifié par grep : aucune occurrence). Le
   compteur ne vit que dans `logs/refresh_deplacement.log`. Il n'est ni dans `_KNOWN_SCRIPTS`
   du digest hebdomadaire, ni dans `_backlog_counts`. `watchdog_crons` surveille que le
   script a **tourné**, pas ce qu'il a **trouvé**. Les 22 fiches n'ont été vues que parce que
   le bilan du matin de 11h lit les journaux — une surveillance générale, pas un compteur.

---

## 4. Comparaison franche avec `docs/ETATS_TERMINAUX.md`

**Ce que le document a juste, et que j'ai revérifié dans le code plutôt que sur parole :**
les six ré-armements automatiques (venues, dates, `api_error`, `error`, `url_officiel`,
`wp_deleted_at`) fonctionnent comme décrit, y compris le traitement de `NULL` comme
« ancien » dans les deux clauses de cooldown. Le mécanisme `unmerge_data` est bien une pile
et non un objet. Et surtout : **`resolve_wp_collision`, écrit le 2026-08-03 après le
recensement, empile un instantané AVANT de poser `merged`** — la crainte du document (« le
portillon écrit ce jour-là a créé, en une heure, un sixième cul-de-sac ») ne s'est pas
répétée sur ce script-là. `refresh_deplacement` et `deplacement_now_publie` sont propres
aussi.

**Ce que le document affirme à tort comme fermé :**

1. **`home_override='excluded'` — « ✅ fermé le 2026-08-04 ».** Faux à un cran plus haut que
   ce qui a été examiné. `weekly_digest` répond bien à la troisième question (combien, depuis
   quand). Mais la première réponse — « un bouton du back-office le lève » — suppose que le
   bouton *pose* quelque chose sur le site. Il ne pose rien. Le document a corrigé
   l'invisibilité de l'état sans vérifier son effet.
2. **`enrich_status='matiere_polluee'` — « ✅ fermé le 2026-08-03 ».** Le rouvreur existe et
   est bien conçu, mais il n'est dans aucun cron, et son compteur n'est dans aucun bilan.
   C'est le critère que le document lui-même pose et qu'il ne s'applique pas ici.

**Ce que le document oublie :**

3. **`statut='rejected'` posé par `retirer_source`** (n° 4) — le tableau a une ligne
   `statut='rejected'` générique dont les trois rouvreurs nommés ne couvrent aucun de ces
   cas, et le nouveau script n'écrit pas de motif qui permettrait de les distinguer.
4. **`translated_at`** (n° 5) — absent du tableau. `unlink_bad_translations` promet en
   docstring qu'« une vraie traduction pourra être refaite plus tard avec
   `translate_events` », mais `translate_events` sélectionne sur
   `COALESCE(translated_at,'')=''` : pour une paire produite par la machine, l'original ne
   repassera jamais. Seul `repair_translation` remet `translated_at=NULL`, et uniquement
   pour le cas très étroit « la traduction porte le MÊME `wp_post_id_as` que l'original ».
   C'est **la même forme que le renvoi d'`audit_wp_ghosts` vers `relink_wp_ids_as`** que le
   document décrit sous « Le diagnostic sans issue » — un renvoi qui n'aboutit pas, en pire
   parce qu'il est écrit dans la docstring d'un script qu'on lance en croyant l'avoir lu.
   *Nuance honnête :* pour les paires NATIVES (`link_translations_as`, source déjà bilingue),
   l'original n'a pas de `translated_at` et redevient bien candidat. Le trou ne concerne que
   les paires produites par `translate_events`. Combien parmi les 72 : invérifiable d'ici.
5. **Le blocage de FILE** (n° 2) — le document ne connaît que deux formes du motif (« un état
   que personne ne rouvre », « une valeur que personne ne recalcule »). Il en manque une
   troisième : *un refus qui ne marque rien et qui, faute de marque, revient occuper le
   plafond tous les jours*. Elle est plus discrète que les deux autres, parce que chaque run
   se termine sans erreur et que le bilan Slack affiche un compte honnête.
6. **Le cas déclaré ouvert par `refresh_deplacement`** (n° 6) — il est écrit dans le code et
   dans un message de commit, nulle part dans le document, et son compteur n'atteint aucun
   bilan. Son remède, `scripts/reconcile_hors_ligne.py`, existe dans l'arbre de travail mais
   n'est ni commité ni branché.

**Note sur l'état de l'arbre de travail au moment de ce balayage** (non modifié par cette
session) : `scripts/audit_coherence.py`, `scripts/audit_deplacement.py` et
`utils/coherence.py` portent des modifications non commitées, et
`scripts/reconcile_hors_ligne.py` est non suivi. Le balayage ci-dessus lit les fichiers
**tels qu'ils sont sur le disque**, pas tels qu'ils sont dans le dernier commit.

**Un point de méthode, pour la prochaine fois.** Cinq des six trous ci-dessus ont la même
origine : on a vérifié qu'un chemin de retour EXISTE, jamais qu'il est ATTEIGNABLE
(dans un cron, sur la bonne classe de fiches, avec un compteur qui remonte). Les trois
questions de la fin du document sont bonnes ; il leur manque une quatrième, qui est en
réalité la vérification de la première : **le rouvreur est-il branché quelque part, et
qu'est-ce qui prouve qu'il tourne ?**

---

## 5. Ce que je n'ai pas pu vérifier

- Le nombre réel de fiches dans chacun des états ouverts (`home_override='excluded'`,
  `matiere_polluee`, rejets de `retirer_source`, refus de traduction récurrents, posts
  corbeillés vus par `refresh_deplacement`) — **invérifiable d'ici**, pas d'accès à
  `data/events.db`.
- Si `[2153]` est réellement hors de la vitrine côté site, ou seulement en base —
  **invérifiable d'ici**, pas d'accès à l'API WordPress.
- Si les fiches refusées par le portillon de traduction sont effectivement en tête du tri sur
  la base réelle : le mécanisme est démontré sur fixture, sa portée réelle dépend de la
  distribution des scores — **invérifiable d'ici**.
