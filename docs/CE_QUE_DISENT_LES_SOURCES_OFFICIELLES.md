# Ce que les sources officielles publient vraiment

Franck, 2026-08-11 : « qu'est-ce que tu apprends de tout ce que tu es en train de faire par
rapport aux informations trouvées dans les sources officielles ? »

La journée a produit assez de mesures pour répondre autrement qu'à l'intuition. Ce
document garde les chiffres et ce qu'ils imposent de changer. Il ne raconte pas les
correctifs — ils sont dans l'historique git — mais ce qu'ils ont appris sur les sources.

**Périmètre** : runs de production du 2026-08-11, environ 500 pages officielles lues.

---

## 1. Les pages officielles sont bavardes en PROSE et muettes en DONNÉES

C'est la mesure la plus nette de la journée, et elle contredit l'hypothèse sur laquelle
toute la chaîne d'extraction était bâtie.

| ce qu'on cherche | pages lues | trouvé |
|---|---|---|
| tarif, horaires, réservation, accessibilité | 167 | **135** |
| tarif, horaires, réservation, accessibilité | 100 | **78** |
| date, lieu, ville, image (JSON-LD) | 167 | **0** |
| date de début (JSON-LD), sur pages muettes | 62 | **0** |

Le `--diagnostic` a tranché la question qui restait ouverte : sur 62 pages sans date,
**pas un seul `@type: Event`**. Ce n'est pas notre extracteur qui échoue, c'est l'objet
qui n'existe pas dans la page.

Ce qui est écrit l'est **pour des lecteurs humains, en toutes lettres** : « Ouverture des
portes à 19h30 », « Tarif plein : 18 € », « sur réservation à la billetterie ». Ce qui
manque, c'est le balisage machine que schema.org prévoit — celui que la chaîne attendait.
La majorité de ces sites sont des WordPress dont le `@graph` Yoast décrit un `Article` ou
une `WebPage`, jamais un `Event`.

**Conséquence pour la suite** : ne plus investir dans l'extraction structurée. Le gisement
est dans la prose, et il faut aller le lire avec des motifs de langue — c'est ce que fait
`utils/infos_pratiques.py`, et c'est ce qui a rapporté le plus aujourd'hui.

---

## 2. Sur une page, on ne peut pas EXTRAIRE — on ne peut que CONFIRMER

Trois mécanismes construits aujourd'hui, trois fois la même forme, et ce n'est pas une
coïncidence.

- `utils.bylines.corrobore` — un nom n'est un organisateur que si le texte le dit, **dans
  la même phrase**. Sans la coupure à la phrase, « Fête organisée par la Pro Loco. Denis
  Falconieri était présent. » corroborait Falconieri avec la preuve qui désignait
  quelqu'un d'autre.
- `scripts.dates.debut_depuis_page` — une date de début n'est retenue que si la plage qui
  la porte **se termine à la date de fin déjà connue**. Et deux débuts possibles pour la
  même fin ne rendent rien.
- `utils.infos_pratiques.extraire` — rend la **phrase** autour du montant, jamais le
  montant seul : « 12 € » peut être le plein tarif, le réduit, le catalogue ou le parking.

La raison est toujours la même. Une page officielle contient beaucoup d'informations et
**aucun marquage de celle qui répond à la question posée** : la date de l'article, celles
des autres événements de la colonne, les horaires d'ouverture, le copyright. « La première
date trouvée » est un tirage au sort.

Mais dès qu'on tient **un fait déjà sûr**, la page redevient lisible : il sert d'ancre, et
ce qui lui est accroché devient vérifiable. Une fin connue transforme une page ambiguë en
source fiable pour le début.

**Conséquence pour la suite** : tout nouvel extracteur doit dire à quel fait connu il
s'accroche. S'il n'y en a aucun, il devine, et il finira par écrire un fait faux que
personne ne verra passer.

---

## 3. Avant de conclure « la source ne publie pas », vérifier qu'on lui a demandé

Trois fois aujourd'hui un « 0 » a semblé désigner une source pauvre. Trois fois c'était la
requête.

