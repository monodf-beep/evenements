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

## Relecture CIBLÉE par territoire
Un événement n'est relu QUE par les personas de son aire (`ev.territoire`) : un événement
de Menton (`Nice`) est jugé par Jean-Pierre et Karine, pas par un ouvrier de Maurienne.
Sinon la note mesure la distance, pas la qualité. Si le territoire est inconnu ou sans
persona dédié, tout le panel relit (filet). Bonus : ~2 relecteurs par article au lieu de 8
→ moins cher.

## Réglages
- `ENRICH_READER_REVIEW=0` désactive tout le panel.
- `ENRICH_READER_PERSONAS=3` limite le nombre de personas consultés (défaut : tous ceux de l'aire).
