# Le juste temps — quand publier ce qu'on sait déjà

**Proposition du 2026-08-04.** Question de Franck : « on connaît déjà des événements de
Noël mais ce n'est pas le moment de les afficher. Quand les afficher ? »

**Implémenté le 2026-08-05** — fenêtre par défaut validée par Franck : 90 jours. Voir
`utils/saison.py`, le portillon dans `scripts/publish_batch_as.py`, et
`config/temps_forts.json` pour les exceptions à 150 jours. La liste ⚖️ « valider/élaguer
cette liste » du tableau plus bas N'A PAS ÉTÉ tranchée : `config/temps_forts.json` ne
contient QUE les rendez-vous nommés explicitement pendant la discussion (Musilac, Nice
Jazz, Carnaval de Nice, Carnaval d'Ivrea, Foire de Saint-Ours, truffe d'Alba) — le
fichier est éditable sans code, Franck peut l'étendre au reste du tableau quand il aura
tranché.

## Le constat, vérifié dans le code le jour même

**Aucun garde-fou d'horizon n'existe à la publication.** `publish_batch_as` trie par date
de début croissante — les plus proches d'abord — mais sans borne haute : un marché de Noël
complet (daté, rédigé, panel) partirait en ligne en août dès que la file des événements
plus proches est vide. Or vider cette file est exactement l'objectif du pipeline. La seule
borne existante (`HORIZON_JOURS = 183`) ne protège que la section « Ça vaut le
déplacement », pas la publication, pas « À la une », pas les archives.

Le problème n'est pas theorique : publier un événement de décembre en août, c'est
- une page qui vieillit quatre mois en ligne avant de servir (et que `site_audit` relit
  pour rien pendant tout ce temps) ;
- un lecteur qui prend l'agenda pour un fourre-tout sans saison ;
- et au moment où l'événement devient d'actualité, une fiche déjà ancienne au lieu d'une
  nouveauté — le SEO et les sections « Nouveautés » travaillent à l'envers.

## ✅ Le principe implémenté : une fenêtre de PUBLICATION, jamais un état

Une fiche complète dont l'événement est trop lointain reste dans son statut retenu — le
lot quotidien la saute avec le motif « pas encore sa saison » (log RETENU), comme il
saute déjà les incomplètes. **Le temps la rouvre tout seul** : la sélection recompare les
dates chaque matin, aucun script de réouverture n'est nécessaire, aucun état terminal
n'est créé (réponse aux quatre questions de `docs/ETATS_TERMINAUX.md` — qui rouvre : le
calendrier ; où se voit le compte : la ligne « N fiche(s) en attente de leur saison »
dans le log de `publish_batch_as`, reprise dans le message Slack du lot quotidien).

S'applique même aux publications lancées avec `--ids` (`scripts/daily_batch.py`, seul
chemin non supervisé du dépôt) — même raison que les portillons éditorial et périmètre
posés le même jour : sans humain dans la boucle, aucune exception ne se justifie.
`--allow-early` reste disponible pour le cas rare où un humain choisit sciemment de
publier en avance.

✅ **La fenêtre par défaut, tranchée par Franck le 2026-08-05 : 90 jours** avant le
début de l'événement. Assez pour préparer un week-end ou des vacances, assez court pour
que l'agenda garde une saison. (Le tri « plus proches d'abord » fait déjà le gros du
travail ; cette borne n'attrape que le cas « file vide ».) Réglable sans code via
`TEMPS_FORTS_FENETRE_DEFAUT` (utils/saison.py).

✅ **Les exceptions qui méritent PLUS de préavis, implémentées** — on réserve tôt :
`config/temps_forts.json` donne 150 jours à Musilac, Nice Jazz, Carnaval de Nice,
Carnaval d'Ivrea, Foire de Saint-Ours et la truffe d'Alba (détection par mot-clé
FR/IT dans le titre ou la description). ⚖️ Reste ouvert : étendre cette liste au reste
du tableau ci-dessous, catégorie par catégorie ou nom par nom — pas tranché.

## Les temps forts du territoire — le calendrier à valider

Réponse à « tu as d'autres temps forts comme ceux-là ? ». La valeur est dans les rendez-
vous PROPRES aux quatre territoires, pas seulement le calendrier universel. Fenêtre
proposée = quand OUVRIR la publication.

| Temps fort | Quand | Ouvrir à | Notes territoire |
|---|---|---|---|
| **Noël / marchés de Noël** | fin nov → 24/12 | ~20 oct | Montreux non, mais Annecy, Nice, Turin… |
| **Luci d'Artista (Turin)** | fin oct → jan | ~1er oct | institution turinoise, à part de Noël |
| **Immaculée (8/12)** | 8 déc | avec Noël | lance la saison côté italien |
| **Épiphanie / Befana (6/1)** | 6 jan | ~1er déc | forte en Italie, quasi absente côté FR |
| **Foire de Saint-Ours (Aoste)** | 30–31 jan | ~15 nov | LE rendez-vous valdôtain, millénaire |
| **Carnavals** | fév → mardi gras | ~15 déc | **Nice** (majeur, billetterie) ; **Ivrea** et sa bataille des oranges (Piémont) |
| **Pâques + Pasquetta** | mars-avril | J-45 | le lundi de Pâques se FÊTE en Italie |
| **Nuit des musées** | mi-mai | J-30 | européen |
| **Fête de la musique / San Giovanni** | 21 et 24 juin | J-30 | la Saint-Jean est la fête PATRONALE de Turin (feux, drone show) |
| **Fêtes du lac, sons & lumières** | juil-août | J-45 | Annecy 1er samedi d'août |
| **Ferragosto (15/8)** | 15 août | J-30 | structurant côté italien, invisible côté FR |
| **Désalpes / transhumances** | sept-oct | J-30 | très alpin, très « spécificité territoriale » |
| **Journées du patrimoine** | 3e w-e sept (FR) / GEP | J-30 | énorme volume — prévoir le cap du lot |
| **Vendanges & sagre d'automne** | sept-nov | J-30 | pilier piémontais |
| **Foire de la truffe d'Alba** | oct-nov | ~1er sept | rayonnement international, réservation |
| **Halloween / Toussaint** | 31/10 | J-30 | châteaux, visites nocturnes |
| **Fête de la science / Nuit des étoiles** | oct / août | J-21 | réseau national |

⚖️ Valider/élaguer cette liste, et décider si elle vit dans `config/temps_forts.json`
(détection par mots-clés FR/IT + fenêtre propre) ou reste une simple paire de constantes.

## Ce que ça ne fait PAS

On n'arrête ni la collecte ni l'évaluation ni la rédaction : tout le travail amont se
fait dès qu'on connaît l'événement — c'est la PUBLICATION seule qui attend sa saison. Le
stock d'hiver se constitue en été, et sort prêt, d'un coup, au bon moment. C'est l'inverse
d'un retard : c'est de l'avance qui ne se voit pas.
