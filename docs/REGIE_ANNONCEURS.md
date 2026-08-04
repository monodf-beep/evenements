# Régie publicitaire — mise en place sur WordPress (Kit Annonceurs)

*Traduction du « Kit Annonceurs » (design system → `Agenda Sabaudo - Kit Annonceurs.dc.html`)
en mécanismes WordPress concrets. Couche PUB uniquement — séparée de l'éditorial.
Rappel décision : **Ad Inserter** = couche pub ; habillage/colonnes = thème + Gutenberg
(voir `PILE_BUILD_WORDPRESS.md`). Consentement déjà géré par **Complianz** (cookie
`cmplz_marketing`).*

---

## Principe : 2 familles d'emplacements

| Famille | Vit… | Outil | Pourquoi |
|---|---|---|---|
| **Dans le flux** (leaderboard, pavés, bandeau sticky bas) | à l'intérieur de la colonne de contenu | **Ad Inserter** (bloc + position + appareil + consentement) | c'est exactement son métier : injecter à un hook précis |
| **Hors flux** (habillage/skin, gouttières skyscrapers) | dans les marges, en `position:fixed` | **code thème** (mu-plugin `cs-regie.php`) | Ad Inserter *gratuit* positionne mal le fond de page et les rails latéraux |

**Pas besoin de plugin de grille.** La « grille » = largeur de contenu centrée du thème + CSS.

---

## Tableau de correspondance — format → mécanisme

| Format (kit) | Dim. | Appareil | Où / comment le poser | Consentement |
|---|---|---|---|---|
| **Habillage / Skin** | 1920×1080 | Desktop **seul** | `cs-regie.php` → fond fixe derrière le contenu, **ON/OFF** (voir §Skin) | oui (masqué sans consentement) |
| **Gouttière gauche** (skyscraper) | 160×600 | Desktop **seul** | `cs-regie.php` → rail fixe sticky, marge gauche | oui |
| **Gouttière droite** (half-page) | 300×600 | Desktop **seul** | `cs-regie.php` → rail fixe sticky, marge droite | oui |
| **Leaderboard** | 970×90 / 728×90 · 350×90 mobile | D + M | Ad Inserter · position **« After element » = header/nav** (ou hook `generate_after_header`) · 2 blocs (viewport desktop / mobile) | oui |
| **Pavé in-list** (home) | 300×250 · 350×292 mobile | D + M | Ad Inserter · position **« Between posts » N** sur la liste — ⚠️ si la liste est un **JetEngine Listing Grid**, injecter via un hook JetEngine plutôt que la boucle WP | oui |
| **Pavé in-article** | 300×250 / 336×280 | D + M | Ad Inserter · position **« Before/After paragraph N »** dans le contenu single | oui |
| **Bandeau bas d'écran** (sticky, fermable) | 970×90 · vignette mobile | D + M | Ad Inserter · **Sticky footer** natif (bouton fermeture inclus) | oui |
| **Mise en avant événement partenaire** (slot 1) | carte 3:2 | D + M | **PAS de la pub display** → champ « sponsorisé » sur l'événement (CPT/JetEngine), épinglé position 1 + badge « Partenaire ». Backoffice/query, pas Ad Inserter | non (contenu) |
| **Article partenaire / contenu partenaire** | 3–6k sig · couv 3:2 | D + M | **Éditorial natif** → post normal avec label « Contenu partenaire » (catégorie ou meta) | non (contenu) |
| **Newsletter** | 560×240 | — | Hors site (Brevo) — spec créative seulement | — |
| **Réseaux sociaux** | 1080² / 1200×627 | — | Hors site — spec créative seulement | — |

> **Point important :** deux « formats » du kit ne sont **pas** de la pub display et ne
> passent **pas** par Ad Inserter : la *mise en avant événement partenaire* (un événement
> sponsorisé épinglé + badge, géré côté données) et l'*article partenaire* (un vrai
> article étiqueté « Contenu partenaire »). Les traiter comme de la pub casserait le SEO
> et la traduction.

---

