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

### 1 bis. La PAGE de l'événement, pas la racine du site (2026-09-08)

Franck : « quand on a une URL généraliste nom de domaine, c'est qu'on n'a pas la source de
la page qui nous donne l'événement. » Mesuré ce jour-là : **41 des 85 fiches publiées
encore devant nous** avaient pour `url_officiel` une racine (`montmelian.com/`,
`camera.to/`, `teatroregio.torino.it/`). Trois causes en chaîne : `resolve_official_site`
rend la racine par construction ; `_programme_links` ne suivait que les liens « presse » et
« programme », jamais le lien dont l'ancre dit le nom de l'événement ; et la mémorisation
écrivait `scheme://host/` même quand une sous-page avait été lue. Conséquences : pas
d'`og:image` (une racine n'en a souvent pas — Musicastelle), moisson et `images_wide` qui
lisent une page d'accueil, et un lien « source » qui envoie le lecteur sur l'accueil.

Depuis : un mot du titre dans le chemin ou l'ancre vaut 4 points dans `_programme_links`
(plus qu'un indice « programme »), et `_page_evenement` mémorise la sous-page qui
mentionne le titre — la racine n'est plus qu'un repli. Pour les fiches déjà écrites :
`scripts/affiner_source.py` (dry-run par défaut), puis moisson et re-push. Fixture :
`tests/test_source_page.py`.

### 1 ter. Les liens de traçage de newsletter — ce qu'ils rendent VRAIMENT (2026-09-08)

**Le constat.** Sur les 108 fiches approuvées, à venir et incomplètes, une vingtaine n'avaient
pour seule adresse qu'un lien de traçage (Brevo, MailUp, Arenametrix, Postmark, OpenEMM,
Sequar, le compteur de clics du département 06), et rien n'en avait jamais été récolté :
date `llm_none`, lieu vide, image jamais tentée. L'hypothèse de départ était « la moisson ne
suit pas les rebonds meta-refresh / JavaScript ». **Mesuré le soir même sur douze adresses,
téléchargées comme le fait `_robust_get` (même User-Agent, redirections suivies)** :

| famille | fiches | ce que rend le lien | ce qu'un jeton VOLONTAIREMENT FAUX rend |
|---|---|---|---|
| Brevo (`sendibm1.com`, `sp1-brevo.net`, `arenametrix.fr`) | 5292, 5098, 5252, 5315 | 404 « Brevo \| Page not found » | la même page |
| Postmark → OpenEMM (`track.pstmrk.it`) | 5303 | 404 « The url requested could not be found » | la même page |
| OpenEMM (`openemm.d40.it/r.html?uid=`) | 5153 | 302 → `/assets/rdir/404/404.html` (200, même hôte) | la même page |
| MailUp court (`tobe.musvc3.net/e/r`) | 5112 | 200, corps VIDE (0 octet) | la même page |
| MailUp sur le domaine du client (`tr.comune.torino.it/e/tr`, `go.fondazionetorinomusei.it/e/tr`) | 5310, 5268 | 200 « Oops! It looks like something went really wrong. » | la même page |
| compteur maison (`stats.departement06.fr/c6.php`) | 5264 | 404 « Lien invalide » | la même page |
| Sequar (`enteturismolmr.sequar.com/r/…/m/651314`) | 5137 | 301 → `comune.asti.it/vivere-comune/eventi?utm_source=…` (la LISTE des événements) | **la même page** |
| billetterie (`www.midaticket.it`, racine) | 5121 | 200, page d'accueil ; og:image = `Arrow_Down_MD.png`, une flèche de menu | — |

Aucune des douze ne rendait une page de rebond : **dix sont mortes** — elles répondent
exactement ce que répond un jeton inventé — et la onzième mène à la page de repli de la
campagne, quel que soit le jeton. Détail à ne pas taire : **les onze adresses de traçage
font toutes exactement 80 caractères**, et celle de 5310 se termine au milieu d'une séquence
`%26B%`. Une coupe à 80 existe donc quelque part — dans l'affichage qui a servi à les
relever, ou en base. `gmail_collect.py` ne tronque pas ; `insert_events` non plus. Ce point
n'est PAS tranché ici (pas d'accès à la base depuis ce conteneur) ; il se tranche en une
commande sur le VPS :
`sqlite3 data/events.db "SELECT id, length(url_source), url_source FROM events_raw WHERE id IN (5292,5098,5252,5315,5303,5153,5112,5310,5268,5264)"`.
Si les longueurs valent 80, la coupe est en base et les liens sont irrécupérables par ce
chemin ; sinon, relancer la moisson sur ces fiches avec les adresses complètes est le test.

**Pourquoi la moisson ne disait rien de tout ça.** Trois raisons, dans le code :
1. deux détecteurs de traqueurs divergents (`publisher_as._TRACKING_HOSTS` connaissait le
   motif MailUp `/e/tr`, `moisson._TRAQUEURS` connaissait sendibm1 et emailsp), et **aucun**
   des deux ne connaissait Brevo en marque blanche, Postmark, OpenEMM, Sequar ni le compteur
   du département — donc `tr.comune.torino.it/e/tr` était lu comme une page officielle
   (l'hôte l'est), et Sequar suivi jusqu'à une page de liste sans que l'adresse d'arrivée
   soit jamais mémorisée ;
