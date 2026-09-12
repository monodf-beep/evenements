# Les 28 doutes de la file « À vérifier » — vérifiés un par un

Franck, le 2026-08-11, devant l'écran tombé de 548 tâches à 28 : **« c'est à toi de
vérifier »**.

Fait. Ce document garde les réponses, leurs sources, et surtout ce que la vérification a
appris sur la file elle-même. Il n'est pas un compte rendu : c'est la matière qui manquait
aux fiches, et de quoi trancher sans la refaire.

**Périmètre du document** (règle 6) : les 28 points EN ATTENTE affichés le 2026-08-11 au
matin, sur 23 événements. Les 425 absences masquées le même jour n'y sont pas — ce ne sont
pas des doutes.

---

## Ce que la vérification a d'abord trouvé : ce n'étaient pas 28 doutes

**Cinq des vingt-huit posaient la même question**, sur cinq fiches sans aucun rapport :

| fiche | le point ouvert |
|---|---|
| 473 | « Organisateur réel de la foire (Arabella Pezza semble être une journaliste) » |
| 3995 | « Stefania Marchiano : autrice de l'article ou organisatrice ? » |
| 4381 | « Rôle exact d'Amelio Ambrosi : organisateur ou contact presse ? » |
| 4127 | « Fonction exacte de Denis Falconieri (organisateur, association, commune ?) » |
| 3545 | « Nom exact de l'organisateur (Emilie DUPONT confirmé ?) » |

Vérification faite, aucune de ces cinq personnes n'organise quoi que ce soit (détail plus
bas). Et « Emilie DUPONT » n'est même pas quelqu'un : c'est le nom-bouchon des formulaires.

**La cause était une ligne de code**, pas cinq faits douteux. `scripts/scraper_events.py`
recopiait `entry.author` du flux RSS dans la colonne `organisateur`. Dans un flux RSS,
`author` / `dc:creator` est l'auteur de l'**article** : le journaliste sur un flux de
presse, le compte du CMS sur un flux d'institution. Jamais l'organisateur de l'événement.

Le modèle recopiait ensuite ce nom dans l'article, le contrôleur s'en méfiait — à juste
titre — et posait une tâche **que personne ne pouvait résoudre en cliquant**, puisque la
réponse ne se trouvait nulle part dans la matière. Cinq clics impossibles par récolte,
tous les jours, depuis toujours.

Correctif : `utils/bylines.py` (le portillon), `scripts/scraper_events.py` (les collectes
futures), `scripts/purge_bylines.py` (les fiches déjà en base), `tests/test_bylines.py` et
`tests/test_purge_bylines.py` (les deux fixtures).

---

## Les corrections à porter — des faits FAUX, aujourd'hui, sur le site

