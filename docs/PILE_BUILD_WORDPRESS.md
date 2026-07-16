# Pile de build WordPress — Agenda Sabauda (recherche 2026)

*Recherche approfondie multi-sources (6 angles, 28 sources, 25 affirmations vérifiées
en 3 votes contradictoires, 0 réfutée — 16 juillet 2026). Contexte : GeneratePress
Child (sans GP Premium ni GenerateBlocks), JetEngine/Crocoblock déjà possédé, Polylang
FR/IT, The Events Calendar, OVH mutualisé (PHP 8.0), règle « jamais d'Elementor »,
objectif = parties éditables en Gutenberg natif + PHP, modifiables par IA.*

---

## TL;DR — la pile recommandée, de bout en bout

| Couche | Choix | Coût |
|---|---|---|
| **Thème / habillage** | **GeneratePress Child classique** (templates PHP + hooks) + `theme.json`/`tokens.css` du design system. **Pas de bascule FSE.** | 0 (déjà là) |
| **Contenu éditorial** (pages, colonnes, textes) | **Gutenberg natif** (blocs core) — le mieux géré par Polylang | 0 |
| **Éléments dynamiques** (listings, hubs) | **JetEngine Blocks** (natif Gutenberg, sans Elementor) | 0 (déjà possédé) |
| **Listings d'événements** | **JetEngine Query Builder + Listing Grid** (Tax/Meta/Date Query) | 0 |
| **Éditabilité IA** | **JetEngine MCP Server** (intégré depuis 3.8) et/ou **Novamira** | 0 |
| **Publicité / bannière** | **Ad Inserter** (+ Complianz, déjà en place) | gratuit (Pro pour auto-reload) |
| **Popup non-pub** (newsletter, annonce) | **Popup Maker** (gratuit, Polylang-neutre) *ou* JetPopup (possédé, mais WPML) | 0 |
| **Multilingue** | Polylang pour l'éditorial ✅ · **point à trancher** pour le dynamique (voir §6) | — |

---

## 1. Habillage / thème → rester en GeneratePress Child classique

**Verdict : ne PAS passer en Full Site Editing. Le plan avait raison.**

- GeneratePress **refuse explicitement** de devenir un *block theme* core / FSE natif :
  c'est un thème **traditionnel** (templates PHP + hooks), qui **ne donne pas accès au
  Site Editor**. Son « FSE » à lui se construit autour de **GenerateBlocks** — que tu
  n'as pas. *(source primaire GeneratePress)*
- The Events Calendar n'a qu'un **support FSE partiel, livré par phases** — et surtout
  **ne couvre PAS les templates de catégorie ni de tag d'événement**… c'est-à-dire
  **précisément nos hubs** (catégorie / territoire). Le Site Editor de TEC exigerait de
  toute façon un block theme (Kadence, Twenty Twenty-Four). *(KB officielle TEC)*

➡️ **Conséquence** : l'habillage et les hubs se font en **PHP (thème enfant) + JetEngine**,
pas via le Site Editor. C'est aligné avec ton objectif « éditable en PHP » et le
`theme.json`/`tokens.css` déjà présents dans le design system.

## 2. Pages / colonnes / éléments → Gutenberg natif + JetEngine Blocks

- **JetEngine est officiellement compatible Gutenberg** (sans Elementor) et fournit
  10+ blocs dynamiques (Dynamic Field/Image, Listing Grid, Map, Calendar…). *(Crocoblock)*
- **Pas besoin** de Kadence / Spectra / Otter / Bricks : tu possèdes déjà JetEngine
  (coût nul), et ajouter une bibliothèque concurrente alourdirait sans bénéfice.
- **Règle de séparation** : contenu **éditorial statique** = blocs **core** (meilleure
  compat Polylang) ; **dynamique** = **JetEngine Blocks**. On ne mélange pas.

## 3. Éditabilité IA → JetEngine embarque son propre MCP Server

- Depuis **JetEngine 3.8** (2025), un **MCP Server for WordPress** intégré exécute des
  commandes depuis des prompts : il crée automatiquement queries, meta boxes, CCT, CPT,
  listings, et **scanne le site pour créer les structures manquantes**. *(Crocoblock)*
- C'est **exactement** l'objectif « site modifiable par une IA » — sans coût, et en plus
  de Novamira (qui, lui, tourne aussi sur le serveur et expose WP aux agents).
- ⚠️ *Question ouverte* : JetEngine MCP et Novamira coexistent-ils, ou faut-il choisir
  un canal ? Le MCP JetEngine couvre surtout **les structures JetEngine**, pas forcément
  l'édition de contenu éditorial en blocs core. → à tester.

## 4. Listings d'événements → JetEngine Query Builder (pas les onglets legacy)

- Utiliser le **Query Builder + Custom Query + Listing Grid** (workflow moderne).
  Crocoblock **déprécie** les anciens onglets (Posts/Terms Query). *(KB Crocoblock)*
- Le Listing Grid gère **Tax Query** (par term ID/slug, opérateurs IN/NOT IN/AND…),
  **Meta Query** et **Date Query** → de quoi bâtir « Ce week-end », les hubs
  catégorie/territoire/lieu et `/[ville]/ce-week-end/`.
- Recette « Ce week-end » : stocker la date en **timestamp**, filtrer via **Meta Query
  Numeric** ; la macro **`%current_terms%`** donne le contexte territoire/catégorie.
- Préférable aux vues natives TEC pour des **hubs multicritères** et pour l'éditabilité IA.

