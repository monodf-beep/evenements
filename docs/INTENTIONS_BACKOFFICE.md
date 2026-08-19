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

### Le contrôle quotidien des pages orphelines

**Snippet 149**, `CS - Audit des pages orphelines`, tous les jours à 10 h,
rapport Slack seulement s'il y a quelque chose à dire.

Il charge les surfaces qui relient (les deux plans du site, les huit hubs de
territoire), lit les menus en base, puis vérifie que chaque page portant
`cs_hub_ville` figure quelque part. Première passe : 232 pages contrôlées,
**zéro orpheline**.

> **Pourquoi un contrôle et pas une colonne dans le tableau.** Il faudrait
> compter les liens en base, or les surfaces qui relient sont des **shortcodes** :
> le plan du site rend 328 liens qui n'existent pas dans `post_content`. Un
> comptage en base annonçait **196 orphelines alors qu'il n'y en avait aucune**.
> Il faut charger la page et regarder le HTML rendu. Trop lourd pour un tableau
> affiché à chaque visite, juste ce qu'il faut une fois par jour.

**À quoi sert un lien entrant**, puisque la question s'est posée. Il rend la page
atteignable autrement que par la recherche. Il dit à Google qu'elle compte, le
maillage interne étant un signal d'importance. Et il fait revenir le robot plus
souvent, ce qui, pour un agenda dont le contenu se périme, vaut plus que pour un
site ordinaire.

### Les cinq contrôles quotidiens

| Heure | Contrôle |
|---|---|
| 09:00 | Médiathèque : vocabulaire et tirets dans les alternatives, mesures |
| 10:00 | Pages orphelines |
| 11:06 | Garde-fous 2 : panel, formes, lieux |
| 15:19 | Doctrine éditoriale, liste complète du lexique |
| 23:30 | Garde-fous dates et sources |

---

## 7. Mise à jour SEO du 2026-08-18, seconde partie

### Les indexables Yoast ne suivent pas un changement de langue

Yoast sert ses données depuis la table `yoast_indexable`, pas depuis les métas.
Après avoir rebasculé huit fiches en français, **sept y portaient encore leur
ancienne URL `/it/`**. Le canonique et l'`og:url` servis étaient donc faux.

Lignes supprimées et reconstruites par `YoastSEO()->meta->for_post()`, après
sauvegarde dans `cs_bk_yoast_indexable_20260818`. Vérifié sur le HTML servi :
canonique, `og:url` et `og:locale` à `fr_FR` corrects.

> **À retenir : tout changement de langue, de slug ou de statut demande une
> reconstruction de l'indexable.** Sinon WordPress dit une chose et Yoast en
> déclare une autre aux moteurs.

### Quatre paires de jumelles n'étaient pas reliées

Appariées sur date de début **et** lieu identiques, un critère volontairement
strict, quatre paires FR/IT du même événement vivaient côte à côte sans lien de
traduction :

| FR | IT | Événement |
|---|---|---|
| 756 | 2299 | Orchestre de la Suisse Romande à Évian |
| 2255 | 7610 | Foire du sanctuaire de Vicoforte |
| 6373 | 7223 | Mausoleo della Bela Rosin, Turin |
| 6405 | 7197 | Salone Auto Torino 2026 |

Reliées par `pll_save_post_translations`, sauvegarde dans
`cs_bk_traductions_20260818`. **Les quatre émettent désormais leur `hreflang`**,
vérifié sur le HTML servi. Deux d'entre elles sont des fiches rebasculées la
veille : leur vraie version italienne existait bien, simplement non reliée.

Un lien de traduction ne coûte aucun texte et produit le `hreflang`, qui dit à
Google que deux pages sont le même contenu en deux langues. Sans lui, les deux
se concurrencent.

### Deux vérifications qui n'ont rien donné, et c'est une bonne nouvelle

**Le défaut inverse n'existe pas** : zéro fiche déclarée française et rédigée en
italien. Le décalage n'allait que dans un sens.

**Un seul slug porte un nom de site tiers** : la 6445, avec
`...-summit-valledaostaglocal-it`. Le contrôle couvrait quatorze noms de sources
et d'agrégateurs, plus les suffixes de domaine.

### Les pages /explore/ déclarent le canonique de l'accueil

`/explore/savoie/`, `/explore/piemont/` et les autres portent le titre de
l'accueil et canonisent vers `/`. C'est la conséquence du routage : ces URL
rendent la page 928.

