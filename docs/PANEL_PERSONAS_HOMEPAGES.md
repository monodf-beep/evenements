# Panel de personas sur les pages d'entrée — cahier de passation

Destinataire : une session Claude Code disposant d'un accès direct au VPS.
Rédigé le 2026-08-03 depuis une session qui n'avait que `novamira/execute-php`,
sans SSH ni FTP. Tout ce qui suit a été vérifié en production ce jour-là, sauf
mention contraire explicite.

---

## 1. Ce qu'on construit, et pourquoi

Un dispositif qui fait relire les pages d'entrée d'agendasabauda.eu par le panel
de 8 personas lecteurs, et qui transforme leurs retours en corrections.

**L'erreur à ne pas commettre : un agent qui « regarde la page et donne son
avis ».** Il produit des phrases convaincantes et partiellement fausses. Cas
réel : Franck a signalé que la section « Les 7 prochains jours » ne contenait
« que du récurrent ». Mesure faite : 5 fiches sur 8 étaient bien des événements
d'un jour. Mais les deux premières places, les seules visibles sans défilement,
duraient 442 et 344 jours. **L'intuition était juste, le diagnostic trop large.**

D'où l'architecture en trois temps, dont aucun n'est optionnel.

### Étage 1 — Extraction (code, aucun avis)

Extrait les faits de la page rendue. Vérifiable, reproductible, sans modèle.

### Étage 2 — Panel (personas, sur les faits)

Deux rôles, et le second est le plus important :

1. **Détecter des incohérences que l'extracteur n'a aucune colonne pour voir.**
   « Une section intitulée *7 prochains jours* remplie de choses qui durent
   depuis un an » est une contradiction entre la **promesse** de la page et son
   **contenu**. Aucune métrique générique ne l'attrape.
2. **Prioriser.** Manuela, sans voiture, met l'accès avant tout. Chantal met la
   qualité de l'italien. Ce n'est pas la même file d'attente.

### Étage 3 — Vérification puis exécution

Tout constat de persona est **converti en assertion mesurable et mesuré** avant
d'entrer dans la file. Ni écarté, ni gobé. C'est le protocole qui a produit le
constat correct sur les 7 jours.

---

## 2. Règles non négociables

### 2.1 Un constat n'est clos que par une remesure

