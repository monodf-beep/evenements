# Règles de sélection des images d'événements

*Comment le pipeline choisit — et surtout REFUSE — une image pour illustrer un
événement (carte d'article ET visuel Instagram, même champ `url_image`). Deux
défenses complémentaires : des **règles déterministes** (gratuites, toujours
actives) et un **agent vision** (payant, ciblé sur la publication).*

## Pourquoi

La chaîne de résolution récupère une image « trouvée sur la page source ». Sans
garde-fou, elle attrape parfois de l'**habillage de site** au lieu de la photo de
l'événement : bandeau de campagne (« Don d'organes », « Territoire engagé pour le
climat »), slider de page d'accueil, image de test (`test2.png`), visuel de
newsletter. Un grand hors-sujet est PIRE qu'un petit pertinent.

Leçon apprise (juillet 2026) : un filtre qui rejetait les petites images et
« descendait chercher plus grand » a fait exactement ça — il préférait les gros
bandeaux. Corrigé. La bonne réponse à une image trop petite, c'est le **fond
abstrait** au rendu (`utils.social_image`), jamais « aller chercher une autre image ».

## La chaîne (du meilleur au repli)

`scripts/visuals.resolve_image` :

1. **og:image** de la page officielle (image de partage — la plus pertinente) ;
2. **1re photo de contenu** de la page (pages sans og:image) ;
3. **Wikimedia Commons** (photo licenciable, requête rédigée par le LLM) ;
4. **bannière de marque** du territoire (repli garanti).

Chaque candidat des étages 1-3 doit passer **les deux défenses** ci-dessous, sinon
on descend d'un étage.

## Défense 1 — Règles déterministes (toujours, gratuit)

`utils.image_verify.looks_parasitic(url)` + les filtres historiques. Une image est
refusée si son URL :

- provient d'un **domaine proscrit** (presse/agrégateur — `is_blocked_image`) ;
- est un **logo/icône** (`is_logo_image`) ;
- correspond à un **motif parasite connu** listé dans
  **`config/blocked_image_patterns.txt`**.

**Ajouter un parasite = ajouter une ligne** à ce fichier (sous-chaîne d'URL,
insensible à la casse). Aucun code à toucher. Pour en trouver de nouveaux, une image
partagée par beaucoup d'événements SANS RAPPORT est presque toujours de l'habillage :

```sql
SELECT url_image, COUNT(*) n FROM events_raw
WHERE image_source IN ('og','page','web') AND COALESCE(url_image,'')<>''
GROUP BY url_image HAVING n > 2 ORDER BY n DESC;
```

*(Attention : une même affiche partagée par plusieurs sous-événements d'un MÊME
festival est légitime — vérifier avant de blocklister.)*

## Défense 2 — Agent vision (ciblé sur la publication)

`utils.image_verify.verify_relevance(...)` : un LLM (Haiku par défaut, économique)
regarde l'image et dit si elle correspond VRAIMENT à l'événement. C'est le seul
garde-fou capable de dire « ce ruban vert est une campagne don d'organes, pas une
reconstitution historique ». Il refuse : bandeaux/pubs, logos, captures, affiches
tout-texte, habillage de site, images sans rapport.

Où il tourne :

| Contexte | Règles (déf. 1) | Agent vision (déf. 2) |
|---|---|---|
| Ingestion en masse (`visuals.py`) | ✅ toujours | ⬜ sur `--verify` seulement (coût) |
| Publication / réparation (`refill_images_as.py`) | ✅ toujours | ✅ par défaut (sauf `--no-verify`) |
| Agent web de dernier recours (`images_web.py`) | ✅ | ✅ (c'était déjà son rôle) |

Principe : en masse, on fait confiance aux règles (gratuit) ; **au moment de publier,
la pertinence prime**, l'agent vérifie. Modèle réglable via `ANTHROPIC_MODEL_VISION`.

## Réparer l'existant

`scripts/refill_images_as.py` :

- `--recheck "page,web"` — ré-résout tous les événements publiés dont l'image vient du
  scan de page (là où les parasites se logent), avec règles + agent, et ne re-pousse
  que si l'image change réellement.
- `--bad-url "<sous-chaîne>"` — cible un parasite précis par son URL.
- `--lowres` — remplace les images trop petites par une plus grande (jamais une
  dégradation, jamais une vraie photo troquée pour une bannière).

## Recadrage / point focal (juillet 2026)

L'agent vision (défense 2) ne se contente plus d'accepter/refuser : quand il valide
une image, il propose aussi un **point focal** `(focal_x, focal_y ∈ [0,1])` — utile
seulement si l'image est PAYSAGE et sera recadrée en 4:3 « cover » (une affiche
PORTRAIT part en letterbox, cf. `utils.card_image`, jamais recadrée). Le focal évite
que le recadrage coupe un **visage** ou une **zone de texte informatif** (horaires,
prix, adresse) incrustée en bas de la photo.

`scripts.visuals.resolve_image(...)` renvoie désormais `(url, credit, source,
focal_x, focal_y)`. Écrit dans `events_raw.card_focal_x/y` **seulement si NULL** —
un cadrage réglé à la main au back-office (`/set-focal/<id>`) n'est **jamais**
écrasé par la suggestion automatique.

## Vignette 4:3 sans « marges blanches »

`utils.card_image.make_card()` produit TOUJOURS une image qui remplit entièrement le
cadre 4:3 (recadrage « cover » ou letterbox flou) — jamais de marge blanche. Si une
carte affiche quand même des marges blanches côté WordPress, ce n'est pas cette
vignette qui est montrée : `scripts/publisher_as.py` téléverse la vignette 4:3 en
`featured_media_id` (prioritaire), mais si cet upload échoue (timeout/504, fréquent
sur l'hébergement mutualisé), `cs-publish.php` retombe sur `image_url` — l'affiche
BRUTE, non recadrée, jamais générée par `card_image` — comme image à la une. Deux
protections : `scripts/publisher.py::_upload_featured_media` réessaie 3 fois sur
échec transitoire (5xx/timeout) avant d'abandonner ; en cas de carte déjà cassée,
`refill_images_as.py --wp-ids <id WordPress>` force un nouvel upload carté.

## Ce qui n'est PAS de ce ressort

- **Image trop petite** → le rendu social bascule sur le **fond abstrait**
  (`utils.social_image._abstract_bg`) ; on ne va jamais chercher une autre image.