**Ce n'est pas un défaut à corriger.** Ce sont des vues filtrées de l'accueil,
et elles disent correctement aux moteurs d'indexer l'accueil à leur place. Les
pages destinées à se classer sont ailleurs et sont saines : `/que-faire-en-savoie/`
et `/it/cosa-fare-in-savoia/` portent leur propre titre, leur propre canonique
et leur `hreflang` croisé. Vérifié sur les trois hubs testés.

---

## 8. Trouver les villes : état réel au 2026-08-18

### Ce qui existe

29 hubs racines en français, chacun avec exactement **trois** pages datées
filles : aujourd'hui, ce week-end, cette semaine. Soit 116 pages françaises et
autant d'italiennes.

| Territoire | Hubs racines |
|---|---|
| Savoie | Savoie, Chambéry, Annecy, Chamonix, Aix-les-Bains, Albertville, Annemasse, Cluses, Moûtiers, Sallanches, Saint-Jean-de-Maurienne, Thonon-les-Bains, Chablais |
| Piémont | Piémont, Turin, Monferrato, et les 8 provinces |
| Comté de Nice | Comté de Nice, Nice, Côte d'Azur |
| Vallée d'Aoste | Vallée d'Aoste, Aoste |

### Le déséquilibre, qui est le vrai sujet

**Onze villes en Savoie, une seule au Piémont, une à Nice, une en Vallée
d'Aoste.** Le Piémont n'a que Turin, alors qu'Asti, Alba, Cuneo, Vercelli,
Novare, Biella, Ivrée existent comme provinces mais pas comme villes. Le comté
de Nice n'a que Nice, sans Menton, Antibes, Grasse ni Vence. La Vallée d'Aoste
n'a qu'Aoste, sans Courmayeur, Châtillon ni Cogne.

Ce n'est pas un défaut de navigation : c'est un défaut de couverture.

### Le pied de page pointait à côté

Les quatre intitulés de territoire du menu `footer-territoires` (281) pointaient
vers `/territoire/savoie/`, une archive de taxonomie qui **301 vers le vrai
hub**. Les liens marchaient, au prix d'un saut inutile sur chaque lien interne.

**Le pied de page italien (521), lui, pointait déjà correctement** vers
`/it/cosa-fare-in-savoia/`. L'asymétrie ne venait pas d'un choix, mais d'un
oubli côté français.

Corrigé : les quatre pointent maintenant directement sur leur hub. Sauvegarde
dans `cs_bk_menu281_20260818`.

### Quinze hubs ne sont pas au pied de page

Les 8 provinces, plus Monferrato, Côte d'Azur et Chablais. Ils ne sont pas
orphelins pour autant : le plan du site généré et la rangée de villes des hubs
de territoire les relient. Les mettre au pied de page allongerait beaucoup une
colonne déjà longue, pour des pages très fines.

### Il n'existe aucune page « ce mois-ci »

Les trois moments sont aujourd'hui, ce week-end, cette semaine.
« Que faire à Annecy en septembre » n'a pas de page, alors que la requête existe
et que la page serait **mieux remplie** que celle du week-end.

> **Une page par mois calendaire serait un piège** : 29 hubs × 12 mois × 2
> langues font 696 pages, presque toutes vides et périmées d'avance. Le bon
> objet est une quatrième page glissante, « ce mois-ci », sur le modèle exact
> des trois autres : 58 pages, pas 696.

---

## 9. Les FAQ génériques (2026-08-19)

### Ce que la mesure a montré

Le snippet 61 construisait la FAQ en « socle hybride » : quatre questions
communes **toujours** présentes, plus une surcouche par ville lue dans
`cs_hub_faq`. Deux conséquences que le nom « socle » masquait.

**Le socle s'ajoutait à la FAQ rédigée au lieu d'être remplacé par elle.** Sur
Chambéry, la page servait les quatre questions génériques *puis* les questions
écrites à la main sur l'Espace Malraux, le théâtre Charles Dullin et les
Charmettes. Deux blocs empilés sur la même page.

**Il s'affichait aussi sur les 174 pages datées.** Le même bloc, avec le même
balisage `FAQPage`, sur **232 pages**. Du balisage de questions dupliqué à cette
échelle est au mieux ignoré, au pire lu comme du remplissage.

### Ce qui est corrigé

