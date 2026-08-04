# Régie publicitaire — mise en place du SOCLE (session Novamira, 2026-07-17/18)

*Journal de ce qui a été fait EN LIVE sur agendasabauda.eu via le connecteur Novamira
(exécution PHP directe + lecture/écriture de fichiers sur le serveur), en dehors de ce
dépôt git. Complète `REGIE_ANNONCEURS.md` (le plan) avec l'état réel après implémentation,
y compris les conflits découverts. Rien de ce qui suit n'était encore commité avant cette
note — c'est la première trace versionnée de ce travail.*

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
   Bloc 3. Son API `/api/active-ads` time-outait le 2026-07-18 ; retestée le 2026-08-04, elle
   répond (HTTP 200, slot `"3"` présent) — le time-out semble résolu, mais l'origine exacte
   (redémarrage du service backoffice ? autre chose ?) n'a pas été investiguée.
3. `cs-regie.php` (skin + gouttières) est passé en v0.2 le 2026-08-04 : il lit désormais ses
   créatives depuis le back-office (`utils/ads.py`, page `/ads`), au lieu d'une option WP
   statique jamais remplie. **Toujours pas déployé sur le VPS WordPress** (le fichier vit dans
   ce dépôt, pas encore copié en `wp-content/mu-plugins/`) — reste à trancher s'il doit
   remplacer notre Bloc 4, comme prévu au point 1.
4. Décider si `single-event-meta.php` doit passer par `the_content()` pour que l'insertion
   automatique Ad Inserter fonctionne réellement sur les fiches événement.

## Mise à jour 2026-08-04 — régie skin/gouttières câblée au back-office

En creusant la demande « aller jusqu'au test avec le back-office » pour skin/gouttières, on a
découvert que **le back-office qui sert `/api/active-ads` et `/go/<id>` est le Flask de ce
dépôt** (`app/app.py`, gunicorn sur `127.0.0.1:8098`, exposé par `deploy/traefik-backoffice.yml`)
— mais que ces deux routes n'existaient dans **aucun fichier de ce dépôt**, alors que le
serveur les sert bel et bien en prod (vérifié en direct : le slot `"3"` répond avec une vraie
créative). Même dérive non versionnée que pour WordPress (conflit #2 ci-dessus), côté backoffice
cette fois — et plus risqué ici, parce que `deploy.sh` fait un `git reset --hard` à chaque
déploiement : le prochain déploiement aurait silencieusement effacé ce code jamais commité.

Ajouté dans ce dépôt pour combler le vide, **sans avoir vu le code réellement en prod** (pas
d'accès SSH dans cette session) :
- `utils/ads.py` : table `ad_slots` (slots `3`/`skin`/`left`/`right`), `/api/active-ads`,
  `/go/<id>` (clic compté). Le slot `"3"` est **reconstruit à l'identique du contrat observé**
  (même `id=2`, pour ne pas casser le lien `/go/2` déjà diffusé) — si le code non versionné
  faisait autre chose (rotation, quota…), ce n'est PAS reproduit.
- Page back-office `/ads` (protégée, nav « Régie pub ») : active/désactive chaque slot, règle
  image + lien annonceur, affiche le compteur de clics.
- `cs-regie.php` v0.2 (détail au point 3 ci-dessus).

**Pas encore fait** : déployer `cs-regie.php` sur le VPS WordPress, pousser `app/app.py` /
`utils/ads.py` sur le VPS backoffice (`deploy.sh`) et vérifier en conditions réelles que le
slot `"3"` reconstruit se comporte bien comme l'ancien code invisible (notamment le lien
`/go/2` déjà en circulation).
