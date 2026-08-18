# Voir les intentions de recherche depuis le site

*Établi le 2026-08-18. Complète `INTENTIONS_RECHERCHE_SEO.md`, qui reste le plan.
Ce document décrit l'outil qui montre ce qui existe réellement.*

---

## Où

**Outils › Intentions de recherche**, dans l'administration WordPress.
Snippet 147, `CS - Intentions de recherche (admin)`.

Le plan vit dans le dépôt, donc invisible depuis le site. Cette page montre
l'état réel, calculé à chaque affichage : rien n'y est écrit à la main, donc
rien n'y vieillit.

---

## Ce qu'elle montre

**Les zones et leurs intentions temporelles.** Une ligne par zone, quatre
colonnes : hub, aujourd'hui, ce week-end, cette semaine. Chaque cellule porte
les liens FR et IT vers la page réelle, ou signale son absence en rouge.

**Les articles.** Titre, langue, territoire, mot-clé cible, état de l'image
(`oui`, `repli`, ou aucune), et un lien.

**Ce qui manque.** Calculé, pas écrit.

---

## La règle qui commande tout

> **Le nombre d'événements est un indicateur de prospection.** Il sert à savoir
> où aller chercher des sources. Il ne doit jamais servir à modifier ou
> dépublier une page.

Décision de Franck du 2026-08-18. Le catalogue se remplira ; une page calibrée
sur la pénurie d'aujourd'hui serait fausse demain.

> **Manquant ne veut pas dire à créer.** Le plan fixe un seuil : pas de page géo
> sous huit à douze événements à venir, sinon contenu mince.

---

## Comment le périmètre d'une zone est calculé

Le périmètre n'est **pas** une méta. Il est déclaré par le shortcode
`[cs_hub_ville]` dans le contenu du hub, sous trois formes :

| Forme | Exemple | Portée |
|---|---|---|
| `villes="…"` | Monferrato : `Casale Monferrato, Nizza Monferrato, Asti, Moncalvo, Costigliole d'Asti` | lieux dont `_VenueCity` correspond |
| `province="<term_id>"` | Province de Turin : `province="7"` | terme de taxonomie |
| `territoire="…"` seul | Savoie | tout le territoire |

Les pages datées sont les **pages filles** du hub (`post_parent`). C'est ce lien,
et non les traductions, qui regroupe une zone.

### Trois erreurs commises en construisant cet outil

1. **Regroupement par traduction.** Chaque page devenait sa propre zone : 61
   lignes au lieu de 21. Le bon lien est la parenté.
2. **Codes courts.** `cs_hub_territoire` vaut `vda` et `nice`, la taxonomie porte
   `vallee-d-aoste` et `comte-de-nice`. La première version affichait zéro pour
   ces deux territoires.
3. **Une seule langue.** Le mode territoire ne comptait que le terme français,
   le mode ville couvrait les deux : Turin sortait à 36 et le Piémont à 20,
   alors que Turin est dans le Piémont. Les deux slugs sont désormais comptés.

---

## Ce que le premier relevé montre

| Zone | Événements à venir |
|---|---|
| Piémont | 64 |
| Savoie | 31 |
| Comté de Nice | 26 |
| Vallée d'Aoste | 21 |
| Turin | 36 |
| Nice | 19 |
| Chablais | 7 |
| Chambéry | 7 |
| Côte d'Azur | 5 |
| Aoste | 4 |
| Province de Turin | 4 |
| **Annecy** | **2** |
| **Monferrato** | **1** |
| Provinces de Cuneo, Vercelli | 1 |
| **Chamonix** | **0** |
| Provinces d'Asti, Alexandrie, Biella, Novare, VCO | 0 |

**Priorités de sourcing qui en découlent.** Annecy est la première ville du plan
par ordre de demande et n'a que deux événements. Chamonix n'en a aucun. Le
Monferrato, dont la page est correctement construite et indexable, n'en a qu'un :
c'est pour cela qu'elle ne se classe pas, pas pour une raison technique.

**La taxonomie province est presque inutilisée** : la province de Turin porte
4 événements quand la ville de Turin en compte 36. Les fiches ne sont pas
étiquetées par province.

---

## Une divergence à arbitrer

Le plan dit que les zones et massifs ne sont **pas** des pages événementielles et
devraient rester des étiquettes en `noindex` tant que le stock et la demande
n'existent pas. Or Monferrato, Chablais, Chamonix et Côte d'Azur sont exactement
ces zones-là, et elles sont indexables.

Ce n'est pas une erreur technique : c'est une divergence entre le plan écrit et
ce qui a été construit. Soit le plan a évolué, soit ces pages devraient attendre
d'avoir de la matière.

---

## 6. Comment on retrouve ces pages (2026-08-18, seconde passe)

Question de Franck : autrement que par la barre de recherche, comment atteindre
ces pages ? Il évoquait un nuage de mots.

**Un nuage n'est pas la bonne forme ici.** Il donne le même poids à tout et
efface la hiérarchie. Ces pages ont une structure nette, territoire puis ville
puis moment. Trois surfaces ont été mises en place, de la plus large à la plus
contextuelle.

### Le menu de pied de page

Les villes sont reliées par le menu `footer-territoires` (281) et sa jumelle
italienne (521), en **sous-menu du territoire**. C'est le mécanisme existant,
et c'est là que les huit nouvelles villes ont été ajoutées, sous Savoie (1576)
et sous Savoia (3318).

> **Les 112 pages créées étaient orphelines** : présentes au sitemap, sans un
> seul lien entrant. Créer des pages sans les relier, c'est les rendre
> invisibles à la navigation et faibles pour Google. À vérifier
> systématiquement après toute création.

### Le plan du site, désormais calculé

`[cs_plan_du_site]`, snippet 148. La page était 10 Ko de HTML écrit à la main :
les nouvelles pages n'y figuraient pas et n'auraient pu y figurer sans
réécriture manuelle à chaque ajout. Elle est maintenant générée depuis les pages
réelles, groupée par territoire, chaque zone suivie de ses trois moments.
Sauvegarde de l'ancien HTML dans `cs_bk_plan_du_site_20260818`.

### La rangée de villes sur les hubs de territoire

`[cs_villes_du_territoire]`, même snippet, posé sur les huit hubs de territoire.
Des pastilles cliquables vers les villes et zones du territoire. C'est la forme
la plus proche d'un nuage qui reste utile : compacte, scannable, et surtout
contextuelle, donc bien plus forte qu'un lien de pied de page pour le
référencement.

### Trois pièges rencontrés en l'écrivant

1. **`\x{2019}` dans une chaîne PHP simple** ne vaut que dans une expression
   régulière : les apostrophes se seraient affichées littéralement. Écrire les
   vrais caractères.
2. **Le filtre `lang` de `get_posts` ne mord pas hors contexte front.** Les hubs
   français et italiens portant le même titre, chaque zone sortait en double.
   Filtrer explicitement avec `pll_get_post_language()`.
3. **`pll_current_language()` rend `false` hors contexte front**, et un ternaire
   retenait ce `false` au lieu du repli : plus aucune page ne correspondait.
   Tester la valeur, pas seulement l'existence de la fonction.
