# Feuille de route de lancement — Agenda Sabauda (master TODO)

*Vue unique de tout ce qui reste. Le détail vit dans les docs référencés. Légende :
[x] fait · [ ] à faire · 🤖 moi (Claude Code, dans le repo) · 🧑 Franck · 🎨 Claude Design ·
⚙️ config manuelle wp-admin (ou Claude-in-Chrome).*

---

## 0. Backoffice & stratégie — ✅ FAIT
- [x] Filtres périmètre (hors-zone/Avignon) + rejet des événements **passés** (`evaluator`, `sources`)
- [x] Dashboard : onglet Actifs · tri qualité · filtre hors-radar · vocabulaire unifié
- [x] **SEO backoffice** (JSON-LD déterministe + agent SEO à la demande) + export WordPress (Yoast/OG)
- [x] Sourcing géo-scopé (Le Dauphiné → flux Savoie/Haute-Savoie)
- [x] Sauvegarde base (`backup_db.py`) + publisher dédup
- [x] Onglet **Pilotage** (santé éditoriale) + **Conseiller** (« ce que Franck doit faire ») + **aperçu des modules de la home**
- [x] Renommage marque **Agenda Sabauda** (féminin IT)
- [x] mu-plugins (territoire, noindex vues techniques, seo-meta), `robots.txt`, runbook, **décisions de build figées**
- [x] Suite documentaire (stratégie, décisions écartées, critique red-team, règles SEO/GEO/AEO, guide indexation, taxonomie, marketing/pilotage, proximité transfrontalière, intentions de recherche, templates, page pub)

