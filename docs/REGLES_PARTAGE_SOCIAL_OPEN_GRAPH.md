# Règles de partage social (Open Graph / X) · Agenda Sabauda

*Ce qui se passe quand quelqu'un colle une URL du site dans WhatsApp, Facebook, LinkedIn,
Slack, Discord ou X. À lire avec `REGLES_SEO_GEO_AEO_AGENDA_SABAUDA.md` (référencement) et
`BRIEF_DESIGN_AGENDA_SABAUDA.md` (charte).*

**Implémentation vivante :** `wp-content/mu-plugins/cs-open-graph.php` sur le site.
Rollback : supprimer ce fichier, Yoast reprend seul la main.

---

## 0. Le principe

Un lien partagé est souvent le **premier contact** avec le site : il circule hors de tout
contexte, dans un fil de discussion. S'il apparaît sans image, avec un titre plat et une
description aspirée du contenu, il ne sera pas cliqué. Les métadonnées de partage ne sont donc
pas un détail technique mais un **support éditorial à part entière**.

Corollaire appliqué ici : les textes de partage sont **écrits**, jamais extraits automatiquement
du contenu de la page.

---

## 1. Les six critères, et leurs seuils réels

| Critère | Cible | Pourquoi |
|---|---|---|
| `og:image` | **1200×630** (ratio 1.91:1) | Format attendu par Facebook, LinkedIn, WhatsApp, X. Un 4:3 ou 16:9 est rogné ou encadré de bandes. |
| Poids image | **< 300 Ko** | Plafond technique 8 Mo (Facebook), mais un aperçu lent n'est pas généré à temps. |
| `og:title` | **≤ 60 caractères** | Au-delà, l'aperçu tronque brutalement, souvent en plein mot. |
| `og:description` | **≤ 125 caractères** | Seuil plus bas qu'on ne croit : 146 passe en recherche Google mais est tronqué sur mobile. |
| `twitter:card` | **`summary_large_image`** | Seule balise X indispensable. Sans elle, X n'affiche qu'une vignette. |
| `og:site_name` | **« Agenda Sabauda »** | Discord, Slack et LinkedIn l'affichent en surtitre. Sans elle, l'aperçu paraît orphelin. |

### Facultatif mais recommandé

`twitter:title`, `twitter:description`, `twitter:image` ne sont **pas nécessaires** : X retombe
sur les `og:` équivalentes. On les déclare quand même, ça ne coûte rien et évite les surprises
si une plateforme change de comportement.

### Le piège à ne pas rater

`og:url` **doit être identique à la balise canonique**, préfixe de langue compris. C'est
l'identité de la page pour les réseaux : une incohérence disperse les compteurs de partage sur
plusieurs adresses. Bug réellement rencontré le 2026-07-20 sur les fiches italiennes
(`og:url` sans `/it/`, canonique avec).

---

## 2. Quelle image pour quel type de page

| Type de page | Image de partage |
|---|---|
| Fiche événement | **Le visuel de l'événement**, recadré en 1200×630 |
| Fiche sélection (carrousel) | **Le visuel de la sélection**, recadré en 1200×630 |
| Home, listes, hubs, pages éditoriales | **Image de marque** (une par langue) |

Règle : quand une image spécifique et parlante existe, elle prime sur le logo. Un visuel
d'événement donne bien plus envie de cliquer qu'une image générique.

### Recadrage à la demande

Les visuels d'événement sont en 4:3 dans la médiathèque. La version 1200×630 est **générée une
seule fois par image, à la première demande**, puis réutilisée (`cs_og_crop()`). On évite ainsi
de régénérer massivement la médiathèque.

**Limite connue :** le recadrage est centré. Sur une affiche verticale dont le texte est en haut,
le cadrage peut mal tomber. À surveiller au cas par cas.

---

## 3. Textes de partage par type de page

Écrits, jamais aspirés. Ce qu'il ne faut pas produire (constaté avant correction) :
« Publicité Annoncer sur Agenda Sabauda → », « Immagine da definire Itinerario da definire ».

| Page | Titre FR | Titre IT |
|---|---|---|
| Home | Agenda Sabauda : quoi faire, où manger | Agenda Sabauda : cosa fare, dove mangiare |
| Ce week-end | Que faire ce week-end ? | Cosa fare questo weekend ? |
| Aujourd'hui | Que faire aujourd'hui ? | *page IT à créer* |
| Cette semaine | Que faire cette semaine ? | *page IT à créer* |
| Tout l'agenda | Tout l'agenda | Tutti gli eventi |
| Hub territoire | *Nom* : que faire ? | *Nome* : cosa fare |
| Hub catégorie | *Nom de la catégorie* | idem |
| Musées | Musée : les événements | Musei : gli eventi |
| Fiche événement | Titre de l'événement | idem |

