# INSTALL RUNBOOK — Agenda Sabaudo (site public)

Checklist pas-à-pas pour la mise en place de ce soir. Ordonné. Cocher au fur et à mesure.
Domaine cible : **agendasabaudo.eu** (à réserver s'il ne l'est pas — cf. plan du site §6).
Socle validé : The Events Calendar (CPT `tribe_events`) + RankMath + Polylang.

> Règles à NE PAS contredire : le temps n'est jamais une taxonomie · IndexNow ON /
> Instant Indexing Google OFF · noindex des vues techniques TEC · robots.txt autorise
> les crawlers IA · une seule source de schema Event.

---

## 0. Pré-requis (avant de commencer)

- [ ] Domaine `agendasabaudo.eu` pointé sur l'hébergement, HTTPS actif (certificat OK).
- [ ] WordPress installé, à jour, thème de base choisi.
- [ ] Accès admin + accès FTP/SFTP (ou gestionnaire de fichiers) à `wp-content/`.
- [ ] Réglages → Permaliens = « Titre de la publication » (`/%postname%/`) — PAS « simple ».

---

## 1. Installer les extensions

- [ ] **The Events Calendar** (gratuit) — Extensions → Ajouter → activer.
- [ ] **RankMath SEO** — installer, activer, lancer l'assistant :
  - [ ] Mode « Avancé », se connecter au compte RankMath.
  - [ ] **Désactiver le module « Schema » de RankMath sur les événements** OU désactiver
        le schema de TEC — **une seule source de schema Event** (jamais les deux → double markup).
        Reco : garder le schema `Event` de TEC (auto), désactiver le schema de RankMath sur `tribe_events`.
