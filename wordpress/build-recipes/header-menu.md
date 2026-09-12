# Recette de build — Header + Menu de navigation (agendasabauda.eu)

*Recette actionnable pour construire le header et la navigation principale du site public
Agenda Sabauda. Écrite le 12/07/2026. Ne modifie rien : c'est le plan de montage.*

**Stack réelle vérifiée sur le site vivant (12/07/2026)** :
GeneratePress + **GeneratePress Child (Crocoblock)** · Elementor 4.1.4 · **JetThemeCore 2.3.1**
(Theme Parts) · **JetBlocks 1.5** (widget Nav Menu, Hamburger Panel, Search) · JetEngine ·
JetSmartFilters · **JetPopup 2.2** · Polylang 3.8.5 · The Events Calendar 6.16.5 ·
Code Snippets (tokens CSS). Taxonomies portées par `tribe_events` : **`tribe_events_cat`**
(catégories) + **`territoire`** (custom, hiérarchique territoire › ville) + `post_tag`.
Base d'archive TEC déjà réglée sur **`/evenements/`**.

> Principe directeur (repris de `BUILD_WORDPRESS_CROCOBLOCK.md`) : **TEC = la donnée, Jet =
> la mise en forme.** Le header se construit en **Theme Part JetThemeCore + Elementor**, avec
> les widgets **JetBlocks**. On câble le menu sur les **archives de taxonomie** (catégories,
> territoires) et sur des **pages/hubs** pour le temporel.

---

## 1. Structure du header

### 1.1 Desktop (barre unique, sticky, compacte au scroll)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  Agenda Sabauda●   Aujourd'hui  Ce week-end  Catégories ▾  Territoires ▾  Agenda ▾   🔍  FR|IT │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

Zones (grille 3 colonnes : marque | nav centrée/gauche | actions à droite) :

1. **Wordmark** « Agenda Sabauda » + **point rouge** final (`●` = `.` coloré `--cs-rouge`).
   Lien vers l'accueil de la langue courante. Option logo-mark SVG (skyline / Mole) à gauche
   du mot si fourni dans `assets/logos/agenda/` (SVG Support est actif → upload direct).
2. **Menu principal** (JetBlocks Nav Menu) :
   - **Aujourd'hui** — lien direct, **sans** sous-menu (1 clic).
   - **Ce week-end** — lien direct, **sans** sous-menu (la page reine).
   - **Catégories ▾** — méga-menu : les 11 catégories sur 2 colonnes + « Toutes ».
   - **Territoires ▾** — 4 entrées (villes en 2ᵉ niveau = v2).
   - **Agenda ▾** — Cette semaine · Mois courant (libellé dynamique) · Les 10 du week-end ·
     Tout l'agenda.
3. **Recherche** 🔍 — icône seule qui **ouvre un overlay** (JetPopup) contenant un champ de
   recherche. Jamais un champ inline qui pousse la nav.
