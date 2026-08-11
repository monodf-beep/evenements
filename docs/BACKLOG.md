# Backlog & tâches à réfléchir — Agenda Cultura Sabauda

Sujets ouverts, par ordre d'idée (pas de priorité figée). Voir aussi
`docs/CHARTE_EDITORIALE.md` (commun aux projets, à migrer dans `cultura-core`).

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

## Journal de session — 2026-07-26 (site WordPress, branche `claude/agenda-sabauda-homepage-test-exckrp`)

*Session parallèle à celle ci-dessus. Périmètre : le **site WordPress live**
(gabarits, contenu, docs), pas le pipeline Python. Peu de recouvrement avec la
session pipeline. Même légende propriétaire.*

### ✅ Fait cette session (commité + vérifié en prod)
- 🤖 **Allocateur home** (snippet 44) : `ala-une` et `weekend` ne tombent plus à 0
  quand le stock est sous une ligne complète (bug IT Savoia : 0 au lieu de 3).
  Seul `jour` garde la règle « 4 ou 8 ».
- 🤖 **« No data was found » traduit** FR/IT (snippet 98, filtre `gettext` selon
  la langue Polylang) : les sections vides s'affichent « Aucun evenement pour le
  moment » / « Nessun evento al momento ».
- 🤖 **Fiche événement** (snippet 56) : 3e rail « Près d'ici, mêmes dates » ;
  badges « Dernier jour »/« En cours » (Complet exclu, meta non fiable) ;
  Instagram Savoie-FR uniquement (masqué sinon) ; **bouton de suivi Facebook
  désactivé** (`$cs_fb_acc = null`) car la page n'est pas encore active.
- 🤖 **Ajouter à mon agenda** (snippet 69) : rappels **J-7 / J-1** via `VALARM`
  dans le `.ics` (impossible via les liens directs Google/Outlook, aucun
  paramètre fiable).
- 🤖 **Gabarit 404 sur-mesure** (snippet 99) : vrai HTTP 404, bilingue, recherche
  + 4 portes territoires.
- 🤖 **Page guide « Cuisine Nissarde »** publiée **FR (post 3648) + IT (post
  3650)**, liées Polylang, rattachées Comté de Nice + Gastronomie (remontent
  auto dans les hubs). Source : dossier de presse OT Nice 2025/26.
- 🤖 **Docs** : renommage `SABAUDO`→`SABAUDA` (13 fichiers + réf croisées) ;
  réconciliation de `TODO_LANCEMENT.md` avec le live ; création de
  `ETAT_DAVANCEMENT_AGENDA_SABAUDA.md` (as-built détaillé, complément de ce
  BACKLOG) ; correction des docs par gabarit (FICHE, HUB, RECHERCHE,
  REGLES_HOMEPAGES).

### 🔎 Diagnostics posés (pas des bugs)
- **Photos** : les images de repli `fallback-*` sont **bakeées comme
  `_thumbnail_id`** → détecter « sans vraie photo » = tester le slug `fallback-`,
  PAS un thumbnail vide (un diagnostic naïf renvoie 0 à tort). Réel : **19 FR +
  23 IT** événements futurs sur repli (liste : `PHOTOS_MANQUANTES_EVENEMENTS.md`).
  → complément WordPress du chantier « alternative pas-de-photo » ci-dessous.
- **« Partager sur Facebook »** vu dans le source = i18n **Elementor** dormante
  (`elementorFrontendConfig`), **jamais rendue** : il n'existe aucun bouton de
  partage Facebook sur le site.
- **Catalogue IT** : nettement plus de sections vides que le FR (volume de
  traductions, pas un défaut technique — l'état vide s'affiche bien en italien).

### ⏳ Reste à faire
- 🧑 **Réactiver le bouton de suivi Facebook** dès que la **page Savoie** sera
  active. URL canonique `https://www.facebook.com/agendasabauda-savoie/`
  (statut « prévue » dans `RESEAUX_FACEBOOK_THREADS_SETUP.md`). À rendre
  **territoire-aware** comme Instagram (une URL par territoire).
