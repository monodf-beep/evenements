# Backlog & tâches à réfléchir — Agenda Cultura Sabauda

Sujets ouverts, par ordre d'idée (pas de priorité figée). Voir aussi
`docs/CHARTE_EDITORIALE.md` (commun aux projets, à migrer dans `cultura-core`) et
`docs/SOURCE_OFFICIELLE.md` (chaîne source officielle + affiches + scores, session 07-28).

## Journal de session — 2026-07-31

### 📐 Protocole de LOT — fin du rattrapage au compte-gouttes
- **Constat de Franck** : la journée a enchaîné des correctifs partiels (images, kill-switch,
  méta `as_enrich_status`…) sans jamais vérifier qu'un événement donné avait TOUTE la chaîne
  appliquée — score, article complet/court selon le score, panel lecteurs, `home_score` posé,
  vraie image. Résultat : des fiches "réparées" sur un aspect (l'image) sans savoir si le
  reste (rédaction, score, panel) avait seulement eu lieu. Refus explicite de continuer à
  "réparer un peu partout" : préférence pour un LOT restreint (ex. dix événements) traité
  **intégralement**, vérifié, puis clos — plutôt que tous les événements avancés d'un cran.
- **Outil ajouté : `scripts/batch_report.py`** — ne modifie rien, prend une liste d'ids et
  affiche pour chacun : score, longueur d'article (+ alerte si court alors que le score
  visait un long), verdict du panel lecteurs, `home_score`/`home_override`, id WordPress AS
  et si l'image posée est réelle. Verdict COMPLET/INCOMPLET par événement + total du lot.
  Code de sortie non-nul si le lot n'est pas intégralement complet — utilisable comme
  portillon avant de passer à l'étape suivante ou au lot suivant.
- **Protocole de lot (à répéter, PAS de nouveau rattrapage large tant qu'un lot n'est pas
  clos)** :
  1. `enrich.py <id1> <id2> ... <idN>` — rédaction + score + panel + `home_score`, EXPLICITEMENT
     sur les ids du lot (jamais la queue entière/`--cap`, pour rester dans un périmètre vérifiable).
  2. `batch_report.py <id1> ... <idN>` — doit rendre COMPLET pour chaque id AVANT de publier.
     Un id INCOMPLET (score absent, article vide, panel jamais passé) se corrige ou sort du
     lot — on ne publie jamais un id resté incomplet en base.
  3. `publish_batch_as.py --ids <id1> ... <idN>` (SANS `--skip-media`) — publication + vraie
     image (cf. correctif du jour sur `image_source='banner'`).
  4. `batch_report.py <id1> ... <idN>` — reconfirme COMPLET, cette fois avec l'id WordPress et
     l'image réelle en place. Le lot n'est clos que si cette dernière vérification est propre.
- **Reste à faire** : choisir le premier lot réel (candidats naturels : les 8 ids Groupe A
  en attente du retour de quota API — 834, 840, 843, 1155, 1447, 2128, 3506, 3512) et dérouler
  le protocole ci-dessus dessus, plutôt que relancer un `--cap` large sur toute la file.

### 🐛 Kill-switch quota increvable — corrigé le jour même de sa mise en place
- **Bug trouvé en le testant en conditions réelles** (quelques heures après l'avoir câblé) :
  le kill-switch ajouté dans `enrich.py` (voir entrée "Automatisation complète" plus bas)
  bloque tout nouvel appel API dès qu'une alerte quota est active — mais l'alerte ne se lève
  QUE via `usage.record()` (appelé après un appel RÉUSSI). Résultat : une fois posée, l'alerte
  ne pouvait plus jamais se lever d'elle-même avant l'expiration dure à 7 jours, puisque le
  kill-switch empêchait justement toute tentative qui aurait pu prouver que le quota était
  revenu. Un run relancé après le reset annoncé par Anthropic (2026-08-01 00:00 UTC) restait
  donc bloqué à tort par une alerte posée la veille.
- **Effet de bord observé** : pendant que `enrich.py` refusait sagement de tourner (bon signe,
  le kill-switch lui-même fonctionnait), `publish_batch_as.py --update` (qui ne dépend pas du
  quota LLM) a re-publié 3 fois de suite le même lot de 8 fiches non enrichies, ré-uploadant
  à chaque fois les mêmes images en médiathèque WordPress pour rien.
- **Correctif** : le message d'erreur Anthropic contient l'heure de reset exacte ("You will
  regain access on AAAA-MM-JJ at HH:MM UTC"). `enrich.py` la lit maintenant
  (`_alert_expired()`, regex + comparaison UTC) : si cette heure est passée, l'alerte est
  ignorée et un nouvel essai a lieu (qui lèvera l'alerte pour de bon si l'appel réussit). Si
  aucune heure n'est trouvée dans le message, comportement inchangé (on bloque par prudence).
  Testé (dates passée/future/absente).

### 🔍 Contamination croisée WP#3713/WP#1938 : incident isolé, confirmé par balayage large
- **Découvert en investiguant une incohérence de titre** (cf. entrée diagnostic orphelins
  ci-dessous) : le 2026-07-30 à 01:51:44, WP#3713 (tribe_events, « parc archéologique
  d'Aoste ») a eu une révision dont le titre correspondait en réalité à WP#1938 (« fête
  patronale de Saint-Martin-de-Corleans »), timestamp identique à la seconde près au
  `post_modified` de WP#1938. Contenu erroné auto-corrigé le même jour à 18h54 (titre correct
  restauré) — aucune conséquence visible côté site aujourd'hui.
- **Cause non identifiée dans le code** : relecture de `translate_events.py`
  (`_translate_one`/`_retranslate_one`, la partie parallélisée `ThreadPoolExecutor`) et
  `publisher_as.py` sans trouver d'état partagé entre threads qui expliquerait un tel
  mélange (chaque worker a sa propre connexion SQLite, son propre dict passé explicitement en
  argument, aucun cache global mutable dans les deux fichiers).
