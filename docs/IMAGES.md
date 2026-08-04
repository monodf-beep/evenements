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
| **3-bis** | **Agent web** (recherche + vision) | **LLM** cherche, **2e LLM** vérifie | recherche web + vision | Dernier recours, haut du panier seulement (`scripts/images_web.py`). |
| **4** | **Bannière** territoire × catégorie | **code** | 0 | Repli **garanti**, jamais parasite. |

**Répartition LLM / code (charte `docs/LLM_OU_CODE.md`)** : le LLM ne fait que le **jugement** (« quoi photographier », « cette image colle-t-elle ? »). La **recherche, le filtrage et le repli restent déterministes**.

Ordre réel dans le pipeline automatique (`autocomplete._fill_image`) : on tente d'abord **l'agent web** (meilleure photo pertinente) si autorisé et hors cooldown, **puis** la chaîne déterministe og→Commons→bannière.

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
- **La liste des domaines proscrits doit couvrir la presse RÉGIONALE, pas seulement
  la nationale** *(incident du 4 août 2026)*. `config/blocked_image_domains.txt` était
  hérité d'un autre projet et bloquait Le Monde, Le Figaro, BFMTV. Or la presse qui
  couvre nos événements, c'est Le Dauphiné Libéré, Nice-Matin, La Stampa, Aosta Oggi.
  Résultat sur le site live : **41 fiches** illustrées par une photo de presse ou
  reprise chez un agenda concurrent (agendaculturel.fr). La règle §1 était juste, la
  liste était fausse. Leçon générale : une règle de droit qui s'appuie sur une liste
  doit être auditée sur les données réelles, pas seulement énoncée dans un document.
- **Un crédit ne régularise pas une image de presse.** Quand une photo n'est pas
  licenciable, la seule issue est le remplacement ou le repli, jamais l'ajout d'une
  ligne d'attribution. On ne crédite que ce qu'on a le droit d'afficher.
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

## 7 bis. Côté WordPress (le site live) — repli, piège de détection, crédit

> *Ajout depuis la branche site (`claude/agenda-sabauda-homepage-test-exckrp`,
> 2026-07-26). Le pipeline s'arrête au téléversement du featured media ; voici ce
> que fait le SITE ensuite. À fusionner avec le reste du doc.*

**Le repli du site (jumeau de l'étage 4).** Le site a son PROPRE repli, indépendant
du pipeline : `cs_fallback_visual()` (snippet 21) + snippet 87 « Fallback visuel =
thumbnail (home + partout) ». Quand un événement n'a pas de vraie miniature, le site
sert à l'affichage l'un des **48 visuels** de la médiathèque
(`fallback-{territoire-fr}-{categorie-fr}.jpg`, 4 territoires × 12 catégories), avec
repli sur un aplat de couleur si le fichier manque. C'est le pendant, côté rendu, de
la bannière territoire × catégorie de l'étage 4.

**⚠️ Deux modèles de repli concurrents — à trancher.** Les deux branches divergent
aujourd'hui :
- **Branche pipeline** : `publisher_as._banner()` **bake** une bannière territoire
  comme featured media WordPress quand l'image échoue ou est un logo (§4).
- **Branche site** : ce repli pipeline a été **retiré** (« Repli 2 retiré le
  2026-07-23 ») au profit du repli runtime `cs_fallback_visual` ci-dessus.

Avoir les DEUX est redondant et a un effet de bord (le piège ci-dessous). **Décision
à prendre** : le repli est-il baké à la publication (pipeline) ou servi à l'affichage
(site) ? Avis côté site : **le repli runtime** (snippet 87), car il reste correct même
si le territoire/catégorie d'un événement change après coup, et il n'encombre pas la
médiathèque de copies de bannières.

**Le piège de détection « sans photo » (leçon dans la douleur, 2026-07-26).** Tant que
le pipeline bake des bannières, un événement « sans vraie photo » a quand même un
`_thumbnail_id` **non vide** (il pointe la bannière). Conséquence pour tout audit :
- compter « sans image » par *miniature vide* renvoie **0 à tort** ;
- il faut tester si le **slug de la miniature commence par `fallback-`**.

Réel au 2026-07-26 : **19 FR + 23 IT** événements futurs affichent un repli (héritage
des bannières bakées). `scripts/image_audit.py` gagnerait à distinguer trois états :
**vraie photo / bannière bakée / repli runtime**. Détail et liste :
`PHOTOS_MANQUANTES_EVENEMENTS.md`.

**Le crédit, jusqu'au bout de la chaîne (réponse à la question §9.5).** Côté site, le
crédit vit dans les métas **`as_image_credit`** / **`cs_credit`** et s'affiche sous
l'image de la fiche. Pour que la chaîne tienne, le pipeline doit écrire le crédit
(auteur + licence Commons) dans `as_image_credit` au push, sinon une photo licenciable
arrive sur le site sans sa mention. À vérifier côté `publisher_as`.

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

---

## 9. Questions ouvertes / pistes (pour tes retours)

1. **Seuils** : `MIN_DIM=700`, `MAX_ASPECT=2.5`, `MIN_ASPECT=1.15`, `thumb_width=2400` — te conviennent, ou on ajuste ?
2. **Agent web en premier** : aujourd'hui le pipeline auto tente la recherche web **avant** Commons. Coût vs qualité : on garde cet ordre, ou Commons d'abord (moins cher) et web seulement si Commons échoue ?
3. **Vérif vision** : par défaut elle tourne surtout à la publication (gratuit ailleurs). Faut-il l'activer plus tôt/systématiquement (plus sûr, plus cher) ?
4. **Sources licenciables** : aujourd'hui Commons + og officiel. Ouvrir à d'autres banques libres (Europeana, collections de musées du territoire) ? Ça collerait à la ligne sabaude.
5. **Crédit** : bien affiché partout (carte, réseaux, WordPress) ? À vérifier avec toi.
6. **Vocabulaire des requêtes** : faut-il que `visual_query` intègre le lexique sabaud (chercher « marché de la Saint-Ours Aoste » plutôt qu'un générique) — jonction avec le chantier rédaction ?
