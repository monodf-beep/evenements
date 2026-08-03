# Migration URL : préfixe `/fr/` explicite (réconciliation avec le contrat)

**Statut : TENTÉE EN LIVE le 2026-07-29 puis ROLLBACK. La bascule a provoqué une PANNE de la
home (`ERR_TOO_MANY_REDIRECTS`) via un cache serveur empoisonné non purgeable → retour à
`hide_default = 1`, site rétabli. À NE REFAIRE QUE SUR STAGING.**

> Cause de la panne : la racine `/` a été mise en cache avec un 302 en boucle pendant les tests.
> Le cache est au niveau Traefik/conteneur (le WP tourne sur un VPS, pas sur l'hébergement
> Hostinger ; `nginx -T` ne montre aucun cache ; hPanel n'a pas ce site). Non purgeable côté WP.
> Avant toute nouvelle tentative : identifier et maîtriser la purge du cache VPS (restart du
> stack WP ou de Traefik), et faire la migration sur staging, pas en prod.

## Résultat de la migration (2026-07-29)

La bonne méthode : changer `hide_default → 0`, puis **`delete_option('rewrite_rules')` pour forcer
la régénération sur une requête fraîche** (Polylang réenregistre alors ses règles `/fr/`). Le flush
immédiat dans la même requête échoue car Polylang s'est déjà initialisé avec l'ancien réglage.

État vérifié :
- `/fr/` (home) **200**, `/it/` **200**, `/fr/`pages **200**, `/fr/evenement/...` **200**.
- Anciennes URL sans préfixe → **301 → `/fr/...` nativement par Polylang** (pas de couche de
  redirection custom à construire, contrairement à la crainte initiale).
- Racine `/` → gérée par le **snippet #100 « CS - Redirect racine vers /fr/ »** (301 → `/fr/`,
  `template_redirect` prio 1).

