# Les pages d'accueil — copies versionnées du `post_content`, PAS la référence

Même statut que `../code-snippets/` : ce dossier est le **miroir** du contenu qui vit dans la
base WordPress (`wp_posts.post_content`), pris à une date donnée. Il prouve qu'on peut relire
et restaurer ; il ne prouve ni que c'est en ligne, ni que c'est à jour (règle 1 de
`CLAUDE.md`). Avant toute écriture : lire ce qui est en ligne, comparer.

| Fichier | Page | md5 (date de relevé) |
|---|---|---|
| `page-928-accueil.html` | #928 · Accueil (FR) — sert aussi les vues territoire `/explore/<territoire>/` | `6a239ea8ca128c08172a26c199b58bf6` (2026-09-07) |
| `page-1717-accueil.html` | #1717 · Home (IT) `/it/home-it/` | `43de5b6e643a680b96357b9a9386ae1b` (2026-09-07) |

Ces pages sont des blocs Gutenberg : des `wp:html` (HTML brut, styles inline) et des
`wp:group` contenant des `wp:jet-engine/listing-grid` dont l'attribut `_element_id`
(`ala-une`, `weekend`, `jour`, `evidence`…) est la clé que lit l'allocateur (snippet #44).

## Deux mises en page dans un seul contenu

Le contenu porte DEUX homes : les blocs `.as-home` (mobile et tablette, masqués à partir de
900 px, colonne de 480 px centrée) et les blocs `.as-home-desktop` (masqués en dessous).
Une section « existe » donc deux fois dans le HTML sans jamais être visible deux fois — piège
documenté dans `../code-snippets/README.md` (cas #44, troisième correctif). Exception : le
groupe `.as-desktop-cols3` (À lire · En évidence · L'agenda à venir · sections catégorie),
enfant d'une enveloppe `.as-home-desktop`, est **forcé visible sur mobile** par le style
`cs-no-hide-empty-cols`, et l'enveloppe masque alors tous ses AUTRES enfants
(`.as-home-desktop:has(> .as-desktop-cols3) > *:not(.as-desktop-cols3)`). Et cette
enveloppe ne se referme qu'au DERNIER octet du contenu (son `</div>` final suit le bandeau
newsletter et la barre pub desktop) : tout ce qui suit les trois colonnes est dedans. Un
bloc mobile inséré « après les trois colonnes » ou « avant le bandeau newsletter » est donc
invisible sur mobile — c'est arrivé le 07/09, deux fois, mesuré par la pile des `<div>`
ouverts au point d'insertion sur la page rendue. Le seul emplacement possible est après ce
`</div>` final, en tout dernier bloc du contenu.

## Journal

**2026-09-06/07 — réordonnancement du mobile (Franck : « je donne mon accord » sur la
maquette « Ordre de la home mobile »).** Mesuré la veille en navigateur sur les 10 homepages
à 390 et 820 px : le mobile n'avait pas « Ce week-end » (mais gardait son bouton « Voir tous
les événements du week-end »), plaçait « Ça vaut le déplacement » AVANT « Les 7 prochains
jours », répétait la newsletter trois fois et les tuiles catégories deux fois. Fait, par
opérations d'ancre sur le `post_content` (essai à blanc d'abord, chaque ancre vérifiée
unique, révision WordPress + sauvegarde `novamira-sandbox/backups/page-<id>-content-*.txt`) :

- **« Ce week-end » ajouté sur mobile** après « À la une » : en-tête au même gabarit, grille
  clonée sur celle de « À la une » mobile (listing 1696, 2 colonnes, `posts_num` 6 — côté IT
  la grille porte `custom_query_id` 15 comme son modèle), `_element_id` `weekend` ;
- **« Ça vaut le déplacement »** (bloc `CVLD_MOBILE`) déplacé en dernier bloc du contenu,
  donc après les trois colonnes et les sections catégorie sur mobile (voir l'enveloppe
  ci-dessus) — le territoire choisi d'abord, les autres ensuite ;
- **retirés** : `TUILES SECONDAIRES` (doublon des tuiles du haut et de celles de la colonne
  « En évidence ») et `NEWSLETTER (bis)` (l'encart sous les tuiles reste : une seule newsletter
  sur mobile, comme le bandeau unique du desktop) ;
- « Suivez-nous », la recherche bis, « Faire de la publicité » et la barre pub sticky suivent
  « Ça vaut le déplacement » dans le nouveau bloc.

Le desktop n'est pas touché (mêmes grilles, mêmes ids rendus avant/après). « En évidence »
reste une section distincte : sa fusion avec « À la une » était « à discuter » sur la
maquette, pas décidée.

Vérifié après écriture, en navigateur à 390 et 820 px sur Savoie FR, « les 4 » FR et IT :
ordre À la une → Ce week-end (6 fiches, mêmes ids que la grille desktop) → Les 7 jours →
À lire → En évidence → L'agenda à venir → catégories → Ça vaut le déplacement → newsletter.
