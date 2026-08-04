# Plancher de « Ça vaut le déplacement » — 2026-08-04

224 fiche(s) en ligne, dont **170 encore devant nous** (à venir, en cours, récurrentes — règle 5).
9 sans note mesurable : hors section quoi qu'on décide, elles ne sont pas « nulles » mais « pas mesurées ».

Seuil actuel : **6** sur 8. Horizon : 183 jours.

## Combien de fiches à chaque note

| Note | Fiches | Exemples |
|---:|---:|---|
| 8 | 6 | La Saint-Ours 2026 - Rendez Vous e · Marisa Merz – La danza delle ore · Il 44TFF sarà dedicato a Marilyn M |
| 7 | 8 | ESTATE REALE 2026. UNA SERA AL MUS · Arte Povera e nuovi allestimenti n · Istituzione musicale | Un annivers |
| 6 | 18 | Un’estate da esploratori: laborato · Brahms / Chostakovitch · Matisse – Yves Saint Laurent, le B |
| 5 | 33 | Visite au Château de Montrottier · La Buona Aria. Un viaggio nel temp · MonumenTO, Torino Capitale. La for |
| 4 | 27 | 60 minutes de violoncelle · Le TNN en tournée dans la Métropol · Little Italy Festival |
| 3 | 26 | Un été à Albé · Festival des Jardins Alpestres · Face à face – Orlando |
| 2 | 10 | Les Jeudis d’Aime · Visite flash : patrimoine vivant · L’hydroélectricité en Tarentaise |
| 1 | 22 | L’été au centre socioculturel · Chopin · Dinosaures: Le voyage de Bumpy®, l |
| 0 | 11 | Story Time · Le Meilleur des Inconnus · Exposition : LEVITATION de Mathieu |

## D'où viennent les points (part de chaque critère)

| Critère | Points donnés | Part du total | Max observé |
|---|---:|---:|---:|
| `notoriete_lieu` | 267 | 44 % | 3 |
| `edition_tradition` | 115 | 19 % | 2 |
| `rayonnement` | 147 | 24 % | 2 |
| `specificite_territoriale` | 76 | 13 % | 1 |

> `notoriete_lieu` note LA SALLE, pas l'événement. S'il pèse le plus lourd,
> la note récompense la réputation du lieu plutôt que la raison de s'y rendre —
> et un plancher plus haut ne corrigerait pas ça, il ne ferait que retenir les
> événements des grandes salles. C'est la PONDÉRATION qu'il faudrait revoir.


## Simulation : ce que la pondération proposée changerait

| Critère | Poids | Plafond | Part du maximum |
|---|---:|---:|---:|
| `rayonnement` | ×2 | — | 4/12 |
| `specificite_territoriale` | ×3 | — | 3/12 |
| `edition_tradition` | ×1 | — | 2/12 |
| `notoriete_lieu` | ×1 | 1 | 1/12 |
| `accessibilite_langue` (NOUVEAU, déduit de la catégorie) | ×1 | — | 2/12 |

### Le haut de chaque territoire — avant / après


**Nice**  ← l'ordre CHANGE

| rang | actuel (/8) | proposé (/10) |
|---:|---|---|
| 1 | 8 · Festival de Musique de Menton | 11 · Festival de Musique de Menton |
| 2 | 6 · Brahms / Chostakovitch | 10 · Matisse – Yves Saint Laurent, le Beau, |
| 3 | 6 · Matisse – Yves Saint Laurent, le Beau, | 9 · Visite guidée du Stade Allianz Riviera |

**Piemonte**  ← l'ordre CHANGE

| rang | actuel (/8) | proposé (/10) |
|---:|---|---|
| 1 | 8 · Marisa Merz – La danza delle ore | 12 · Tour de l'Avenir 2026 - Strambino Lago |
| 2 | 8 · Il 44TFF sarà dedicato a Marilyn Monro | 12 · Marisa Merz – La danza delle ore |
| 3 | 8 · Dal 24 al 27 settembre Terra Madre Sal | 12 · Dal 24 al 27 settembre Terra Madre Sal |

**Savoie**  ← l'ordre CHANGE