## 5. Publicité → Ad Inserter reste le bon choix (avec une nuance)

- **Ad Inserter s'intègre nativement à Complianz** : affichage pub **conditionné au
  consentement** (gating sur `cmplz_marketing=allow` / TCF v2). *(Complianz + Ad Inserter)*
- ⚠️ **Nuance** : le **rechargement automatique** des pubs après consentement (« Manual
  loading = Auto ») nécessite **Ad Inserter Pro** (payant). En gratuit, il faut câbler
  `ai_load_blocks()` en JS. Avec du cache (OVH), régler les blocs en **insertion
  client-side** pour lire le cookie.
- Alternative crédible : **Advanced Ads** (intègre Complianz 7.x + Cookiebot/CookieYes…),
  mais le consent gating avancé y est **aussi** en version Pro. → **Reste sur Ad Inserter**,
  plus léger et déjà envisagé.

## 6. Popup non-pub → Popup Maker (recommandé) ou JetPopup

- **JetPopup** : déjà inclus dans ton abonnement Crocoblock (coût nul), **natif Gutenberg**
  sans Elementor — mais sa localisation officielle est **WPML**, pas Polylang.
- **Popup Maker** : **gratuit**, **Gutenberg par défaut depuis 1.21**, couvre newsletter /
  annonces / exit-intent, et **plus neutre vis-à-vis de Polylang**.
- ➡️ **Reco** : **Popup Maker** si tu veux des popups traduits proprement en Polylang ;
  JetPopup seulement si tu restes tout-WPML.

---

## ⚠️ LE POINT SENSIBLE DU DOSSIER — Polylang vs WPML

C'est **la** tension à connaître avant de bâtir :

- **Tout l'écosystème Crocoblock (JetEngine, JetPopup) est certifié/documenté pour WPML,
  jamais pour Polylang.** JetEngine est « fully compatible with WPML » (testé v3.8.4 le
  26/02/2026) ; la **seule** méthode multilingue documentée par Crocoblock est **WPML**
  (package Multilingual CMS ~**99 $/an**). Polylang n'est **jamais cité**, et des bugs de
  rendu JetEngine+Polylang sont connus (issue GitHub #7591). *(WPML.org + Crocoblock)*

**Ce que ça implique concrètement pour nous :**
- Le **contenu éditorial en blocs core** (pages, textes) se traduit **très bien avec
  Polylang** → on garde Polylang pour tout l'éditorial. ✅
- Les **structures JetEngine** (listings, CCT, glossaires, popups) ne sont **pas
  officiellement couvertes par Polylang**. Deux stratégies :
  1. **Limiter JetEngine au dynamique dont les libellés traduisibles restent minces**
     (les événements eux-mêmes sont déjà taggés FR/IT par le backoffice + les taxonomies
     bilingues qu'on a déployées). ← *voie « coût nul », à privilégier au lancement.*
  2. **Budgéter WPML (~99 $/an)** si le multilingue **dynamique** devient central plus tard.

*Cette contradiction n'est pas 100 % tranchée par les sources (le claim « Polylang absent
du guide » n'a eu qu'un vote 2-1). À valider empiriquement sur le site.*

## Autres réserves (honnêteté sur les limites de la recherche)
- **Aucune source** ne traite la compat **PHP 8.0 / WordPress 7.0.1 sur OVH mutualisé**
  pour ces plugins → **à valider empiriquement** avant déploiement.
- Versions/prix 2026 (JetEngine 3.8.4, Complianz 7.x, Popup Maker 1.21) **évolueront**.
- Plusieurs pages Crocoblock renvoient du 403 aux fetch automatisés → vérifs faites via
  extraits indexés + sources tierces concordantes.

## Questions ouvertes à trancher
1. Le dynamique JetEngine (Listing Grids, CCT) est-il traduisible de façon **fiable avec
   Polylang** en 2026, ou faut-il **WPML** pour tout le multilingue dynamique ?
2. JetEngine 3.8+, Ad Inserter, Popup Maker, TEC : pleinement OK en **PHP 8.0 / OVH
   mutualisé** sans perte de perf ?
3. Le **MCP JetEngine** interopère-t-il avec **Novamira**, ou impose-t-il son canal — et
   couvre-t-il l'édition de contenu **blocs core**, ou seulement les structures JetEngine ?
4. Pour `/[ville]/ce-week-end/` en FR **et** IT : quelle combinaison **Polylang + réécriture
   d'URL + Listing Grid** produit des archives localisées **sans conflit avec TEC** ?

---

### Sources primaires clés
- GeneratePress — position FSE : generatepress.com/generatepress-and-the-future-of-full-site-editing-our-approach/
- The Events Calendar — Full Site Editor (KB) : theeventscalendar.com/knowledgebase/the-events-calendar-full-site-editor/
- Crocoblock — JetEngine (Gutenberg) : crocoblock.com/plugins/jetengine/
- Crocoblock — MCP Command Center : crocoblock.com/plugins/jetengine/wordpress-mcp-command-center/
- Crocoblock — Listing Grid Query : crocoblock.com/knowledge-base/jetengine/listing-grid-posts-query-overview/
- WPML — compat JetEngine : wpml.org/plugin/jetengine/
- Complianz — Ad Inserter + consentement : complianz.io/ads-based-on-consent-with-ad-inserter-pro/
- Popup Maker (WordPress.org) : wordpress.org/plugins/popup-maker/