- [ ] **Polylang** (gratuit ou Pro) — installer, activer (config langues à l'étape 6).

---

## 2. Réglages RankMath (indexation)

- [ ] **IndexNow : ON** — RankMath → Modules → activer « IndexNow » (soumission auto Bing/Yandex/Copilot).
- [ ] **Instant Indexing (Google) : OFF** — ne PAS configurer/activer le module « Instant Indexing »
      Google (son API est réservée à JobPosting/BroadcastEvent — hors périmètre, risque de révocation).
- [ ] **Sitemaps : ON** — RankMath → Sitemap Settings :
  - [ ] Activer le sitemap XML (URL : `https://agendasabaudo.eu/sitemap_index.xml`).
  - [ ] Inclure le CPT **Événements** (`tribe_events`) et les taxonomies **catégories** + **territoire**.
  - [ ] Exclure les fiches passées / vues techniques du sitemap.
- [ ] **Titres & Meta** : suffixe de marque « — Agenda Sabaudo » ; templates title/meta par gabarit
      (cf. REGLES_SEO §1.1).
- [ ] **noindex** des vues techniques : géré par le mu-plugin `as-noindex-tech-views.php` (étape 4) —
      vérifier après coup qu'une URL `?eventDisplay=week` sort bien en `noindex`.

---

## 3. Réglages des slugs d'URL

**The Events Calendar** → Réglages → Événements → onglet **URLs** :

- [ ] Slug d'un événement (singulier) : **`evenement`**  → `/fr/evenement/{slug}/`
- [ ] Base d'archive des événements : **`evenements`**  → `/fr/evenements/{cat}/`
- [ ] Slug des lieux (Venues) : **`luoghi`**  → `/luoghi/{lieu}/` (repris de GuidaTorino)

**Taxonomie territoire** (mu-plugin, étape 4) :

- [ ] Slug de réécriture : **`territoire`**  → `/territoire/{terr}/` et `/territoire/{terr}/{ville}/`

**Après tout changement de slug** :

- [ ] Réglages → Permaliens → **Enregistrer** (purge des règles de réécriture, sinon 404).
- [ ] Vérifier à la main : ouvrir un événement, un hub catégorie, `/territoire/piemont/`, une page lieu.

> Note : le préfixe de langue `/fr/`, `/it/` est ajouté par Polylang (étape 6), pas par ces slugs.

---

## 4. Déposer les mu-plugins

Copier dans **`wp-content/mu-plugins/`** (créer le dossier s'il n'existe pas ; les must-use
plugins s'activent seuls) :

- [ ] `as-territoire-taxo.php` — taxonomie « territoire » + amorce des 4 territoires & villes.
- [ ] `as-noindex-tech-views.php` — noindex des vues techniques TEC.
- [ ] (déjà en place si backoffice branché : `cs-rest-auth.php`, `cs-seo-meta.php`.)
- [ ] Réglages → Permaliens → **Enregistrer** (pour activer la réécriture `/territoire/`).
- [ ] Vérifier : Événements → **Territoires** liste bien les 4 territoires + villes enfants.

---

## 5. Créer les 11 catégories

Événements → **Catégories** — créer les 11 (noms + slugs **exacts**, voir `categories.md`) :

- [ ] `expositions-patrimoine` — Expositions & Patrimoine
- [ ] `concerts-musique` — Concerts & Musique
- [ ] `spectacle-vivant` — Spectacle vivant
- [ ] `festivals` — Festivals
- [ ] `gastronomie-sagre` — Gastronomie & Sagre
- [ ] `marches-foires` — Marchés & Foires
- [ ] `sport` — Sport
- [ ] `cinema` — Cinéma
- [ ] `jeune-public-famille` — Jeune public & Famille
- [ ] `conferences-rencontres` — Conférences & Rencontres
- [ ] `fetes-traditions` — Fêtes & Traditions populaires

> Rappel : « Gratuit » = étiquette + booléen, pas une catégorie. Le temps = hubs evergreen, jamais une taxo.

---

## 6. Bilingue FR/IT (Polylang) + hreflang

- [ ] Langues → ajouter **Français** (langue par défaut) et **Italien**.
- [ ] Réglages Polylang → URL modifiée : **répertoire de langue** (`/fr/`, `/it/`),
      masquer le code pour la langue par défaut = **NON** (on veut `/fr/` explicite, cf. plan du site).
- [ ] Cocher la **traduction du CPT `tribe_events`** et des **taxonomies** (catégories, territoire, lieux).
- [ ] Traduire les **termes** : les 11 catégories (libellés IT dans `categories.md`), les 4 territoires,
      les villes. Les **noms de lieux ne se traduisent pas** (Château de Chambéry reste tel quel).
- [ ] Traduire les **slugs** des hubs (`/it/questo-weekend/`, `/it/evento/…`).
- [ ] **hreflang** : Polylang émet les balises automatiquement. Vérifier que chaque page
      s'auto-référence + pointe sa jumelle + `x-default`. Une fiche non traduite n'émet PAS
      de hreflang vers une page inexistante.
- [ ] Vérifier : dans le `<head>` d'une fiche FR traduite, présence de `hreflang="fr"`,
      `hreflang="it"`, `hreflang="x-default"`.

---

## 7. robots.txt

- [ ] Déposer `robots.txt` à la **racine** du site (ou, si RankMath sert un robots.txt virtuel :
      RankMath → Réglages généraux → **Modifier robots.txt** et y recopier les blocs).
- [ ] Vérifier `https://agendasabaudo.eu/robots.txt` : Sitemap référencé, GPTBot / PerplexityBot /
      Google-Extended autorisés, Disallow des vues techniques TEC présents.
- [ ] Test : une URL `?eventDisplay=week` doit être Disallow ; une fiche doit être Allow.

---

## 8. Google Search Console + sitemap

- [ ] Ajouter la propriété **Domaine** `agendasabaudo.eu` (vérif DNS TXT) — couvre `/fr/` et `/it/`
      d'un coup. (Alternative : 2 propriétés préfixe-URL `.../fr/` et `.../it/` si tu veux des
      rapports séparés par langue — cf. REGLES_SEO §6.)
- [ ] **Soumettre le sitemap** : Sitemaps → ajouter `sitemap_index.xml`.
- [ ] Vérifier le rapport **Couverture** (aucune erreur bloquante) et, plus tard, le rapport **Événements**.
- [ ] (Optionnel) Bing Webmaster Tools + clé IndexNow (RankMath la gère).

---

## 9. Analytics

- [ ] Installer un outil de mesure — au choix :
  - **GA4** : créer une propriété, insérer le tag (via RankMath → Analytics, ou plugin de tag,
    ou header) ; activer le consentement cookies (bannière RGPD).
  - **Matomo** (auto-hébergé, plus souple RGPD) : installer, ajouter le site, poser le tracker.
- [ ] Vérifier la réception des premières visites (temps réel).
- [ ] Prévoir le suivi du **trafic référent depuis les moteurs IA** (mesure GEO, cf. REGLES_SEO §6).

---

## 10. Validation finale (avant d'annoncer)

- [ ] Une **fiche événement** : schema `Event` valide au **Rich Results Test** (une seule source).
- [ ] Un **hub catégorie** et `/territoire/piemont/` s'affichent, sont indexables (pas de noindex).
- [ ] Vues techniques TEC (`/week/`, `?eventDisplay=photo`) sortent en **noindex** + Disallow robots.
- [ ] hreflang FR↔IT vérifié sur une paire traduite.
- [ ] Sitemap accessible, soumis en GSC.
- [ ] IndexNow ON confirmé ; Instant Indexing Google confirmé OFF.
- [ ] Analytics reçoit les visites.

---

### Ordre de dépendance (résumé)

1 Extensions → 2 RankMath → 3 Slugs → 4 mu-plugins (+ permaliens) → 5 Catégories →
6 Polylang/hreflang → 7 robots.txt → 8 GSC/sitemap → 9 Analytics → 10 Validation.