| ce que le run affichait | ce que c'était |
|---|---|
| « 0 daté par le texte » pendant des semaines | la passe ne regardait chaque fiche **qu'une fois** |
| « 0 page à lire » côté dates | la sélection ignorait les fiches n'ayant qu'une **fin** |
| « 200 pages lues, 0 résultat » | pas d'`ORDER BY` : le plafond lisait les **200 plus vieilles** |

Le même chemin qui a rendu 0 sur 200 pages avait daté **31 fiches sur 49** une heure plus
tôt. La différence n'était pas dans les pages, elle était dans le choix des pages.

C'est le piège propre à ce sujet : un pipeline qui ne trouve rien **ressemble exactement** à
un monde où il n'y a rien à trouver. Les deux produisent un zéro, et le zéro est muet.

**Conséquence, déjà appliquée** : un compteur doit dire si le cas s'est présenté. La
moisson annonce désormais « N fiches étaient dans ce cas, M y ont gagné une date » — sans
quoi on part chercher un défaut là où il n'y a que du vide, ou l'inverse.

---

## 4. La presse et l'officiel ne portent pas la même information — pas seulement la même valeur

On savait déjà qu'un article de presse ne se cite ni ne se lie (doctrine radar,
`utils/radar.py`). La journée ajoute un motif purement factuel, et il est plus fort.

- **La presse écrit ce qui fait actualité** : « l'exposition est visible jusqu'au
  20 septembre ». Vrai, publiable, et **incomplet par nature** — le début n'intéresse plus
  le journaliste au moment où il écrit.
- **L'organisateur écrit le fait entier** : « du 12 juin au 20 septembre ».

D'où les 54 fiches restées avec une fin et pas de début : elles viennent toutes d'un flux
de presse. C'est la même page, lue chez deux émetteurs, qui donne une donnée mutilée ou
une donnée complète.

Et la pollution des organisateurs vient exactement du même endroit : `entry.author` d'un
flux RSS, c'est la signature du journaliste. **187 fiches** en portaient une, dont 64 en
ligne.

**Conséquence** : résoudre vers la page officielle n'est pas un scrupule juridique, c'est
la condition pour avoir des faits complets. Ce qui vient de la presse est à considérer
comme partiel jusqu'à preuve du contraire.

---

## 5. Certaines informations n'existent nulle part, et il faut savoir s'arrêter

Vérifié à la main, pas supposé.

- **Fiche 2374, « Per Olivia » (Teatro Stabile di Torino)** — la page ne contient aucune
  date. Ni texte, ni JSON-LD, ni méta. Le spectacle relève de la « Stagione 2026-2027 » et
  ses dates vivent dans la billetterie (vivaticket). Aucun modèle, aucun nombre de
  tentatives ne fera apparaître ce qui n'y est pas.
- **315 des 454 points « à vérifier »** du matin n'étaient pas des faits douteux mais des
  informations que la source ne publie pas : capacité d'accueil d'une sortie au lac, langue
  de la médiation, âges. Personne ne peut les vérifier — ni Franck, ni le modèle.

« Officiel » ne veut pas dire « complet ». Il y a un plancher, et le reconnaître est ce qui
distingue une file de tâches d'un inventaire des silences de la source.

**Conséquence** : quand une donnée manque, la question n'est pas « comment la trouver ? »
mais d'abord « existe-t-elle quelque part ? ». Si la réponse est non, la seule décision
honnête est éditoriale : publier sans, ou ne pas publier.

---

## 6. Et le plus inattendu : le modèle n'était pas le goulot

Le plafond d'API courait depuis ce matin — il a été levé le 12 août au soir, par un
rechargement de crédits. Ce qui suit ne perd rien pour autant : tout ce que la journée a
produit l'a été **sans un seul appel**, et c'est ça qui compte, pas la contrainte qui l'a
provoqué :

- 187 organisateurs faux retirés (3 faux positifs, rattrapés) ;
- 31 fiches datées par leur page, dont 6 par corroboration ;
- 135 puis 78 fiches pourvues de tarifs, horaires, conditions d'accès ;
- la file de tâches passée de 548 à une centaine.