## Comment poser un encart Ad Inserter (recette, une fois)
1. **Extensions → Ad Inserter → un Block libre** (1 à 16).
2. **Coller la créative** : soit `<a href="…"><img src="…" width=970 height=90 alt="Publicité — …"></a>`, soit le code AdSense.
3. Onglet **Insertion** : choisir la **position** (Before/After content, Between posts, Before/After paragraph, Footer sticky…).
4. Onglet **Devices** : cocher **Desktop** et/ou **Mobile** (largeurs).
5. Onglet **Misc / Consent** : activer le **gating Complianz** (catégorie *marketing*, cookie `cmplz_marketing=allow`). Sur hébergement avec cache (OVH) → régler l'insertion en **client-side** pour lire le cookie.
6. **Toujours** encadrer par le libellé « Publicité » ou « Partenaire » (déjà prévu dans le design).

## Comment CHOISIR les types d'encart (ne pas tout allumer)
Ordre recommandé, du plus rentable/moins intrusif au plus premium :
1. **Leaderboard** (haut) + **1 pavé in-article** + **bandeau sticky bas** → socle, desktop + mobile. Suffisant au lancement.
2. **Pavé in-list** sur la home → quand la liste est bien remplie.
3. **Gouttières** (skyscrapers) → **desktop seulement**, quand tu as des annonceurs « semaine ».
4. **Habillage / Skin** → **desktop seulement**, format premium « 1 annonceur/jour », à activer **à la demande** (voir §Skin).

Règles de choix :
- **Densité** : pas plus de ~3 emplacements pub visibles simultanément par écran (UX + politique AdSense).
- **Appareil** : skin & gouttières = **desktop only** ; leaderboard/pavé/sticky = D + M.
- **Contexte** : couper la pub sur pages légales / « Annoncer » / 404.

---

## §Skin — activation, désactivation, circonstances

La skin est **désactivable** et livrée **OFF par défaut**. Elle est pilotée par une option
`cs_regie[skin_active]` (0/1) dans `cs-regie.php`.

**Comment l'activer / la couper :**
- Un seul interrupteur (réglage ou constante). `0` → le site reprend son fond beige normal, aucune trace.
- Prévu pour être piloté à la journée (format « 1 annonceur/jour »), à terme depuis le back-office.

**Circonstances où la skin est (ou doit être) désactivée :**
1. **Aucun annonceur réservé** ce jour-là → OFF (défaut).
2. **Mobile** → **jamais** de skin (le code la masque sous 1280 px).
3. **Consentement pub non donné** → masquée automatiquement jusqu'à l'acceptation (Complianz).
4. **Pages sensibles** (légales, « Annoncer », 404, checkout éventuel) → OFF.
5. **Gros temps fort éditorial** (une Une importante) → tu peux vouloir la couper pour ne pas parasiter.
6. **Kill-switch global** `cs_regie[enabled]=0` → coupe skin **et** gouttières d'un coup.

---

## Ce que couvre `deploy/wordpress/cs-regie.php`
Les 3 emplacements **hors flux** qu'Ad Inserter gère mal en version gratuite :
- **Skin** desktop (fond fixe cliquable, ON/OFF, consent-gated) ;
- **Gouttières** gauche/droite (rails fixes sticky, desktop only, consent-gated) ;
- (option) **bandeau sticky bas** si tu préfères le gérer côté thème plutôt qu'Ad Inserter.

Tout le reste (leaderboard, pavés in-list / in-article, sticky bas) = **blocs Ad Inserter**
configurés en wp-admin selon le tableau ci-dessus.

Depuis la version 0.2, les créatives skin/gouttières ne sont **plus** une option WP
statique : elles viennent du back-office (`utils/ads.py`, page `/ads`), via le même
`{backoffice}/api/active-ads` que `cs-regie-serve.php` (slots `"skin"`, `"left"`,
`"right"`, en plus du `"3"` déjà servi pour le bandeau bas). `cs_regie[enabled]` reste
un kill-switch WP local, toujours OFF par défaut, qui coupe tout indépendamment de ce
que le back-office propose. Voir `docs/REGIE_MISE_EN_PLACE_SOCLE.md` pour le statut de
déploiement réel (ce fichier n'était, à la connaissance de ce dépôt, jamais allé en
production avant cette version).