| rang | actuel (/8) | proposé (/10) |
|---:|---|---|
| 1 | 8 · Une semaine pas plus | 11 · Une semaine pas plus |
| 2 | 6 · orchestre de la suisse romande | 10 · Chambéry. Les trésors des empires de l |
| 3 | 6 · Chambéry. Les trésors des empires de l | 9 · Visite au Château de Montrottier |

**Vallee-Aoste**  ← l'ordre CHANGE

| rang | actuel (/8) | proposé (/10) |
|---:|---|---|
| 1 | 8 · La Saint-Ours 2026 - Rendez Vous en Va | 12 · La Saint-Ours 2026 - Rendez Vous en Va |
| 2 | 7 · Le avventure di Pinocchio, dal Monte B | 11 · Collontrek 2026 |
| 3 | 7 · Al Marché au Fort l’enogastronomia del | 10 · Al Marché au Fort l’enogastronomia del |

### Où se placerait le plancher

| Plancher /10 | Fiches retenues |
|---:|---:|
| **4** | 119 |
| **5** | 110 |
| **6** | 99 |
| **7** | 85 |
| **8** | 57 |
| **9** | 35 |
| **10** | 17 |
| **11** | 10 |
| **12** | 4 |

> Le plancher ne se transpose PAS : 6/8 et 6/10 n'expriment pas la même
> exigence, et la distribution change aussi. À re-décider sur ce tableau.


## Ce que chaque plancher laisse, PAR TERRITOIRE

| Plancher | Total | Nice | Piemonte | Savoie | Vallee-Aoste |
|---:|---:|---:|---:|---:|---:|
| **3** | 118 | 21 | 47 | 28 | 22 |
| **4** | 92 | 17 | 38 | 17 | 20 |
| **5** | 65 | 10 | 33 | 10 | 12 |
| **6** | 32 | 6 | 16 | 3 | 7 | ← actuel
| **7** | 14 | 1 | 9 | 1 | 3 |
| **8** | 6 | 1 | 3 | 1 | 1 |

> Un zéro dans une colonne = cette carte de la home reste VIDE. C'est le seul
> chiffre qui compte ici : le total global peut rester confortable pendant qu'un
> territoire disparaît de la section.

## Le versant ITALIEN, qui casse en premier

La home italienne ne puise que dans les fiches traduites — Savoie et Comté de Nice.
Deux places à remplir, et ce vivier-là seul pour les remplir.

| Plancher | Candidates traduisibles (Savoie + Nice) |
|---:|---:|
| **3** | 49 |
| **4** | 34 |
| **5** | 20 |
| **6** | 9 |
| **7** | 2 |  ⚠️ moins de 2 par place
| **8** | 2 |  ⚠️ moins de 2 par place

> Sous quatre candidates, il n'y a plus de marge : deux arrivent à terme et la
> section italienne se vide. Plus d'exigence se gagne alors en TRADUISANT et en
> ÉVALUANT davantage, pas en relevant le plancher.

## Les 26 fiche(s) entre 6 et 7

Ce sont elles qui sortiraient. Lire quelques justifications vaut mieux que lire un total — c'est là qu'on voit si le score dit vrai.

- **7/8** · Piemonte · ESTATE REALE 2026. UNA SERA AL MUSEO
    - notoriete_lieu (3) : Musei Reali di Torino, lieu emblématique et majeur du centre-ville
    - edition_tradition (2) : 10e anniversaire, rendez-vous estival récurrent et identifié
- **7/8** · Piemonte · Arte Povera e nuovi allestimenti nella collezione permanente
    - notoriete_lieu (3) : Castello di Rivoli, musée d'art contemporain emblématique et internationalement reconnu
    - edition_tradition (1) : Réaménagement de la collection permanente, récurrent mais non ponctuel
- **7/8** · Piemonte · Istituzione musicale | Un anniversario importante per il C2C
    - notoriete_lieu (2) : Festival se déroule dans divers lieux emblématiques de Turin (club, spazi culturali)
    - edition_tradition (2) : Anniversario importante, edizione storica del festival
- **7/8** · Piemonte · Cavallerizza ospita Graphic Days
    - notoriete_lieu (3) : Cavallerizza Reale, sito storico emblematico di Torino
    - edition_tradition (2) : Settima edizione, evento consolidato
- **7/8** · Piemonte · La grande Fiera del Santuario di Vicoforte
    - notoriete_lieu (3) : Santuario di Vicoforte, basilique célèbre à la coupole elliptique la plus grande du monde
    - edition_tradition (2) : Tradition séculaire liée à la Natività di Maria, mémoire historique des falò