### Résidu : cache serveur sur `/`
`/` propre renvoie encore **302 en boucle** (entrée mise en cache pendant la fenêtre de test
cassée) alors que `/?nc=xxxx` (non caché) renvoie correctement **301 → `/fr/`**. Le canari prouve
que WP n'est pas exécuté sur `/` caché. Cache serveur Hostinger **non purgeable en PHP** (pas de
plugin de cache ; en-tête `X-LiteSpeed-Purge` sans effet ; re-save de la page 928 sans effet).
**Action requise : purge du cache depuis le hPanel Hostinger** (ou attendre l'expiration TTL).
Une fois purgé, `/` servira le 301 → `/fr/` correct.

---

## (Historique) Diagnostic initial — pourquoi la bascule à sec échouait

## Contexte

Le contrat documenté (`PROMPTS_CHROME_WORDPRESS.md` l.42-43, `BRIEF_DESIGN_AGENDA_SABAUDA.md`,
`DECISIONS_ECARTEES.md`, `REGLES_PARTAGE_SOCIAL_OPEN_GRAPH.md`) impose des URL **symétriques**
`/fr/` + `/it/` : « Masquer l'information de langue pour la langue par défaut = NON, on veut
`/fr/` explicite ». Objectif éditorial : FR et IT à égalité (un italophone ne doit pas sentir un
site « fait par un francophone », et inversement).

**Dérive constatée en prod :** Polylang est réglé sur `hide_default = true` (FR **sans** préfixe),
soit l'inverse du contrat. Les guides existants sont donc en `/xxx/` (FR) au lieu de `/fr/xxx/`.

## Test de bascule à sec (2026-07-29) — ÉCHEC, rollback effectué

Bascule `hide_default → 0` + `flush_rewrite_rules()`, puis test HTTP. Résultats :

| URL | Code | Diagnostic |
|---|---|---|
| `/` | 302 en boucle sur elle-même | canonicalisation cassée |
| `/fr/` (home FR, page 928) | **404** | front-page non routée sous `/fr/` |
| `/fr/evenement/...` (314 events TEC) | **404** | réécritures TEC sans préfixe |
| `/it/`, pages IT | 200 | non impacté |
| hub FR (`ce-week-end/...`) | 301 → `/fr/...` | les hubs suivent |

Rollback auto (`hide_default → 1`, flush) déclenché car la home cassait. Prod re-vérifiée saine
(root 200, page FR 200). **Backup du réglage Polylang** : option `cs_backup_polylang_<timestamp>`.

## Cause racine

La bascule du seul réglage Polylang ne suffit pas : la home (pages **928/1717** + snippet **29**
qui les intercepte via `template_redirect`), les réécritures de **The Events Calendar**, et les
règles de **hub custom** (`cs_rewrite`) sont couplées à la structure actuelle sans préfixe.

### Diagnostic approfondi (2026-07-29, flip + rollback dans le même appel)

Avec `hide_default = 0`, en requête fraîche :
- `pll_home_url('fr')` renvoie toujours **`/`** (pas `/fr/`) et `get_permalink(928)` = `/`.
  `/fr/` tombe en **404** : la page d'accueil n'est pas routée sous `/fr/`.
- `get_permalink(1717)` (home IT) = **`/it/home-it/`** et non `/it/` : **la paire de pages
  d'accueil par langue n'est pas configurée comme front-page traduite** dans Polylang. C'est le
  nœud du problème home.
- Les événements gardent `/evenement/...` **sans** `/fr/` ; `/fr/evenement/...` n'existe pas
  (réécritures TEC non préfixées).
- `/` répond **302 en boucle** sur elle-même.

**Conséquence :** le chantier exige de l'**admin Polylang** (front-page par langue) + du code
(snippets home #29/#71, réécritures TEC, redirections) + une recette itérative. Non réalisable à
l'aveugle en PHP sur la prod. À faire sur **staging**, ou en **session guidée** (l'utilisateur agit
dans l'admin Polylang/WP, Claude gère snippets + redirections + tests).

### Ordre de bataille conseillé (staging)
1. Configurer la front-page traduite FR(928)/IT(1717) avec préfixe actif, valider `/fr/` et `/it/`.
2. Adapter snippets #29/#71 (interception home) à la home sous `/fr/`, tuer la boucle 302 sur `/`.
3. Régénérer les réécritures TEC (`evenements`/`evenement`) sous `/fr/` (resave réglages TEC + flush).
4. Vérifier hubs custom (`cs_rewrite`, #15/#60/#61) sous `/fr/`.
5. Poser la couche 301 `/xxx/` → `/fr/xxx/`.
6. Yoast (canonical/hreflang/sitemap) + recette complète.

## Travail réel nécessaire (à faire sur staging, pas en prod à l'aveugle)

1. **Front-page par langue** sous `/fr/` : régler la page d'accueil Polylang par langue, corriger
   le snippet 29 et la boucle 302 sur `/`.
2. **The Events Calendar** : base de réécriture des 314 événements sous `/fr/` (option
   `permalink` TEC + regénération).
3. **Hubs custom** (`cs_rewrite`, `/explore/`, `/choisir/`, `ce-week-end`, `territoire`) :
   intégrer `/fr/` proprement.
4. **Couche de redirections 301** : chaque URL FR sans préfixe `/xxx/` → `/fr/xxx/` (~240 URL :
   12 posts + ~150 pages + ~150 events, moitié FR). Pas de plugin de redirection installé →
   à coder (règle catch-all sur `template_redirect`) ou installer *Redirection*.
5. **Yoast** : vérifier canonical / `og:url` / hreflang / sitemap avec préfixe.
6. **Recette** : home FR, une fiche event, un hub, un guide, un lien IT, plus contrôle des
   anciennes URL (301, pas 404).

## Timing

À faire **avant lancement/indexation large** (docs en `TODO_LANCEMENT`) : la dette de
redirections est minime maintenant, lourde après. Ne PAS lancer sans redirections en place.

## Rollback

`update_option('polylang', <valeur de cs_backup_polylang_<timestamp>>)` puis
`flush_rewrite_rules()`.