- 🤖/🧑 **Alternative « pas de photo »** (COMMUN avec la session pipeline, cf.
  §Images du BACKLOG) : côté site, 42 événements futurs affichent un repli. À
  décider ensemble : repli générique (état actuel) vs vrai visuel par
  territoire/catégorie.
- 🤖 **Étiquettes** (Gratuit / En famille / Transfrontalier / massifs) : pas de
  taxonomie dédiée, seulement des `post_tag` ad hoc. À structurer si on veut des
  hubs d'étiquette propres.
- 🧑 **Communs aux deux sessions** : hygiène sécurité (mot de passe FTP OVH + clé
  API Anthropic), sourcing Annecy/Chambéry au seuil, GSC, décisions stratégiques.

---

## Journal de session — 2026-08-08/11 (WordPress via MCP Novamira)

Session menée entièrement côté WordPress. Ce qui suit a été **constaté en base ou sur le HTML
servi**, pas déduit. Voir `docs/MCP_NOVAMIRA.md` pour l'outillage et
`docs/POSTMORTEM_2026-08-11_MU_PLUGIN.md` pour l'incident de production.

### ✅ Fait et vérifié en prod
- 🤖 **Décidia 2026 retiré du site (WP 1934), décision Franck du 2026-08-11** : salon d'affaires,
  hors périmètre d'un agenda culturel. Mis à la corbeille, donc réversible, sauvegarde complète
  du post et de ses 58 métas dans `cs_bk_1934_avant_corbeille_20260811`. L'URL répond 404.
  **La règle qui manquait est écrite dans `docs/CHARTE_EDITORIALE.md` §3 bis** : la charte
  demandait « le public peut-il assister », ce qu'un salon professionnel satisfait puisqu'on
  peut s'y inscrire. Le critère devient « l'événement s'adresse-t-il au grand public », avec
  quatre marqueurs et une liste de contre-exemples pour ne pas rejeter les foires et salons
  grand public. **À porter dans la notation du pipeline** : sans ce critère en amont, l'édition
  2027 reviendra toute seule.
- 🤖 **28 sources officielles** écrites après double vérification de l'éditeur (15 + 13). Le
  manque `source_officielle` passe de 59 à 31. Sauvegardes `cs_bk_sources_20260809`,
  `cs_bk_sources_20260809_lot2`.
