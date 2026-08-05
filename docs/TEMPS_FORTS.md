# Le juste temps — quand publier ce qu'on sait déjà

**Proposition du 2026-08-04.** Question de Franck : « on connaît déjà des événements de
Noël mais ce n'est pas le moment de les afficher. Quand les afficher ? »

**Implémenté le 2026-08-05, corrigé le jour même.** Première version : une fenêtre de 90
jours s'appliquant à TOUT événement daté. Faux — Franck : « je n'ai pas demandé les 90
jours pour ce genre de festival [Nice Jazz, Carnaval de Nice]… ça peut être plus loin. »
Le problème n'est pas la distance dans le temps, c'est le DÉCALAGE THÉMATIQUE (un marché
de Noël en plein été jure ; un concert de mars annoncé en septembre ne jure de rien).

**Le principe corrigé : AUCUNE fenêtre par défaut.** Seuls les temps forts THÉMATIQUES
nommés dans `config/temps_forts.json` en ont une — pour l'instant seulement Noël (65
jours) et Halloween (30 jours), les deux seuls exemples confirmés par Franck. Les grands
festivals à billetterie (Musilac, Nice Jazz, Carnaval de Nice…) n'ont DÉLIBÉRÉMENT aucune
entrée : ils n'ont pas de problème de décalage saisonnier, la réservation anticipée leur
sert. Voir `utils/saison.py` et le portillon dans `scripts/publish_batch_as.py`.

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

✅ **Pas de fenêtre par défaut** — un événement ordinaire (concert, expo, marché
hebdomadaire…) se publie dès qu'il est prêt, quelle que soit la distance dans le temps,
comme avant le 2026-08-04. Seuls Noël (65 jours) et Halloween (30 jours) sont **confirmés
par Franck** dans `config/temps_forts.json` (détection par mot-clé FR/IT dans le titre ou
la description).

⚖️ **Proposé le 2026-08-05, PAS ENCORE CONFIRMÉ** : le reste du tableau ci-dessous a été
ajouté à `config/temps_forts.json` avec les fenêtres qu'il propose déjà — Luci d'Artista,
Immaculée, Épiphanie, Pâques/Pasquetta, Nuit des musées, Fête de la musique, Ferragosto,
Désalpes, Journées du patrimoine, Vendanges & sagre, Fête de la science/Nuit des étoiles.
Chaque entrée porte `"notes": "PROPOSÉ, pas confirmé…"` dans le fichier — à valider ou
corriger un par un, ou à retirer en bloc si Franck préfère s'en tenir aux deux confirmés.
**Volontairement absents** (même logique que Musilac/Nice Jazz — Franck, 2026-08-05) :
Carnavals (Nice/Ivrea, billetterie), Foire de Saint-Ours, Foire de la truffe d'Alba — ce
sont des rendez-vous à réserver tôt, pas des moments à décalage saisonnier.

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