### Fiche 3527 — Orchestre de la Suisse Romande à Évian
« Chef d'orchestre : Jonathan Nott est-il toujours en poste en 2026 ? » → **Non.**
Jonathan Nott a quitté la direction artistique et musicale de l'OSR fin 2025, après huit
saisons ; il revient en chef invité. Tugan Sokhiev a été nommé chef principal et conseiller
artistique. Si la fiche le présente comme « directeur musical », c'est faux au présent.
Sources : [RTS — nomination de Sokhiev](https://www.rts.ch/info/culture/musiques/2026/article/le-russe-tugan-sokhiev-nomme-chef-principal-de-l-orchestre-de-la-suisse-romande-29266999.html),
[ResMusica](https://www.resmusica.com/2026/03/13/des-chefs-en-residence-a-lorchestre-de-la-suisse-romande/).

### Fiche 473 — Foire de Saint-Ours
Organisateur : la **Région autonome Vallée d'Aoste** (Assessorat de l'artisanat), qui
publie la foire sur son propre site. Arabella Pezza signe l'article.
Source : [regione.vda.it](https://www.regione.vda.it/artigianato/Fiera_di_Sant_Orso_2026/default_f.aspx).

### Fiche 4381 — Marché au Fort, Forte di Bard
Organisateurs : **Assessorat de l'agriculture de la Région autonome Vallée d'Aoste,
Commune de Bard, Chambre valdôtaine et Forte di Bard**. 22ᵉ édition, **10 et 11 octobre
2026**. Amelio Ambrosi n'est pas organisateur.
Source : [Aosta Oggi](https://www.aostaoggi.it/attualita/34067-marche-au-fort-2026-aperte-le-iscrizioni).

### Fiche 3995 — Percorso in Rosso, Saint-Rhémy-en-Bosses
Organisateur : la **Pro Loco de Saint-Rhémy-en-Bosses**. **Jeudi 13 août 2026 à partir de
16 h**, autour du Jambon de Bosses DOP. Stefania Marchiano signe l'article.
Source : [La Prima Linea](https://www.laprimalinea.it/2026/08/05/leggi-notizia/argomenti/eventi-e-appuntamenti-2/articolo/st-rhemy-en-bosses-si-tinge-di-rosso-torna-il-percorso-in-rosso-dedicato-al-jambon-de-bosses-dop.html).

### Fiche 3545 — La Farandole (version italienne)
Organisateurs : **Ville de Nice** avec le **Collectif des Arts Traditionnels – Lou Cat**.
« Emilie DUPONT » est à retirer sans hésiter.
Source : [nice.fr](https://www.nice.fr/la-farandole-festival-international-de-folklore-de-nice/).

### Fiche 4127 — Fénis, « Tsantì de Bouva »
« Date unique ou série d'été ? » → **ni l'un ni l'autre : Tsantì de Bouva est un LIEU**,
l'aire verte de Fénis. Elle accueille plusieurs rendez-vous distincts dans la saison (52ᵉ
Raduno des fanfares valdôtaines fin mai–début juin, Le Cors dou Heralt les 24-25 juillet,
Etetrad du 27 au 30 août). La fiche a pris un lieu pour un événement : elle est à
retailler sur un rendez-vous précis, ou à retirer.
Sources : [AostaSera — Etetrad](https://aostasera.it/notizie/cultura-e-spettacolo/la-musica-tradizionale-di-etetrad-2026-attraversa-le-alpi-fino-al-giappone/),
[AostaSera — Raduno des bandes](https://aostasera.it/notizie/comuni/fenis-si-prepara-al-52-raduno-delle-bande-valdostane/).

### Fiche 3083 — Tour de France Femmes, étape 9
« Étape 9 (Nice > Nice) confirmée comme contre-la-montre individuel ? » → **Non.** C'est
une étape de montagne en circuit, 99 km, avec les ascensions du col d'Èze et arrivée sur
la Promenade des Anglais. **Mais l'épreuve s'est courue les 8 et 9 août : c'est du passé**
(règle 5), et le point n'aurait pas dû rester à l'écran le 11.
Source : [letourfemmes.fr, étape 9](https://www.letourfemmes.fr/en/stage-9).

---

## Les doutes levés — rien à faire, la fiche était juste

### Fiche 580 — L'Héritier de village, tournée du TNN
Deux points, deux réponses, et elles ne disent pas la même chose.

- « Fin de tournée : 28 ou 29 août ? » → **29 août**, à Beaulieu-sur-Mer. Le 28, c'est
  Vence. Tournée complète : La Bollène-Vésubie 19, Clans 20, Isola 21, Levens 24,
  Tourrette-Levens 26, Vence 28, Beaulieu-sur-Mer 29 — 20 h 30, gratuit.
- « Vence fait-elle bien partie du territoire métropolitain annoncé ? » → **oui**, Vence
  est une des 51 communes de la Métropole Nice Côte d'Azur, et y joue le 28.

**Attention au piège, il resservira** : *Métropole Nice Côte d'Azur* ≠ *Comté de Nice*.
Vence appartient à la première et **pas** au second — elle est dans l'arrondissement de
**Grasse**, donc hors du périmètre `comte-de-nice` fixé par
`config/communes_comte_de_nice.json` (101 communes pour Nice, 62 pour Grasse). Une fiche
peut donc être « métropolitaine » et ne pas porter l'étiquette du territoire.
Sources : [Métropole NCA — Vence](https://www.nicecotedazur.org/metropole/territoire/les-communes/vence/),
[Métropole NCA — le TNN en tournée](https://www.nicecotedazur.org/actualites/le-tnn-en-tournee-dans-la-metropole-cet-ete/).

### Fiche 2043 — La Farandole, ballet de Macédoine du Nord
« Représente-t-il un des 5 pays annoncés ? » → **oui.** 66ᵉ édition, **12-16 août 2026**,
cinq pays : **Mexique, Macédoine du Nord, Timor-Leste, Cuba, Bénin**. Plus de 20 rendez-vous
gratuits, à Nice et à Levens, Belvédère, Saint-Jeannet, La Trinité, Saint-André-de-la-Roche,
Châteauneuf-Villevieille et Drap.
Source : [nice.fr](https://www.nice.fr/la-farandole-festival-international-de-folklore-de-nice/).

### Fiche 3558 — Jazz Art Lympia, « Luz do Samba »
→ **un groupe**, pas un intitulé de soirée : répertoire brésilien (Djavan, Ivan Lins, João
Donato) relu au prisme du jazz, programmé le 30 juillet. 8ᵉ édition, six jeudis gratuits du
16 juillet au 20 août, 20 h sur le toit-terrasse de l'Espace culturel départemental Lympia.
Source : [Nice Premium](https://www.nice-premium.com/jazz-art-lympia-2026-six-free-jazz-evenings-scheduled-starting-tonight-on-the-nice-waterfront/).

### Fiche 3498 — Estate Reale, Musei Reali di Torino
« Billet unique ou billetterie séparée ? » → **billetterie par soirée**
(museireali.midaticket.com). Le billet donne accès à une section du musée, différente
chaque soir, et au spectacle programmé ; certaines dates ont leur tarif propre (10 € le
14 octobre). Du 12 juin au 31 octobre, 19 h 45 – 23 h 30, dernière entrée 22 h 45.
Source : [Musei Reali](https://museireali.beniculturali.it/estate-reale-2026-una-sera-al-museo/).

### Fiche 4621 — Torino Film Festival, Ambra Angiolini
« Présente-t-elle aussi la clôture ? » → **ouverture seulement**, au Teatro Regio, aux
côtés du directeur Giulio Base. 44ᵉ édition du 24 novembre au 2 décembre 2026. Aucun nom
n'est annoncé pour la clôture à ce jour : ce n'est pas un doute, c'est une information qui
n'existe pas encore.
Source : [torinofilmfest.org](https://www.torinofilmfest.org/it/ambra-angiolini-condurra-la-serata-di-apertura-del-44tff/).

### Fiche 1080 — Reale Mutua Basket Torino en Serie A2
→ **oui**, en A2 en 2025/26 comme en 2026/27. Mais le point ne méritait pas d'exister : la
division d'un club de basket ne change rien à un événement d'été au Blooming Playground.
Même vérifié, personne n'en aurait rien fait.
Source : [Lega Nazionale Pallacanestro](https://www.legapallacanestro.com/serie-a2/reale-mutua-torino).

### Fiche 4125 — Collontrek, rôle de la Loterie Romande
→ **soutien financier, pas co-organisateur.** La course a été fondée en 2009 par Laurent
Pitteloud (versant suisse) et Maurizio Lanivi (versant italien), qui la coordonnent.
⚠️ Deux dates circulent pour 2026 (5 et 7 septembre) : à trancher sur
[collontrek.com](http://www.collontrek.com/) avant publication.
Source : [Running Passion](https://runningpassion.it/news/il-7-settembre-ritorna-il-collontrek-la-corsa-da-bionaz-ad-arolla/).

### Fiche 3094 — Guitare en Scène, « This is Michael & Jennifer Batten »
→ **les deux à la fois** : le spectacle officiel *This Is Michael* (Lenny Jay) et Jennifer
Batten, guitariste de Michael Jackson pendant dix ans, pour leur **seule date européenne**.
Samedi 18 juillet, 21 h 30, Chapiteau. **Passé** — le point n'avait plus lieu d'être.
Source : [guitare-en-scene.com](https://www.guitare-en-scene.com/artiste/this-is-michael-jennifer-batten-425).

---

## Un arbitrage ÉDITORIAL, qui n'est pas le mien

### Fiche 3379 — Grand Continent Summit, Vallée d'Aoste
Les deux points portaient sur le tarif et la langue des sessions. La vraie question est
ailleurs : **ce sommet a-t-il sa place dans l'agenda ?** Il réunit sur invitation environ
180 chefs de gouvernement, intellectuels et scientifiques ; seul le colloque inaugural est
ouvert sur inscription. La charte est explicite — « un congrès, un colloque scientifique ou
un salon B2B n'a pas sa place, même ouvert à tous » : c'est le **public visé** qui décide.

Et l'édition trouvée (3-5 décembre, Grand Hotel Billia puis Petit Cervin) est celle de
**2025** ; aucune édition 2026 n'est annoncée à ce jour, alors que la fiche annonce « du 3
au 6 décembre ». Décision à prendre par Franck : retirer, ou attendre l'annonce officielle.
Sources : [Région VdA](https://www.regione.vda.it/pressevda/Eventi/summit_gc_2025_f.aspx),
[summit.legrandcontinent.eu](https://summit.legrandcontinent.eu/fr/).

---

## Ce que je n'ai pas pu trancher

Quatre points restent ouverts faute de source publiée — et c'est une réponse, pas un échec :

- **fiche 13** — date de la seconde séance de ciné plein air à Albertville ;
- **fiche 4705** — titre complet du film du 24 août à la Citadelle de Villefranche. Le site
  de la commune ne publie que les programmes du 4 au 22 juillet et du 24 juillet au
  10 août : **la programmation « du 11 au 29 août » de la fiche n'est corroborée nulle
  part** et mérite un coup d'œil avant tout ;
- **fiche 3594** — nature de LivePlay (DJ, orchestre, groupe) à la Citadelle de
  Villefranche ;
- **fiche 3734** — format exact de la venue de L. Tessarollo au Conservatoire de Turin
  (masterclass, cours ouvert ou concert), et s'il joue seul ou avec des élèves.

Trois autres relèvent de la même famille que les 425 absences déjà masquées le 11 août
— la source ne publie pas l'information, personne ne peut la vérifier : langue de la
médiation de l'exposition Chagall (3026), horaires des séances For All / For Kids de
That's Animato! (1745), et le périmètre du tarif de 28 € de *Tout est calme dans les
hauteurs* (924).

---

## Ce que la file elle-même a révélé

**Deux points portaient sur des événements terminés** — le Tour de France Femmes (fini le
9 août) et Guitare en Scène (18 juillet) — et s'affichaient encore le 11. Le filtre de date
de la file existe pourtant. Deux explications possibles, et une seule commande pour
trancher :

```sql
SELECT id, date_event_start, date_event_end, recurring
  FROM events_raw WHERE id IN (3083, 3094);
```

Si `date_event_end` est vide, c'est une donnée manquante et non un défaut du filtre — une
fiche sans date ne se classe pas en « passé » (règle 5), elle attend `dates.py`. Si la date
est renseignée et passée, c'est le filtre qui fuit, et il faut le reprendre.

**Et le vrai enseignement, celui qui vaut pour la suite :** sur 28 points, cinq venaient
d'un bug, deux d'un événement fini, un d'une question sans conséquence (la division de
basket), trois relevaient d'absences déjà écartées ailleurs, et un cachait une question
éditoriale bien plus grosse que lui (le Grand Continent Summit). **Onze points sur
vingt-huit n'auraient jamais dû être posés.** Avant d'ajouter une ligne à une file, la
question reste celle de la règle 6 : qu'est-ce que le lecteur en FERA ?

---

## Le soir : dix-sept fiches en ligne annonçaient des événements déjà passés

Trouvées par `scripts/verifier_dates.py`, à son premier passage complet — et toutes par la
même règle, celle du JOUR DE LA SEMAINE. Le texte source nomme un jour ; ce jour ne
correspond qu'à une année ou deux sur la décennie ; si notre date n'en fait pas partie,
elle est fausse.

### Ce qui a été vérifié à la source, une par une

| fiche | notre date | ce que dit le texte | vérifié |
|---|---|---|---|
| 1069 | 07/05/2027 | « sabato 7 maggio » | page Paratissima : « 4 anni fa » → **2022** |
| 1079 | 11/12/2026 | « Sabato 11 dicembre » | la page annonce 2022 AU FUTUR → **11/12/2021** |
| 1080 | 09/12/2026 | « Giovedì 9 dicembre » | page Paratissima : « 5 anni fa » → **2021** |
| 1092 | 30/09/2026 | « giovedì 30 settembre », 2ᵉ édition | Esterno Notte 2 = **30/09/2021** (presse turinoise) |
| 1081 | 02/12/2026 | « Giovedì 2 dicembre » | 2021 ou 2027 ; même lot que les précédentes |
| 1036 | 17/12/2026 | « DOMENICA 17 DICEMBRE » | 2023 ou 2028 ; 2028 est absurde → **2023** |

**Neuf fiches Paratissima sur neuf sont des archives.** Ce n'est plus un défaut de
datation, c'est un problème de SOURCE : le flux republie ses vieux billets, et rien dans la
chaîne ne distingue une annonce de 2021 d'une annonce de demain.

### Les deux faux positifs, qui valent autant que les vrais

**Terra Madre Salone del Gusto** (fiches 3491 et 2507, française et italienne). TorinoClick,
l'agence de la Ville de Turin, écrit « du **vendredi** 24 au **lundi** 27 septembre ». Les
vraies bornes de l'édition 2026 sont un **jeudi** et un **dimanche** (slowfood.it, site de
l'édition, Région Piémont). **C'est la source officielle qui se trompe de jour, pas nous.**

**Charlie Winston** (923) : notre 22/09/2026 est confirmé par la billetterie de la Maison
des Arts du Léman. Le « 7 juillet » venait d'un autre spectacle de la même lettre.

**Saint-Ours** (473) : la foire a lieu les 30 et 31 janvier chaque année, donc notre
2027 est juste. Mais son TITRE en ligne annonce « 2026 » — autre défaut, autre geste.

### Ce que ces trois-là enseignent

Le jour de la semaine est le signal le plus contraignant qu'on ait — il réduit l'année à
une sur sept, gratuitement, à partir d'un mot que l'auteur a écrit sans y penser. **Ce
n'est pas pour autant un oracle.** Une source peut se tromper de jour ; une lettre
d'information peut mélanger deux spectacles ; un titre de presse peut porter l'année de
l'édition précédente.

D'où la règle de conduite, qui vaut pour tous les portillons de ce dépôt : **le
signalement doit porter la PHRASE, et c'est un humain qui tranche.** Les dix-neuf premiers
signalements ont été rendus sans elle ; il a fallu la rajouter pour découvrir qu'il y avait
un faux positif dedans — et pour rendre les dix-sept autres jugeables en dix minutes au
lieu d'une soirée.
