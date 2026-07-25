# Feuille de route de lancement — Agenda Sabauda (master TODO)

*Vue unique de tout ce qui reste. Le détail vit dans les docs référencés. Légende :
[x] fait · [~] partiel · [ ] à faire · 🤖 moi (Claude Code, dans le repo/WP) · 🧑 Franck ·
🎨 Claude Design · ⚙️ config manuelle wp-admin.*

> **Réconcilié avec la réalité le 2026-07-26.** Ce document avait pris beaucoup de
> retard sur l'état réel (il décrivait un site « qui n'existe pas encore »). Or le
> site agendasabauda.eu est **en ligne et alimenté** (153 pages, 270 événements
> publiés, FR + IT). Pour l'état as-built détaillé de ce qui a été construit côté
> WordPress, voir **`ETAT_DAVANCEMENT_AGENDA_SABAUDA.md`** et les docs par gabarit
> (`REGLES_HOMEPAGES`, `FICHE_EVENEMENT`, `HUB_TERRITOIRE_VILLE`, `RECHERCHE`,
> `AJOUTER_AU_CALENDRIER`).
>
> **Coordination deux sessions (2026-07-26)** : ce fichier est édité par deux
> branches Claude en parallèle. La branche `claude/quirky-davinci-jvqrnw` couvre
> le **pipeline** (enrich, newsletter, dédup, dossiers de presse) ; la branche
> `claude/agenda-sabauda-homepage-test-exckrp` couvre le **site WordPress**
> (gabarits, contenu, docs). Les deux journaux de session sont consignés dans
> `BACKLOG.md`. À la fusion, préférer la version la plus cochée de la section 1
> (site) et conserver la section « Outillage de build » + les items pipeline.

---

## Reste à faire en un coup d'œil (au 2026-07-26)

**Le socle fonctionnel du site est construit, en ligne et vérifié.** Ce qui reste
n'est presque plus du code de construction :

- 🤖 **Côté Claude (repo/WP)** : quasiment plus rien de bloquant. Restent, à la
  demande : la **traduction IT** de la page Cuisine Nissarde, et les **dettes
  pipeline** (dédup multi-sources, pré-filtre territoire, `og:image` sans photo,
  `cultura-core`) qui sont optionnelles / améliorations.
