# Le gabarit des pages pilier « Que faire à X »

192 pages en ligne, trois fenêtres de temps par ville (aujourd'hui, ce week-end, cette
semaine) plus les pages de territoire, le tout en français et en italien. Ce document dit
**comment une de ces pages est construite**, **où le texte éditorial atterrit vraiment**,
et **ce qui a été mesuré** — pour qu'on n'ait plus à le redécouvrir.

Écrit le 2026-09-21, après que Franck a posé la bonne question : « la partie SEO article se
trouve en bas de page, est-ce que le lecteur va le voir ? ». La réponse tenait dans une
mesure, pas dans une opinion.

---

## 1. Ce que le visiteur voit, dans l'ordre

Mesuré sur `/que-faire-a-chambery/aujourdhui/`, en mots visibles depuis le début du `<main>` :

| position | bloc | d'où il vient |
|---|---|---|
| ~11 | **H1** | `cs_hub_h1`, sinon le titre de la page |
| ~32 | **chapeau** | le contenu AVANT `<!--more-->` |
| ~91 | filtres (date, ville, catégorie) + chips de fenêtre | snippet 61 |
| ~120 | **le listing** des événements de la ville | shortcode `[cs_hub_ville]` |
| ~263 | « Aux alentours » — seulement si la ville a **3 événements ou moins** | snippet 61 |
| ~499 | **« À propos de X »** : le contenu APRÈS `<!--more-->` | le reste du `post_content` |
| ~879 | pied de page | thème |

**Avant le correctif du 21/09**, il n'y avait pas de chapeau : le texte éditorial commençait
au **mot 559** d'une page de 1038. Un visiteur venu de Google ne lisait aucune phrase lui
confirmant qu'il était au bon endroit.

---

## 2. La règle d'écriture : couper au bon endroit

**Le `post_content` d'une page pilier s'écrit ainsi, et dans cet ordre :**

```html
<p>Que faire à X aujourd'hui : … (5W + expression clé, 2 à 4 phrases)</p>

<!--more-->

<h2>Que faire à X aujourd'hui, …</h2>
<p>…</p>
<h2>…</h2>
<p>…</p>
<h2>Demain et après-demain</h2>
<p>… liens vers les pages sœurs …</p>

<p>LIRE AUSSI : <a…>le guide de la ville</a> · <a…>le territoire</a></p>

[cs_hub_ville villes="X" territoire="…" quand="…"]
```

- **Le chapeau, c'est ce qui précède `<!--more-->`.** Deux à quatre phrases, pas plus.
- **Pourquoi pas tout le texte en haut.** Le visiteur qui cherche « que faire à X
  aujourd'hui » vient pour les événements. Mettre 400 mots devant la liste, c'est le schéma
  des blogs de recettes : ça enterre ce qu'il cherche et ça augmente le rebond. Le texte
  long a sa place SOUS la liste, où Google l'indexe très bien.
- **Une page sans `<!--more-->` se comporte exactement comme avant** : tout le texte passe
  sous le listing. Le correctif est rétro-compatible, aucune des 188 autres pages n'a bougé.
- **La position du shortcode dans le `post_content` n'a aucune importance** : le gabarit
  l'extrait par `preg_match` et le replace lui-même.

---

## 3. Ce que le snippet 61 fait, dans l'ordre

`CS · Hub ville (gabarit reutilisable)`, Code Snippets, **en base — aucun dépôt de fichier
ne l'atteint** (règle transposée de `docs/DEPLOIEMENT_WORDPRESS.md`).

1. `cs_hub_ville_takeover()` s'accroche à `template_redirect` et prend la main sur toute
   page portant la méta `cs_hub_ville`. Il appelle `get_header()`, écrit la page, `exit`.
2. Fil d'Ariane, H1 (`cs_hub_h1`), H2 optionnel (`cs_hub_h2`), image (`cs_hub_image`,
   **héritée du parent** si la page n'en a pas).
3. `post_content` : le shortcode est extrait, le reste devient `$cs_rest`.
4. **Si `$cs_rest` est vide, il est HÉRITÉ de la page parente.** C'est pour ça que les
   pages sans texte propre affichent quand même un « À propos » : celui du guide de la
   ville. Écrire la page guide couvre donc ses trois filles d'un coup.
