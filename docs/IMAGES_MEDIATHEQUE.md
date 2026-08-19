# Images : ce qui est automatisé, ce qui reste au pipeline

*Établi le 2026-08-18. Chaque chiffre a été mesuré en base ou sur le HTML servi.
Rien n'est déduit.*

---

## 1. L'état mesuré

Sur 3 584 pièces jointes :

| | |
|---|---|
| Noms de fichiers descriptifs | 25 opaques seulement, soit 0,7 % |
| Textes alternatifs renseignés | 3 490, soit 97 % |
| Sitemap images | en place, 157 images pour 159 pages événement |
| Formats modernes | **33 WebP**, contre 3 194 JPEG |
| Utilisées comme vignette | **371** |
| Jamais utilisées | **3 213, soit 90 %** |
| Poids sur le disque | 19 188 fichiers, 2,69 Go |

Trois piliers sur cinq étaient déjà bien tenus. Les deux qui manquaient étaient
le format et les données structurées.

> **Un champ rempli n'est pas un champ juste.** L'alternative de la fiche du Tour
> de l'Avenir disait « Tour de l'Avenir 2026 - Strambino - Lago Serrù » sous une
> affiche d'aide aux devoirs d'une bibliothèque. Un audit qui compte les cases
> vides ne verra jamais ça. Google, lui, croise l'alternative, la vision par
> ordinateur et le contenu de la page.

---

## 2. Pourquoi la médiathèque contient trois copies de chaque visuel

Deux mécanismes distincts, tous deux dans le pipeline.

**Trois variantes téléversées, une seule employée.** Chaque visuel arrive en
`-original`, `-fiche-carte` et `-carte`. Seule la `-carte` devient la vignette
des fiches française et italienne. Cas témoin, la Fiera del Peperone : six
pièces jointes, une seule utilisée.

**Re-téléversement à chaque republication.** Le pipeline ne cherche pas la pièce
jointe existante, il en crée une. Le fichier part dans le dossier du mois
courant, donc WordPress ne voit aucune collision de nom. **235 fichiers** portent
un nom déjà présent ailleurs.

Vérification que les 3 213 orphelines le sont vraiment : sur un échantillon de
60 tirées au hasard, aucune n'est citée dans un `post_content` ; sur un autre de
40, aucune n'apparaît dans une méta, Elementor et JetEngine compris.

### Correctifs attendus côté pipeline

1. Ne téléverser que la variante réellement employée.
2. Retrouver la pièce jointe existante avant d'en créer une, par empreinte du
   fichier ou par identifiant conservé, pas par nom.

**L'ordre compte : corriger avant de nettoyer.** Un ménage fait aujourd'hui
serait défait à la republication suivante. Le nettoyage libérera environ 2 Go,
mais c'est une suppression de milliers de fichiers : par paquets, avec une liste
d'exclusion vérifiée.

---

## 3. Ce qui est en place côté WordPress

| Snippet | Rôle |
|---|---|
| **142** | Sous-tailles générées en WebP, qualité 82 |
| **143** | Crédit et licence dans les données structurées d'image |
| **144** | Vignette de partage 1200x630, déclarée et en JPEG forcé |
| **145** | Audit quotidien de la médiathèque, rapport Slack |

Aucun plugin d'optimisation n'a été installé : le serveur a GD **et** Imagick
compilés avec WebP, et WordPress convertit nativement depuis la 6.1.

### 142, la conversion WebP

Filtre `image_editor_output_format`. Touche les **sous-tailles**, pas le fichier
d'origine, qui reste en JPEG comme archive. Ne touche pas les images déjà en
ligne : **décision de Franck du 2026-08-18, pas de rattrapage**. Le catalogue se
renouvelle, les images servies dans six mois auront été téléversées après.

### 143, crédit et licence

Filtre `wpseo_schema_imageobject`. Distinction à ne jamais supprimer :

- `creditText` et `copyrightNotice` sur **toutes** les images créditées : ce sont
  des mentions d'attribution, elles n'affirment rien sur les droits ;
- `license` et `acquireLicensePage` **uniquement** sur nos propres images, celles
  créditées « Agenda Sabauda », vers la page crédits de la langue courante.
  Déclarer licenciable une affiche d'organisateur serait faux, et le badge
  Google deviendrait un mensonge affiché en notre nom.

### 144, la vignette de partage