- **Balayage large fait (via Novamira, requête $wpdb directe sur wp_posts + révisions,
  2026-07-27 → 2026-07-31, 697 lignes)** : 8 clusters de timestamps identiques trouvés, 7
  explicables (lots de publication simultanés, ou paires de traduction FR/IT légitimes du
  même sujet — comportement normal), **1 seul cas de vraie contamination croisée entre deux
  sujets différents : WP#3713/WP#1938, celui déjà connu**. Aucune autre paire dormante trouvée.
- **Conclusion** : incident isolé, pas un bug systémique récurrent (sinon on en aurait trouvé
  d'autres sur 4 jours de pipeline parallélisé qui tourne en continu). Pas de correctif de code
  à apporter faute de mécanisme identifié — classé « surveillé », pas « résolu ». Si un cas
  similaire réapparaît, ce balayage (requête $wpdb sur les révisions à timestamp identique
  entre parents différents) est la méthode à réutiliser pour le confirmer vite.

### 🤖 Automatisation complète enrich → publish (décision Franck : « oui, cent pour cent automatisé »)
- **Câblé en cron** (`crontab.txt`) : `scripts/enrich.py --cap 20` à 9h30 (après l'évaluation
  de 9h), `scripts/publish_batch_as.py --cap 20` à 11h. Plafonds volontairement prudents pour
  un premier lancement autonome, à ajuster une fois la fiabilité confirmée sur plusieurs jours.
- **Garde-fous ajoutés dans `enrich.py`** (nécessaires avant d'automatiser sans supervision) :
  - Kill-switch quota : `usage.get_alert()` vérifié en tout début de `main()` — si un run
    précédent a déjà signalé un souci API (quota/crédit, cf. `utils/usage.py`, mécanisme déjà
    existant mais jamais consulté avant de lancer un run), le cron s'arrête immédiatement sans
    tenter un seul appel. L'alerte se lève automatiquement au prochain appel réussi
    (`usage.record()` appelle déjà `clear_alert()`).
  - Notification Slack (`utils/slack.py`, déjà existant pour un autre usage, réutilisé ici) dès
    qu'un run déclenche une NOUVELLE alerte quota/crédit — Franck n'a plus à consulter le
    dashboard pour savoir qu'un cron nocturne a buté sur le quota (découvert aujourd'hui même :
    on a tapé le plafond API en pleine session sans alerte proactive).
  - `--cap` ajouté à `enrich.py` (n'existait pas — seul `publish_batch_as.py` l'avait déjà) pour
    borner le coût par run, cohérent avec le style déjà utilisé ailleurs dans le dépôt.
- **⚠️ Point de vigilance découvert en vérifiant avant de câbler** : la docstring de
  `scripts/publish_batch_as.py` affirmait que tout partait "en brouillon" côté WordPress —
  **faux** : le payload Python ne fixe jamais de `status`, donc `cs-publish.php` applique son
  défaut (`'publish'`) → les événements partent **en ligne publique immédiatement**, sans
  relecture humaine entre la rédaction et la mise en ligne. Docstring corrigée pour refléter
  la réalité. Ce chemin automatisé s'appuie donc ENTIÈREMENT sur les garde-fous en amont
  (`utils.eventness.non_event_reason` intégré ce même jour dans `enrich.py`, complétude
  `utils.completeness`, panel de relecture) — aucun filet de sécurité humain après coup.
- **Reste à faire (Franck)** : `crontab crontab.txt` sur le VPS pour activer (pas fait par cette
  session, pas d'accès shell VPS). Recommandé : laisser tourner manuellement une fois de plus
  demain (quota reset 2026-08-01) avant d'installer le cron, pour valider le comportement des
  nouveaux garde-fous en conditions réelles avant de le laisser tourner sans supervision.

### 🔍 Déduplication multi-sources : déjà implémentée (item backlog obsolète) — validée par tests synthétiques
- **Constat** : la tâche demandée (fusionner via `same_story()` les doublons inter-flux,
  institutionnel > radar, en récupérant les champs manquants) est **déjà en production**
  depuis le 2026-07-26 (commit `55cbb7b` et affinages `1134a9b`/`798f219`/`4b4458b`) dans
  `scripts/dedupe.py`, appelé par le cron de 8h30 (avant `dates.py` et `evaluator.py`,
  comme demandé). L'entrée « Déduplication multi-sources » plus bas dans ce fichier était
  restée à `[ ]` malgré l'implémentation — corrigée en `[x]`.
- `utils/sources.py:same_story()`/`strip_tracking()` existent déjà (pas de divergence
  Observatoire constatée à date, contrairement à la note historique du backlog).
- Algorithme en place : union-find par territoire + `same_story(titre)` (+ garde
  `_years_incompatible` pour ne pas fusionner deux éditions annuelles distinctes) ; gagnant
  = `max(score)` avec `TIER_RANK` (`officielle`=3 > `institution`=2 > `tourisme`=1 >
  `radar`=0, vocabulaire identique à `config/sources.txt`) puis richesse (image, longueur
  description, champs structurés, url hors Google News) ; fusion réelle sur le gagnant
  (image/lieu/ville/organisateur manquants complétés depuis les perdants, description la
  plus longue du groupe conservée) ; perdants → `statut='merged'`, `duplicate_of=<id
  gagnant>` — vocabulaire déjà utilisé ailleurs (`cleanup_as_audit.py`,
  `triage_chantier_casse.py`). Dry-run par défaut avec `--apply` n'est PAS utilisé ici
  (volontaire) : traitement 100 % déterministe qui ne touche que les `pending`, protège
  déjà les fiches poussées sur l'agenda (`wp_post_id_as`), et tourne sans supervision
  depuis des jours en cron — changer la convention casserait `crontab.txt`/
  `deploy/cron_pipeline.sh` sans bénéfice.
- Pas de comparaison de dates à quelques jours près : choix délibéré, pas un oubli — à
  8h30 `date_start` est le texte brut du flux (formats hétérogènes), `date_event_start`
  normalisé n'existe qu'après `scripts/dates.py` (8h45, après dedupe). La garde contre les
  éditions différentes passe par les années détectées dans le TITRE
  (`_years_incompatible`), plus robuste qu'un diff de dates non normalisées à ce stade.
- **Validation** : 3 groupes synthétiques dans une DB SQLite temporaire (jamais la base
  réelle) — institutionnel sans image + radar avec image (même sujet, dates à 1 jour
  d'écart) ; office de tourisme vs source officielle avec description longue ; un événement
  isolé. Résultat : le gagnant institutionnel récupère l'image du radar perdant, le gagnant
  officielle hérite de la description la plus longue, les deux perdants passent
  `statut='merged'` + `duplicate_of` correct, l'événement isolé reste intact
  (`pending`/`duplicate_of IS NULL`). Aucun code modifié — uniquement cette entrée de
  journal et la correction de la case à cocher.

### 🐛 `scripts.enrich` publiait des articles de presse comme événements (ids explicites)
- **Bug** : appeler `scripts.enrich <ids locaux>` (bouton « 1 événement », ou tout appel
  avec des ids en argument) enrichissait et publiait la fiche SANS repasser par
  `utils.eventness.non_event_reason()`, le garde-fou déterministe qui détecte les articles
  de presse pris à tort pour des événements (alertes sécurité publique, faits divers,
  comptes-rendus institutionnels, résultats sportifs déjà joués, rétrospectives
  d'anniversaire déjà célébré, panoramas de presse). Ce garde-fou est bien branché dans
  `scripts/evaluator.py` (évaluation normale) et dans `scripts/audit_non_events.py` (audit
  a posteriori sur toute la base), mais **jamais dans `scripts/enrich.py`** : or
  `select_events()` ne filtre par `statut` QUE dans le mode file d'attente par défaut — avec
  des ids explicites, elle fait `SELECT * FROM events_raw WHERE id IN (...)` sans aucun
  filtre de statut. Résultat vécu : 6 fiches sur 10 forcées par id se sont avérées être des
  articles de presse (« PLAN CANICULE », « Un incendie se propage à un chalet », « Enquête
  publique… ») rédigées en « articles d'événement » puis publiées, avant d'être repérées et
  corrigées à la main.
- **Correctif** : appel à `non_event_reason(title, description)` ajouté tout au début de
  `scripts/enrich.py:_process_one_event()`, avant tout appel réseau/LLM (avant même la
  récupération de l'og:image de secours). Si une raison est détectée : aucun appel API,
  fiche marquée `statut='rejected'` + `llm_justification` (même style que le pré-filtre de
  `evaluator.py`), `enrich_status` laissé tel quel (jamais tentée), log `warning`. La
  fonction renvoie un nouveau statut `'rejected'` (au lieu de `'skip'`, pour rester visible
  dans les stats plutôt que noyé en silence) ; `main()` l'affiche dans le résumé final
  (« N rejeté(s) [non-événement] »). Comme `_process_one_event()` est le SEUL chemin de
  traitement par événement, aussi bien pour les ids explicites que pour le mode file
  d'attente (`main()` ne fait qu'un seul `ex.submit(_process_one_event, …)` par événement),
  le garde-fou s'applique désormais dans les deux cas sans court-circuit possible.

### 🔍 Nouvel outil `scripts/diag_wp_orphans.py` (lecture seule, à lancer sur le VPS)
- **Anomalies non résolues à date** : 5 WP#id orphelins (`1674, 1677, 1680, 2232, 4113`,
  aucune ligne locale avec ce `wp_post_id_as`) ; id local `4199` dont `wp_post_id_as`
  est passé de `4121` à `NULL` entre 07:56 et 08:39 sans action volontaire connue ; id
  local `4113` dont le titre stocké (« Ouverture du nouveau parc archéologique d'Aoste »)
  ne correspond pas au titre vu en direct sur `WP#3713` (« Aoste : la fête patronale du
  quartier de Saint-Martin-de-Corleans »).
- **Outil écrit** (pas exécutable depuis cet environnement : ni `.env`, ni accès réseau au
  site) : `scripts/diag_wp_orphans.py`, 100 % lecture seule. Source principale `cs/v1/list`
  (un seul appel, réutilise `fetch_list` de `scripts/cleanup_as_dupes.py`) ; comme cette
  route exclut la CORBEILLE par construction, repli automatique sur `wp/v2/tribe_events/
  <id>?context=edit` (route standard WP core, déjà éprouvée dans
  `scripts/relink_wp_ids_as.py`) pour les ids absents de la liste — seul moyen de
  distinguer « en corbeille » de « supprimé définitivement ». Propose aussi, pour chaque
  orphelin trouvé, des candidats locaux par titre proche (`difflib.SequenceMatcher`).
  Vérifié par `python3 -m py_compile` + import du module + test de `fuzzy_candidates`/
  `lookup` sur fixtures en mémoire (aucune base réelle touchée).
- **À faire par Franck sur le VPS** : `.venv/bin/python -m scripts.diag_wp_orphans`.

## Journal de session — 2026-07-30

### ✅ Audit AdSense (demande Franck : « fais un audit pour adsense »)
- 🚨 **Bloqueur trouvé et corrigé — page `/confidentialite/` publique cassée** : le site
  affichait en public le bandeau « ⚠️ Brouillon interne — page non publiée » suivi d'une
  dizaine de placeholders `[...]` non remplis, très probablement la cause du statut AdSense
  bloqué en « En préparation ». Root cause inattendue : cette page n'est pas du contenu
  WordPress classique (`post_content` vide) mais entièrement rendue par un snippet Code
  Snippets (`template_redirect` sur l'ID de page) qui contenait le markdown brut en dur,
  crochets compris — quelqu'un avait copié-collé la trame de `docs/legal/confidentialite.md`
  telle quelle. Corrigé aux deux endroits : `docs/legal/confidentialite.md` finalisé (FR+IT,
  infos reprises de `/mentions-legales/` déjà correcte : Cultura Sabauda/Franck Monod,
  Chambéry, OVH SAS, GA4 G-HWRKPM4F7J consent-gated Complianz, Brevo) **et** le snippet WP
  live corrigé directement (accès Novamira MCP obtenu en cours de session — exécution PHP
  directe sur le site, plus besoin de repasser par une session Novamira séparée pour ce
  type d'action). Vérifié en direct : page propre, plus de bandeau ni de crochets.
- ✅ **Lien « Mentions légales » manquant au footer** — corrigé côté Novamira (menus WP FR
  « Mentions légales » et IT « Note legali », pas dans le code du snippet footer comme
  supposé au départ). Vérifié en direct : lien présent, page 200.
- ✅ **ads.txt / robots.txt** : déjà conformes (bon pub ID `ca-pub-4040905402577097`, sitemap
  référencé, rien de bloqué au crawl).
- ✅ **Script AdSense en `<head>`** : bon pub ID confirmé. **Pas de balise
  `google-site-verification`** trouvée (ni snippet, ni Yoast, ni Site Kit) — à ajouter si
  la vérification de propriété du site coince côté Search Console/AdSense.
- ✅ **GA4** : un seul point de configuration (réglages natifs Complianz), pas de double-tag
  (pas de GTM/gtag en doublon dans les snippets actifs).
- 🐛 **Bug latent trouvé et corrigé en marge** : `cs-trash.php` (endpoint `cs/v1/trash`)
  bloquait TOUTES les mises à la corbeille de posts publiés avec 409 « non touché
  (sécurité) » malgré `force:true` envoyé par `scripts/trash_by_ids.py` — bug côté WP
  (snippet #10 déployé en v1.0, sans le support `force` pourtant présent dans
  `deploy/wordpress/cs-trash.php` du dépôt depuis le début). Corrigé et vérifié en direct
  (WP#2309 trashé avec succès). **Reste à faire (Franck)** : relancer
  `scripts.trash_by_ids <les 30 ids locaux> --apply` pour finir le nettoyage du chantier
  contenu cassé (`docs/CHANTIER_CONTENU_CASSE_2026-07-29.md`) — **fait, confirmé par Franck** :
  `trash_by_ids --apply` relancé le 30/07 09:52, 30 corbeillé(s), 0 échec (dont WP#2188 et
  WP#3964, les deux doublons italiens du cluster « attentat de Nice » identifiés dans le
  chantier). Restent hors de ce lot les 2 fiches françaises d'origine du même cluster
  (id 2225/WP#1116, id 2927/WP#1125) — décision à prendre : les corbeiller aussi, ou rédiger
  un article dédié à la commémoration plutôt que tout balayer.

## Journal de session — 2026-07-29 (soir)

### ✅ Fait (branche `claude/quirky-davinci-jvqrnw`)
- 🤖 **Fix traduction** : `json.loads(..., strict=False)` — un saut de ligne brut renvoyé par
  le modèle faisait échouer silencieusement certaines re-traductions (ex. id=1552).
- 🤖 **Alerte source non institutionnelle (charte §8)** : un article publié créditait
  guidatorino.com (guide touristique tiers) comme source, alors que le prompt seul ne
  l'interdit pas assez explicitement. Garde-fou déterministe à deux niveaux : filtrage à
  l'enrichissement (`scripts/enrich.py:filter_official_sources`, ne garde que les domaines
  VÉRIFIÉS officiels — pages effectivement lues, `url_officiel`, flux tier « officielle » de
  `config/sources.txt`) + filet à CHAQUE republication (`scripts/publisher.py:build_post`,
  relit `enrich_data` à chaque fois → corrige aussi les fiches enrichies AVANT ce correctif,
  sans réécriture DB ni coût LLM). Script de diagnostic en lecture seule :
  `scripts.audit_bad_sources` (repère les fiches concernées) + nouveau `--ids` sur
  `publish_batch_as` pour republier précisément celles-là.
- 🚨 **CORRECTIF URGENT (même soir)** : la 1ʳᵉ version de `filter_official_sources` était en
  liste BLANCHE (n'autorisait qu'un domaine « vu » par le résolveur officiel cette fois —
  `official_pages`/`url_officiel`). Testée en vrai sur les 112 fiches publiées : **61/112
  (54 %) auraient perdu une source LÉGITIME** (musilac.com, comune.torino.it,
  castellodirivoli.org, nice.fr, abbonamentomusei.it… tous de vrais organisateurs/
  institutions, juste jamais passés par le résolveur déterministe sur cette fiche
  historique) — bien pire que le bug d'origine. **La commande `--ids …` imprimée par l'audit
  n'a PAS été exécutée**, elle aurait cassé 60 fiches saines. Corrigé : liste NOIRE
  (`config/non_institutional_sources.txt`, extensible sans code comme les autres listes du
  dossier), permissive par défaut — un domaine reste gardé sauf s'il est CONNU non
  institutionnel. Revalidé sur les cas réels : plus aucun faux positif, guidatorino.com/
  ici.fr/aostaoggi.it toujours écartés.
- 🧑 **Reste à faire** : relancer `.venv/bin/python -m scripts.audit_bad_sources
  --published-only` sur le VPS avec le correctif (bien plus court — normalement guidatorino
  et ses 2 fiches, plus éventuellement 1-2 autres cas de presse locale), puis republier avec
  `--ids` la liste (courte, cette fois) que le script imprime.
- ✅ **Fait — RÉGLÉ EN LIVE, confirmé sur le VPS** : les 4 fiches concernées (guidatorino
  ×2, ici.fr, aostaoggi.it) republiées avec succès (`publish_batch_as --ids 159 1552 2943
  3521`, 4/4 ok).
- 🤖 **Parallélisation `enrich.py` / `translate_events.py`** : chaque événement passait
  entièrement en séquentiel (lecture pages officielles + rédaction + panel + révision côté
  enrich ; traduction titre/desc + article + publication WP côté translate) — un lot de 10
  prenait 45-90 min. Extraction du corps de boucle en fonction PAR ÉVÉNEMENT
  (`_process_one_event` / `_translate_one` / `_retranslate_one`), chacune avec sa PROPRE
  connexion SQLite (WAL — plusieurs écrivains coexistent, déjà configuré dans
  `scripts.scraper_events.init_db`), dispatchées via `ThreadPoolExecutor`. Réglages
  `ENRICH_WORKERS` / `TRANSLATE_WORKERS` (déf. 3 chacun, `.env.example`). Points de
  vigilance traités : l'ancien `break` sur panne API (enrich) devient un `threading.Event`
  partagé (les workers déjà lancés finissent, les autres abandonnent) ; la dédup « même
  affiche → pas de 2e traduction » (translate) est protégée par un `threading.Lock` avec
  réservation AVANT le travail (pas après coup, sinon deux threads pourraient tous deux
  passer le contrôle avant que l'un des deux ne réserve). Testé (hors LLM/réseau réels,
  mocké) : 6 événements enrichis/traduits concurremment sans corruption DB ni doublon
  WP ; le verrou de dédup image tient sous concurrence (8 événements à affiche partagée
  → 1 seule traduction produite).
- 🤖 **Scores détaillés + relecture panel sur WordPress** (demande Franck) : 7 nouvelles
  métas `as_panel_*` / `as_affiches` / `as_placement`, extraites d'`enrich_data` à la
  publication (`scripts.publisher_as._panel_meta`) — moyenne panel locaux/visiteurs, nb de
  votes révision, verdict, **et surtout `as_panel_revision`** (`aucune`/`appliquée`/
  `tentée`) qui répond à « a-t-on relu et corrigé grâce aux retours du panel ? ». Nouveau
  suivi côté `scripts/enrich.py` : la boucle panel/révision marque maintenant explicitement
  ce statut (avant, seul le résultat final était gardé, sans trace de si une révision avait
  eu lieu). Whitelist `cs-publish.php` + doc `CONTRAT_META_AS.md` à jour. **Affichage réel
  sur la fiche/l'admin WP = à câbler côté Novamira** (comme `as_home_score`), pas fait ici.
- 🤖 **Flèches ▲▼ pour l'ordre des fiches « forcées »** (demande Franck, précision sur le
  chantier home_score) : nouvelle colonne `home_order` (rang manuel, PARMI les fiches
  `home_override='featured'` seulement), flèches dans `/events` (liste) et `/preview`
  (fiche), route `/set-home-order/<id>/<up|down>` — échange le rang avec la voisine.
  Poussé en méta WP `as_home_order`. Testé (logique de permutation isolée).
- 🤖 **Visibilité + pilotage du score home** (répond à la question « pourquoi la home
  n'affiche pas les mieux notés ») : colonne `home_score` + tri `?sort=home` dans `/events`
  (back-office), badge 🏠 déjà présent en fiche (`/preview`). **Nouveau : override manuel**
  `home_override` (`''`=auto · `featured` · `excluded`), posé via boutons en fiche
  (`/set-home-override/<id>`), poussé en méta WP `as_home_override` (whitelist
  `cs-publish.php` + doc `CONTRAT_META_AS.md`).

### ⏳ Reste à faire / décisions
- 🎨 **Câblage JetEngine effectif** de `as_home_score` + `as_home_override` sur les sections
  « À la une »/« En évidence » de la home — instructions à jour dans `docs/CABLAGE_HOME.md`
  (étapes 2-3), mais le câblage lui-même se fait côté WordPress (session Novamira/Claude
  Design), pas dans ce repo. Tant que ce n'est pas fait, la home reste chronologique
  (sélections en mode auto, `docs/SELECTIONS_HOME.md`) et ignore le score home.
- 🧑 **Gros événements multi-sites (ex. Journées du Patrimoine)** : comment le pipeline doit
  représenter un « méta-événement » qui regroupe des dizaines de lieux/sites participants —
  à cadrer plus tard (pas urgent, noté ici pour ne pas l'oublier).

## Journal de session — 2026-07-27/28 (nuit)

### ✅ Fait (branche `claude/quirky-davinci-jvqrnw`)
- 🤖 **Panel de personas lecteurs** : 8 personas sourcés (recherche territoriale, `docs/personas/`),
  ciblage par territoire (locaux + visiteur d'aire voisine via `visite:`), révision si moyenne < 3.
- 🤖 **Chaîne « source officielle fait foi »** (`docs/SOURCE_OFFICIELLE.md`) : agrégateur bloqué →
  résolution du site officiel par recherche web (vérifiée) → lecture pages presse/programme +
  dossier de presse en iframe → **mémorisation `url_officiel`** (déterministe) + **verrou manuel**
  au back-office. Recherche web coupée si matière officielle trouvée.
- 🤖 **Affiches** portrait + paysage depuis le dossier de presse (affiche-grade only), affichées +
  téléchargeables + **verrou manuel** (sites JS/gated). **Statut dossier de presse** au back-office
  (public / accréditation requise / sans affiche / absent).
- 🤖 **Deux scores** : avant (matière officielle → article complet) + **score home** 0-10 (panel +
  source + affiches) → colonne `home_score` → méta `as_home_score`.
- 🤖 **Garde-fous déterministes** : gras (charte), cadrage temporel (à venir/en cours/terminé +
  anti « bluff rétro »), interdit méta-vide, substance par genre, hotlink (no-referrer).
- 🤖 **Durcissement pré-campagne** (revue multi-agents) : G1 fausses affiches (vignettes WP), G2
  agrégateur mémorisé comme officiel, G3 saut vers sponsor ; généralisation FR (accents,
  mono-token) + IT (`stampa`/`comunicat`).

### ⏳ Reste à faire / décisions
- 🧑 **Vérifier la date de l'événement 825 (Musilac)** : 2027 futur (le cadrage temporel corrige)
  ou 2026 passé (question de filtrage). Cf. la commande sqlite fournie en session.
- 🧑 **Demander l'accréditation presse** pour les événements au statut `accreditation` (ex. Musilac)
  → récupérer affiche + dossier de presse.
- 🎨 **WordPress/JetEngine** : trier « À la une » / « En évidence » sur la méta `as_home_score`
  (cf. `docs/CABLAGE_HOME.md`) + **backfill** (`scripts/backfill_home_score.py`) puis republier.
- 🧑 **Décisions éditoriales score home** : quelles sections basculent sur `as_home_score` (vs
  `as_score`/importance) ; seuil « En évidence » (back-office traite ≥ 6 comme « bon »).
- 🤖 **Valider large** : lancer sur événements FR grand public + IT/Piémont/Vallée d'Aoste avant
  la campagne complète.
- 🤖 **Option B (article vivant)** : gros événement annoncé loin, programme non sorti → article qui
  s'enrichit à mesure des annonces (chantier de fond, à voir au back-office).

---

## Journal de session — 2026-07-25/26

## Journal de session — 2026-07-25/26

Légende propriétaire : 🤖 Claude Code (repo) · 🧑 Franck (VPS/décision) · 🎨 Claude Design (WordPress).

### ✅ Fait cette session (commité, branche `claude/quirky-davinci-jvqrnw`)
- 🤖 **Charte** : §5 bis « faits structurés obligatoires par type » (10 types + pièges :
  horaires≠dates, spectateurs vs participants, VO/VF, récurrence…) + §11 « rythme newsletter ».
- 🤖 **`enrich.py`** : champ `programme` (LISTE) dans le schéma + rendu markdown + consignes par type.
- 🤖 **`newsletter.py`** : axe TEMPOREL (ouvre / continue / dernière chance) au lieu du tri par
  score qui laissait un événement long squatter le héros ; anti-répétition PERSISTANTE
  (table `newsletter_sent`) ; fin de la fuite de `llm_justification` ; **fix responsive** mobile
  (media query dans `newsletter_variants` — débordement 624→485 px).
- 🤖 **Audit Observatoire** (4 agents) : **zéro dépendance code réelle**. Couplages restants =
  voulus (fichiers `# SYNCED FROM`, VPS/Traefik commun). Seul point dur = **clé Brevo partagée**.
- 🤖 **Fuite bannière « Observatoire économique » (§9)** : `pick_banner_image` réécrit
  (`_canon_territory` FR+IT — Nizza/Savoia inclus ; résout UNIQUEMENT dans le set catégorie
  Agenda, sinon "") ; `config/territory_images.txt` **vidé** des URLs Brevo ;
  `upgrade_category_banners_as.py` durci (attrape `%mailinblue%`).
- 🤖 **Dédup** : `cleanup_as_dupes.py --include-published` + envoi `force:true` au mu-plugin.
- 🤖 **Docs reconciliées** avec l'état LIVE (sélections/hubs déjà en ligne) : `SELECTIONS_HOME.md`,
  `TODO_LANCEMENT.md`. + URL Page Facebook Savoie consignée (`RESEAUX_FACEBOOK_THREADS_SETUP.md`).

### 🔎 Diagnostics posés (pas des bugs)
- **Bannière « Espace Sabaudo » visible** = artefact **WordPress** (thème GeneratePress / masthead PNG),
  PAS le pipeline (vérifié : posts sans image à la une → placeholder de thème). → 🎨.
- **Sélections vides** (Annecy…) = **volume faible** sur filtre ville×week-end, pas un bug de filtre
  (la sélection large `/selections/ce-week-end/` liste bien ~8 événements).

### ⏳ Reste à faire
- 🧑 **Déployer `cs-trash.php` sur OVH** : `push-wordpress.sh` échoue (`WP_DEPLOY_SSH` absent du `.env`).
  Sinon **trasher à la main** les 8 doublons publiés (WP# 2319, 2356, 2329, 2340, 2323, 2205, 2271, 2228)
  dans wp-admin. Puis re-lancer le ménage pour les futurs.
- 🤖 **Durcir la résolution d'image** (bug Yerai) : (a) ne PAS re-résoudre quand une og:image valide
  existe ; (b) recherche Commons par **sujet** (artiste/événement), pas par **lieu** (« Fondation Maeght »
  → l'architecte Sert au lieu de Yerai Cortés) ; (c) agent vision qui rejette le hors-sujet.
- 🧑 **Poser l'image Yerai à la main** en attendant le durcissement.
- 🧑 **Décisions produit** : clé Brevo dédiée Agenda ; client OAuth Google = même que l'Observatoire ? ;
  seuil ville 8 vs 15 ; sélections auto vs manuel.
- 🎨 **Claude Design** : hero « Espace Sabaudo » (masthead) ; formulation « espace Sabaudo » sur les
  couvertures ; repli JetEngine des sélections vides (→ requête plus large).
- 🤖/🧑 **Code mort `utils/sources.py`** (filtre radar « économique » de l'Observatoire) : inerte, mais
  fichier `SYNCED` → à retirer côté Observatoire aussi (décision partagée).
- 🤖 **Cultura Sabauda : rédacteur + panel dédiés (chantier différé — décision « Agenda d'abord »).**
  Constat : `enrich.py` a UN seul prompt, désormais 100 % Agenda (pyramide inversée), et
  `publisher.py` (CS) lit le MÊME `article_md` que `publisher_as.py` (AS). Donc l'escalier de
  Cultura Sabauda n'est plus branché : ce qui part sur CS sort en style Agenda. Les 6 personas
  et le panel lecteurs (`docs/personas/`) sont le dispositif **Agenda uniquement**.
  Quand CS redevient prioritaire : (a) rendre `enrich.py` conscient de la publication — escalier
  pour CS, pyramide pour AS ; (b) construire un panel de personas CS distinct (lecteurs d'essai,
  lentille « qu'est-ce que ça m'apprend de durable / honnêteté de l'idée / anti-cliché »), pas les
  lecteurs d'agenda actuels. Vérifier au passage si des posts CS sont publiés en style Agenda
  aujourd'hui (régression réelle) ou si CS est de facto en veille.

## Le pipeline, étape par étape — où placent-on agents & règles ?

```
1. COLLECTE            RSS (scraper_events) + Newsletters Gmail (gmail_collect)
   règles : dédup par url_source ; filtrage images CDN presse ; label « Agenda »
   →
2. ÉVALUATION          evaluator.py — 1 appel LLM par événement
   agent/règles : CHARTE §1-3 (escalier, périmètre strict, scoring) → score 0-10
   →
3. ENRICHISSEMENT  ✅ scripts/enrich.py (déclenché à la main, pas en cron)
   agent de recherche (web + sources officielles, outil web_search_20260209)
   UNIQUEMENT sur les événements retenus (score ≥ ENRICH_MIN_SCORE, coût maîtrisé,
   doublons exclus). Agrège d'abord la MATIÈRE (description + doublons fusionnés),
   puis récupère le contexte selon CHARTE §5. Sortie : enrich_data (JSON :
   contexte_lieu, contexte_entites, angle, infos_pratiques, sources, confiance).
   →
4. RÉDACTION       ✅ scripts/enrich.py (même appel agentique que l'étape 3)
   rédige l'article selon CHARTE §4/§6/§7. Sortie : article_title + article_md
   (titre, chapô, corps, encadré, sources) → visible dans /preview, file de relecture.
   →
5. RELECTURE / VALIDATION   Franck (backoffice) : valider / corriger / rejeter.
   →
6. PUBLICATION       Home CS = brouillon WordPress (publisher) ; Site dédié = auto
   APRÈS relecture. Jamais d'écho RSS brut.
```

## Tâches à réfléchir

### Images (signalé par Franck)
- [x] Récupérer l'**image OG** (`og:image`) de la page source quand le flux n'a pas de
      photo. FAIT : `enrich.py` (repli à l'enrichissement) + cascade complète `scripts/visuals.py`
      (og:image → 1re photo de contenu → recherche Commons → bannière territoire/catégorie).
- [ ] Définir l'**alternative « pas de photo »** : ne rien afficher (état actuel) vs
      générer un **visuel culturel** par territoire/catégorie (≠ bannière éco de
      l'Observatoire, qui est inadaptée). Décider du style.
- [ ] Légendes / crédits photo si requis.

### Enrichissement & rédaction (cœur du « site dédié » qualitatif)
- [x] Construire l'étape 3 (agent de recherche) + l'étape 4 (agent de rédaction)
      → `scripts/enrich.py` (un seul appel agentique : recherche web puis rédaction).
- [x] **Enrichissement = automatique** : depuis le signal (titre/date/lieu/entités),
      recherche web → **source officielle libre** (organisateur, lieu, agenda officiel,
      billetterie) → extraction du contenu pour la rédaction. **Ne JAMAIS franchir un
      paywall** (CHARTE §5). C'est la réponse à « comment avoir du contenu quand c'est
      payant » : on prend le contenu à la source primaire gratuite, pas à la presse.
- [x] Schéma de données enrichies en base : colonnes `enrich_status`, `enriched_at`,
      `enrich_model`, `enrich_data` (JSON), `article_title`, `article_md`.
- [x] Budget : réservé aux retenus (`ENRICH_MIN_SCORE`), par lots (`ENRICH_BATCH`),
      modèle configurable (`ANTHROPIC_MODEL_ENRICH`), plafond de recherches web
      (`ENRICH_MAX_SEARCHES`). Déclenché à la MAIN (bouton), **pas en cron** pour l'instant.
- [x] Sourcing strict : ne jamais inventer ; `sources[]` tracées + `confiance` affichée.
- [ ] **À valider par Franck** : passer l'enrichissement en cron (auto quotidien) une
      fois le coût réel observé ? seuil de score ? auto-publication du site dédié ?
- [ ] Plafond mensuel de coût (kill-switch) si l'enrichissement tourne en auto.

### Matière maximale (décision Franck : 1 + 3)
- [x] **Canal « dossiers de presse »** (`scripts/press_kits.py`) : label Gmail « Presse »,
      extraction texte PDF (pypdf) + photos HD sur disque, rattachement à l'événement
      (same_story). L'agent d'enrichissement en fait sa **matière prioritaire**.
- [x] **Faits vs expression** : l'agent exploite la presse (même payante) pour les FAITS
      (dates, lieu, casting), jamais le texte ni le crédit ; expression/attribution =
      source officielle. CHARTE §5 mise à jour.
- [ ] **Hébergement des photos de dossier** pour l'image à la une WordPress (upload média
      WP) — aujourd'hui les photos HD sont juste enregistrées sous `data/press_kits/`.
- [ ] **Suivi des accréditations** (option 2, non retenue pour l'instant) : registre des
      organisateurs accrédités → priorité + relances aux lieux clés.

### Newsletter (canal automatique)
- [x] **Charte §11 — rythme temporel**. Axe « ouvre / continue / dernière chance » au lieu
      d'un tri par score qui laissait un événement long (expo sur 3 mois) squatter le héros
      chaque semaine. Fondé sur les bonnes pratiques des newsletters d'événements locaux.
- [x] **`newsletter.py` — axe temporel** (`_split_temporal`) : répartition déterministe en
      3 seaux (ouvre = héros + cartes ; dernière chance + continue = sommaire compact borné
      `MAX_CONTINUE`). Mode `temporal=False` pour la composition MANUELLE (l'ordre humain fait
      foi — `app.py` newsletter_brevo). Retrait de la fuite de `llm_justification` (scoring)
      dans `_summary` : plus de texte back-office dans les cartes / le preheader.
- [x] **Anti-répétition inter-envois PERSISTANTE** : table `newsletter_sent` (territoire,
      edition, event_id, slot) — CLI-owned, distincte de `newsletter_editions` (compos
      manuelles) pour éviter tout conflit de clé. `main()` lit les ids déjà listés en sommaire
      les semaines passées (`_seen_continue_ids`) et les retire du seau « continue » → un
      événement long n'y figure qu'UNE fois sur toute sa durée ; il est ensuite tracé
      (`_record_sent`) après création du brouillon. Testé (héros non répété, sommaire purgé,
      pas de fuite de scoring).
      Reste optionnel : appliquer la même trace au canal MANUEL (app.py) — écarté (clé de
      territoire groupée différente, et l'humain contrôle déjà sa sélection).
- [x] **Responsive** : bug trouvé et corrigé. Le `max-width:100%` sur le conteneur fixe
      `width="600"` ne collapsait PAS (les attributs `width="600"/"528"` imposaient une largeur
      mini > viewport → texte rogné à droite sur mobile). Mesuré : scrollWidth 624px (débordait)
      → 485px après correction. Fix ADDITIF dans `utils/newsletter_variants._shell` : un
      `<style>@media (max-width:600px)` qui passe le conteneur et les grandes images en fluide,
      ciblé par attribut (favicons/logo intacts). Desktop et clients sans media query (Outlook)
      inchangés. Vérifié au rendu Chromium (mobile + desktop). NB : `variant_magazine` est
      PARTAGÉ avec l'Observatoire → le fix améliore les deux, sans toucher au desktop.
- [ ] Reste à vérifier une fois en conditions réelles : une liste `## Programme` LONGUE dans un
      article (rendu par le thème WordPress, hors template email).

### Enrichissement — faits structurés (charte §5 bis)
- [x] **Champ `programme` (LISTE)** ajouté au schéma JSON d'`enrich.py` + rendu markdown
      (`## Programme`, défensif) : un programme / line-up / déroulé n'est plus noyé en prose et
      survit au mode court.
- [x] **Consignes par type** dans le prompt (expo, concert, spectacle, festival, sagra, marché,
      conférence, sport, cinéma, fêtes populaires) avec les pièges : horaires ≠ dates,
      spectateurs vs participants (sport), VO/VF (cinéma), récurrence (marchés/fêtes).

### Qualité de la collecte
- [x] **Déduplication multi-sources** ⟵ signalé par Franck. Un même événement arrive
      par plusieurs flux (institutionnel + radar + office de tourisme). **Fait** (voir
      Journal 2026-07-31) : `scripts/dedupe.py` regroupe via `same_story()` (titre +
      territoire, garde anti-éditions par année) et **fusionne vers la source la plus
      riche/autoritaire** (officielle > institution > tourisme > radar ; avec photo ;
      contenu le plus complet), en cron à 8h30 avant l'évaluation. Voir CHARTE §8.
- [x] **Travailler par PÉRIODE (« ce week-end »)** ⟵ signalé par Franck. `scripts/dates.py`
      extrait la vraie date d'événement (FR/IT, plages, « jusqu'au X ») → `date_event_*`.
      Filtre de période dans `/events` (presets + mini-calendrier + bac « date à confirmer »),
      tri chronologique. **Principe** (validé sur GuidaTorino) : *la période pilote la
      VALORISATION* (une expo longue re-fait surface à chaque week-end qu'elle chevauche),
      *le STATUT pilote le COÛT* (Évaluation/Enrichissement ne traitent que les `pending`
      de la fenêtre — `--from/--to` — et ne repaient jamais un événement déjà traité).
      Aperçu du compte avant de lancer. Reste à faire : angle « dernier week-end » auto ;
      re-valorisation d'un événement déjà publié sur une nouvelle période.
- [ ] **Géo-filtrage des radars Google News** : ils ramènent du hors-périmètre
      (ex. « Lombardia »). Aujourd'hui l'évaluation LLM les rejette (score 0) — OK,
      mais coûteux. Envisager un pré-filtre territoire avant l'appel LLM.
- [ ] Nettoyage des titres Google News (suffixe « - source », entités HTML — partiellement fait).

### Plateforme & partage
- [ ] **`cultura-core`** : extraire la charte + `utils` partagés (logger, sources, usage,
      google_auth) en dépôt versionné réutilisé par les 3 projets. Miroir Obsidian possible
      pour l'éditorial. (Voir le plan dans `README.md`.)
- [ ] **Sélecteur de modèle** dans le dashboard (Sonnet/Haiku/Opus) sans éditer le `.env`.
- [ ] Vraie URL `backoffice.agendasabauda.eu` (DNS + Traefik) au lieu de sslip.io (corrigé
      2026-07-31 : la marque est Agenda Sabauda, pas culturasabauda.eu).

### UX / UI du backoffice (signalé par Franck)
- [x] Messages de retour après action (publication, rejet…).
- [x] Boutons explicites (« ✅ WordPress » + confirmation) au lieu de « CS ».
- [x] Page Événements (liste filtrable) + schéma « comment ça marche ».
- [ ] Passe UX globale : cohérence visuelle, aide contextuelle, états vides soignés.

## À faire valider par Franck
- Style des visuels de substitution (s'il y en a).
- Seuil d'enrichissement (à partir de quel score on enrichit/rédige ?).
- Le site dédié auto-publie-t-il, ou file de relecture aussi pour les 4-6 ?
