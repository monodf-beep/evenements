# SPEC pixel-précise — Header / Footer / Homepage (BLOQUÉ : source Claude Design inaccessible)

*Tentative d'extraction du 12/07/2026. Ne modifie rien : recherche seule.*

## ⚠️ BLOCAGE — l'outil DesignSync n'existe pas dans cette session

La mission demandait d'utiliser un outil **DesignSync** (`method: "get_file"`) pour lire, dans le
design system Claude Design **« Cultura Sabauda Design System »** (projectId
`756af367-0f11-4104-9780-d252a774c9e7`) :

1. `ui_kits/agenda/kit.css`
2. `ui_kits/agenda/components.jsx`
3. `ui_kits/agenda/app.jsx`
4. `Navigation Lecture.html`
5. `Ecrans Evenementiel.html`
6. `assets/logos/agenda/agenda-mole.svg` et `agenda-skyline-full.svg`

**Cet outil n'est pas disponible dans cet environnement.** Vérifications faites :

- Recherche dans les outils différés (`ToolSearch`) avec plusieurs requêtes (« DesignSync
  get_file », « design sync kit css jsx figma », « Cultura Sabauda Design System ui_kits ») :
  aucun outil nommé `DesignSync` ou équivalent (Figma/Claude Design) trouvé — uniquement des
  outils Notion, Google Drive, Shopify, Higgsfield, Gmail, Calendar, etc.
- Les fichiers `.mcp.json` du poste (`C:\Users\Monod\.mcp.json` et
  `C:\Users\Monod\evenements\.mcp.json`) ne déclarent que deux serveurs MCP WordPress
  (`wordpress` → culturasabauda.eu, `wordpress-mcp` → agendasabauda.eu). **Aucun connecteur
  DesignSync/Figma/Claude Design n'est configuré.**
- Aucun cache local du design system : pas de dossier `screenshots/`, pas de
  `assets/logos/agenda/`, pas de `Navigation Lecture.html` ni `Ecrans Evenementiel.html` nulle
  part dans `C:\Users\Monod\evenements` (recherche exhaustive par nom et par glob `**/*.html`).
- **C'est une limitation déjà connue** : `wordpress/build-recipes/header-menu.md` §6 point 9
  le documentait déjà le 12/07/2026 : *« Design system Claude Design (…) non consulté — aucun
  connecteur DesignSync/Drive exposé dans cette session. »* Cette tentative confirme que le
  problème persiste — ce n'est pas un aléa ponctuel.

**Conséquence directe** : je ne peux pas produire les specs « pixel/couleur près » demandées
(CSS réel de `kit.css`, JSX réel des composants, structure DOM réelle, noms de fichiers
screenshots). Toute valeur que j'inventerais à leur place serait une fabrication dangereuse :
le but même de la mission est de combler un écart *mesuré contre la vraie maquette*, donc
publier des pixels/couleurs non vérifiés créerait un faux sentiment de précision et risquerait
d'aggraver l'écart perçu par le client plutôt que de le combler.

### Pour débloquer

- Si le design system vit dans **Figma** : il faut un connecteur Figma (MCP officiel ou plugin)
  configuré dans `.mcp.json`, avec accès au fichier `Cultura Sabauda Design System`.
- Si « Claude Design » = un espace **claude.ai** (Artifacts/Projects) : il faudrait soit un accès
  navigateur (Claude Browser) à l'URL du projet claude.ai concerné pour lire `kit.css` /
  `components.jsx` / les HTML de démo à l'œil et copier leur contenu, soit que l'utilisateur
  exporte/colle ces fichiers directement dans la conversation ou le repo local.
- Si ces fichiers existent déjà quelque part sur le disque (autre dossier que
  `C:\Users\Monod\evenements`), une recherche plus large (hors du repo) pourrait les localiser —
  à confirmer avec l'utilisateur avant d'aller chercher en dehors du périmètre du projet.

---

## Ce qui EST disponible localement (état actuel, PAS vérifié contre la maquette)

Les 3 fichiers `wordpress/build-recipes/{header-menu,footer,homepage}.md` et
`wordpress/design-system/components.css` existent et sont cohérents entre eux, mais ce sont des
**specs auto-rédigées** (probablement par une session précédente qui a elle aussi buté sur
l'absence de DesignSync) — pas une extraction du vrai kit Claude Design. Elles s'appuient sur
`wordpress/design-system/tokens.css` (variables `--cs-*`) plutôt que sur le CSS réel du kit.
Résumé de ce qu'elles contiennent (donc de ce qu'il faudra comparer, une fois `kit.css` obtenu) :

### Header (`header-menu.md`)
- Barre unique desktop, grille 3 zones : wordmark (gauche) | nav (centre/gauche) | actions
  (droite, loupe + FR|IT).
