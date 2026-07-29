# Backlog & tâches à réfléchir — Agenda Cultura Sabauda

Sujets ouverts, par ordre d'idée (pas de priorité figée). Voir aussi
`docs/CHARTE_EDITORIALE.md` (commun aux projets, à migrer dans `cultura-core`) et
`docs/SOURCE_OFFICIELLE.md` (chaîne source officielle + affiches + scores, session 07-28).

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
- [ ] **Déduplication multi-sources** ⟵ signalé par Franck. Un même événement arrive
      par plusieurs flux (institutionnel + radar + office de tourisme). Aujourd'hui la
      dédup est seulement par `url_source` exacte → on garde des **doublons**, parfois la
      **version la plus pauvre**. À faire : regrouper via `same_story()` (titre +
      territoire + dates proches) et **fusionner vers la source la plus riche/autoritaire**
      (institutionnel > radar ; avec photo ; contenu le plus complet). Voir CHARTE §8.
      NB : `same_story()` / `strip_tracking()` existent dans l'Observatoire mais ont
      **divergé** de notre copie synchronisée `utils/sources.py` → resynchroniser au passage.
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
- [ ] Vraie URL `agenda.culturasabauda.eu` (DNS + Traefik) au lieu de sslip.io.

### UX / UI du backoffice (signalé par Franck)
- [x] Messages de retour après action (publication, rejet…).
- [x] Boutons explicites (« ✅ WordPress » + confirmation) au lieu de « CS ».
- [x] Page Événements (liste filtrable) + schéma « comment ça marche ».
- [ ] Passe UX globale : cohérence visuelle, aide contextuelle, états vides soignés.

## À faire valider par Franck
- Style des visuels de substitution (s'il y en a).
- Seuil d'enrichissement (à partir de quel score on enrichit/rédige ?).
- Le site dédié auto-publie-t-il, ou file de relecture aussi pour les 4-6 ?