| | Avant | Après |
|---|---|---|
| Pages datées (aujourd'hui, week-end, semaine) | FAQ + schéma | **plus de FAQ du tout** |
| Hub avec `cs_hub_faq` | socle **+** FAQ rédigée | **FAQ rédigée seule** |
| Hub sans `cs_hub_faq` | socle | socle, en attendant sa rédaction |

Le bloc générique a disparu de **191 pages sur 232**. Sauvegarde du code dans
`cs_bk_snippet61_20260819`.

### Ce qui reste : 41 hubs à écrire

17 hubs ont une FAQ rédigée, **41 n'en ont pas** et gardent donc le socle : les
8 villes de Savoie créées le 2026-08-18, les 8 provinces du Piémont, les 4
territoires, et les jumelles italiennes manquantes.

> **Une FAQ ne se remplit pas, elle s'écrit.** Le modèle est celui de Chambéry :
> des lieux nommés, une programmation réelle. « Misez sur les sorties couvertes »
> ne dit rien que la page ne dise déjà, et le dit à l'identique partout.

**Méthode retenue :** la matière vient du site lui-même, lieux du catalogue
(`tribe_venue`), texte d'introduction du hub déjà validé, événements récurrents.
On n'invente pas un patrimoine, on nomme celui qui est déjà documenté.

**Les propositions vont dans `cs_hub_faq_propose`, jamais directement dans
`cs_hub_faq`**, conformément au non-négociable « aucune publication autonome ».
Première proposition écrite : Annemasse, français et italien (7823 et 7824).

---

## 10. Ce que doit contenir le résumé d'un hub (2026-08-19)

### La question

Faut-il détailler les lieux dans le résumé d'une ville, ou parler de la ville ?
Position de Franck : les lieux sont déjà cités dans les fiches d'événements.

### Réponse mesurée

**D'accord sur le sujet, pas sur le motif.** Les lieux ne sont cités dans les
fiches que si des événements s'y tiennent au moment de la visite. Annemasse en
compte trois. Si aucun ne se joue à Château Rouge cette semaine, la page ne
nomme jamais l'équipement principal de la ville. Le hub est justement la page
qui doit poser les ancrages, parce que la liste ne peut pas s'en charger.

**Le défaut est ailleurs.** Sur 29 hubs français :

| Constat | Nombre |
|---|---|
| Même phrase « Retrouvez ici tout ce qu'il y a à faire à… » | 11 |
| Même phrase « l'agenda passe des concerts et des expositions… » | 5 |
| Intro sous 70 mots | 12 |

Les douze intros courtes sont les 8 provinces (33 à 45 mots), **les 4
territoires** (54 à 59) et Annecy (57). Les pages censées se classer le plus
large sont les plus maigres.

### Le partage retenu

- **Intro** : deux ou trois phrases sur la ville, puis deux ou trois sur le
  **rythme** de ce qui s'y passe. C'est la seule matière que ni Wikipédia ni les
  fiches ne portent. Modèle déjà en production : Chamonix, « l'agenda y suit le
  rythme de la montagne, entre saison estivale et hivernale ».
- **FAQ** : les mêmes lieux, mais pour dire **comment s'en servir** — horaires,
  gratuité, quel parc quel soir. Pas une seconde description.

### La recherche n'est pas optionnelle

Sur Annemasse, elle a corrigé une erreur de fond de mon brouillon : les
Musical'été occupent **deux** parcs, le vendredi à La Fantasia (sonorités du
monde) et le samedi à Montessuit (jazz), du 3 juillet au 22 août, gratuits,
portés par Château Rouge et la Ville. Elle a aussi rétabli deux faits que
j'avais affaiblis par prudence : la Villa du Parc est bien **centre d'art
contemporain d'intérêt national**, et Château Rouge présente **environ 130
spectacles par saison dans quatre salles**.

Sources chez les organisateurs, jamais les agrégateurs, conformément au vault.
Le site de la ville d'Annemasse est derrière une protection anti-robot : elle
n'est pas contournée.

**Compter environ trois recherches par ville**, soit une centaine pour les 41
hubs. Ce n'est plus de la rédaction, c'est de la documentation.

### Les FAQ rédigées, ville par ville (2026-08-19)

Six villes traitées après Annemasse, français et italien, avec recherche chez
les organisateurs et les communes avant écriture :