5. `$cs_rest` est coupé sur `<!--more-->` : le chapeau est affiché, puis le listing.
6. `do_shortcode()` rend le listing : chips de fenêtre, formulaire de filtres, compteur,
   cartes groupées par jour, et un JSON-LD `ItemList` sur les pages week-end.
7. « Aux alentours » : **uniquement si le listing rend 3 événements ou moins**, et plafonné
   à **4 cartes** (c'était 6 jusqu'au 21/09 — avec 3 locaux, le voisinage dominait la page).
8. FAQ (`cs_hub_faq_build`) sur les pages guides, avec son JSON-LD `FAQPage`. Une FAQ
   rédigée dans la méta `cs_hub_faq` REMPLACE le socle, elle ne s'y ajoute pas.
9. Le bloc « À propos de X » avec `$cs_rest`.
10. « À lire » : jusqu'à 4 articles portant `cs_guide_territoire`.

### Les métas qui pilotent tout ça

| méta | portée | effet |
|---|---|---|
| `cs_hub_ville` | la page | déclenche le gabarit |
| `cs_hub_quand` | page fille | `aujourdhui` / `weekend` / `semaine` ; sert aussi au repérage des sœurs |
| `cs_hub_h1`, `cs_hub_h2` | la page | remplacent le titre |
| `cs_hub_image` | la page | vignette de tête, héritée du parent |
| `cs_hub_faq` | page guide | FAQ rédigée, une ligne « Question \| Réponse » |
| `cs_hub_territoire` | la page | alimente le bloc « À lire » |
| `cs_cle_auto` | la page | marque les pages à métadonnées générées (`seo-textes-pages.php`) |

Sur une page `quand="weekend"`, le titre et la méta description sont **réécrits à la volée**
par `wpseo_title` / `wpseo_metadesc` avec les dates du week-end courant. Ne pas s'étonner
que le titre en base ne corresponde pas à celui qui s'affiche.

---

## 4. Les trois formes de shortcode réellement en ligne

Relevé sur les 192 pages le 2026-09-19. Un script qui n'en traite qu'une se trompe sur 108.

```
[cs_hub_ville villes="Chambéry" territoire="savoie" quand="weekend"]          84 pages
[cs_hub_ville villes="Aoste,Aosta" territoire="vda" quand="weekend"]          36 pages
[cs_hub_ville territoire="vda" ville_label="Vallée d'Aoste" prep_fr="en"
              prep_it="in" quand="weekend"]                                   72 pages
```

- `villes` peut être une **liste** : la même ville écrite des deux côtés. Interroger la base
  sur « Aoste,Aosta » ne rend aucune ligne.
- Les pages de **territoire** n'ont pas d'attribut `villes` du tout. Se replier sur
  `territoire="vda"` revient à chercher des fiches dont la VILLE vaut « vda ».
- Le **libellé change de langue** (« Savoie » / « Savoia ») mais pas la cible : regrouper
  les jumelles sur le libellé les sépare.

`scripts/textes_hubs.cible()` lit ces trois formes, et `tests/test_textes_hubs.py` les
éprouve avec les shortcodes copiés tels quels depuis la production.

---

## 5. Ce qui a été MESURÉ sur le SEO

Tout ce qui suit vient du moteur de Yoast (`scripts/yoast_score.js`), pas d'une estimation.

| levier | effet | portée |
|---|---|---|
| écrire un texte (de rien à ~400-480 mots) | **+25 à +27** | les 192 pages |
| ajouter une vignette à la une | **+7** (81 → 88 sur le témoin) | les 192 pages |
| ancres internes courtes sur une page « aujourd'hui » | **+4** | les 64 pages « aujourd'hui » |
| mettre la clé dans un second H2 | **0** (essayé, score inchangé) | — |

**Les ancres.** Sur une page « aujourd'hui », une ancre interne qui reprend le titre d'une
page sœur (« Que faire à Chambéry ce week-end ») fait tomber `textCompetingLinks` de 8 à 2.
Une ancre courte (« ce week-end ») le remet à 8. La page « ce week-end », elle, ne gagne
rien : elle était déjà à 8. Hypothèse **non isolée** : Yoast traiterait « aujourd'hui »
comme un mot fonction, ne laissant que {faire, Chambéry} — que les deux ancres sœurs
contiennent en entier. Le fait est mesuré, l'explication ne l'est pas.

