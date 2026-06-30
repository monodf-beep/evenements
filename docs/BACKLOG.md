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
3. ENRICHISSEMENT  ⟵ À CONSTRUIRE
   agent de recherche (web + sources officielles) UNIQUEMENT sur les événements
   retenus (coût maîtrisé). Récupère contexte selon CHARTE §5 (lieu, artiste/groupe,
   plat, conférencier…). Sortie : champs structurés (contexte_lieu, contexte_artiste,
   angle, infos_pratiques) stockés en base.
   →
4. RÉDACTION       ⟵ À CONSTRUIRE
   agent de rédaction LLM, à partir des données enrichies, selon CHARTE §4, §6, §7.
   Sortie : article (titre, chapô, corps, encadré) → file de relecture.
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
- [ ] Construire l'étape 3 (agent de recherche) + l'étape 4 (agent de rédaction).
- [ ] **Enrichissement = automatique** : depuis le signal (titre/date/lieu/entités),
      recherche web → **source officielle libre** (organisateur, lieu, agenda officiel,
      billetterie) → extraction du contenu pour la rédaction. **Ne JAMAIS franchir un
      paywall** (CHARTE §5). C'est la réponse à « comment avoir du contenu quand c'est
      payant » : on prend le contenu à la source primaire gratuite, pas à la presse.
- [ ] Schéma de données enrichies en base (nouvelles colonnes / table).
- [ ] Budget : l'enrichissement web a un coût → seuils, plafond mensuel, choix du modèle.
- [ ] Sourcing strict : ne jamais inventer ; tracer les sources utilisées.

### Qualité de la collecte
- [ ] **Déduplication multi-sources** ⟵ signalé par Franck. Un même événement arrive
      par plusieurs flux (institutionnel + radar + office de tourisme). Aujourd'hui la
      dédup est seulement par `url_source` exacte → on garde des **doublons**, parfois la
      **version la plus pauvre**. À faire : regrouper via `same_story()` (titre +
      territoire + dates proches) et **fusionner vers la source la plus riche/autoritaire**
      (institutionnel > radar ; avec photo ; contenu le plus complet). Voir CHARTE §8.
      NB : `same_story()` / `strip_tracking()` existent dans l'Observatoire mais ont
      **divergé** de notre copie synchronisée `utils/sources.py` → resynchroniser au passage.
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
