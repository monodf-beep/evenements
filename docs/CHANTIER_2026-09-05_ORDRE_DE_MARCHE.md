# Chantier du 2026-09-05 — ce qui est fait, et deux points qui se sont dissous

*Franck : « ok fais tout dans l'ordre », sur le plan en six points que j'avais proposé.
Voici l'état réel après exécution. **Deux des six points n'ont pas survécu à la
vérification** : ils reposaient sur des affirmations que j'avais faites sans mesurer.*

---

## Point 1 — Réparer `/ou-manger/` ✅ FAIT

Pages 1811 (FR) et 1812 (IT), en ligne, vérifiées après écriture.

| Avant | Après |
|---|---|
| note de travail interne publiée (« à vérifier auprès de l'office de tourisme avant publication définitive ») | supprimée |
| « Liste 2022 » + 32 noms périmés pour Nice | remplacés par le lien vers l'article qui porte la liste **2025/26** |
| **0 lien interne** dans le contenu | **22 liens FR, 17 IT**, tous vérifiés par `url_to_postid` |
| H2 « Savoie » (adresses en Haute-Savoie) | « Savoie & Haute-Savoie » |
| widget sidebar « Recent Posts », en anglais, sur FR et IT | supprimé (`_generate-sidebar-layout-meta = no-sidebar`) |
| Yoast title et description **vides** | renseignés dans les deux langues |
| lien de footer dans « Infos & légal », entre *Plan du site* et *Mentions légales* | déplacé dans « Catégories », après *Gastronomie* (FR et IT) |

**Deux liens italiens que j'avais écrits de mémoire étaient faux** et ont été corrigés avant
publication : `/it/tutta-l-agenda/` n'existe pas (c'est `/it/eventi/`), et la catégorie IT a
son propre slug (`gastronomia-sagre`, pas `gastronomie-sagre`). Les 39 liens ont été
résolus un par un côté serveur avant écriture.

