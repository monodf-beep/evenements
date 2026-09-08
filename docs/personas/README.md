# Personas lecteurs — panel de relecture

Chaque fichier `.md` de ce dossier (sauf ce README) est un **persona lecteur** : une
personne fictive mais crédible du public de Cultura Sabauda / Agenda Sabauda. Après la
rédaction d'un article développé, **chaque persona relit le brouillon** et donne son avis
(intérêt sur 5, ce qui lui manque, un conseil). Si le panel juge l'article creux, une
révision est demandée au rédacteur.

## Comment ça marche
- Le pipeline lit ce dossier à chaque run (`utils/personas.py`). Ajoute, retire ou édite
  un fichier : le prochain enrichissement en tient compte, sans redéploiement.
- On peut aussi pointer un dossier Obsidian avec la variable d'env `PERSONAS_DIR`
  (comme `VOIX_DIR` pour la voix). Sinon, c'est ce dossier du dépôt qui sert.
- Le panel s'affiche au back-office (page **Personas** et encart dans le preview d'un
  événement).

## Écrire un persona
Un titre `# Nom du persona`, puis en quelques lignes : qui il est, ce qu'il cherche dans
un article d'agenda, et ce qui le déçoit (ses drapeaux rouges). Reste concret : le persona
sert à faire remonter un MANQUE de fond (pas de têtes d'affiche, pas de programme, langue
de bois), pas à réécrire la charte de style (c'est le rôle de la voix).

## Le panel actuel (8 personas sourcés, 2 par aire)
Issus d'une recherche territoriale (voir `RECHERCHE.md`), curés pour couvrir les axes
capital culturel × moyens × mobilité × urbain/rural × âge × langue, sans caricature.
Chaque persona porte une **aire** (frontmatter `aire:`) alignée sur `events_raw.territoire` :

| Aire (`territoire`) | Personas |
|---|---|
| **Savoie** | Kévin (ouvrier de vallée, Maurienne) · Camille (frontalière pauvre en temps, Genevois) |
| **Vallee-Aoste** | Chantal (fonctionnaire bilingue, Aoste) · Rémy (agriculteur, vallée du Lys) |
| **Piemonte** | Manuela (quartier populaire sans voiture, Turin) · Piera (rurale grande lectrice, Valle Maira) |
| **Nice** | Jean-Pierre (retraité de l'arrière-pays, Roya) · Karine (Niçoise sans voiture, Riquier) |

## Relecture CIBLÉE : deux notes (locaux + visiteur)
Un événement a **deux publics**, jugés séparément :

1. **Locaux (sur place)** — personas dont l'`aire` == `ev.territoire`. Ils jugent l'accès,
   la pertinence quotidienne, le prix. **Ce sont eux qui pilotent la note et la révision.**
2. **Visiteur d'une aire voisine** — persona d'une AUTRE aire qui irait plausiblement là-bas
   (corridor déclaré dans son frontmatter `visite:`). Il juge une autre question : « est-ce
   que ça vaut l'aller-retour / le week-end ? ». Signal complémentaire, ne déclenche pas la
   révision.

La distance n'est donc plus pénalisée à tort : un événement de Menton est jugé par des
Niçois (locaux) et par Piera (Cuneo, qui irait via Tende) — **jamais par un Savoyard**, pour
qui Nice n'est pas un corridor. Corridors actuels (`visite:`) :

| Persona | Aire | Irait en visite à |
|---|---|---|
| Camille (Genevois) | Savoie | Vallée d'Aoste (Courmayeur), Piémont (Turin) |
| Chantal (Aoste) | Vallee-Aoste | Piémont (Turin), Savoie |
| Piera (Cuneo) | Piemonte | Nice (col de Tende) |

Les personas enracinés (Kévin, Rémy, Manuela, Jean-Pierre, Karine) n'ont pas de `visite:` :
ils ne font pas de sorties culturelles lointaines. Édite ces tags pour ajuster les corridors.
Filet : territoire inconnu → tout le panel relit (locaux), aucun visiteur.

## Réglages
- `ENRICH_READER_REVIEW=0` désactive tout le panel.
- `ENRICH_READER_PERSONAS=3` limite le nombre de personas consultés (défaut : tous ceux de l'aire).
