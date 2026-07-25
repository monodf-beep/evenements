# Backlog & tâches à réfléchir — Agenda Cultura Sabauda

Sujets ouverts, par ordre d'idée (pas de priorité figée). Voir aussi
`docs/CHARTE_EDITORIALE.md` (commun aux projets, à migrer dans `cultura-core`).

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
- [ ] Récupérer l'**image OG** (`og:image`) de la page source quand le flux n'a pas de
      photo (scraping HTML léger de l'URL de l'événement).
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
- [ ] **Responsive** : le template `variant_magazine` est fluide (viewport + conteneur
      600px/max-width:100%, colonne unique) — OK par construction. À vérifier visuellement une
      fois : rendu mobile réel + une liste `## Programme` longue (rendu thème WordPress).

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
