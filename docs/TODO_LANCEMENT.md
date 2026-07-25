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
- [ ] 🤖 **Gabarit 404 sur-mesure** — **confirmé absent** (aucun handler `is_404`).
  Recherche + portes principales, pour ne pas être un cul-de-sac.
- [ ] 🤖 **Bouton Facebook de la fiche** : lien mort `href="#"`. À masquer tant
  qu'aucun compte n'existe (même traitement qu'Instagram), réapparition auto le
  jour où un compte FB est fourni.

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
- [ ] 🧑 **Cuisine Nissarde** : décider la forme (reco : page guide « Le Fil »,
  prête dans `CUISINE_NISSARDE_PAGE_GUIDE.md`) + trancher le décompte 29 vs 30

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
Annecy + Chambéry** au seuil → **404 + hygiène sécurité** → **ouverture publique**
→ leviers de croissance (newsletter, widget, backlinks).