**Description de fiche événement :** date puis lieu (« Le 24 juillet 2026 · Forte di Bard,
Bard »). Concret et immédiatement utile, plutôt qu'un extrait de texte tronqué.

**Description de repli** (toutes les autres pages) :
- FR : « L'agenda culturel de l'espace alpin occidental : Savoie, Piémont, Vallée d'Aoste et Nice. »
- IT : « L'agenda culturale dello spazio alpino occidentale : Savoia, Piemonte, Valle d'Aosta e Nizza. »

### Troncature

Couper soi-même, **sur un mot entier**, avec points de suspension (`cs_og_couper()`). On garde
ainsi la maîtrise de l'endroit de coupe au lieu de subir celle de la plateforme.

---

## 4. Langue

`og:locale` doit refléter la langue **réelle de la page** : `fr_FR` ou `it_IT`, avec
`og:locale:alternate` pour l'autre. Défaut constaté avant correction : `fr_FR` servi même sur
une fiche italienne.

---

## 5. Cohabitation avec Yoast

Yoast reste en charge du **titre SEO, de la meta description, de la balise canonique, des
sitemaps et des données structurées**. Seules les balises de partage sont reprises.

**Point technique important :** les filtres historiques (`wpseo_opengraph_*`) n'ont plus d'effet.
Depuis Yoast 14, la sortie passe par des *presenters*. C'est ce qui produisait une `og:image` en
double sur la home, la mauvaise passant en premier. La neutralisation correcte se fait via le
filtre `wpseo_frontend_presenters`.

---

## 6. Règle typographique

**Jamais de tiret cadratin** (le caractère U+2014, « em dash ») dans les titres, descriptions,
métadonnées de partage et contenus publiés, y compris ceux générés programmatiquement.

Remplacer par une ponctuation naturelle selon le sens : deux-points, virgule, parenthèses,
point, ou point médian (·).

Exemple de correction appliquée : « Agenda Sabauda — Quoi faire » est devenu
« Agenda Sabauda : quoi faire ».

Vérification : `grep -rn $'—' docs/ deploy/` doit ne rien remonter, à l'exception de la
présente phrase de définition.

---

## 7. Comment tester

Le **Facebook Sharing Debugger exige un compte développeur** : souvent inutilisable en pratique.

Alternatives sans inscription :

| Outil | Adresse |
|---|---|
| OpenGraph.xyz | opengraph.xyz |
| metatags.io | metatags.io |
| LinkedIn Post Inspector | linkedin.com/post-inspector (compte LinkedIn ordinaire) |

**Le test le plus fiable** : coller l'URL dans une conversation WhatsApp, Telegram ou Signal
sans envoyer. L'aperçu se génère immédiatement, sans aucun compte.

**Attention au cache :** les réseaux conservent l'ancienne version, parfois plusieurs jours.
Pour contourner sans outil, ajouter `?v=2` à l'URL : c'est une adresse neuve pour le cache.

---

## 8. Besoins visuels à demander à Claude Design

Assets standards nécessaires, en complément des images de marque déjà produites
(`og-agenda-sabauda-fr.png` et `-it.png`, 1200×630, skyline + logotype + baseline).

### Prioritaires

| Asset | Format | Usage |
|---|---|---|
| Image de partage **par territoire** (×4, ×2 langues) | 1200×630 | Hubs territoire : un visuel identifiable par territoire plutôt que le logo générique |
| Image de partage **par grande catégorie** (concerts, expositions, gastronomie, famille) | 1200×630 | Hubs catégorie |
| **Gabarit de repli** pour événement sans photo | 1200×630 | Aujourd'hui, un événement sans image n'est pas affiché ; un gabarit permettrait de le partager quand même |

### Utiles

| Asset | Format | Usage |
|---|---|---|
| Déclinaison **carrée** de l'image de marque | 1200×1200 | WhatsApp Status, Instagram, certains agrégateurs |
| Déclinaison **verticale** | 1080×1920 | Stories Instagram / Facebook |
| Bandeau réseaux sociaux | 1500×500 | En-tête X / LinkedIn |

### Contraintes techniques à respecter

- Ratio **1.91:1 strict** pour l'Open Graph (1200×630), pas d'approximation
- Poids **< 300 Ko**, JPEG pour les photos, PNG pour les visuels avec texte
- **Zone de sécurité** : les plateformes rognent jusqu'à 5 % sur les bords. Aucun texte ni
  élément essentiel dans cette marge.
- Lisibilité **à 400 px de large** : c'est la taille réelle d'affichage dans un fil mobile.
  Un texte fin ou un logo détaillé devient illisible.
- Contraste suffisant en **mode sombre** : la plupart des messageries affichent les aperçus sur
  fond sombre.
