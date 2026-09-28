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

## Ce qui attend un humain

- **Le texte de l'encadré** sous les articles (`deploy/wordpress/cs-encadre-suivre.php`,
  installé, inactif) : à rédiger selon la doctrine, relu par Franck, puis posé dans les
  options `cs_encadre_suivre_texte_fr` / `_it` avec les marqueurs `{discover:libellé}` et
  `{sources:libellé}`, et `cs_encadre_suivre_actif` = 1. Aperçu sur un article :
  `?cs_encadre_suivre=1`.

## Mesurer

Search Console → Performances → **Discover**. Ce rapport n'apparaît qu'une fois que le
site a reçu du trafic Discover : son absence veut dire « pas encore », pas « cassé ».

## Diagnostiquer

`/feed/?cs_flux_une=1` renvoie l'en-tête `X-CS-Flux-Une` (« actif » ou la raison du
refus) et `X-CS-Flux-Une-Ids` (les fiches retenues). Deux versions du 24/09 ont rendu un
flux inchangé sans rien dire — d'où cet en-tête.

## Revenir en arrière

Option `cs_flux_une_actif` à 0 : le flux redevient celui des seuls articles.