- `.as-header` : fond `var(--cs-blanc)`, `border-bottom: 1px solid var(--rule)`, pas de hauteur
  fixe déclarée en px (seul `~72px desktop` mentionné en prose §1.3, pas en CSS).
- Wordmark `.as-wordmark` : `font-family: var(--font-editorial)` (« La Semplicita »),
  `font-weight: 700`, `font-size: 1.5rem`, `color: var(--cs-bleu)` (#18365E). Le point final
  `.as-dot` en `var(--cs-rouge)` — **pas de valeur hex directe pour le rouge dans ce fichier**
  (le tokens.css indirect donne `#DC5D45`, cité en commentaire ligne 212 du header-menu.md).
  Taille/position du point non spécifiées au pixel (hérite de la taille du texte).
- Sticky : `elementor-sticky--effects` réduit le padding à 6px et la taille du wordmark à
  1.25rem — mécanisme Elementor natif, pas une valeur de maquette.
- Mobile < 1024px : nav desktop cachée, burger visible. Pas de hauteur mobile spécifiée.
- **Logos SVG** (`agenda-mole.svg`, `agenda-skyline-full.svg`) : le fichier lui-même signale
  §6 point 8 que `assets/logos/agenda/` est **introuvable dans le repo local** — non résolu ici
  non plus (dossier confirmé absent, voir Glob ci-dessus).

### Footer (`footer.md`)
- 5 zones verticales : A newsletter, B marque, C 4 colonnes, D nav thématique, E barre légale.
- Fond confirmé dans ce fichier local : `var(--bg-deep)` — le commentaire dans le tokens indique
  bleu Savoie **`#18365E`** (même valeur que `--cs-bleu` du header ; à vérifier si kit.css a une
  nuance distincte pour le fond deep vs le bleu texte).
- Texte `var(--fg-on-deep)` = beige **`#F7F1E8`** (cité en commentaire §4, ratio contraste ~11:1
  annoncé mais pas vérifié outil).
- Typo : `--font-body` (Nunito Sans) pour le corps, `--font-editorial` (La Semplicita) pour les
  titres de colonnes et le wordmark footer.
- Grille colonnes : `repeat(4, 1fr)` desktop → 2 colonnes ≤1024px → 1 colonne ≤480px.

### Homepage (`homepage.md`)
- Hero `.as-hero` : fond `var(--bg)` (beige #F7F1E8) ou `var(--bg-deep)`, padding
  `var(--s-9) var(--s-5)` commenté « 96px / 24px » — **pas d'image de fond décrite**, positionnement
  du texte non précisé (pas de coordonnées, juste un bloc padding).
- H1 `.as-hero__h1` : `font-family: var(--font-display)` commenté **« Alumni Sans Pinstripe —
  CAPS only »**, `text-transform: uppercase`, `font-size: var(--fs-hero)` = **`clamp(3.5rem, 7vw,
  6.5rem)`**, `line-height: 0.95`, `letter-spacing: 0.05em`, couleur `var(--cs-bleu)` (#18365E).
  C'est la seule mention trouvée de « Alumni Sans Pinstripe » dans tout le repo local — **non
  confirmée contre une maquette réelle**, seulement contre le brief texte
  (`docs/BRIEF_DESIGN_AGENDA_SABAUDA.md`, non lu dans cette passe).
- Pas de hauteur de hero en px (juste le padding).
- Grilles de cartes : `repeat(3, 1fr)` ≥1024px, `repeat(2, 1fr)` ≥768px, 1 colonne mobile ; ratio
  image carte fixé `3/2`.

---

## Écarts entre `wordpress/design-system/components.css` et... rien de vérifiable

`components.css` est un **agrégat généré** (bandeau ligne 2-5 : « Généré depuis
`wordpress/build-recipes/*.md` — NE PAS éditer à la main ») des blocs CSS ci-dessus
(`carte-evenement`, `header-menu`, `footer`, `homepage`), copiés tels quels. Il n'y a **aucun
écart interne** entre ces `.md` et `components.css` — ils sont synchronisés (probablement via
`apply-components.mjs`, cité ligne 4). L'écart réel à mesurer — celui contre le **vrai** kit
Claude Design — reste impossible à établir tant que `kit.css` n'est pas lu.

## Screenshots
Aucun fichier `screenshots/*.png` lié à navigation/header/footer trouvé dans le repo
(`C:\Users\Monod\evenements`). Recherche par glob (`**/screenshots/**`) infructueuse.

---

## Prochaine étape recommandée

Avant de rebâtir header/footer/home dans WordPress, il faut d'abord obtenir un accès réel au
design system (connecteur Figma/DesignSync configuré, ou export manuel de `kit.css` +
`components.jsx` + `app.jsx` + les 2 HTML de démo + les 2 SVG dans le repo, par ex. sous
`wordpress/design-system/source/`). Une fois ces fichiers disponibles localement ou via un
outil connecté, relancer cette même extraction produira la vraie comparaison pixel/couleur
demandée par le client.
