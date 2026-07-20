# Régie publicitaire — mise en place du SOCLE (session Novamira, 2026-07-17/18)

*Journal de ce qui a été fait EN LIVE sur agendasabauda.eu via le connecteur Novamira
(exécution PHP directe + lecture/écriture de fichiers sur le serveur), en dehors de ce
dépôt git. Complète `REGIE_ANNONCEURS.md` (le plan) avec l'état réel après implémentation,
y compris les conflits découverts. Rien de ce qui suit n'était encore commité avant cette
note — c'est la première trace versionnée de ce travail.*

---

## ✅ Mise à jour 2026-07-20 — modèle arrêté + blocages levés

- **Modèle « override » validé (Franck).** Toutes les pubs sont **AdSense par défaut** ;
  quand un annonceur est vendu, sa créative est créée dans le backoffice et **remplace
  l'AdSense du bloc concerné** le temps de la campagne. Pas d'emplacement séparé.
- **`/api/active-ads` n'est plus en time-out.** Diagnostic du 20/07 : DNS OK
  (`backoffice.agendasabauda.eu` → IP VPS), route Traefik déposée, HTTP **200**. Le
  « time-out » du 18/07 était transitoire / déjà réparé.
- **Lien `/go` déterministe.** Le backoffice force une base publique https
  (`PUBLIC_BASE_URL`) au lieu de `request.host_url`, pour ne pas produire un lien
  `http://` (rejeté par le fail-safe https-only côté WP).
- **Créatives hébergées uniquement sur `agendasabauda.eu`** → allowlist image du
  mu-plugin = `agendasabauda.eu` seul (pas de `culturasabauda.eu`).
- **`cs-regie-serve.php` réécrit (v0.2)** : de « sticky bas manuel-only » à **primitive
  d'override par bloc** — shortcode `[cs_slot bloc="N"]…code AdSense…[/cs_slot]`. Reste
  le **câblage thème** : envelopper le code AdSense de chaque bloc dans ce shortcode.
  → conflit #2 ci-dessous **résolu** (plus de sticky bas concurrent).

---

## ⚠️ Conflits connus, non résolus au moment de ce commit

1. **Collision de numérotation de blocs Ad Inserter.** Le template homepage
   (`wordpress/design-system/homepage-template.php` + `homepage-mobile.gutenberg.html`)
   câble déjà `[adinserter block="1"]` à `[adinserter block="12"]` pour des emplacements
   homepage précis (gouttières, sous-carrousel, sous-tuiles, colonne "En évidence", sticky
   desktop/mobile — voir `REGIE_ANNONCEURS.md` et `wordpress/build-recipes/STATUS.md`).
   Cette session a configuré les blocs **1 à 4** pour tout autre chose (leaderboard,
   pavé in-article, sticky bas, skin) sans le savoir. Blocs 1 et 2 sont actifs → risque de
   double rendu sur la home (le code s'insère à la fois automatiquement ET via le shortcode
   câblé dans le gabarit). **À trancher avec Franck avant d'aller plus loin** : renuméroter
   vers 13-16, ou abandonner le plan homepage pré-câblé.
2. **`wp-content/mu-plugins/cs-regie-serve.php` existe en production, absent de ce dépôt.**
   Système de sticky bas indépendant, alimenté par `https://backoffice.agendasabauda.eu/api/active-ads`,
   avec le même gating Complianz. Testé le 2026-07-18 : l'API **time-out** (backoffice
   injoignable ou route absente) — le bandeau ne s'affiche donc jamais actuellement.
   Fait doublon avec le Bloc 3 (sticky) configuré ci-dessous.
3. **Compte AdSense (`ca-pub-4040905402577097`) au statut « Examen requis »** chez Google —
   aucune annonce réelle ne peut s'afficher tant que ce n'est pas approuvé, indépendamment
   de toute config technique.

---

## Ce qui a été configuré (état réel, blocs Ad Inserter 1-4)

Gating consentement identique sur les 4 blocs — **vérifié en lisant le code réel de
Complianz sur ce site** (pas une doc générique) :
```js
// Cookie posé par Complianz quand le marketing est accepté : cmplz_marketing=allow
// Événement émis au changement de consentement (template officiel Complianz) :
document.addEventListener('cmplz_status_change', function (e) {
  if (e.detail.category === 'marketing' && e.detail.value === 'allow') { /* charger la pub */ }
});
```
Le préfixe de cookie (`cmplz_`) a été confirmé en appelant en direct
`COMPLIANZ::$banner_loader->get_cookie_prefix()` sur le serveur — pas une supposition.

