# La source officielle fait foi — chaîne d'enrichissement Agenda

*Principe (Franck) : avant toutes les règles de style, la **source officielle** (site de
l'événement + dossier de presse) est la PREMIÈRE source. Elle donne le vrai programme ET les
visuels, sans deviner. Tout est dans `scripts/enrich.py`.*

## 1. Trouver la source officielle (déterministe, puis vérifié)
1. **`url_officiel` mémorisée / verrouillée** → lue DIRECTEMENT (rien d'autre). Verrou manuel
   au back-office (« ✍️ Compléter à la main » → champ Site officiel). La **page source**
   (page événement du flux) reste TOUJOURS lue en plus (matière événement : line-up, dates).
2. Sinon on lit `url_source`. **Seules les sources tier « officielle »** (lieu/organisateur,
   `config/sources.txt`) font foi de leur propre domaine. Toute autre source (radar/presse,
   guides type guidatorino, institutions, tourisme) ou une source **bloquée (403)** → on
   remonte au vrai site officiel : **lien sortant** d'abord (gratuit), sinon **recherche web
   ciblée** (`resolve_official_site`, 1 requête Sonnet).
3. Le **lien sortant** (`_find_official_site`) : domaine qui recoupe le titre (accents pliés ;
   un token long ≥ 8 suffit) — jamais sur une simple ancre « en savoir plus » ; à score égal,
   le **domaine racine** prime sur un sous-domaine (www.fortedibard.it, pas hotelcavour.*).
4. **Vérification + mémorisation** : une URL n'est écrite dans `url_officiel` que si elle
   produit des pages presse/programme **qui mentionnent l'événement** (pertinence par tokens
   du titre — nice.fr et ses pages municipales ne se figent plus). Un agrégateur n'est JAMAIS
   mémorisé. → déterministe aux runs suivants.

## 2. Lire le programme
On suit les pages **presse / programmation / line-up** (`_PROG_HINTS` + `_PRESS_HINTS`, FR+IT :
`presse`, `press`, `stampa`, `comunicat`, `programm`…), y compris les **dossiers de presse
chargés en iframe** (`<iframe src="/presse/">`). Si on a la matière officielle, la **recherche
web du rédacteur est coupée** (rapide, pas de troncature). Le web n'est qu'un secours.

## 3. Récupérer les affiches (portrait + paysage)
`extract_press_visuals` ne retient que des images **« affiche-grade »** : issues du dossier de
presse (`_KIT_PATH`) OU au nom d'affiche (`_AFFICHE_HINT` : affiche, visuel, poster, manifesto,
locandina…). Un nom de FORMAT (`120x176`) est un bonus, pas une éligibilité (sinon les vignettes
WordPress `-800x600.jpg` passeraient). Orientation tranchée par mesure réelle (`remote_dims`).
Stockées dans `url_image_portrait` / `url_image_wide`. **Verrou manuel** au back-office pour les
sites JS / dossiers gated (Musilac).

**Statut du dossier de presse** affiché au back-office (`press_kit_status`) : `public` (affiche
récupérée) · `accreditation` (réservé → demander l'accès) · `sans_affiche` (public mais visuel
non téléchargeable) · `absent`.

## 4. Deux scores + placement
- **AVANT (pré-rédaction)** : si la matière officielle est là, on POUSSE l'article complet
  (`court=False`) même à llm_score moyen — on a tout pour bien faire.
- **APRÈS (`home_score`, 0-10)** : qualité panel lecteurs (0-6) + source officielle (+2,5) +
  visuels. Hiérarchie des visuels : **affiches portrait+paysage +1,5** > **une affiche OU une
  PHOTO DU SITE OFFICIEL +0,75** (règle Franck : une photo issue du site officiel — ex. la
  photo Cazzullo de la page événement du Forte di Bard — garde la note haute) > rien.
  Colonne `home_score` → méta `as_home_score` → tri home (JetEngine, `docs/CABLAGE_HOME.md`).
- **PLACEMENT (📍 affiché sur la fiche)** : ≥ 8 + combo d'affiches → hero home ; ≥ 6 + affiche
  ou photo officielle → « En évidence » + newsletter AVEC visuel ; ≥ 6 sans visuel officiel →
  listes texte / brève sans visuel ; < 6 → catalogue.

## 4 bis. Panel lecteurs & révision
Panel ciblé par territoire (locaux pilotent la note ; visiteurs d'aires voisines = signal
« vaut le déplacement »). Révision déclenchée si moyenne locale < 3 (`ENRICH_REVISE_UNDER`) ;
on garde la MEILLEURE des deux versions (une révision peut faire pire). La révision peut
**creuser LE SITE OFFICIEL** (recherche restreinte à ses domaines — jamais le web ouvert)
pour répondre aux manques concrets du panel : horaires, parcours, accès, gratuité.

## 5. Garde-fous déterministes (en code, pas au bon vouloir du modèle)
- **Gras** imposé (charte) : dégraisse chiffres, noms propres, titres, phrases ; plafond 5.
- **Temporel** : `_dates_hint` calcule à venir / en cours / terminé vs aujourd'hui ; interdit
  « à venir »/« pas encore publié » pour un événement commencé, et le **« bluff rétro »**
  (présenter l'édition passée comme la programmation à venir).
- **Méta-vide interdit** : ne jamais écrire « à ce stade, la matière ne précise pas… ».
- **Hotlink** : le back-office lit les images en `no-referrer` (dossiers de presse protégés).

## Réglages (.env)
`ENRICH_WEB_SEARCH` (secours), `ENRICH_SITE_DEEP` / `ENRICH_SITE_SUBPAGES`, `ENRICH_MAX_TOKENS`,
`ENRICH_READER_REVIEW` / `ENRICH_READER_PERSONAS`, `ENRICH_REVISE_UNDER` (seuil révision, défaut 3).