**Rédigé avec `utils/voix.py`**, comme demandé. Mon premier brouillon violait la charte sur
quatre points : tiret cadratin en incise, définition par la négation (« un agenda
d'événements, pas un guide de restaurants »), triade, et « d'un versant à l'autre » que la
règle « Les Alpes ne sont pas une frontière » proscrit. Un garde-fou refuse désormais
l'écriture si l'un des termes interdits apparaît.

---

## Point 2 — Titres/metas des pages à 0 % de CTR ❌ SANS OBJET

**Je m'étais trompé, et la règle 5 le dit :** les pages que je citais sont des événements
**passés**.

| Page annoncée | Réalité mesurée |
|---|---|
| `/evenement/vence-aux-milles-bougies/` (163 impressions, position 7,9) | **n'existe plus** en base |
| `/evenement/la-farandole-a-nice…/` (62 impressions) | **n'existe plus** |
| Concerts Quartetto Lys (74 impressions, position 9) | eu lieu le **8 août** |
| Mausolée de la Bela Rosin (11 impressions) | terminé le **29 août** |

Optimiser leurs titres serait exactement ce que la règle 5 interdit : *« réparer une fiche
dont l'événement a eu lieu ne sert personne »*. J'avais présenté ce point comme le meilleur
rapport effort/retour du site **sans regarder une seule date**.

Ce qui reste, ce sont les hubs, qui ne périment jamais. Or ils ont **déjà** des titres et
descriptions Yoast corrects. Leur problème n'est pas le taux de clic mais le rang :
position 43, page 5, où personne ne clique. **Le point 2 se fond dans le point 4.**

---

## Point 3 — Les URL `/explore/`, `/choisir/`, `/scopri/` ❌ CE N'ÉTAIT PAS UN BUG

Deuxième erreur, en deux temps.

J'ai d'abord annoncé que ces URL « déclarent la page d'accueil comme canonique » comme s'il
s'agissait d'un défaut. Lecture faite, ce sont des **règles de réécriture délibérées** :

```
^explore/([^/]+)/?$   =>  index.php?page_id=928&as_home_territoire=$matches[1]
^choisir/([^/]+)/?$   =>  index.php?page_id=928&as_home_choix=$matches[1]
^it/scopri/([^/]+)/?$ =>  index.php?page_id=1717&as_home_territoire=$matches[1]
```

Ces adresses **sont** la page d'accueil filtrée par territoire. La canonique vers `/` est
donc le comportement correct, pas une anomalie : Yoast consolide comme il faut.

J'ai ensuite proposé de repointer ces liens vers les pages hub. **Ç'aurait été une
régression.** Le code qui les génère est `wp-content/mu-plugins/cs-territoire-persistant.php`,
dont l'en-tête dit : *« Chantier "territoire partout" demandé par Franck le 2026-07-20 :
persistance, tout clic pose un cookie »*. Les repointer casserait le sélecteur de territoire
persistant. **Rien n'a été modifié.**

Si tu veux quand même que la barre de territoires nourrisse les hubs, c'est un arbitrage de
design, pas un correctif : à décider, pas à appliquer en passant.

---

## Ce que le point 3 a révélé, et qui compte plus que le point 3

En cherchant qui générait cette barre, j'ai dû fouiller la production : le fichier n'est pas
dans le dépôt. Mesure complète :

> **33 mu-plugins `cs-*` tournent en production (320 Ko). 10 seulement ont leur double ici.
> 23 ne sont versionnés nulle part.**

Le CLAUDE.md annonce « il reste 34 mu-plugins `cs-*` en ligne dans ces conditions, dont 18
seulement ont leur double ici ». **Le chiffre réel est 10, pas 18.** L'écart s'est creusé.

Les 23 non versionnés :

`cs-agenda-list-shared` · `cs-cards-conformite` · `cs-completude` · `cs-corps-lint` ·
`cs-event-statut` · `cs-extracteur-pages` · `cs-gabarit-infos-utiles` · `cs-garde-fou-langue` ·
`cs-garde-fou-nationalisation` (43 Ko) · `cs-garde-fou-structure` · `cs-home-territoire-choix-langue` ·
`cs-home-territoire-filtre` · `cs-hub-musees` · `cs-lang-switch-taxonomies` · `cs-open-graph` ·
`cs-query-ce-week-end-dates` · `cs-redirect-ancien-slug` · `cs-redirect-weekend-legacy` ·
`cs-redirections-301` · `cs-taxonomie-type-de-lieu` · `cs-territoire-persistant` (22 Ko) ·
`cs-territoire-terms-racines` · `cs-territoire-urls-jolies`

C'est la configuration exacte de l'incident du 8 au 10 août : un mu-plugin écrit sur le
serveur, sans copie versionnée, une faute de syntaxe, et le site injoignable pendant deux
jours parce qu'aucun retour arrière n'était possible sans FTP. Ces 23 fichiers pilotent
l'open graph, les redirections 301, les garde-fous de langue et la barre de territoires.

**C'est le chantier qui devrait passer devant les articles « où manger ».** Il est
mécanique : rapatrier, passer `php -l`, committer. Aucune décision éditoriale.

---

## Point 4 — Faire monter les hubs ⏳ NON COMMENCÉ

Absorbe le point 2. Les quatre hubs territoire ont leurs metas ; ils sont en position 43 sur
`eventi aosta`, `valle d'aosta eventi`, `manifestazioni aosta`. C'est un travail de fond
(contenu, maillage, volume d'événements), pas un réglage.

## Points 5 et 6 — Événements gastronomiques, puis articles ⏳ NON COMMENCÉS

Le point 5 est du sourcing (2 événements Gastronomie & Sagre publiés sur 86). Le point 6
dépend du 5. Ni l'un ni l'autre ne se fait en une session.

---

## Récapitulatif honnête

| Point | État |
|---|---|
| 1. Réparer `/ou-manger/` | ✅ fait, en ligne, vérifié |
| 2. Titres/metas 0 % CTR | ❌ sans objet, mon erreur (événements passés) |
| 3. URL de nav canonicalisées | ❌ pas un bug, mon erreur (feature demandée) |
| 3bis. **23 mu-plugins non versionnés** | 🔴 trouvé en chemin, plus grave que 2 et 3 réunis |
| 4. Monter les hubs | ⏳ à faire |
| 5. Publier des événements gastro | ⏳ à faire |
| 6. Articles « où manger » | ⏳ dépend du 5 |

Sur six points, deux étaient des affirmations que je n'avais pas vérifiées avant de les
présenter comme le meilleur usage de ton temps. Les deux fois, aller lire a inversé la
conclusion, et les deux fois c'est la même faute que `ERREURS_2026-08-17` et
`ERREURS_2026-08-18` décrivent : conclure sur un indice de surface.
