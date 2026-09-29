# Suivre Agenda Sabauda sur Google (Discover, sources préférées)

Décidé par Franck le 24/09/2026, après l'encadré vu sur guidatorino.com.

## Ce qui tourne tout seul

- **Le flux** `https://agendasabauda.eu/feed/` (et `/it/feed/`) contient les articles
  ET les quatre fiches « À la une » du jour — mu-plugin `deploy/wordpress/cs-flux-une.php`,
  **actif depuis le 24/09 à 9h40** (option `cs_flux_une_actif` = 1). C'est ce flux que
  Google lit pour les personnes qui suivent le site dans Discover.
- Chaque fiche y est datée du jour où elle est ENTRÉE dans la une (méta
  `as_flux_une_depuis`, posée une fois, jamais réécrite).
- Vérifié à l'activation : 14 éléments en FR et en IT, XML bien formé, dates stables
  d'un passage à l'autre.

## Les deux liens

- Suivre sur Discover : `https://profile.google.com/cp/EhIKEGFnZW5kYXNhYmF1ZGEuZXU=`
  (page Google du site ; elle existe, mesuré le 24/09 : 200, « agendasabauda.eu | Google »).
- Sources préférées : `https://google.com/preferences/source?q=agendasabauda.eu`

## L'encadré sous les articles et les fiches

`deploy/wordpress/cs-encadre-suivre.php`, **actif depuis le 25/09** (texte rédigé selon la
doctrine, validé par Franck). Le texte vit dans les options `cs_encadre_suivre_texte_fr` /
`_it`, avec les marqueurs `{discover:libellé}` et `{sources:libellé}` ; le corriger ne
demande pas de toucher au code. Retour arrière : `cs_encadre_suivre_actif` = 0.

Vérifié en ligne le 25/09 : un encadré, dans la bonne langue, sur les guides FR/IT et sur
les fiches FR/IT (sous l'encadré de maillage des Journées du patrimoine quand il y en a
un) ; aucun dans le flux RSS ni sur l'accueil.

Non vérifié : que la fonction « sources préférées » de Google soit ouverte en France
(guidatorino.com l'emploie en Italie).

## Mesurer

Search Console → Performances → **Discover**. Ce rapport n'apparaît qu'une fois que le
site a reçu du trafic Discover : son absence veut dire « pas encore », pas « cassé ».

## Diagnostiquer

`/feed/?cs_flux_une=1` renvoie l'en-tête `X-CS-Flux-Une` (« actif » ou la raison du
refus) et `X-CS-Flux-Une-Ids` (les fiches retenues). Deux versions du 24/09 ont rendu un
flux inchangé sans rien dire — d'où cet en-tête.

## Revenir en arrière

Option `cs_flux_une_actif` à 0 : le flux redevient celui des seuls articles.