- 🧑 **Côté Franck (le vrai chemin critique vers l'ouverture)** : **sécurité**
  (mot de passe FTP + clé API), **remplir Annecy + Chambéry** au seuil, **GSC**,
  et les **décisions stratégiques** (ambition, seuil de score, cron, Brevo).
- 🎨 **Côté Design** : figer la **DA finale**.

Autrement dit : il ne reste plus de « construction de site » majeure à faire en
autonomie. La suite dépend surtout de contenu (sourcing), de sécurité, de
décisions, et de design. Détail par lot ci-dessous.

---

## 0. Backoffice & stratégie — ✅ FAIT
- [x] Filtres périmètre + rejet des événements passés (`evaluator`, `sources`)
- [x] Dashboard : onglet Actifs · tri qualité · filtre hors-radar · vocabulaire unifié
- [x] SEO backoffice (JSON-LD déterministe + agent SEO) + export WordPress
- [x] Sourcing géo-scopé (Le Dauphiné → Savoie/Haute-Savoie)
- [x] Sauvegarde base (`backup_db.py`) + publisher dédup
- [x] Onglet Pilotage + Conseiller + aperçu des modules de la home
- [x] Renommage marque **Agenda Sabauda** (féminin IT)
- [x] mu-plugins socle, `robots.txt`, runbook, décisions de build figées
- [x] Suite documentaire complète

## 1. Site WordPress en ligne — ✅ FAIT (vérifié en prod 2026-07-26)
### Infra & config
- [x] Domaine **agendasabauda.eu** + HTTPS
- [x] **The Events Calendar** + **Polylang** (FR/IT) + **Yoast** *(et non RankMath : correction)*
- [x] Permaliens + slugs (`evenement`/`evenements`/`luoghi`/`territoire`)
- [x] Polylang FR/IT + **hreflang** (via Polylang)
- [x] **GA4** (`G-HWRKPM4F7J`, consent-gated) + **Complianz** (RGPD, opt-in)
- [x] Open Graph (`cs-open-graph.php`), emplacements pub (`cs-pub-slots-vides`, `cs-regie-serve`)
- [ ] ⚙️ **Sitemap Yoast + IndexNow** : à vérifier/activer proprement
- [ ] 🧑 **Google Search Console** (propriété domaine, DNS TXT) — besoin du login Google

### Contenu / taxonomie
- [x] **11 catégories** (× FR/IT via Polylang = 24 termes) + 4 territoires + villes
- [x] Pages **légales · À propos · Annoncer · Proposer un événement** (FR **et** IT)
- [x] Menus (overlay + footer), sélecteur FR|IT
- [~] **Étiquettes** : « Gratuit / En famille / Transfrontalier / massifs » ne sont
  **pas** une taxonomie dédiée ; ce sont aujourd'hui des `post_tag` libres et
  hétérogènes. À structurer si on veut des hubs d'étiquette propres (le filtre
  « Gratuit » est de toute façon reporté tant que la donnée prix n'est pas fiable).

### Gabarits (thème via Code Snippets, rendu hors Boucle)
- [x] Home (FR/IT unifiée) · Fiche événement · Hub catégorie · Hub territoire/ville
  · sous-pages datées `/[ville]/ce-week-end/` · Hub lieu · liste filtrable
  (Ce week-end / Tout l'agenda) · Recherche contextuelle
- [x] Composants : carte événement · carrousel · newsletter · module transfrontalier
  (« Ça vaut le déplacement ») · Ajouter à mon agenda (+ rappels J-7/J-1)
- [x] 🤖 **Gabarit 404 sur-mesure** (snippet 99, 2026-07-26) : vrai code HTTP 404,
  bilingue FR/IT, formulaire de recherche + 4 portes territoires + accueil.
- [x] 🤖 **Bouton Facebook de la fiche** (snippet 56, 2026-07-26) : bouton de
  **suivi** (lien vers la future page FB d'Agenda Sabauda), désactivé pour
  l'instant (`$cs_fb_acc = null`) car la page n'existe pas encore. 🧑 **À
  réactiver dès que la page Facebook sera créée** (renseigner l'URL). Aucun
  bouton de partage FB sur le site (ce n'était pas demandé).

### Pile de build (tranchée — voir docs dédiés)
Décision d'outillage figée (16 juillet), conservée ici pour mémoire :
- **Habillage** (header/footer, couleurs, polices) → **thème enfant GeneratePress**
  + `theme.json`/`tokens.css`.
- **Colonnes / éléments éditoriaux** → **Gutenberg natif** ; **dynamique** (listings,
  hubs) → **JetEngine Blocks + Query Builder** ; **Elementor** actif mais non prioritaire.
- **Pub / bannière / popup pub** → **Ad Inserter** uniquement (consent-gated, Complianz).
- **Popup non-pub** (newsletter/annonce) → Popup Maker.
- Détail : `PILE_BUILD_WORDPRESS.md`, `REGIE_ANNONCEURS.md` (+ scaffold
  `deploy/wordpress/cs-regie.php`), `SELECTIONS_HOME.md` (carrousel de sélections).
- ⚠️ Point ouvert : **Polylang vs WPML** pour le dynamique JetEngine (Crocoblock
  certifié WPML, pas Polylang) — budgéter WPML ~99 €/an seulement si le multilingue
  dynamique devient central.

## 2. Design / maquettes — 🎨🧑 EN COURS (hors périmètre repo)
- [ ] DA finale figée (typo, couleurs) → base du thème enfant
- [ ] Écrans secondaires validés visuellement (le fonctionnel est construit ; reste l'habillage)

## 3. Sécurité & hygiène — 🧑 À FAIRE (important, ne pas oublier)
- [ ] Réinitialiser le **mot de passe FTP OVH** (a transité en clair)
- [ ] Régénérer la **clé API Anthropic** (idem)
- [ ] Supprimer le **mu-plugin orphelin** résiduel s'il existe encore

## 4. Consentement / analytics — 🧑⚙️ À FAIRE
- [ ] Bannière de consentement **IT** (reste FR pour tous) → **Complianz Premium
  (~49 €/an)** = multilingue + Consent Mode v2, seulement quand `/it/` a du trafic
- [ ] Vérifier l'absence de **double-tag GA4** (un seul hit `g/collect`)
- [ ] (option) Décocher le **partage de données** GA4 côté compte + Complianz

## 5. Sourcing de lancement — 🧑 + pipeline
- [ ] **Remplir Annecy + Chambéry** au-dessus du seuil (~8-12 événements) avant
  d'ouvrir d'autres villes (cf. `INTENTIONS_RECHERCHE_SEO`)
- [ ] Produire en continu le format `/[ville]/ce-week-end/` (hebdo)
- [~] Combler les trous (Pilotage) : territoires/catégories vides · **photos** :
  19 FR + 23 IT événements futurs sur image de repli (liste dans
  `PHOTOS_MANQUANTES_EVENEMENTS.md`), sourcing humain
- [x] **Cuisine Nissarde** : page guide « Le Fil » FR **publiée** (post 3648,
  `/cuisine-nissarde-tables-labellisees/`), rattachée Comté de Nice + Gastronomie.
  Reste : [ ] traduire la version IT.

## 6. Pipeline — dettes ouvertes 🤖 (extrait de `BACKLOG.md`)
- [ ] **Dédup multi-sources** (`same_story` → fusion vers la source la plus riche)
- [ ] **Pré-filtre territoire avant le LLM** (radars hors-zone = coût inutile)
- [ ] **`og:image` quand pas de photo** + décider l'alternative « pas de photo »
  (lié au constat 2026-07-26 : les images de repli sont bakeées comme miniatures)
- [ ] `cultura-core` : extraire charte + `utils` partagés

## 7. Post-lancement (leviers de croissance)
- [ ] **Newsletter hebdo** (Brevo — connecteur à autoriser)
- [ ] **Widget embeddable** (levier n°1 : backlinks + distribution)
- [ ] **Backlinks locaux** (OT + presse : Le Dauphiné, La Stampa)
- [ ] Looker Studio (GSC + GA4) quand il y a du trafic
- [ ] Filtre **« Gratuit »** (quand la donnée prix est fiable)
- [ ] Comptes **Instagram** Piémont / VdA / Nice (le code les branche dès qu'ils existent)
- [ ] Google Discover / GEO (socle déjà en place : schema, grandes photos, titres datés)

## 8. Décisions stratégiques encore ouvertes — 🧑
- [ ] **Ambition** : actif de marque **ou** business autonome ? (conditionne l'effort)
- [ ] Recalibrage du **seuil de score ≥ 7** (routage CS/AS)
- [ ] **Enrichissement en cron** (auto) ? seuil ? auto-publication ? kill-switch coût
- [ ] Autoriser le connecteur **Brevo**

---

### Le chemin critique restant
Le socle fonctionnel du site est **construit et en ligne**. Le chemin critique
n'est plus « construire le site » mais : 🎨 **figer la DA** → 🧑 **remplir
Annecy + Chambéry** au seuil → 🧑 **hygiène sécurité** → **ouverture publique**
→ leviers de croissance (newsletter, widget, backlinks).