Ce matin, Franck : « je consomme beaucoup trop de token API pour le résultat médiocre. »
La journée en donne la lecture : **l'API sert à ÉCRIRE, pas à SAVOIR.** Les faits sont dans
les pages, et les aller chercher est de l'analyse syntaxique — gratuite, instantanée,
rejouable autant de fois qu'on veut. Chaque fait qu'on laisse le modèle deviner est à la
fois plus cher et moins sûr que le même fait lu à la source.

C'est la ligne de partage à tenir : **collecter sans modèle, rédiger avec.**

---

## 7. 2026-09-08 — les pages municipales le disent, sous un libellé plutôt qu'un `@type: Event`

Mesuré ce soir en base de production : sur 108 fiches approuvées, à venir et incomplètes,
une vingtaine sont des pages municipales (bct.comune.torino.it, comune.biella.it,
comune.casale-monferrato.al.it, villefranche-sur-mer.fr, ugine.com), marquées
`venue_source='novenue'` — la passe JSON-LD n'y trouve aucun `location`. Dix-neuf ont été
téléchargées pour de bon. Aucune ne porte de balisage `@type: Event`. **Douze écrivent
pourtant le lieu**, toujours de la même façon : un libellé court, seul dans sa balise
(`<h2>Dove</h2>`), ou une icône d'épingle, suivi de la valeur dans le bloc d'après.

Deux pièges, mesurés sur les pages réelles :

- **torinoclick.it** porte « Sede: piazza Palazzo di Città 1 – Torino » — c'est l'adresse
  de l'agence de presse, dans son pied de page, pas celle de l'événement. Le pied de page
  est retiré avant lecture, et « Sede » n'est accepté comme libellé qu'à la ligne, jamais
  en tête d'une phrase de prose.
- **comune.biella.it** liste « Cos'è · A chi è rivolto · Luogo · Date e orari… » dans son
  sommaire, AVANT la vraie section : le premier « Luogo » de la page est donc suivi de
  « Date e orari », pas d'un lieu. `lieu_depuis_libelles` parcourt toutes les occurrences
  et retient la première dont la valeur est plausible — ce qui saute le sommaire.

**Un défaut découvert en écrivant le cas frontière qui doit passer**, exactement la
manière dont la règle 3 de CLAUDE.md dit qu'un portillon doit être éprouvé : le libellé
« Sede dell'evento » (apostrophe droite) était dans la liste des libellés acceptés, mais
les pages municipales l'écrivent avec l'apostrophe typographique — « Sede dell'evento »
(’, celle que produit `htmlmod.unescape` sur `&rsquo;`). Sans normalisation, ce libellé
pourtant explicitement prévu ne matchait JAMAIS. Corrigé dans `_libelle` (`scripts/venues.py`).

**Et un défaut d'ordonnancement, indépendant du libellé** : ni `scripts/dates.py` ni
`scripts/venues.py` ne lisaient `url_officiel` — la vraie page qu'`scripts/moisson_officielle.py`
et `scripts/affiner_source.py` mémorisent quand `url_source` est un lien de suivi ou une
racine de site. La date et le lieu étaient donc cherchés sur la page de rebond. Les deux
scripts lisent désormais `COALESCE(NULLIF(url_officiel,''), url_source)` — même expression
dans les deux fichiers (`URL_PAGE_SQL`), pas deux détecteurs qui divergent.

Et la sélection de la passe LLM de `venues.py` n'avait pas d'`ORDER BY` : plafonnée à
`VENUES_LLM_CAP` (150) et servie par numéro croissant, elle traitait les plus vieilles
fiches en premier, jamais les 'novenue' fraîchement posées par la passe 1 le jour même
tant que le plafond n'était pas atteint par des fiches plus anciennes — c'est l'hypothèse
la plus probable pour les fiches restées 'novenue' un jour entier. Corrigé : les fiches
'novenue' passent avant les 'none' (ré-armées), les plus récentes d'abord ; et la règle 5
(rien sur le passé) s'applique désormais à cette sélection, ce qui n'était pas le cas.

**Reste ouvert** : le registre `lieux_villes.json` reste petit, la voie qui gagne le plus
de fiches est `ville_du_domaine` (commune nommée dans le sous-domaine ou le domaine).