## 1. Design / maquettes — 🎨🧑 EN COURS
- [ ] **Home mobile** finalisée (corrections actées : pub gardée · bandeau territoire retiré · lisibilité police · bandeau noir repurposé « Tout l'agenda du week-end » · Gratuit retiré · tuiles Gastronomie/En famille · Météo retirée)
- [ ] Écrans secondaires (prompts fournis) : fiche · hub catégorie · hub territoire (+ module transfrontalier « Y aller ») · hub lieu · liste filtrable · recherche · Proposer un événement · 404 · le fil/article · **Annoncer**
- [ ] Figer la **DA finale** (typo, couleurs) → base du thème enfant

## 📅 À revoir la semaine prochaine (~20 juillet 2026)

**Fait le 14-15 juillet** (contexte) : Polylang **langue + liage FR/IT** en prod (mu-plugin
`cs-polylang.php`) · **taxonomies bilingues** déployées (`cs-taxo-it.php`) · **GA4** propre
(`G-HWRKPM4F7J`, injecté par Complianz, consent-gated) · **consentement RGPD** conforme via
**Complianz** (opt-in, 3 boutons, blocage AdSense avant consentement) — **bannière en français**.

À trancher / faire la semaine prochaine :
- [ ] 🧑 **Construire le contenu italien** (traduire **pages + menu** via Polylang) — aujourd'hui
  `/it/` est vide (« Non è stato trovato nulla »). *C'est le vrai préalable : la bannière IT ne
  sert à rien tant que le site IT n'existe pas.* → chantier **WordPress local**.
- [ ] **Bannière de consentement multilingue IT** — reste **en français pour tous** en attendant.
  Le multilingue est **payant** dans Complianz **et** CookieYes (gating inversé). Quand `/it/` aura
  du vrai contenu + des visiteurs → **Complianz Premium (~49 €/an)** = multilingue **+** Consent
  Mode v2 d'un coup (6× moins cher que CookieYes Pro). **Pas avant.**
- [ ] Vérif **double-tag GA4** : après consentement, un **seul** hit `g/collect` avec
  `G-HWRKPM4F7J` (GTM/gtag détectés à côté d'AdSense — s'assurer qu'aucune autre source ne pose GA).
- [ ] (optionnel, confidentialité) décocher le **partage de données** GA4 (« Produits et services
  Google »…) côté compte, puis cocher la case correspondante dans Complianz.
- [ ] 🧑 **Hygiène sécurité** (suite à la soirée) : réinitialiser le **mot de passe FTP** OVH et
  **régénérer la clé API Anthropic** (toutes deux ont transité en clair) ; supprimer le mu-plugin
  orphelin dans `www/wp-content/mu-plugins/`.
- [ ] 🧑 Programmer la **tâche récurrente Cowork** (prompt rangé : back-office → Aide → Cowork).

## 2. WordPress — construction
### 2a. Config admin ⚙️ (runbook `deploy/agenda-sabaudo/INSTALL_RUNBOOK.md`)
- [ ] Domaine **agendasabauda.eu** + HTTPS
- [ ] Installer **The Events Calendar + RankMath + Polylang**
- [ ] Permaliens + slugs (`evenement`/`evenements`/`luoghi`/`territoire`)
- [ ] RankMath : **IndexNow ON**, Instant Indexing Google **OFF**, sitemaps, **une seule source de schema**
- [ ] Polylang FR/IT + **hreflang**
- [ ] `robots.txt` + **GSC** (DNS) + sitemap + **GA4** (ou Matomo)
### 2b. Contenu / taxonomie 🤖 seeding + ⚙️
- [ ] **11 catégories** (mu-plugin de seeding — *je peux l'écrire maintenant*)
- [ ] 4 territoires + villes (`as-territoire-taxo.php` — fait, à déployer)
- [ ] Étiquettes : Gratuit · En famille · Transfrontalier · **massifs** (Bauges, Aravis… `noindex`)
- [ ] Pages : **légales** (contenu prêt `docs/legal/`) · À propos · **Annoncer** (contenu prêt) · Proposer un événement
- [ ] Menus (overlay + footer)
### 2c. Thème enfant / templates 🤖 (quand maquettes figées)
- [ ] Home · Fiche (mode minimal) · Hub catégorie · **Hub territoire** · Hub lieu · **liste filtrable** (Ce week-end + Tout l'agenda) · **`/[ville]/ce-week-end/`** daté · Recherche · 404
- [ ] Composants : carte événement · carrousel · newsletter · **module transfrontalier** · emplacements pub
- [ ] Copier `cs-seo-meta.php` + `cs-rest-auth.php` sur l'hôte WP

### 🔧 Outillage de build — tranché (16 juillet)
Question : « **Ad Inserter** suffit-il pour tout (habillage, bannière, colonnes,
éléments de page, popup) ? » → **Non.** Ad Inserter est un **injecteur de code** :
bon **uniquement pour la couche publicité** (emplacements partenaires/AdSense,
sticky mobile, popup **pub**), avec respect du consentement (Complianz déjà en
place). Il ne fait ni thème, ni colonnes, ni contenu — l'y forcer casse Polylang,
l'édition non-dev et l'objectif « parties éditables en **Gutenberg natif** ».
- **Habillage entier** (header/footer, couleurs, polices) → **thème enfant**
  GeneratePress + `theme.json` / `tokens.css` (design system `implementation/`).
- **Colonnes / éléments de page** → **Gutenberg natif** (+ **JetEngine Blocks**
  pour le dynamique : listings d'événements, hubs). **Préférence Gutenberg natif** (perfs/portabilité) ; **Elementor non proscrit** (il est actif sur le site).
- **Pub / bannière / popup pub** → **Ad Inserter** (le garder pour ça, rien d'autre).
  Mise en place détaillée : **`docs/REGIE_ANNONCEURS.md`** (tableau format→mécanisme,
  recette Ad Inserter, choix des encarts, skin ON/OFF) + scaffold thème
  **`deploy/wordpress/cs-regie.php`** (skin + gouttières, consent-gated, desktop only).
- **Popup non-pub** (newsletter, annonce) → à décider (cf. recherche ci-dessous).
- [x] **Pile de build tranchée** → voir **`docs/PILE_BUILD_WORDPRESS.md`** (recherche
  2026 sourcée). Résumé : GeneratePress Child **classique** (pas FSE) · éditorial en
  **blocs core** (Polylang) · dynamique en **JetEngine Blocks + Query Builder** ·
  éditabilité IA via **MCP JetEngine / Novamira** · pub **Ad Inserter** · popup non-pub
  **Popup Maker**. **⚠️ Point à trancher : Polylang vs WPML pour le dynamique JetEngine**
  (Crocoblock est certifié WPML, pas Polylang → garder JetEngine au dynamique « à faibles
  libellés » au lancement, budgéter WPML ~99 €/an seulement si le multilingue dynamique
  devient central).

## 3. Pont backoffice → WordPress 🤖 (après création du site)
- [ ] **2ᵉ publisher** : export vers Agenda Sabauda (nécessite URL + credentials du site)
- [ ] **Routage** : score ≥ 7 → Cultura Sabauda · < 7 → Agenda Sabauda (un site par événement, pas de canonical croisé)
- [ ] Export complet : featured media + catégorie/territoire/lieu/étiquettes + meta Yoast
- [ ] Hébergement des **photos de dossiers de presse** (upload média WP)

## 4. Sourcing de lancement 🧑 + pipeline
- [ ] **Remplir Annecy + Chambéry** au-dessus du seuil (~8-12 événements) **avant** d'ouvrir d'autres villes (cf. `INTENTIONS_RECHERCHE_SEO`)
- [ ] Produire le format prioritaire **`/[ville]/ce-week-end/`** (daté, hebdo)
- [ ] Combler les trous (onglet Pilotage) : territoires vides · catégories vides · photos manquantes

## 5. Post-lancement (leviers de croissance)
- [ ] **Newsletter hebdo** (Brevo — connecteur à autoriser)
- [ ] **Widget embeddable** (levier n°1 : backlinks + distribution)
- [ ] **Backlinks locaux** (OT + presse : Le Dauphiné, La Stampa)
- [ ] Looker Studio (GSC + GA4) quand il y a du trafic
- [ ] Filtre **« Gratuit »** (quand la donnée prix est fiable)
- [ ] Module transfrontalier **« Ça vaut le déplacement »** actif (dès qu'un voisin est sourcé)
- [ ] Google Discover / GEO (socle déjà en place : schema, grandes photos, titres datés)

## 6. Déploiement / exploitation ⚙️
- [ ] `bash deploy/update.sh` sur le VPS (tire Pilotage + renommage + seeding)
- [ ] `crontab crontab.txt` (sauvegarde + collectes)
- [ ] Vraie URL `agenda.culturasabauda.eu` (DNS + Traefik) au lieu de sslip.io

## 7. Pipeline — dettes ouvertes 🤖 (extrait de `BACKLOG.md`)
- [ ] **Dédup multi-sources** (`same_story` → fusion vers la source la plus riche/autoritaire)
- [ ] **Pré-filtre territoire avant le LLM** (radars Google News hors-zone = coût inutile)
- [ ] `og:image` quand pas de photo + décider l'alternative « pas de photo »
- [ ] `cultura-core` : extraire charte + `utils` partagés

## 8. Décisions encore ouvertes 🧑 (elles conditionnent le reste)
- [ ] **Ambition** : Agenda Sabauda = actif de marque de Cultura Sabauda **ou** business autonome ? (conditionne tout l'effort)
- [ ] **Recalibrage du seuil de score ≥ 7** (routage CS/AS)
- [ ] **Enrichissement en cron** (auto) ? seuil ? auto-publication du site de volume ? kill-switch coût
- [ ] **Autoriser le connecteur Brevo** (newsletter)

---

### Le chemin critique (l'ordre qui débloque le reste)
**Maquettes figées** → 🤖 **thème enfant** (2c) ∥ ⚙️ **config admin** (2a) → 🤖 **seeding taxo/pages** (2b) → 🤖 **2ᵉ publisher** (3) → 🧑 **remplir Annecy+Chambéry** (4) → **ouverture** → leviers (5).
Tout le reste (7, une partie de 5) est parallélisable après.