**Une limite du score, à ne pas oublier.** Yoast analyse le `post_content`. Google lit la
page RENDUE, où le texte long commence au mot 499. Le score décrit le texte, pas la page.

**Ce qui reste rouge et ne se répare pas au clavier** : `images` et `imageKeyphrase` tant
qu'il n'y a pas de vignette ; `subheadingsKeyword` parce que la clé n'est que dans un H2
sur quatre, et que l'y remettre ailleurs ne rapporte rien.

---

## 6. Écrire une page : la procédure

1. **Charger la doctrine** — elle n'est jamais en mémoire. `utils.voix.load_voix()` et
   `utils.vocabulaire.consigne_prompt()`, plus `docs/CHARTE_EDITORIALE.md`. Voir la règle
   dans `CLAUDE.md` et le skill `.claude/skills/redaction-agenda-sabauda/`.
2. **Rassembler des faits SOURCÉS.** Chaque nom propre, date et chiffre doit venir de notre
   base ou d'une page qu'on a ouverte et dont on garde l'adresse. Les sites d'office de
   tourisme changent d'arborescence : trois de mes quatre sources l'avaient fait en un jour.
3. **Écrire** sur le moule de `config/modele_hub_chambery.json` (deux gabarits validés :
   `weekend` et `aujourdhui`, FR et IT).
4. **Contrôler** : `python -m scripts.textes_hubs --essai-controles fichier.html --langue fr
   --cle "…"`. Le contrôle appelle chaque adresse citée et refuse un 404.
5. **Noter** avec `scripts/yoast_score.js`.
6. **Publier**, puis recompter sur le site — jamais sur la foi d'une liste.

**Les trois pages d'une même ville ne doivent pas se ressembler.** Trois quasi-doublons se
cannibaliseraient, exactement ce qui a coûté les redirections Vicoforte du 15/09. Chacune a
sa matière : le week-end parle du patrimoine et de la table, « aujourd'hui » de la marche en
ville et d'une curiosité, « cette semaine » reste à écrire.

---

## 7. Le déploiement du 2026-09-21, et comment revenir en arrière

Snippet 61, modifié en base par `novamira/execute-php` :

- md5 **avant** : `c40f27e52f7e2fb1a73cdbbb5edee6b9` (32 638 octets)
- md5 **après** : `c9d9c84a0e1bd03fed7dec24d24cc192` (34 067 octets)
- sauvegarde : option WordPress **`cs_snippet61_sauvegarde_20260921`**, qui contient le code
  d'avant, à l'octet près.

Trois changements : le listing descend après le chapeau ; la coupure sur `<!--more-->` ;
« Aux alentours » passe de 6 à 4 cartes.

La procédure suivie, à reprendre telle quelle : contrôle de dérive (le md5 lu doit être
celui qu'on a analysé), vérification que **chaque cible existe exactement une fois**,
sauvegarde, `token_get_all('<?php ' . $code, TOKEN_PARSE)` dans un `try` — une exception et
on n'écrit rien —, écriture, relecture, comparaison, puis contrôle de syntaxe du code
STOCKÉ. Ensuite seulement : charger le site et l'API REST pour vérifier qu'ils répondent.

**Revenir en arrière**, si besoin :

```php
global $wpdb;
$old = get_option('cs_snippet61_sauvegarde_20260921');
if ($old) { $wpdb->update($wpdb->prefix . 'snippets', array('code' => $old), array('id' => 61)); }
```

> ⚠️ **Dette assumée, à ne pas oublier.** Le snippet 61 n'est **toujours pas** dans
> `deploy/wordpress/code-snippets/` à l'octet près : seul le correctif du 21/09 est
> documenté ici. C'est exactement le défaut que `CLAUDE.md` décrit pour
> `cs-source-garde.php`. Le rapatrier reste à faire, et tant que ce n'est pas fait, la
> sauvegarde en option WordPress est le seul filet.