### Bloc 1 — Leaderboard
- Position Ad Inserter : « Avant le contenu » (`display_type=3`, confirmé via les
  constantes réelles `AI_AUTOMATIC_INSERTION_*` du plugin)
- Appareils : Ordinateur + Téléphone
- Code : AdSense gaté (slot `5007380676`), format 970×90 desktop / 350×90 mobile (media query 768px)
- **Statut : actif, en attente de validation Google**

### Bloc 2 — Pavé in-article
- Position : « Après le paragraphe » n°3 (`display_type=6`)
- Condition URL : `/evenement/*` (fiches événement individuelles uniquement, pas l'archive `/evenements/`)
- Appareils : Ordinateur + Téléphone
- Code : AdSense gaté (slot `4871649309`, layout in-article fluid), 300×250
- **Statut : actif, en attente de validation Google**
- ⚠️ **Point non vérifié** : `single-event-meta.php` rend le contenu via `get_the_content()`
  directement plutôt que `the_content()` (le tag de template qui applique le filtre
  `the_content` où Ad Inserter s'accroche — confirmé : `add_filter('the_content', 'ai_content_hook', ...)`
  dans `ad-inserter.php`). **Si confirmé, ce bloc ne s'insère probablement jamais sur les vraies
  fiches événement** malgré une configuration par ailleurs correcte. À vérifier visuellement
  avant de compter sur ce bloc.

### Bloc 3 — Bandeau bas sticky (fermable)
- Position : « Pied de page » (`display_type=13`)
- CSS maison `position:fixed`, z-index 9000 (sous la bannière Complianz à 99999),
  fermeture mémorisée en `localStorage`
- Appareils : Ordinateur + Téléphone
- **Statut : DÉSACTIVÉ** (placeholder retiré ; fait doublon avec `cs-regie-serve.php`, cf. conflit #2 ci-dessus)

### Bloc 4 — Habillage / Skin
- Position : « Avant le contenu » (`display_type=3`), visibilité gérée par CSS `@media (max-width:1840px){display:none}`
- Seuil de 1840px recalculé à partir de la largeur réelle du conteneur GeneratePress
  (**1200px, confirmé en direct** via `generate_get_option('container_width')`) — le
  résumé initial du Kit Annonceurs disait « ≥1280px », incohérent avec sa propre formule
  `container + 640px` ; corrigé dans le kit et le README du handoff par l'utilisateur.
- Architecture : deux bandes latérales `position:fixed` dans les marges (pas un calque
  plein écran en `z-index:-1`) — élimine tout risque de passer derrière un fond de thème opaque.
- Appareils : Ordinateur uniquement
- **Statut : DÉSACTIVÉ** (aucune vraie créative 1920×1080 fournie à ce stade — fait doublon avec `cs-regie.php`, cf. conflit #1)

---

## Hors blocs — réglages site

### `ads.txt`
Créé à la racine (`/ads.txt`), vérifié HTTP 200 :
```
google.com, pub-4040905402577097, DIRECT, f08c47fec0942fa0
```

### Cache page d'accueil
Le cache HTTP OVH ignorait le paramètre `?nocache=1` mais respecte les en-têtes
`Cache-Control` d'origine (vérifié empiriquement). Snippet ajouté (voir
`deploy/wordpress/cs-cache-control-home.php`, à déployer comme mu-plugin) :
```
Cache-Control: public, max-age=300, s-maxage=300
```
sur la page d'accueil uniquement — remplace un `no-store` de test initial (qui aurait
annulé tout bénéfice du cache OVH en permanence).

### Sauvegardes
Avant chaque écriture directe en base sur l'option `ad_inserter`, une copie complète de
la valeur précédente a été écrite dans `wp-content/uploads/ai-backup-<timestamp>.txt`
sur le serveur (plusieurs fichiers, non repris ici — restaurables en cas de besoin).

---

## Prochaines étapes proposées (à trancher avec Franck)

1. Renumberoter les blocs 1-4 vers 13-16 pour lever le conflit avec le plan homepage déjà câblé.
2. Vérifier si `cs-regie-serve.php` (sticky bas piloté par backoffice) doit remplacer notre
   Bloc 3, et pourquoi son API `/api/active-ads` time-out actuellement.
3. Vérifier si `cs-regie.php` (skin + gouttières, jamais déployé) doit remplacer notre Bloc 4.
4. Décider si `single-event-meta.php` doit passer par `the_content()` pour que l'insertion
   automatique Ad Inserter fonctionne réellement sur les fiches événement.