| Ville | Ce que la recherche a apporté |
|---|---|
| Albertville | Le Dôme réunit théâtre (scène conventionnée), cinéma Art et Essai deux salles, médiathèque ; Théâtre de Maistre 400 places ; Halle olympique, ancienne patinoire de 1992 rénovée en 2015, jusqu'à 9 000 personnes en concert |
| Thonon-les-Bains | Maison des Arts du Léman, plus de 60 rendez-vous par saison, au théâtre Maurice Novarina (1961) ; galerie de l'Étrave, trois expositions photo par an ; Chemins de Traverse d'octobre à mai, Montjoux Festival en juillet ; Ripaille visitable d'avril à octobre, mardi au dimanche |
| Saint-Jean-de-Maurienne | Cloître de 1450, stalles en noyer de 1498, l'un des treize ensembles du Credo savoyard subsistant en Europe ; théâtre Gérard Philipe de 1934, 328 places ; musée Opinel dans l'atelier du grand-père Jean |
| Moûtiers | Centre culturel Marius Hudry dans l'ancien palais archiépiscopal des comtes de Tarentaise, entrée libre, expositions mensuelles ; cathédrale à chœur roman, façade gothique, nefs néoclassiques, orgue Cavaillé-Coll |
| Sallanches | Château des Rubins, Observatoire des Alpes, rouvert en juillet 2021, cinquante modules interactifs sur quatre étages et 500 m² ; église Saint-Jacques reconstruite en 1681, juste devant |
| Cluses | Musée de l'Horlogerie et du Décolletage dans l'Espace Carpano et Pons, pièce la plus ancienne du XVIe siècle, fondé par l'École nationale d'horlogerie |

Réponses de 38 à 80 mots, sans gras, sauvegardes dans `cs_bk_faq_<id>_20260819`.
Vérifié sur les seize pages servies : le socle générique n'apparaît plus.

**16 hubs sur 29 ont une FAQ rédigée.** Restent Aix-les-Bains, les quatre
territoires et les huit provinces.

> **La recherche apporte ce que le catalogue ne contient pas.** Aucun de ces
> faits, 9 000 places, 1498, 1681, 500 mètres carrés, ne se trouvait dans la
> base du site. Ce sont eux qui distinguent une page.

---

## 11. Comment tenir les villes et les hubs quand ils se multiplient (2026-08-19)

### Le problème posé

Le pied de page montrait onze villes sous Savoie et **une seule** sous Piémont,
Nice et Vallée d'Aoste. Déséquilibre créé le 2026-08-18 en ajoutant les huit
nouvelles villes de Savoie sans traiter les autres territoires.

Ce n'est pas qu'une affaire d'apparence. La Charte commune pose que **Nice est
core, pas périphérique**, et que les quatre territoires sont à égalité. Un pied
de page à onze contre un dit le contraire, au lecteur comme aux moteurs.

### Le principe retenu : quatre étages, un seul qui grandit

| Surface | Contenu | Croît ? |
|---|---|---|
| Pied de page | les 4 territoires, jusqu'à 4 villes chacun | **non, stable** |
| Hub de territoire | toutes les villes, zones et provinces | oui |
| Hub de ville | les villes voisines du même territoire | oui |
| Plan du site | tout, généré | oui |

**Le pied de page ne doit pas grandir.** Il est présent sur toutes les pages ;
au delà de quelques entrées par colonne, plus personne ne le lit et la valeur de
chaque lien se divise. **La surface qui grandit, c'est le hub de territoire**,
où un lien vers une ville est thématiquement adjacent, donc bien plus fort.

### Ce qui a été fait, dans cet ordre

**1. La rangée de villes voisines, d'abord.** `[cs_villes_du_territoire]` posé
sur les **50 hubs de ville et de province**, français et italiens. Le shortcode
exclut déjà la page courante et filtre par territoire : aucun développement.
Chaque ville de Savoie pointe désormais vers dix voisines, Turin vers neuf.

**2. Le pied de page, ensuite.** Quatorze entrées retirées, sept par langue :
Albertville, Annemasse, Cluses, Moûtiers, Sallanches, Saint-Jean-de-Maurienne,
Thonon-les-Bains. Restent Chambéry, Annecy, Chamonix et Aix-les-Bains sous
Savoie. Sauvegarde complète dans `cs_bk_menus_footer_20260819`.

> **L'ordre n'est pas un détail :** ajouter les liens avant d'en retirer garantit
> qu'aucune page ne passe, même une minute, par un état non relié.

Contrôle des orphelines relancé après coup : **232 pages, zéro orpheline.** Les
sept villes retirées du pied de page répondent toujours 200 et sont reliées par
dix pages sœurs, par leur hub de territoire et par le plan du site, soit
davantage qu'avant.

### Une fausse piste écartée

Le bloc « Aux alentours » des hubs de ville n'est pas un lien vers les villes
voisines : c'est un repli qui affiche **d'autres événements du même territoire**.
Il ne pouvait pas jouer ce rôle, d'où la rangée ajoutée.

### La suite

Le pied de page se remplira à mesure que les villes du Piémont, du comté de Nice
et de la Vallée d'Aoste seront créées, **jusqu'à quatre par territoire, pas
au delà**.