2. un lien mort (404, 200 vide, « Oops ») était fondu dans « sans donnée exploitable », sans
   identifiant de fiche : vingt fiches invisibles dans le bilan (règle 6) ;
3. quand un traqueur aboutissait, la page d'arrivée était crue sur parole : pour 5137 la
   moisson aurait mémorisé la liste des événements d'Asti comme page officielle du Palio et
   y aurait pris les horaires d'un spectacle de théâtre du 8 novembre (mesuré avec le code
   corrigé à moitié : WP#6798 en version « infos pratiques »).

**Ce qui est corrigé** (`utils/traqueurs.py`, `scripts/moisson_officielle.py`,
`scripts/publisher_as.py`, `utils/sources.py`, `utils/radar.py`) :
- **un seul détecteur**, `utils.traqueurs.est_traqueur`, par HÔTE (sendibm, musvc, brevo,
  arenametrix, pstmrk, sequar…) et par CHEMIN sur n'importe quel hôte (`/e/tr`, `/e/r`,
  `/mk/cl/f/`, `/r.html?uid=`, `/r/<x>/m/<n>`, `/c6.php?ec=`, `?e=`…). `bct.comune.torino.it`
  reste une source (décision de Franck) : on bannit le chemin du routeur, jamais le domaine
  du client. La moisson et le publieur l'appellent tous deux ;
- **les rebonds non-HTTP sont suivis**, trois sauts au plus, jamais la même adresse deux
  fois : meta refresh toujours ; `location.href` et « page à lien sortant unique » seulement
  sur une page qui n'a presque rien d'autre à dire (texte visible < 400 caractères). Une
  vraie page riche qui porte un `location.href` dans un script est moissonnée elle-même — c'est
  le cas frontière de la fixture, et il passe ;
- **les traqueurs sans destination sont comptés à part, avec l'identifiant et la longueur de
  l'adresse**, dans le bilan de chaque run (pas seulement en `--diagnostic`). Aucun verdict
  n'est posé, la fiche reste candidate : c'est l'enrichissement (`resolve_official_site`) ou
  la main de Franck (Site officiel au back-office) qui lui rendra une adresse — et le corps du
  mail (`mail_corps`) est toujours là ;
- **la destination d'un traqueur doit parler de l'événement** (un mot du titre, hors mots déjà
  dans l'hôte : « asti » sur comune.asti.it ne compte pas) **et dépendre du jeton** : la moisson
  re-télécharge l'adresse avec son dernier groupe de caractères remplacé par des zéros ; même
  arrivée = page de repli, rien n'est récolté ni mémorisé. Une requête de plus, uniquement
  quand un traqueur a abouti quelque part ;
- l'adresse mémorisée dans `url_officiel` perd ses `utm_*` ; l'image et l'hôte se jugent sur
  la page d'ARRIVÉE, plus sur l'adresse du routeur ;
- `is_logo_image` connaît « arrow, chevron, spacer, pixel, blank, bullet, loader, spinner » ;
  `midaticket.` rejoint billetweb et weezevent dans `radar._GENERIC_HOSTS` — un guichet n'est
  pas l'organisateur. Conséquence à mesurer sur le VPS avant de s'en étonner :
  `SELECT id, statut FROM events_raw WHERE url_officiel LIKE '%midaticket%' OR url_source LIKE '%midaticket%'`
  dit quelles fiches perdent une ancre.

**Ce que ça change pour les douze fiches** : rien de plus n'est récolté — les liens sont
morts, et un correctif ne ressuscite pas un jeton. Ce qui change, c'est que le run le dit,
fiche par fiche, au lieu de le fondre dans un total ; que 5137 ne reçoit plus une page de
liste et des horaires d'un autre spectacle ; que 5121 n'est plus lue du tout ; et que les
PROCHAINS liens Brevo/MailUp/Sequar valides seront suivis jusqu'à la page de l'organisateur,
mémorisés sans leurs paramètres de campagne, et refusés s'ils mènent à la presse.

**Comment se rejoue le contrôle.** Fixture : `.venv/bin/python -m tests.test_moisson_officielle`
(section « rebonds non-HTTP, traqueurs morts, et la page qui ne parle pas de la fiche » : meta
refresh vers l'officiel qui DOIT récolter, rebond JS, rebond vers la presse qui DOIT refuser,
traqueur 404 et « Oops » comptés morts, chaîne de 4 sauts arrêtée, page de repli qui parle du
titre mais qu'un jeton brouillé atteint aussi, et le cas frontière qui doit passer) ; et
`tests/test_source_publiable.py` pour le détecteur commun. Sur données réelles :
`.venv/bin/python -m scripts.moisson_officielle --diagnostic 5292 5098 5252 5315 5303 5153 5137 5112 5310 5268 5264 5121`
(dry-run) doit lister ces fiches sous « lien(s) de traçage SANS destination propre », avec la
longueur de chaque adresse.

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