**Piège évité de justesse.** La taille `cs_og_1200x630` alimentait réellement la
balise `og:image` sur 841 pièces jointes, mais elle n'était **déclarée nulle
part** : scan des 12 066 fichiers PHP de `wp-content`, le seul `add_image_size`
du site est celui de Complianz.

Conséquence : régénérer les métadonnées, par un plugin, par une retouche dans la
médiathèque ou **par WP-CLI**, la faisait disparaître en silence et cassait
l'aperçu de partage. Le problème n'était pas *où* l'on exécute, mais que
WordPress ignorait cette taille.

Elle est désormais fabriquée explicitement, **en JPEG forcé**. Toutes les
plateformes acceptent le WebP depuis que LinkedIn s'y est mis en décembre 2024,
mais JPEG et PNG restent les plus sûrs et l'aperçu de partage est la surface la
plus visible du site.

Deux détails : WordPress **n'agrandit jamais**, une source de 1 024 px donne une
vignette de 1024x630 ; et rien n'est fabriqué sous 600 px de large.

---

## 4. L'audit quotidien, et le trou qu'il comble

L'audit doctrine du snippet 130 ne regarde que posts, pages, fiches et
sélections. **Il ignore les pièces jointes.** C'est pour cela que du vocabulaire
proscrit a vécu dans des textes alternatifs sans que personne le voie :

- « Ce week-end — agenda **transfrontalier** de l'espace Sabaudo »
- « Questo weekend — agenda **transfrontaliera** delle **Alpi** »
- « Vale il viaggio — Savoia e **Nizza Marittima** », forme irrédentiste

Un texte alternatif est lu par les lecteurs d'écran et par les moteurs : c'est du
texte publié.

**Et la liste du snippet 130 est plus courte que le lexique.** Elle ignore
`versant`, `transalpin`, `côté français/italien`, `de part et d'autre`,
`franco-italien`, `haut-savoyard`, `Nizza Marittima`. Ce sont précisément ceux
qui étaient passés en production. Le snippet 145 utilise la liste **complète**.

Quatre contrôles : vocabulaire proscrit dans les alternatives ; tirets cadratins
dans les alternatives ; part des pièces jointes jamais utilisées ; part des
images au format WebP. Les deux derniers ne déclenchent aucune alerte : ce sont
des **mesures**, destinées à vérifier que les correctifs du pipeline produisent
leur effet.

Première passe, le 2026-08-18 : 3 490 alternatives lues, zéro vocabulaire
proscrit, zéro tiret hors exceptions. Le contrôle tourne chaque jour à 9 h.

### Les exceptions sont nécessaires, pas un contournement

Le vault interdit de rebaptiser un événement réel. « Matisse – Yves Saint
Laurent » et « Marisa Merz – La danza delle ore » portent un tiret parce que
c'est leur **nom officiel**. Elles vivent dans l'option `cs_audit_media_ignore`.

> Ajouter un titre officiel à cette liste est légitime. Y ajouter une formule de
> notre cru ne l'est pas.

---

## 5. Méthode de transport, à reprendre

Le passage de code par base64 recopié à la main **a échoué deux fois** : ajout de
remplissage `=` au milieu d'un morceau, puis trois blocs sur sept altérés.

La méthode fiable : écrire le contenu avec `novamira/write-file` dans un fichier
`.txt` sous `uploads`, le lire côté serveur, comparer l'empreinte à l'original,
valider la syntaxe avec `token_get_all(..., TOKEN_PARSE)`, insérer, supprimer le
fichier. Les PHP ne peuvent aller que dans le bac à sable ; les autres extensions
vont où l'on veut sous `ABSPATH`.

---

## 6. Les images d'en-tête des hubs (2026-08-18)

### La méthode était déjà là, mais pas écrite

Les 13 hubs qui ont une image la tiennent de **Wikimedia Commons**, sous licence
CC, **l'attribution étant portée par la légende du média** (`post_excerpt`) et
non par `as_image_credit` :

> `© Florian Pépellin / Wikimedia Commons (CC BY-SA 4.0)` (Chambéry)

C'est reproductible : l'API de Commons rend l'auteur et la licence exacts dans
`extmetadata`, ce qui évite d'attribuer de mémoire.

| État | Hubs |
|---|---|
| Image en place | 13 : les 4 territoires, Chambéry, Annecy, Turin, Nice, Aoste, Chamonix, Monferrato, Côte d'Azur, Chablais |
| `cs_hub_image_a_fournir` | 8 villes de Savoie créées le 2026-08-18 |
| Rien du tout | 8 provinces du Piémont |

