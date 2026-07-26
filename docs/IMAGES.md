# Les images — comment on en trouve de bonnes

*État des lieux du pipeline image de Cultura Sabauda / Agenda Sabauda (26 juillet 2026). Décrit le système RÉEL (tel qu'il est codé), qui fait quoi, les astuces accumulées, et les leviers de qualité. Document de travail — à relire et amender.*

---

## 1. Le principe (posture de droits)

Cultura Sabauda est un **média publié**. On n'affiche donc pas « une image trouvée sur le web » (risque de droit d'auteur, au même titre qu'un contenu sous paywall). On tire d'une **source licenciable, avec crédit** :

- **Wikimedia Commons** (CC / domaine public) — crédit auteur + licence automatique ;
- la **photo de partage officielle** (og:image) de la page de l'événement, du lieu ou de l'artiste (institutionnel) ;
- à défaut, une **bannière de marque** du territoire (repli maison, toujours licite).

On **évite les photos d'agence / de presse**. Une carte n'est **jamais vide** : il y a toujours un repli garanti (bannière).

---

## 2. La chaîne de résolution — du meilleur au repli

Le cœur est `scripts/visuals.py → resolve_image()`. Chaque événement sans image descend la chaîne jusqu'au premier candidat qui **passe les deux défenses** (§3) :

| Étage | Source | Qui décide | Coût | Note |
|---|---|---|---|---|
| **1** | Image du **flux RSS** | — (déjà en base) | 0 | On ne touche pas à une vraie photo déjà valide (`keep_existing`). |
| **2** | **og:image** de la page officielle | **code** (déterministe) | 0 | Jamais pour un *radar* (ce serait une image de presse). |
| **2b** | **1re vraie photo de contenu** de la page | **code** | 0 | Pour les pages sans og:image (offices de tourisme…). |
| **3** | **Wikimedia Commons** | **LLM** rédige la requête, **code** cherche/filtre | ~1 appel Haiku | Photo licenciable + crédit. |
| **3b** | **Europeana** (musées/bibliothèques du territoire) | **LLM** requête (la même), **code** filtre | ~0 | Licenciable + crédit. **INACTIF sans `EUROPEANA_API_KEY`** (expérimental, à valider). |
| **3-bis** | **Agent web** (recherche + vision) | **LLM** cherche, **2e LLM** vérifie | recherche web + vision | **Dernier recours** (le plus cher), haut du panier (`scripts/images_web.py`). |
| **4** | **Bannière** territoire × catégorie (`fallback-*`) | **code** | 0 | Repli **garanti**, jamais parasite. |

**Répartition LLM / code (charte `docs/LLM_OU_CODE.md`)** : le LLM ne fait que le **jugement** (« quoi photographier », « cette image colle-t-elle ? »). La **recherche, le filtrage et le repli restent déterministes**.

Ordre réel dans le pipeline automatique (`autocomplete._fill_image`), **depuis 2026-07-26** : on lance d'abord la **chaîne déterministe** (og → contenu → Commons → Europeana) — gratuite/économique ; l'**agent web payant n'intervient qu'en dernier recours**, si le déterministe n'a rien donné de mieux qu'une bannière. *(Avant, l'agent web passait en premier — coûteux et souvent inutile puisque l'og:image officielle suffit.)*

---

## 3. Les deux défenses (anti-hors-sujet)

Tout candidat, à chaque étage, doit passer **deux filtres complémentaires** (`utils/image_verify.py`) :

1. **Règles déterministes** (gratuites, toujours actives) :
   - domaine proscrit (`config/blocked_image_domains…`), logo/blason/icône (`is_logo_image`) ;
   - motif d'URL parasite connu (`config/blocked_image_patterns.txt` : slider, header, banniere, pub…) — extensible **sans code** ;
   - **forme** suspecte (`looks_like_banner_shape`) : trop plat/étroit = bandeau, trop carré = vignette CMS générique (voir seuils §5).

2. **Agent vision** (`verify_relevance`, payant, ciblé) : un LLM **regarde** l'image et dit si elle correspond VRAIMENT à l'événement. C'est le seul capable de dire « ce ruban vert est une campagne don d'organes, pas l'événement ». Il renvoie aussi le **point focal** (§6). Il refuse : bandeaux/pubs/logos/captures/affiches-tout-texte, **portrait d'une personne qui n'est pas le sujet**, photo du **bâtiment** quand le sujet est une personne/œuvre, **saison** incompatible visible, **paysage naturel générique** pour un événement urbain.

En cas de panne technique (image injoignable), on **ne bloque pas** — les règles déterministes ont déjà filtré, et la vérification se refait au moment de publier.

---

## 4. Qui fait quoi (scripts & modules)

- **`scripts/visuals.py`** — l'orchestrateur de la chaîne (« Compléter les visuels »). `resolve_image()` applique les 4 étages ; `visual_query()` = le prompt LLM qui propose la requête Commons.
- **`scripts/images_web.py`** — le **dernier recours** : agent Claude **avec recherche web** pour dénicher une photo du sujet, puis **second agent vision** qui valide. Réservé au haut du panier (retenu, daté, à venir, score ≥ seuil, pas encore de vraie image). Modèle recherche = Sonnet ; vérif = Haiku.
- **`utils/images.py`** — la boîte à outils **déterministe** : `fetch_og_image`, `fetch_content_image`, `commons_search`, `remote_dims`, `looks_like_banner_shape`, seuils.
- **`utils/image_verify.py`** — les **deux défenses** en un seul endroit (`looks_parasitic` + `verify_relevance` + `season_fr`).
- **`utils/sources.py`** — domaines/logos proscrits, bannières territoire × catégorie (`pick_banner_image`).
- **`scripts/publisher_as.py`** — à la **publication** : téléverse l'image en « featured media » WordPress (`_upload_featured_media`), avec `_recover_image` (og→photo de contenu) si besoin, et **repli bannière** si le téléversement échoue ou si c'est un logo.
- **Rendu social** : `utils/card_image.py` (carte back-office) et `utils/social_image.py` (visuels réseaux) — cadrage, point focal, fond abstrait (§6).

---

## 5. Les astuces (leçons apprises, souvent dans la douleur)

- **Cibler le SUJET, jamais le LIEU** *(incident « Yerai Cortés », juillet 2026)*. Une requête « Fondation Maeght » ramène l'architecture et un portrait de l'architecte (Josep Lluís Sert) — jamais le concert de flamenco. Le nom de l'artiste / de l'œuvre est le meilleur sujet ; le lieu n'est un bon sujet que s'il **est** le sujet (visite de monument), et on vise alors le **bâtiment**, jamais une personne liée au lieu.
- **Petite pertinente > grande parasite** *(incident « DON D'ORGANES »)*. On ne va jamais « chercher plus grand » sur une page au risque d'attraper un bandeau de campagne. Une petite vraie photo de l'événement vaut mieux qu'une grande image sans rapport ; si elle est trop petite pour le rendu social, c'est l'affichage qui bascule sur le fond abstrait.
- **Ne JAMAIS dégrader une image déjà valide** (`keep_existing`). Si l'événement a déjà une og/photo de page qui passe les défenses, on la garde — pas question de la troquer contre un résultat Commons de moindre confiance.
- **Commons cherche le MÊME sujet** : quand on complète une petite photo de page, Commons vise précisément le sujet (pas « une grande image quelconque »), ce qui évite le piège « grand mais hors-sujet ».
- **Le nom du fichier Commons est un indice** (« File:Marché Saint-Ours Aoste.jpg ») donné à l'agent vision : utile quand l'image seule est ambiguë.
- **Saison cohérente** : pas de prairie verte pour un événement de janvier, pas de neige en juillet — sauf intérieur/monument où la saison ne se voit pas.
- **Pas de paysage alpin par défaut** : si l'événement n'a rien à voir avec la nature, on évite lac/sommet/vallée génériques juste parce que le territoire est montagneux.
- **Radar = presse** : jamais d'og:image pour une source radar (droits).
- **Lire les pages en UA navigateur** : certains sites servent une page vide/403 à un bot mais tout à un navigateur (`_PAGE_UA`).
- **Retries Wikimedia** : `upload.wikimedia.org` renvoie par intermittence un 400 en rafale — sans retry, une bonne photo serait faussement mesurée à 0 et remplacée à tort.

---

## 6. Seuils & rendu (les chiffres qui comptent)

**Filtres de forme/taille** (`utils/images.py`) :
- `MIN_DIM = 700` px (plus petit côté) : sous ce seuil, l'image floute une fois étirée aux formats sociaux (un og standard 600×315 est sous le seuil → on cherche mieux).
- `MAX_ASPECT = 2.5` : au-delà, la forme trahit un **bandeau** (large et plat, ou colonne étroite).
- `MIN_ASPECT = 1.15` : en dessous (trop carré), c'est une **vignette CMS générique** (miniature de partage 1:1, avatar) qui a perdu l'info réelle. *(Repère de Franck.)*
- `commons_search(thumb_width=2400)` : nos formats sociaux sont **portrait** (jusqu'à 1080×1920) et beaucoup de photos Commons sont paysage — une miniature 1200px de large ne fait que ~700px de haut. 2400px couvre la hauteur *(cas château de Montrottier : original 5337×3138, miniature 1280 refusée à tort).*

**Rendu** (`card_image.py`, `social_image.py`) :
- **Affiche portrait** → **letterbox** (jamais recadrée, on garde tout le visuel).
- **Photo paysage** → **cover 4:3** recadré autour du **point focal** (x,y ∈ [0,1]) fourni par l'agent vision, pour ne couper ni visage, ni titre incrusté, ni zone de texte.
- Agrandissement **plafonné** (`MAX_UPSCALE`) : au-delà, on bascule sur un **fond abstrait** dérivé de l'image plutôt qu'une bouillie de pixels.
- Le **point focal réglé à la main** au back-office n'est **jamais** écrasé par le pipeline (`COALESCE`).

---

## 7. Où ça se déclenche (câblage)

- **Pipeline quotidien** — `autocomplete.py` complète les fiches retenues incomplètes (dont l'image : agent web puis chaîne déterministe). `gmail_collect.py` appelle aussi `visuals`.
- **Back-office** — bouton **« Compléter les visuels »** (lance `visuals` sur une période) et **éditeur de point focal** (route `/…focal…` dans `app.py`).
- **Publication** — `publisher_as` téléverse l'image en featured media WordPress au push (sauf `skip_media=True` = mise à jour texte seul), avec récupération og et repli bannière.

---

## 8. Maintenance & réglages

**Outils de contrôle** :
- `scripts/image_audit.py` — audit des images posées (source, permaliens).
- `scripts/refill_images_as.py` — re-remplissage / amélioration d'images en masse.
- `scripts/conform_articles.py`, `scripts/upgrade_category_banners_as.py` — mises en conformité.

**Config sans code** :
- `config/blocked_image_patterns.txt` — motifs d'URL parasites (ajout à chaud).
- domaines d'images proscrits + bannières **territoire × catégorie** (`utils/sources.py`).

**Variables d'environnement** :
- `VISUALS_CAP` (défaut 80) — plafond d'événements par lancement.
- `ANTHROPIC_MODEL_VISUALS` / `_VISION` / `_SEARCH` — modèles par étape (défauts : Haiku pour requête & vision, Sonnet pour recherche web).
- `AUTOCOMPLETE_VERIFY_IMAGES` (défaut **on**) — vérif vision **dès la pose** dans le pipeline auto ; `=0` pour couper (économie).
- `EUROPEANA_API_KEY` — active l'étage 3b Europeana (absent = étage sauté, sans erreur).

---

## 9. Décisions & questions

### Tranché / fait (2026-07-26)
- **Ordre agent-web / Commons (A) — FAIT** : chaîne déterministe (og→contenu→Commons→Europeana) d'abord, agent web payant en dernier recours. Économie sans perte (l'og officielle suffit le plus souvent).
- **Vérif vision plus tôt (B) — FAIT** : agent vision actif **dès la pose** dans le pipeline auto (`AUTOCOMPLETE_VERIFY_IMAGES`, défaut on). Écarte les hors-sujet en amont.
- **Nouvelle source licenciable (C) — FAIT (à activer)** : étage 3b **Europeana** (musées/bibliothèques du territoire), inactif sans `EUROPEANA_API_KEY`. **Expérimental** : à valider en conditions réelles (pertinence/qualité des fonds variable) avant de s'y fier.

### Encore ouvert
- **Seuils** : `MIN_DIM=700`, `MAX_ASPECT=2.5`, `MIN_ASPECT=1.15`, `thumb_width=2400` — te conviennent, ou on ajuste ?
- **Crédit** : bien affiché partout (carte, réseaux, WordPress) ? (`as_image_credit` écrit au push, ligne 202 de `publisher_as`.)
- **Vocabulaire des requêtes** : `visual_query` pourrait intégrer le lexique sabaud (« marché de la Saint-Ours Aoste » plutôt qu'un générique) — jonction chantier rédaction.

---

## 10. Modèle de repli : bake vs runtime (tranché)

**Constat prouvé (event 2222, live) :** le repli WordPress `cs_fallback_visual` (snippet 87) filtre `_thumbnail_id` au **niveau données** (pas seulement l'affichage) → quand un événement n'a pas de vraie miniature, Yoast en dérive l'`og:image` = `fallback-{terr}-{cat}-og1200x630.png`, **sans aucun bake côté pipeline**. Les crawlers (front-end) voient donc le bon fallback de catégorie.

**Piège :** snippet 87 est **scope front-end** (inactif en REST/admin/CLI). Un consommateur lisant la featured image hors front-end ne verrait rien — **mais vérifié côté pipeline : aucun ne le fait** (`ig_scheduler` lit `url_image`/`wp_raw_image` en base, jamais la featured media via REST ; tous les `featured_media` du code sont des écritures au push).

**Décision : arrêter de baker une copie par événement.** Le runtime couvre le front-end (og/partage/SEO) ; le signal « pas de photo » reste honnête via `image_source='banner'` (l'audit le filtre déjà). Pas besoin de la piste « attachement partagé » (#3) tant qu'aucun consommateur REST n'apparaît.

**FAIT côté pipeline (2026-07-26, `publisher_as`)** — trois verrous :
1. La featured media n'est **plus téléversée** quand `image_source == 'banner'` (l'affiche/récupération réelles, elles, montent toujours).
2. Le **Repli 2 `_banner()` est retiré** du flux de push (fonction conservée mais non appelée).
3. `image_url` et `as_image_original` sont **vidés** pour une bannière (sinon l'endpoint la re-télécharge → re-bake).
Résultat : événement sans vraie photo → `_thumbnail_id` vide → repli runtime WordPress. La bannière **reste dans `url_image`** (carte back-office + compositeur réseaux couverts ; pas de trou social à combler — le point #3 initial devient sans objet).

*Reste à faire, côté SITE (conversation dédiée) : nettoyer les ~42 vignettes déjà bakées dans la média-thèque WordPress pour qu'elles repassent au repli runtime. Rien de bloquant : les nouveaux push sont déjà propres.*