4. **Commutateur FR | IT** — **texte, JAMAIS de drapeau** (un drapeau = un pays, pas une
   langue ; piège d'un site transfrontalier). Séparateur `|`, langue courante en gras.

Interdits (rappel brief §12) : pas d'emoji comme icône d'UI (la loupe = pictogramme trait ou
SVG, pas 🔍 littéral en prod), pas de dégradé, pas de glassmorphism.

### 1.2 Mobile (< 1024 px)

Barre compacte : **wordmark (ou mark seul)** · **loupe** · **burger**. Le menu déroulant
plein écran (JetBlocks **Hamburger Panel** ou JetPopup) présente, dans l'ordre :

1. **Aujourd'hui** puis **Ce week-end** en très gros (les 2 actions reines).
2. Accordéon **Catégories** (11).
3. Accordéon **Territoires** (4).
4. **Agenda** (Cette semaine · Mois · Les 10 du week-end · Tout l'agenda).
5. **FR | IT** en texte.

Pas de bottom-tab-bar. Sur les pages de liste : la barre de chips temporelles scrollable
(Aujourd'hui · Week-end · Semaine · Dates) vit **sous** le header, dans le gabarit de hub
(hors de cette recette header).

---

## 2. Le menu WordPress à créer

Créer le menu dans **Apparence › Menus** (nom : `Principal FR`). Il sera référencé par le
widget JetBlocks Nav Menu. Colonne « Type de lien » = ce que pointe chaque item.

| # | Libellé FR | Type de lien | Cible (FR) | Sous-menu |
|---|---|---|---|---|
| 1 | **Aujourd'hui** | Page/hub temporel | `/aujourdhui/` (gabarit requête dates, `noindex`) | — |
| 2 | **Ce week-end** | Page/hub temporel | `/ce-week-end/` (URL fixe evergreen) | — |
| 3 | **Catégories** | Lien personnalisé `#` (parent non cliquable) | — | ▼ 11 items |
| 3.1 | Expositions & Patrimoine | **Archive taxo** `tribe_events_cat` | `/evenements/expositions-patrimoine/` | |
| 3.2 | Concerts & Musique | Archive taxo | `/evenements/concerts-musique/` | |
| 3.3 | Spectacle vivant | Archive taxo | `/evenements/spectacle-vivant/` | |
| 3.4 | Festivals | Archive taxo | `/evenements/festivals/` | |
| 3.5 | Gastronomie & Sagre | Archive taxo | `/evenements/gastronomie-sagre/` | |
| 3.6 | Marchés & Foires | Archive taxo | `/evenements/marches-foires/` | |
| 3.7 | Sport | Archive taxo | `/evenements/sport/` | |
| 3.8 | Cinéma | Archive taxo | `/evenements/cinema/` | |
| 3.9 | Jeune public & Famille | Archive taxo | `/evenements/jeune-public-famille/` | |
| 3.10 | Conférences & Rencontres | Archive taxo | `/evenements/conferences-rencontres/` | |
| 3.11 | Fêtes & Traditions populaires | Archive taxo | `/evenements/fetes-traditions/` | |
| 3.12 | **Toutes les catégories →** | Page « Tout l'agenda » | `/evenements/` | |
| 4 | **Territoires** | Lien personnalisé `#` (parent non cliquable) | — | ▼ 4 items |
| 4.1 | Savoie / Haute-Savoie | **Archive taxo** `territoire` | `/territoire/savoie-haute-savoie/` | |
| 4.2 | Piémont | Archive taxo | `/territoire/piemont/` | |
| 4.3 | Vallée d'Aoste | Archive taxo | `/territoire/vallee-d-aoste/` | |
| 4.4 | Nice / Alpes-Maritimes | Archive taxo | `/territoire/nice-alpes-maritimes/` | |
| 5 | **Agenda** | Lien personnalisé `#` (parent non cliquable) | — | ▼ 4 items |
| 5.1 | Cette semaine | Page/hub temporel | `/cette-semaine/` (`noindex`) | |
| 5.2 | Ce mois-ci (libellé dyn.) | Page/hub mois | `/agenda/{aaaa}/{mm}/` (v2) | |
| 5.3 | Les 10 du week-end | Page/article listicle | `/les-10-du-week-end/` | |
| 5.4 | Tout l'agenda | Page « Tout l'agenda » | `/evenements/` | |

**Recherche** et **FR|IT** ne sont **pas** des items de ce menu WP : la loupe est un widget
Elementor/JetBlocks dédié (overlay), le switch est le widget Polylang (§5).

### 2.1 Archive de taxonomie vs page/hub — la règle

- **Items qui pointent vers des ARCHIVES de taxonomie** (auto-générées par WP/TEC, chaque terme
  a sa page + son intro pérenne posée par le gabarit d'archive) :
  - **Catégories** (3.1–3.11) → termes de **`tribe_events_cat`**.
  - **Territoires** (4.1–4.4) → termes de **`territoire`** (+ villes en enfants, v2).
  - Dans le menu, préférer le type **« Catégorie d'événement »** / **« Territoire »** (WP liste
    les termes dans la boîte Menus) plutôt qu'un lien brut : le lien reste correct si le slug
    change, et Polylang lie automatiquement la traduction du terme.
- **Items qui pointent vers des PAGES / HUBS maison** (gabarits qui interrogent les dates, pas
  des taxonomies — cf. `TAXONOMIE_WORDPRESS…md` §2.3 : « le temps n'est jamais une taxonomie ») :
  - **Aujourd'hui, Ce week-end, Cette semaine, Ce mois-ci** → pages/endpoints à URL fixe.
  - **Tout l'agenda** → page listant tout (archive `tribe_events` filtrable) = base `/evenements/`.
  - **Les 10 du week-end** → article/listicle à URL fixe recyclée.

> ⚠️ **URL réelles à confirmer** : la base d'archive TEC est `/evenements/`, mais l'archive
> **par catégorie** sort par défaut en `/evenements/category/{slug}/` (schéma TEC), pas en
> `/evenements/{slug}/` visé par le plan. Deux options au build : (a) accepter le défaut TEC ;
> (b) poser une **règle de réécriture** (mu-plugin / Code Snippets) `evenements/{cat}` →
> archive du terme. Idem pour l'archive `territoire` (slug de réécriture `territoire`). Le menu
> se construit sur le **terme** (pas l'URL en dur), donc il suivra la réécriture retenue.

---

## 3. Recette de build (Theme Part JetThemeCore + Elementor)

### Étape 0 — Prérequis
- Vérifier que les **11 termes `tribe_events_cat`** et les **4 termes `territoire`** existent
  (Événements › Catégories ; Événements › Territoires). Si absents, les créer avec les slugs
  du §2 **avant** de bâtir le menu. *(Terminologie live confirmée : taxonomies enregistrées ;
  seeding des termes à vérifier — voir §6.)*
- Globals Elementor : vérifier que les couleurs de marque et polices sont bien dans les
  **réglages globaux** (sinon on utilise les variables `--cs-*` en CSS custom, §4).

### Étape 1 — Créer le Theme Part Header
1. **Crocoblock › Theme Templates** (ou **JetThemeCore › Theme Parts**) › **Add New** ›
   type **Header**. Nom : `Header — Agenda Sabauda (FR)`. Éditeur : **Elementor**.
2. Structure : 1 section, 1 conteneur **flex** en ligne, `justify-content: space-between`,
   `align-items: center`, hauteur ~72 px (desktop). 3 blocs enfants : **marque** | **nav** |
   **actions (loupe + switch)**.

### Étape 2 — Bloc marque (wordmark + point rouge)
- Widget **Heading** (ou HTML) contenant `Agenda Sabauda<span class="as-dot">.</span>`,
  enveloppé d'un lien vers l'accueil. Police titres (`--font-editorial` : « La Semplicita »).
- Le point rouge se fait en CSS (§4). Si logo SVG fourni : widget **Image** (SVG) à gauche,
  hauteur ~32–36 px.

### Étape 3 — Bloc navigation (JetBlocks **Nav Menu**)
- Widget **Nav Menu** (JetBlocks). **Menu** = `Principal FR` (créé au §2).
- Layout **horizontal**. Activer **Dropdown** pour les items parents (Catégories/Territoires/
  Agenda). Pour « Catégories » en 2 colonnes : soit régler la largeur du sous-menu + CSS
  `column-count`, soit utiliser un **Mega Menu** (JetBlocks : un item peut ouvrir un template
  Elementor — utile pour poser les 11 catégories + pictos trait sur 2 colonnes).
- **Breakpoint mobile** : activer le **toggle hamburger** intégré du widget (ou passer par un
  **Hamburger Panel** JetBlocks distinct pour le menu plein écran mobile du §1.2).
- Indicateur de sous-menu : chevron « ▾ » (option du widget), pas d'emoji.

### Étape 4 — Bloc actions
- **Loupe** : widget **Search** de JetBlocks *ou* — pour l'overlay — une **Icône** (SVG loupe)
  dont l'action ouvre un **JetPopup** « Recherche » (popup plein largeur avec le champ de
  recherche + résultats orientés événements). Recommandé : icône + JetPopup (contrôle total du
  design de l'overlay ; JetPopup est déjà actif).
- **Switch FR | IT** : widget du §5.

### Étape 5 — Sticky / compact au scroll
- Section header : **Advanced › Motion Effects › Sticky = Top**, `Sticky On: Desktop+Tablet+
  Mobile`. Ajouter une classe `as-header--scrolled` via l'option « Effects Offset » + CSS pour
  réduire la hauteur et l'ombre au scroll (§4). JetTricks (actif) peut aussi gérer le sticky.
- Alternative : le sticky natif GeneratePress si on veut alléger — mais comme le header est un
  Theme Part Elementor, garder le sticky Elementor est cohérent.

### Étape 6 — Conditions d'affichage (JetThemeCore)
- Onglet **Conditions** du Theme Part : **Include › Entire Site**.
- **Exclure** les éventuels gabarits où l'on veut un header nu (ex. overlay recherche plein
  écran, 404 si voulu — optionnel).
- **Bilingue** : voir §5.2 (deux Theme Parts par langue, ou traduction du template).

### Étape 7 — Publier + assigner
- Publier le Theme Part. Vérifier en front (desktop + mobile) le rendu, le sticky, l'ouverture
  des sous-menus et de l'overlay, le switch de langue.

---

## 4. CSS (classes + variables `--cs-*`)

À coller dans **Code Snippets** (scope `site-css`, comme les tokens) ou dans le CSS custom du
Theme Part. Les variables `--cs-*` / `--fg-*` viennent de `wordpress/design-system/tokens.css`
(déjà poussé sur le site).

```css
/* ===== Header Agenda Sabauda ===== */
.as-header {
  background: var(--cs-blanc);
  border-bottom: 1px solid var(--rule);
  transition: box-shadow var(--dur-fast) var(--ease-std),
              padding var(--dur-fast) var(--ease-std);
}

/* Wordmark + point rouge (la signature de marque) */
.as-wordmark {
  font-family: var(--font-editorial);      /* La Semplicita */
  font-weight: 700;
  font-size: 1.5rem;
  letter-spacing: var(--tracking-caps);
  color: var(--cs-bleu);                    /* #18365E */
  text-decoration: none;
  line-height: 1;
}
.as-wordmark .as-dot { color: var(--cs-rouge); }  /* #DC5D45 — le point */

/* Menu de nav (JetBlocks Nav Menu) */
.as-header .jet-nav__item-inner {
  font-family: var(--font-body);            /* Nunito Sans */
  font-size: var(--fs-body-sm);
  font-weight: 600;
  color: var(--fg-1);
  letter-spacing: .01em;
}
.as-header .jet-nav__item > .jet-nav__link:hover,
.as-header .jet-nav__item.jet-current-menu-item > .jet-nav__link {
  color: var(--fg-link);                    /* rouge accent au survol/actif */
}
/* Les 2 items temporels reines : légèrement appuyés */
.as-header .menu-item-aujourdhui > a,
.as-header .menu-item-ce-week-end > a { font-weight: 700; }

/* Sous-menus (dropdown) */
.as-header .jet-nav__sub {
  background: var(--cs-blanc);
  border: 1px solid var(--rule);
  border-radius: var(--r-2);
  box-shadow: var(--shadow-lift);
  padding: var(--s-2);
}
/* Méga-menu Catégories : 2 colonnes */
.as-header .menu-item-categories .jet-nav__sub { column-count: 2; column-gap: var(--s-5); min-width: 460px; }

/* Loupe */
.as-search-toggle { color: var(--fg-2); cursor: pointer; }
.as-search-toggle:hover { color: var(--fg-link); }

/* Switch de langue FR | IT (texte, pas de drapeau) */
.as-lang { display: inline-flex; gap: var(--s-2); font-family: var(--font-body);
           font-size: var(--fs-meta); font-weight: 700; }
.as-lang a { color: var(--fg-3); text-decoration: none; }
.as-lang a:hover { color: var(--fg-link); }
.as-lang .current-lang > a,
.as-lang .lang-item.current-lang { color: var(--cs-bleu); }         /* langue active */
.as-lang .lang-item + .lang-item::before { content: "|"; color: var(--rule-strong);
           margin-right: var(--s-2); }
.as-lang img.flag, .as-lang .flag { display: none !important; }      /* jamais de drapeau */

/* Sticky compact au scroll */
.as-header.elementor-sticky--effects { padding-top: 6px; padding-bottom: 6px;
           box-shadow: var(--shadow-paper); }
.as-header.elementor-sticky--effects .as-wordmark { font-size: 1.25rem; }

/* Mobile */
@media (max-width: 1023.98px){
  .as-header .as-nav-desktop { display: none; }
  .as-header .as-burger { display: inline-flex; }
}
```

> Les sélecteurs `.jet-nav__*` sont ceux de JetBlocks Nav Menu (à confirmer selon la version au
> build via l'inspecteur). Le `.as-header`, `.as-wordmark`, `.as-dot`, `.as-lang` sont des
> classes à poser sur les widgets Elementor (champ « CSS Classes »).

---

## 5. Polylang FR / IT

### 5.1 Le commutateur de langue
- **Le plus simple / fiable** : ajouter le **commutateur Polylang** au menu WP via
  **Apparence › Menus › (boîte) Commutateur de langue** → cocher **« Afficher les noms de
  langues »**, **décocher « Afficher les drapeaux »**, décocher « Forcer le lien vers la page
  d'accueil » (on veut le lien vers la **page équivalente**). Résultat : items `Français` /
  `Italiano` → renommer en **FR** / **IT** via le libellé, stylés `|` par le CSS `.as-lang`.
- **Alternative** : widget Elementor/JetBlocks « Language Switcher » s'il est dispo, ou
  shortcode `[pll_the_languages show_flags=0 show_names=1]` dans un widget **Shortcode**.
- Comportement attendu (brief §9) : le switch **mène à la page équivalente** ; repli sur le hub
  parent + micro-message « Questo evento non è ancora tradotto » si la fiche n'est pas traduite
  (géré côté gabarit fiche, hors header).

### 5.2 Menus et header par langue
- Créer **deux menus** : `Principal FR` et `Principal IT` (mêmes items, libellés + termes
  traduits ; Polylang lie automatiquement chaque **terme** de taxo à sa traduction).
- **Point de friction connu JetBlocks Nav Menu + Polylang** : le widget Nav Menu référence **un
  menu précis (par ID)**, il ne bascule pas automatiquement selon la langue. Deux solutions :
  1. **(Recommandé) Dupliquer le Theme Part Header par langue** : `Header FR` (menu FR) et
     `Header IT` (menu IT), puis **conditions d'affichage par langue**. JetThemeCore + Polylang :
     traduire le Theme Part (Polylang gère les CPT `jet-theme-core`) et assigner le menu IT dans
     la version IT. Le header s'affiche dans la bonne langue automatiquement.
  2. **(Plus léger, à tester)** garder **un** Theme Part et remplacer le widget Nav Menu par le
     **menu de localisation GeneratePress** (emplacement de thème) : Polylang bascule nativement
     les menus assignés à un **emplacement** (Réglages › Menus, un menu par langue par
     emplacement). Moins de contrôle visuel que JetBlocks, mais zéro duplication.
- **Libellés à traduire** (pour le menu IT) : Aujourd'hui→**Oggi**, Ce week-end→**Questo
  weekend**, Catégories→**Categorie**, Territoires→**Territori**, Agenda→**Agenda**, Cette
  semaine→**Questa settimana**, Les 10 du week-end→**I 10 del weekend**, Tout l'agenda→**Tutti
  gli eventi**. Slugs IT des hubs : `/it/oggi/`, `/it/questo-weekend/`, etc. (cf. plan du site).
- Prévoir **+10–15 %** de largeur pour les chaînes IT (brief §9) : ne pas figer les largeurs
  d'items en px.

---

## 6. Incertitudes / décisions à confirmer

1. **Elementor free (pas Pro), pas de Bricks.** La stack live est **GeneratePress + Elementor +
   Jet** — ce qui **contredit** la reco « PAS Elementor » de `BUILD_WORDPRESS_CROCOBLOCK.md`
   (qui préconisait Bricks ou Gutenberg pour la perf/CWV). Décision déjà prise côté site
   (Elementor est installé et actif). **Conséquence perf à surveiller** : Elementor + Jet est le
   combo le plus lourd → soigner le cache et limiter les widgets. À acter : on assume Elementor.
2. **Seeding des termes** : les taxonomies `tribe_events_cat` et `territoire` sont **enregistrées**
   sur `tribe_events`, mais je n'ai pas pu confirmer via MCP que les **11 + 4 termes** sont déjà
   créés (l'accès REST direct est bloqué par le sandbox ; pas d'outil MCP listant ces termes).
   **À vérifier dans l'admin avant de câbler le menu.**
3. **URLs des archives catégorie/territoire** : défaut TEC `/evenements/category/{slug}/` vs
   cible plan `/evenements/{cat}/`, et slug de réécriture `territoire`. Choisir : accepter le
   défaut TEC, ou poser des règles de réécriture (§2.1). Impacte les liens (mais le menu pointe
   sur les termes, donc robuste).
4. **Hubs temporels** : Aujourd'hui / Ce week-end / Cette semaine / Mois n'existent pas encore
   (aucune page hub créée — seules 2 pages par défaut sur le site). Il faut **créer ces pages/
   gabarits** (requête sur dates) avant que les items de menu 1, 2, 5.1, 5.2 aient une cible
   valide. « Tout l'agenda » peut pointer dès maintenant sur `/evenements/`.
5. **Overlay recherche** : JetBlocks Search inline vs JetPopup dédié. Reco = **JetPopup** (design
   maîtrisé, résultats orientés événements). À confirmer selon le temps.
6. **Méga-menu Catégories** : simple dropdown 2 colonnes (CSS) vs vrai Mega Menu JetBlocks avec
   template (pictos trait). Reco = commencer simple (CSS `column-count`), passer au Mega Menu
   si l'on veut les pictogrammes.
7. **Prefix `/fr/`** : le plan prévoit `/fr/…` + `/it/…`. Actuellement le front sort en racine
   (`/`, `/evenements/`) — la langue par défaut Polylang **masque** peut-être le code `/fr/`.
   Décider si FR doit être préfixé (cohérence hreflang) ou rester en racine. Impacte les URL du
   menu (mais pas les liens vers termes/pages, gérés par Polylang).
8. **Logo-mark SVG** : le dossier `assets/logos/agenda/` référencé dans le brief est **absent du
   repo local** (introuvable). Si un mark (skyline/Mole) doit accompagner le wordmark, fournir le
   SVG ; sinon, wordmark texte seul (suffisant, + point rouge).
9. **Design system Claude Design** (« Navigation Lecture.html », etc.) : **non consulté** — aucun
   connecteur DesignSync/Drive exposé dans cette session. Recette bâtie sur les docs du repo
   (brief §5, plan du site §3) + tokens `design-system/tokens.css`, qui sont la source figée.
```