**Jamais sur la déclaration de l'agent.** Preuve du jour : le premier correctif
sur les 7 jours a bien changé quelque chose (l'ordre est devenu chronologique),
et un agent se serait déclaré vainqueur. La section ouvrait toujours sur 442
jours. Il a fallu trois tentatives et deux hypothèses fausses.

L'agent marque « intervenu ». La passe suivante de l'extracteur décide.

### 2.2 Les trois conditions de l'action autonome

Le critère n'est pas « suis-je sûr », qui est invérifiable. Il est structurel :

1. **Réversible** — sauvegarde dans `wp_options` avant toute écriture.
2. **Vérifiable par remesure** — la mesure déclenchante doit être relisible.
3. **Dans un motif connu** — écrire une méta, patcher un snippet avec ancre
   unique et contrôle de syntaxe.

Les trois réunies : agir. Une seule manquante : déposer dans la file et passer.

### 2.3 Rien d'irréversible en autonomie

Jamais de fusion, suppression définitive, publication, ni envoi.

**Preuve du jour.** La file disait « dédoublonner 7 lieux avant d'écrire les
adresses ». En regardant : `37 Théâtre des Collines` (Annecy) et `796 Le Point
Commun` (Cran-Gevrier) sont deux lieux différents ; `2022 Biblioteca Passerin
d'Entrèves` et `1137 Cascina Giaione` aussi. Et `603 ARTiglieria` et `2047
ARTiglieria` désignent le même lieu avec **deux adresses contradictoires**, donc
au moins une fausse. Un agent qui exécute la file fusionne et détruit.

Écrire une adresse est réversible. Fusionner ne l'est pas. **Faire d'abord ce
qui se défait.**

### 2.4 Ce qui n'est pas mesurable ne disparaît pas

« Ce ton ne s'adresse pas à des gens comme moi » ne se chiffre pas, et c'est le
drapeau rouge central de Kévin et de Manuela. Ces constats remontent à Franck
tels quels, marqués non vérifiés. Ne garder que le quantifiable viderait le
dispositif de son intérêt.

### 2.5 Un constat vérifié fabrique une colonne permanente

C'est ce qui empêche le système de plafonner sur les mêmes quatre défauts.
« Écart entre la fenêtre annoncée par le titre et la durée des fiches » doit
devenir une mesure appliquée aux dix pages à chaque passe.

---

## 3. Le périmètre : dix pages

Arbitré par Franck : les deux accueils et les quatre territoires, FR et IT.
**Ne pas y ajouter** les sous-territoires (Chablais, Monferrato, Côte d'Azur) ni
les 16 pages de province, bien qu'ils portent le même `cs_hub_type=territoire`.

| ID | Page | Langue | Territoire |
|---|---|---|---|
| 928 | Accueil | fr | — |
| 1717 | Home (IT) | it | — |
| 2857 | Savoie | fr | savoie |
| 2858 | Savoia | it | savoie |
| 2859 | Piémont | fr | piemont |
| 2860 | Piemonte | it | piemont |
| 2861 | Vallée d'Aoste | fr | vda |
| 2862 | Valle d'Aosta | it | vda |
| 2863 | Comté de Nice | fr | nice |
| 2864 | Contea di Nizza | it | nice |

---

## 4. Le panel

Fichiers : `docs/personas/*.md`, **branche `fix/langue-savoyarde`** (pas `main`).
Lire aussi `docs/personas/README.md`, qui porte la règle d'attribution.

Chaque persona a une `aire` alignée sur `territoire`, et certains une `visite:`
(corridor de déplacement plausible). **Cinq n'ont aucun corridor** : Kévin,
Rémy, Manuela, Jean-Pierre, Karine ne font pas de sorties lointaines. Les faire
juger un territoire qui n'est pas le leur produit du bruit.

| Page | Locaux (pilotent le verdict) | Visiteur (signal complémentaire) |
|---|---|---|
| Hub Savoie | Kévin, Camille | Chantal |
| Hub Vallée d'Aoste | Chantal, Rémy | Camille |
| Hub Piémont | Manuela, Piera | Camille, Chantal |
| Hub Comté de Nice | Jean-Pierre, Karine | Piera |
| Accueil FR et IT | tout le panel | — |

Sur l'accueil italien, **Chantal est centrale** : elle lit spontanément l'italien
et repère une traduction bâclée. C'est le seul persona qui puisse juger la
qualité du versant IT.

### Ce que le panel doit recevoir

Le tableau des fiches **et la promesse de la page** : H1, titres de section,
chapôs, FAQ. Sans les textes qui annoncent quelque chose au lecteur, un persona
ne peut pas repérer un écart entre l'annonce et le réel — c'est-à-dire sa
fonction principale.

### Discipline

Toute critique doit citer une ligne du tableau ou une phrase de la page. « La
page manque de fraîcheur » n'est pas recevable. « Les deux premières cartes
durent 442 et 344 jours » l'est.

---

## 5. Les quatre classes, attribuées mécaniquement

Le classement se déduit du **type de mesure** qui a déclenché le constat, jamais
d'un jugement d'agent — sinon tout finit en classe 1, la plus facile à traiter.

| Classe | Nature | Propriétaire | Autonome ? |
|---|---|---|---|
| 1 | Affichage, tri, filtre | snippet | oui |
| 2 | Donnée de fiche manquante | lot de métas | oui |
| 3 | Contenu ou traduction absent | pipeline | non |
| 4 | Arbitrage éditorial | Franck | non |

---

## 6. L'extracteur, code validé le 2026-08-03

Trois pièges réglés, à ne pas réintroduire.

**Piège 1 — les commentaires CSS.** Les feuilles de style de ce site contiennent
des libellés de section en clair. Une recherche de « Les 7 prochains jours »
dans le HTML brut tombe d'abord dans un commentaire CSS. **Retirer `<style>`,
`<script>` et les commentaires HTML avant toute analyse.**

**Piège 2 — le double rendu.** L'accueil rend les mêmes cartes deux fois : une
série mobile sans libellé, puis la série desktop libellée. Dédoublonner sur le
couple `(section, slug)`.

**Piège 3 — les `h3` sont des titres de cartes**, pas de sections. Marqueurs de
section : `h1`, `h2`, et `class="...section-title__label..."`.

```php
function cs_pj_extraire($url) {
    $x = wp_remote_get($url, ['timeout' => 40]);
    if (is_wp_error($x)) { return ['erreur' => $x->get_error_message(), 'cartes' => []]; }
    $h    = wp_remote_retrieve_body($x);
    $code = wp_remote_retrieve_response_code($x);

    // Piege 1 : indispensable, et avant tout le reste.
    $h = preg_replace('#<style[^>]*>.*?</style>#is', '', $h);
    $h = preg_replace('#<script[^>]*>.*?</script>#is', '', $h);
    $h = preg_replace('#<!--.*?-->#s', '', $h);

    $mk = [];
    if (preg_match_all('#<h([12])[^>]*>(.*?)</h\1>#is', $h, $m, PREG_OFFSET_CAPTURE)) {
        foreach ($m[2] as $t) {
            $mk[] = ['pos' => $t[1], 'label' => trim(preg_replace('/\s+/', ' ', wp_strip_all_tags($t[0])))];
        }
    }
    if (preg_match_all('#class="[^"]*section-title__label[^"]*"[^>]*>(.*?)<#is', $h, $m2, PREG_OFFSET_CAPTURE)) {
        foreach ($m2[1] as $t) {
            $mk[] = ['pos' => $t[1], 'label' => trim(wp_strip_all_tags($t[0]))];
        }
    }
    usort($mk, function ($a, $b) { return $a['pos'] - $b['pos']; });

    preg_match_all('#href="https://agendasabauda\.eu/(?:it/)?evenement/([a-z0-9\-]+)/"#i', $h, $me, PREG_OFFSET_CAPTURE);

    $cartes = []; $vus = [];
    foreach ($me[1] as $t) {
        $pos = $t[1]; $slug = $t[0]; $sec = '(hors section)';
        foreach ($mk as $k) { if ($k['pos'] < $pos) { $sec = $k['label']; } else { break; } }
        $cle = $sec . '|' . $slug;
        if (isset($vus[$cle])) { continue; }   // Piege 2
        $vus[$cle] = 1;
        $cartes[] = ['section' => $sec, 'slug' => $slug];
    }
    return ['code' => $code, 'cartes' => $cartes];
}

function cs_pj_faits($slug) {
    global $wpdb;
    $id = $wpdb->get_var($wpdb->prepare(
        "SELECT ID FROM {$wpdb->prefix}posts WHERE post_name = %s AND post_type = 'tribe_events' AND post_status = 'publish' LIMIT 1",
        $slug
    ));
    if (!$id) { return null; }
    $id = (int) $id;

    $sd  = get_post_meta($id, '_EventStartDate', true);
    $ed  = get_post_meta($id, '_EventEndDate', true);
    $now = current_time('timestamp');
    $ts  = strtotime($sd); $te = strtotime($ed);

    $vid   = (int) get_post_meta($id, '_EventVenueID', true);
    $adr   = $vid ? trim((string) get_post_meta($vid, '_VenueAddress', true)) : '';
    $ville = $vid ? trim((string) get_post_meta($vid, '_VenueCity', true)) : '';
    $terr  = wp_get_object_terms($id, 'territoire', ['fields' => 'names']);
    $gr    = get_post_meta($id, 'as_gratuit', true);

    return [
        'id'          => $id,
        'titre'       => html_entity_decode(get_the_title($id), ENT_QUOTES, 'UTF-8'),
        'debut'       => substr($sd, 0, 10),
        'fin'         => substr($ed, 0, 10),
        'duree_j'     => (int) round(($te - $ts) / 86400),
        'jours_avant' => (int) floor(($ts - $now) / 86400),
        'en_cours'    => ($ts <= $now && $te >= $now),
        'passe'       => ($te < $now),
        'ville'       => $ville,
        'adresse'     => ($adr !== ''),
        'territoire'  => $terr ? $terr[0] : '',
        'lang'        => pll_get_post_language($id),
        'gratuit'     => ($gr === '' ? 'inconnu' : ($gr == '1' ? 'oui' : 'non')),
        'mots'        => str_word_count(wp_strip_all_tags(get_post($id)->post_content)),
    ];
}
```

### Colonnes déduites des drapeaux rouges

Ne pas inventer de grille. **Les drapeaux rouges des personas EN SONT une**, et
ils sont mesurables. C'est ce qui empêche l'outil de dériver.

| Drapeau rouge | Mesure |
|---|---|
| « prix caché ou flou » (Rémy) | `as_gratuit` — **voir arbitrage §7** |
| « sans accès en transport » (Manuela, Karine) | `adresse` |
| « à 1h30 sans le dire » (Piera) | `ville`, `territoire` |
| « le tout-Turin qui ignore les vallées » (Piera, Rémy) | répartition des villes |
| « annoncé trop tard » (Camille) | `jours_avant` |
| « listing plat sans hiérarchie » (Camille) | ordre et `duree_j` |
| « traduction bâclée » (Chantal) | `lang`, cohérence des taxonomies |
| « longueur excessive » (Karine, Jean-Pierre) | `mots` |

---

## 7. Arbitrages déjà rendus par Franck

**Ne pas les rouvrir.**

- **Absence d'information de prix = neutre, jamais un défaut.** Le site ne
  publie qu'une seule information tarifaire, la gratuité. 44 fiches à « oui »,
  544 à « 0 » — et « 0 » signifie *on ne sait pas*, pas *payant*. Le panel ne
  doit pas compter ça contre le site.
- **Périmètre : les quatre territoires uniquement**, FR et IT.
- **Une section courte est un signal honnête de pénurie**, jamais à masquer par
  du remplissage. Principe posé en tête du snippet 44.

---

## 8. Contexte technique indispensable

- **Préfixe de tables : `wor4956_`.** Toujours passer par `$wpdb->prefix`.
- **`get_posts()` et `WP_Query` masquent silencieusement les `tribe_events`
  passés.** Écart constaté : 324 en SQL direct contre 224 par l'API. **Tout
  comptage ou audit passe par du SQL direct.**
- Le CSS du snippet 12 est stocké **encodé en base64**.
- Le snippet 77 **n'accepte aucune apostrophe dans ses commentaires** : elle
  casse silencieusement tout le bloc `<style>`.
- `position: sticky` est inopérant sur tout le site (`body` en
  `overflow: hidden auto`).
- Polylang : `pll_set_post_language`, `pll_save_post_translations` et
  `PLL()->model->post->save_translations` fonctionnent.
  **`pll_set_post_translations` n'existe pas.**
- The Events Calendar **réordonne les grilles par date de début** et annule tout
  `orderby => post__in`. Ne pas chercher à corriger un ordre : corriger la
  **sélection**.

### Motif récurrent : le tri qui enterre le ponctuel

**À chercher partout où une liste d'événements est rendue.** Trouvé deux fois le
2026-08-03, à deux endroits sans rapport, et il produit le même effet à chaque
fois : ce qui dure depuis longtemps écrase ce qui arrive.

Un tri par `_EventStartDate ASC` remonte en tête les événements **déjà
commencés** — une exposition ouverte depuis mars passe devant un festival qui
commence demain. C'est l'inverse du besoin : on rate un événement d'un jour,
jamais une expo ouverte jusqu'au 15 octobre.

| Endroit | État | Correctif |
|---|---|---|
| Accueil, section « 7 prochains jours » (snippet 44) | corrigé | borne basse sur `_EventStartDate` : la section n'admet plus que ce qui **démarre** dans la fenêtre |
| Recherche, 3 requêtes (snippet 23) | corrigé | réordonnancement après construction : à venir d'abord par date de début, déjà commencés ensuite par date de **fin** croissante |
| Hubs territoire (snippet 61) | **non atteint**, vérifié en direct | aucun |

Les deux correctifs diffèrent volontairement. Sur l'accueil, la section **promet**
une fenêtre de sept jours : ce qui n'y démarre pas n'y a pas sa place, on
filtre. Sur la recherche, l'utilisateur veut voir **tout** ce qui correspond à sa
requête : on ne retire rien, on réordonne.

Entre deux événements déjà commencés, trier par date de **fin** croissante : ce
qui ferme le plus tôt est la seule urgence qui leur reste.

**Sur les hubs, ne rien corriger sans mesurer d'abord.** L'hypothèse de départ
était qu'ils souffraient du même défaut — c'était faux. Le hub Savoie affiche 30
fiches d'affilée toutes à venir, et ses longues durées (« Les monologues du
machin », jusqu'en juin 2027) démarrent dans le futur, donc leur rang est
légitime. Le mécanisme exact qui produit cet ordre n'a pas été élucidé et diffère
de l'accueil : à documenter par qui aura l'accès au code.

### Protocole de déploiement d'un snippet

Éprouvé toute la journée, ne pas s'en écarter :

1. Sauvegarder le code actuel dans `wp_options`, clé `cs_bk_<cible>_<date>`.
2. Vérifier que l'ancre de remplacement apparaît **exactement une fois**.
3. Valider la syntaxe : `token_get_all('<?php ' . $code, TOKEN_PARSE)` sous
   `try/catch`.
4. Écrire.
5. **Vérifier en production** par `wp_remote_get`, jamais sur la seule
   confirmation d'écriture.

---

## 9. État au 2026-08-03, à la remise

Le premier passage de l'extracteur a produit ces quatre constats. Ils servent de
jeu de test : une implémentation correcte doit les retrouver.

**Classe 1 — traité ce jour.** Section « 7 prochains jours » : le filtre `next7`
ne bornait que la fin de fenêtre, donc tout événement en cours la traversait.
Corrigé par l'ajout d'une borne basse sur `_EventStartDate`. FR affiche
désormais 8 fiches du 3 au 10 août, IT en affiche 4 — pénurie réelle, assumée.
Sauvegardes `cs_bk_snippet44_20260803` et `...b`.

**Classe 1 — traité ce jour également.** Résultats de recherche : les 20 fiches
de `?s=festival` sortaient longue durée en tête. Réordonnées — 11 à venir
d'abord, puis 9 en cours par date de fin croissante. Aucune n'a été retirée.
Sauvegarde `cs_bk_snippet23_20260803_tri`. Voir le motif récurrent au §8.

**Classe 2 — partiellement traité.** 90 adresses écrites sur 247 lieux, tous
niveaux `sure`, `haute` et `moyenne`. Sauvegarde `cs_bk_adresses_lieux_20260803`.
Restent 48 lieux en `A VERIFIER` ou `faible` — **ne pas écrire sans
vérification**, une mauvaise adresse envoie quelqu'un au mauvais endroit — et
109 sans adresse trouvée. Source : `data/adresses-lieux-FUSION-2026-08-03.csv`
— **attention, `data/` est dans le `.gitignore`**, ce fichier n'est donc pas
versionné et vit uniquement sur le poste de Franck. Le réclamer avant de
reprendre ce chantier.

**Classe 3 — ouvert.** 142 fiches FR contre 59 IT en cours ou à venir, et **101
fiches FR sans aucune version italienne**. Conséquence mesurable : le hub Savoie
affiche 48 cartes en FR et 7 en IT ; le Comté de Nice, 29 contre 7. C'est le
constat le plus lourd du lot.

**Classe 1 + 4 — EN ATTENTE D'ARBITRAGE, ne pas corriger sans Franck.**
Section « Ça vaut le déplacement » de l'accueil. Trois défauts empilés :

1. `cs_home_deplacement_pick()` trie sur `as_score` (qualité éditoriale
   générale) et **ne lit jamais `as_deplacement`**, le score qui porte pourtant
   le nom de la section. La matière existe : 6 fiches à 8 et 10 fiches à 7.
2. **Le plan n'est pas appliqué à cette grille.** La fonction renvoie 2 fiches
   des territoires d'en face (FR → Piémont + Vallée d'Aoste ; IT → Savoie +
   Comté de Nice). La page en affiche 4, dont deux de territoires que la
   fonction **exclut explicitement**. La grille tourne donc sur sa requête par
   défaut. Conséquence visible : la fiche 330, titrée « au diapason » en
   minuscules et jamais rédigée, avec les scores les plus bas du lot (3 et 4),
   occupe la première place d'une vitrine.
3. La fiche 578 (Castello di Rivoli) porte des dates par défaut, 01/01 →
   31/12/2026. La carte affiche « 1 Jan », information sans valeur.

L'idée éditoriale de la section est juste — « ça vaut le déplacement » signifie
franchir la frontière, et c'est cohérent avec la ligne du site. Mais Franck a
déjà écarté ce même concept comme **filtre de recherche**, faute d'être
convaincu. Le sort de la section relève donc de lui, pas d'un agent.

**Contexte AdSense, pertinent pour la classe 3.** Le site est « En préparation »
chez AdSense. Le fichier `ads.txt` a été vérifié le 2026-08-03 et est
**correct** — servi en `text/plain` sur les quatre variantes d'URL, sans BOM,
identifiant conforme, `robots.txt` n'interdisant rien. L'état « Introuvable »
affiché par AdSense est figé depuis le 20 juillet et ne reflète plus la réalité.
**Ne pas perdre de temps dessus.**

Ce qui bloque réellement l'examen est ailleurs et recoupe le travail du panel :
143 fiches de moins de 150 mots et 169 pages de lieu sans événement à venir,
indexables. C'est exactement le contenu mince qu'un examen AdSense sanctionne,
et c'est aussi ce que Karine et Jean-Pierre signalent sous « longueur » et
« page qui ne m'apprend rien ».

**Classe 4 — arbitré.** Voir §7.

### Garde-fous déjà en place

- `mu-plugins/cs-garde-fou-langue.php` — cohérence de la **prose**.
- `mu-plugins/cs-garde-fou-structure.php` — **structure** : taxonomies en langue
  étrangère, doublons de collecte. Écrit ce jour.

Les deux sont en lecture seule et ne se recouvrent pas.

---

## 10. Ordre de montage recommandé

**Le panel d'abord, sur l'extracteur tel quel**, même incomplet. Sinon on grave
dans un mu-plugin un jeu de colonnes inventé par un développeur, et le panel
passera sa vie à commenter ses angles morts.

Ce que le panel trouve dicte les colonnes. Le mu-plugin d'extraction périodique
vient ensuite, une fois qu'on sait quoi y graver.

**La mesure doit vivre dans WordPress, pas dans l'agent.** C'est la seule
architecture où la règle de clôture du §2.1 est structurellement garantie
plutôt que promise : le site se mesure lui-même, et le chiffre du lendemain
tranche, quoi que l'agent ait cru accomplir.
