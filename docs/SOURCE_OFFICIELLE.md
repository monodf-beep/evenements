# La source officielle fait foi — chaîne d'enrichissement Agenda

*Principe (Franck) : avant toutes les règles de style, la **source officielle** (site de
l'événement + dossier de presse) est la PREMIÈRE source. Elle donne le vrai programme ET les
visuels, sans deviner. Tout est dans `scripts/enrich.py`.*

## 1. Trouver la source officielle (déterministe, puis vérifié)
1. **`url_officiel` mémorisée / verrouillée** → lue DIRECTEMENT (rien d'autre). Verrou manuel
   au back-office (« ✍️ Compléter à la main » → champ Site officiel).
2. Sinon on lit `url_source`. Si c'est un **agrégateur** (`_NOT_OFFICIAL` : agendaculturel,
   infoconcert, réseaux, billetteries…) ou s'il **bloque le VPS (403)** → on **résout le vrai
   site officiel par une recherche web ciblée** (`resolve_official_site`, 1 requête Sonnet).
3. Depuis une page-source accessible, on peut aussi suivre le **lien sortant** vers le site
   officiel (`_find_official_site`) : domaine qui recoupe le titre (accents pliés ; un token
   long ≥ 8 suffit) — jamais sur une simple ancre « en savoir plus ».
4. **Vérification + mémorisation** : une URL n'est retenue et écrite dans `url_officiel` que si
   elle **produit réellement des pages presse/programme**. Un agrégateur n'est JAMAIS mémorisé
   comme officiel. → déterministe aux runs suivants.

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

## 4. Deux scores
- **AVANT (pré-rédaction)** : si la matière officielle est là, on POUSSE l'article complet
  (`court=False`) même à llm_score moyen — on a tout pour bien faire.
- **APRÈS (`home_score`, 0-10)** : qualité panel lecteurs (0-6) + source officielle (+2,5) +
  affiches (portrait+paysage +1,5 / une +0,75). Colonne `home_score` → méta `as_home_score` →
  tri des sections « À la une / En évidence » de la home (JetEngine, cf. `docs/CABLAGE_HOME.md`).

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