- **7/8** · Vallee-Aoste · Le avventure di Pinocchio, dal Monte Bianco ai mari di Ischi
    - notoriete_lieu (3) : Forte di Bard, lieu culturel emblématique et très fréquenté de la Vallée d'Aoste
    - edition_tradition (2) : Projet célébrant le bicentenaire de la naissance de Collodi, événement commémoratif majeur
- **7/8** · Vallee-Aoste · Al Marché au Fort l’enogastronomia della Valle d’Aosta in ve
    - notoriete_lieu (3) : Forte di Bard, lieu emblématique très fréquenté de la Vallée d'Aoste
    - edition_tradition (2) : 22e édition, rendez-vous historique et bien ancré
- **7/8** · Piemonte · Tour de l'Avenir 2026 - Strambino Lago Serrù
    - notoriete_lieu (2) : Lago Serrù, site naturel emblématique du Parc National du Gran Paradiso
    - edition_tradition (2) : Course historique, 65 ans d'existence
- **6/8** · Vallee-Aoste · Un’estate da esploratori: laboratori per bambini ogni marted
    - notoriete_lieu (3) : Forte di Bard, site emblématique et très cité en Vallée d'Aoste
    - edition_tradition (1) : Programmation estivale récurrente saisonnière
- **6/8** · Nice · Brahms / Chostakovitch
    - notoriete_lieu (3) : Opéra de Nice, salle emblématique de la ville
    - edition_tradition (1) : Concert récurrent de la saison symphonique
- **6/8** · Nice · Matisse – Yves Saint Laurent, le Beau, la Mode et le Bonheur
    - notoriete_lieu (3) : Musée Matisse, institution muséale majeure de Nice
    - edition_tradition (0) : Exposition ponctuelle, pas de tradition établie
- **6/8** · Savoie · orchestre de la suisse romande
    - notoriete_lieu (3) : La Grange au Lac est une salle de concert renommée internationalement
    - edition_tradition (1) : Programmation récurrente de la saison musicale
- **6/8** · Piemonte · La Fiera del Bue grasso
    - notoriete_lieu (2) : Foro boario de Carrù, lieu emblématique local très cité pour cette foire
    - edition_tradition (2) : Tradition vieille de cinq siècles, rendez-vous historique
- **6/8** · Piemonte · Palio Montis Regalis: la tenzone più folle
    - notoriete_lieu (2) : Centre historique de Mondovì, ville moyenne reconnue du Piémont
    - edition_tradition (2) : Palio storico traditionnel, rendez-vous annuel établi de fin août
- **6/8** · Vallee-Aoste · Apre il nuovo parco archeologico di Aosta
    - notoriete_lieu (3) : Area megalitica, site archéologique majeur d'Aoste, l'un des plus riches d'Europe
    - edition_tradition (1) : Site historique majeur, réouverture après rénovation muséographique
- **6/8** · Nice · Visite guidée du Stade Allianz Riviera & Musée National du S
    - notoriete_lieu (3) : Stade Allianz Riviera, lieu emblématique de Nice, abritant le Musée National du Sport
    - edition_tradition (1) : Visite guidée récurrente, sans mention d'édition particulière
- **6/8** · Piemonte · Cinema sotto le stelle al Valentino: torna “Cinema nel Prato
    - notoriete_lieu (3) : Parco del Valentino, luogo iconico e centrale di Torino
    - edition_tradition (1) : Rassegna estiva ricorrente, torna ogni anno
- **6/8** · Nice · La Farandole, festival international de folklore
    - notoriete_lieu (2) : Lieu non précisé mais événement se déroulant dans Nice, ville majeure
    - edition_tradition (2) : Festival international établi, rendez-vous récurrent
- **6/8** · Nice · Arrivée du Tour de France Féminin 2026
    - notoriete_lieu (3) : Promenade des Anglais, lieu emblématique de Nice
    - edition_tradition (1) : Événement récurrent (édition 2026)
- **6/8** · Vallee-Aoste · Collontrek 2026
    - notoriete_lieu (2) : Barrage de Place Moulin, site naturel emblématique du Val d'Aoste
    - edition_tradition (1) : Édition 2026 suggère un rendez-vous annuel établi