- 🤖 **22 sources proscrites retirées** des fiches en ligne ou en brouillon : 13 vers
  `rendezvous-vda.it` (magazine privé enregistré au tribunal d'Aoste), le reste vers
  `agendaculturel.fr`, `piemontedalvivo.it`, `mentelocale.it`. Sauvegarde
  `cs_bk_sources_proscrites_20260809`. La doctrine tranche : mieux vaut aucune source qu'une
  source douteuse.
- 🤖 **Spectacle annulé rattrapé** : la source officielle du Forte di Bard annonçait
  l'annulation du K-Pop live show du 18/07, la fiche l'annonçait toujours comme maintenu.
  Titre, avis de remboursement et `eventStatus: EventCancelled` posés sur les deux langues.
- 🤖 **Fiche de report remise en forme d'annonce** (6352, Estivales Sauvages), nouveau titre,
  nouveau slug, `EventRescheduled` + `previousStartDate`, ancienne URL en 301.
- 🤖 **Titres nettoyés** : « - Torino Oggi » et « ANSA – » retirés (6275, 1873), redirections
  301 vérifiées. Titre « Programme » corrigé en « Distribution » sur une fiche où le bloc ne
  listait que la distribution (752).
- 🤖 **Quatre mu-plugins** posés : `cs-corps-lint.php` (contrôle mécanique d'un corps),
  `cs-event-statut.php` (statuts d'événement dans le graphe Yoast),
  `cs-redirect-ancien-slug.php`, `cs-completude.php` (passe quotidienne).

### 🔎 Diagnostics posés
- 🤖 **`wp_old_slug_redirect()` ne fonctionne pas sur `tribe_events`.** The Events Calendar
  intercepte l'URL, rend son archive et pose un 404 avant `template_redirect` priorité 5. Toute
  fiche renommée jusqu'ici perdait son URL en silence.
- 🤖 **Les placeholders de l'accueil sont servis aux robots.** Les deux faux articles
  (« Juillet 2026 : douze expositions… ») étaient masqués en CSS mais présents dans le HTML.
- 🤖 **La substance d'une fiche vient de la source ouverte**, pas de la consigne de rédaction :
  sur 50 fiches réécrites sans source, 10 seulement ont dépassé 900 caractères, et ce sont
  exactement celles dont l'agent avait lu la source.

### ⏳ À corriger dans le pipeline (🧑 VPS, hors de portée du MCP)
Tant que ces points tiennent, **tout nettoyage fait dans WordPress est réécrit à la
republication suivante**.

- 🧑 **Sources proscrites écrites dans `as_source_officielle_url`.** Le pipeline y met des
  agrégateurs et des magazines privés. Il faut une liste de refus en amont.
- 🧑 **Un report crée un article distinct** au lieu de mettre à jour la fiche existante. Google
  demande l'inverse : même URL, on change `eventStatus` et on conserve l'ancienne date dans
  `previousStartDate`. Deux URL pour un même événement se concurrencent.
- 🧑 **Le panel rend un verdict `revise` sans motif.** Huit fiches portent
  `as_panel_verdict = revise` avec `as_panel_revision` vide (6297, 7225, 6373, 7223, 2255,
  6405, 7197, 6433). Un verdict sans reproche est inexploitable : soit la passe écrit ce
  qu'elle reproche, soit elle ne rend pas ce verdict.
- 🧑 **Le nom du média de collecte reste dans le titre** (« - Torino Oggi », « ANSA – »), avec
  au passage un tiret demi-cadratin proscrit.
- 🧑 **Les sources contredisent les fiches sans que personne ne le voie** : Nice Classic
  Festival daté 2025 quand la source annonce 2026, Ah ! La Belle Saison daté 2026 quand la
  source décrit 2025, Guitare en scène qui va jusqu'au 18/07 et non au 17, le Forte di Bard
  situé à Aoste alors qu'il est à Bard, la Festa di San Savino donnée sur un jour quand la
  commune annonce du 4 au 8 juillet, et une fiche 2026 rédigée depuis un communiqué de 2023.
  La passe de vérification devrait comparer la fiche à sa source et signaler l'écart.
- 🧑 Rappels des sessions précédentes toujours ouverts : passe-3 non bloquante, suffixe à tiret
  cadratin, contrôle de langue, déduplication, coupe des extraits sur mot entier, écriture du
  titre Yoast, artefact « l'Savoia » du dictionnaire FR vers IT.

### ⏳ Reste à faire côté WordPress
- 🤖 Déposer les 71 corps réécrits en meta `as_corps_propose` (jamais dans `post_content` :
  « aucune publication autonome », Non-négociables).
- 🤖 Seuil de disparition des fiches : décision Franck, **à minuit**, donc filtrage sur
  `_EventEndDate` et non sur `_EventStartDate`. Deux fiches datées 2025 sont encore publiées et
  l'une remonte dans le bloc « ce week-end ».
- 🤖 Doublons entre blocs de l'accueil : « Aujourd'hui » reprend intégralement « À la une ».
- 🎨 Gabarit « Le Fil » / Article inexistant. Le bloc « Nouveautés » ne pourra ressembler à
  celui de Guida Torino, qui liste des **articles** et non des fiches, qu'une fois ce type de
  contenu créé.
- 🧑 Arbitrage : les organisateurs génériques du type `turismo` ou `mairie` ; les liens `#` des
  réseaux sociaux sur l'accueil, dont les URLs n'ont jamais été fournies ; le périmètre
  éditorial des salons d'affaires.

---

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