### Trois images CC sans attribution

**Chamonix (2658), Monferrato (2659) et Villefranche-sur-Mer (2660) n'ont aucune
légende.** Sur du CC BY-SA, l'attribution n'est pas une politesse, c'est la
condition de la licence. À retrouver et à écrire.

### Aix-les-Bains, faite de bout en bout

Casino Grand-Cercle, le repère que le texte du hub cite lui-même. Attachement
7921, alt « Le Casino Grand-Cercle à Aix-les-Bains », légende
`© Morio60 / Wikimedia Commons (CC BY-SA 2.0)`, plus `as_image_credit` et
`as_image_source` vers la page Commons. Posée sur le hub français **et** italien.

### Trois pièges rencontrés, à connaître avant les suivantes

1. **`chr(224)` et `chr(169)` ne sont pas de l'UTF-8.** Ces octets isolés font
   rejeter la requête par la base, silencieusement du point de vue de
   `update_post_meta`. Écrire les vrais caractères, « à » et « © ». C'est
   exactement ce que dit la note de mémoire sur les accents, et je l'ai quand
   même fait.
2. **La conversion WebP touche l'original sur un ajout programmatique.** La
   documentation dit qu'elle ne touche que les sous-tailles : c'est vrai par la
   médiathèque, faux ici. `_wp_attached_file` passe en `.webp` tandis que
   `post_mime_type` reste `image/jpeg`. Corriger le type après coup.
3. **`wp_insert_attachment` a rendu 0 sans erreur.** `wp_insert_post` avec
   `post_type => attachment` puis `_wp_attached_file` à la main fonctionne.

### Reste à faire

Sept villes de Savoie, les trois attributions manquantes, puis les images des
villes à créer au Piémont, dans le comté de Nice et en Vallée d'Aoste.

### Les huit images d'en-tête posées le 2026-08-19

| Hub | Sujet | Auteur, licence |
|---|---|---|
| Annemasse | Hôtel de Ville | Yann, CC BY-SA 4.0 |
| Saint-Jean-de-Maurienne | Cathédrale Saint-Jean-Baptiste | Benjamin Smith, CC BY-SA 4.0 |
| Moûtiers | Cathédrale Saint-Pierre | MOSSOT, CC BY-SA 3.0 |
| Sallanches | Église de Sallanches | TarichaRivularis, CC BY-SA 3.0 |
| Cluses | Église Saint-Nicolas | Tournasol7, CC BY 4.0 |
| Albertville | Cité de Conflans et son clocher | Florian Pépellin, CC BY-SA 4.0 |
| Thonon-les-Bains | Port de Rives | Krzysztof Golik, CC BY-SA 4.0 |
| Chamonix | Statue de Balmat et Saussure | Fred Romero, CC BY 2.0 |

Chacune porte son alternative, sa légende de crédit, `as_image_credit` et
`as_image_source` vers la page Commons, et sert les deux langues du hub.

**21 hubs sur 29 ont désormais une image.** Restent les 8 provinces du Piémont.

### Le critère, corrigé par Franck

Ma première image d'Annemasse était une photo de concert prise dans la salle de
Château Rouge : sombre, une foule, des projecteurs. Elle ne disait rien
d'Annemasse.

> **Une photo de ville ou un monument historique reconnaissable.** Les treize
> images posées avant moi respectaient ce motif, château des ducs de Savoie,
> Palais de l'Isle, Piazza San Carlo, Arc d'Auguste, port de Villefranche. Je
> l'avais rompu.

Chamonix a été remplacée dans la foulée, sur la même remarque : la vue de vallée
disait la montagne, la statue de Balmat et Saussure dit Chamonix.

**Deux pièges de sélection automatique.** Une recherche sur un nom de ville
remonte volontiers des planches de guides anciens (Baedeker 1913) et des photos
de presse d'archives en format portrait. Filtrer sur le ratio, écarter les
titres contenant *map*, *handbook*, *plan*, et vérifier que le nom de la ville
est bien dans le titre du fichier.

**Le bandeau ne montre que les 180 premiers pixels** d'un rendu en 1024 de large,
avec `overflow:hidden`. Le sujet doit donc être dans le haut de l'image.

L'ancienne photo d'Annemasse (7940) reste en médiathèque, inutilisée : rien
n'est supprimé.
