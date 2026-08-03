# Chantier contenu cassé — événements FR/IT et résidus RSS (trouvé le 2026-07-29)

Document autonome pour reprise dans une autre session. Contexte : agendasabauda.eu, WordPress
(The Events Calendar, CPT `tribe_events`), édité en live via l'outil MCP **Novamira**
(`mcp__64e8930a-bae6-4567-865a-4432c4cf7967__mcp-adapter-execute-ability`, ability
`novamira/execute-php`) qui exécute du PHP directement sur le WordPress de production. Pas d'accès
SSH au VPS : tout passe par ce tool.

## Règles impératives (déjà établies, à appliquer sans exception)

- **Jamais de tiret cadratin** « — » dans aucun contenu écrit ou publié.
- **Préfixe DB** = `wor4956_`, jamais `wp_` en dur : toujours `$wpdb->prefix`.
- **Vocabulaire interdit** : "espace alpin" → dire "espace sabaudo" (FR) / "spazio sabaudo" (IT) ;
  "frontière"/"frontiera", "transfrontalier"/"transfrontaliero" → à éviter complètement, surtout
  dans les titres ; "francoprovençal"/"arpitan"/"patois" → dire "savoyard" (FR) / "savoiardo" (IT).
- **Anti-hallucination stricte** : vérifier chaque fait (prix, dates, lieux, artistes) par
  recherche web sur des sources fiables (site officiel de l'organisateur/du lieu) avant de
  publier. Ne jamais inventer un chiffre.
- **Règle sources** (posée le 2026-07-29, voir `docs/CHANTIERS_A_FROID_2026-07-29.md` et mémoire
  `agendasabauda-sources-organisateurs`) : un lien "Source" en bas d'article ne peut désigner
  QUE un organisme public ou l'organisateur réel de l'événement. Jamais un site tiers/guide, jamais
  un email personnel en "organisateur".
- **Validation avant écriture DB** : sauvegarder l'ancien contenu via
  `update_option('cs_bk_<description>_'.$id, $ancien_contenu, false)` avant tout `wp_update_post`,
  puis vérifier en live (`wp_remote_get` avec `?nc=`+random pour casser le cache) que la page
  répond 200 et affiche le bon contenu après modification.
- **Polylang** : `pll_get_post_language()` / `pll_get_post_translations()` fonctionnent dans le
  contexte Novamira, mais **`pll_set_post_translations()` N'EST PAS disponible**. Pour lier deux
  posts en traduction, utiliser `PLL()->model->post->save_translations($id, ['fr'=>$idFr,'it'=>$idIt])`.
- Le snippet Polylang source unique est l'**id 33** dans `{$wpdb->prefix}snippets` : ne jamais y
  toucher, ne jamais redéployer le mu-plugin `cs-polylang.php` (supprimé).

## Méthode qui a marché aujourd'hui (2 cas déjà corrigés en exemple)

Deux fiches ont déjà été traitées avec cette méthode, à reproduire :

1. **id 758 / 2215** (« C2C Festival Torino ») : le post IT (758) avait le bon slug italien mais
   le contenu était resté en français. Fix : recherche web (WebSearch/WebFetch) sur les sources
   officielles (site du festival, du lieu) pour compléter les faits manquants, rédaction d'une
   vraie traduction/adaptation italienne (pas mot à mot), `wp_update_post` sur le contenu +titre.
2. **id 702** (« Yerai Cortés at the Fondation Maeght ») : contenu = résidu brut de scraping RSS
   (`"The post [titre] appeared first on [site]"`). Fix : recherche web sur le site officiel
   (fondation-maeght.com), rédaction d'un vrai article court en français (intro factuelle, section
   "Infos pratiques", section "Sources" avec le site officiel de l'organisateur), `wp_update_post`.

Ces deux fiches sont **déjà corrigées**, ne pas les refaire.

## Requêtes SQL pour re-générer les deux listes (au cas où l'état a changé)

```php
// Bug 1 : événements tagués IT dont le contenu est resté en FR
global $wpdb;
$rows=$wpdb->get_results("SELECT p.ID,p.post_title,p.post_content FROM {$wpdb->prefix}posts p WHERE p.post_type='tribe_events' AND p.post_status='publish'");
$fr_markers=array(' le ',' les ',' des ',' avec ',' être ',' été ',' était ',' où ',' cette ',' ville ',' entre ',' pour ',' dans le ');
$it_markers=array(' il ',' gli ',' con ',' per ',' città ',' tra ',' che ',' però ',' dove ',' questo ',' della ',' dello ',' anche ');
foreach($rows as $r){
  $lang=pll_get_post_language($r->ID);
  if($lang!=='it') continue;
  $txt=' '.mb_strtolower(strip_tags($r->post_content)).' ';
  $fr_score=0;foreach($fr_markers as $m){$fr_score+=substr_count($txt,$m);}
  $it_score=0;foreach($it_markers as $m){$it_score+=substr_count($txt,$m);}
  if($fr_score>$it_score && $fr_score>=4){ /* suspect */ }
}

// Bug 2 : contenu = résidu RSS ou vide
$rows=$wpdb->get_results("SELECT p.ID,p.post_title,p.post_content,p.post_status FROM {$wpdb->prefix}posts p WHERE p.post_type='tribe_events' AND (p.post_content LIKE '%appeared first on%' OR LENGTH(p.post_content) < 150)");
// filtrer post_status='publish' pour la liste actionnable
```

---

## BUG 1 — 34 fiches publiées taguées IT avec du contenu resté en FRANÇAIS

Titre ET contenu sont en français alors que Polylang dit `lang=it`. Le slug, lui, est parfois déjà
en italien (comme pour le cas C2C déjà corrigé) — vérifier au cas par cas avec
`get_post_field('post_name', $id)`. Pour chaque id : rédiger une vraie adaptation italienne du
contenu français existant (pas une nouvelle recherche from scratch, le fond factuel FR est
généralement bon), en respectant les règles ci-dessus, puis `wp_update_post` sur titre+contenu.

**Vérifier avant de traiter chaque fiche** : est-ce un doublon avec la vraie fiche FR (via
`pll_get_post_translations`) ou une fiche isolée sans FR liée ? Si liée à une fiche FR existante,
utiliser cette dernière comme base de traduction (comme pour le cas C2C : fiche FR=2215, IT=758).

| ID | Titre (encore en FR) | Slug |
|---|---|---|
| 663 | Trois générations du rap romain réunies en Piémont : Noyz Narcos, Rancore, Danno & DJ Craim au Flowers Festival | trois-generations-du-rap-romain-reunies-en-piemont-noyz-narcos-rancore-danno-dj-craim-au-flowers-festival |
| 1158 | Aoste, l'artisanat comme mémoire vivante : la Foire d'Été 2026 | aosta-lartigianato-come-memoria-viva-la-fiera-destate-2026 |
| 694 | Stefano Mancuso au Forte di Bard : ce que les plantes savent faire sans cerveau | stefano-mancuso-au-forte-di-bard-ce-que-les-plantes-savent-faire-sans-cerveau |
| 715 | Palio Montis Regalis : les quartiers de Mondovì s'affrontent au parc Europa | palio-montis-regalis-la-tenzone-piu-folle |
| 779 | À Turin, la musique s'installe durablement parmi les rois d'Égypte | a-turin-la-musique-sinstalle-durablement-parmi-les-rois-degypte |
| 1202 | Fénis : une fête médiévale biennale ravive la mémoire des Challant | fenis-una-festa-medievale-biennale-rievoca-la-memoria-degli-challant |
| 1931 | Terra Madre Salone del Gusto quitte le Lingotto pour investir le centre historique de Turin | terra-madre-salone-del-gusto-lascia-il-lingotto-per-il-centro-storico-di-torino |
| 1938 | Aosta ressuscite ses pierres levées : le parc archéologique sort de terre en novembre 2026 | apre-il-nuovo-parco-archeologico-di-aosta |
| 1888 | Niccolò Fabi en concert à Aosta Classica, au Forte di Bard | niccolo-fabi-au-forte-di-bard-un-rendez-vous-romain-pour-aosta-classica-2026 |
| 1890 | Paolo Crepet joue Riprendersi l'anima au Forte di Bard | paolo-crepet-au-forte-di-bard-un-monologue-sur-la-perte-de-soi-a-lere-numerique |
| 1892 | Raf en concert au Forte di Bard pour Aosta Classica | raf-au-forte-di-bard-la-chanson-dauteur-italienne-face-a-la-memoire-dune-forteresse-alpine |
| 1894 | Aldo Cazzullo raconte saint François au Forte di Bard | au-forte-di-bard-aldo-cazzullo-raconte-les-huit-siecles-de-saint-francois |
| 1899 | Super Nature : au Forte di Bard, le monde filmé en Super 8 par 25 pays | super-nature-au-forte-di-bard-le-monde-filme-en-super-8-par-25-pays |
| 1905 | À Turin, la tranvia à crémaillère de Superga prolonge ses soirées jusqu'à fin septembre 2026 | a-torino-la-tranvia-a-cremagliera-di-superga-prolunga-le-serate-fino-a-fine-settembre-2026 |
| 1914 | Grupo Compay Segundo, l'héritage vivant du Buena Vista Social Club au Forte di Bard | au-forte-di-bard-le-grupo-compay-segundo-perpetue-lheritage-du-buena-vista-social-club |
| 1922 | John Ford au Cinema Massimo de Turin : l'Amérique en dix films | john-ford-au-cinema-massimo-de-turin-lamerique-en-dix-films |
| 902 | À Turin, deux soirées pour rejouer la mémoire musicale populaire des années 1980 à 2000 | la-notte-delle-hit-a-torino-nuovi-ospiti-e-sconto-speciale-per-levento-con-clerici-e-clementino |
| 1207 | Angelo Branduardi chante saint François au Forte di Bard, huit siècles après sa mort | angelo-branduardi-chante-saint-francois-au-forte-di-bard-huit-siecles-apres-sa-mort |
| 729 | Voci riapparse: compositrici oltre il silenzio — MITO per la Città 2026 | voci-riapparse-compositrici-oltre-il-silenzio-mito-per-la-citta-2026 |
| 739 | Quand la Cavallerizza Reale de Turin accueille le design graphique | quando-la-cavallerizza-reale-di-torino-ospita-il-design-grafico |
| 792 | George Clooney à Cuneo : quand le cinéma parle de droits aux jeunes du Piémont | dialoghi-sul-talento-con-george-clooney |
| 725 | La fiera du Santuario di Vicoforte, rendez-vous du 7 septembre | la-grande-fiera-del-santuario-di-vicoforte |
| 280 | Au Parco del Valentino, le cinéma italien projeté gratuitement sous les étoiles | au-parco-del-valentino-le-cinema-italien-projete-gratuitement-sous-les-etoiles |
| 578 | Au Castello di Rivoli, trois générations de regards sur l'art italien | al-castello-di-rivoli-larte-povera-si-riappropria-delle-sue-sale |
| 593 | Sotto i portici del Risorgimento : le musée turinois sort dehors pour les enfants | a-torino-il-museo-del-risorgimento-riapre-il-suo-programma-estivo-per-le-famiglie |
| 606 | La Buona Aria. Respirer l'histoire dans les appartements du Castello di Rivoli | al-castello-di-rivoli-leggere-le-ambizioni-incompiute-della-residenza-sabauda |
| 608 | Au Forte di Bard, l'été des enfants explorateurs entre jeu et patrimoine alpin | au-forte-di-bard-lete-des-enfants-explorateurs-entre-jeu-et-patrimoine-alpin |
| 718 | À Turin, la musique entre en dialogue avec les arts décoratifs | a-torino-la-musica-dialoga-con-le-arti-decorative |
| 782 | À Turin, la Sala del Senato interroge la mémoire d'une capitale éphémère | a-torino-la-sala-del-senato-interroga-la-memoria-di-una-capitale-effimera |
| 786 | TJF Piemonte 2026 : la huitième édition de la danse qui monte des Alpes | piemonte-il-festival-tjf-apre-unottava-edizione-distribuita-su-unintera-stagione |
| 788 | À Turin, une exposition relie l'archéologie de Gaza et l'art contemporain | a-torino-una-mostra-unisce-larcheologia-di-gaza-e-larte-contemporanea |
| 2205 | Marisa Merz – La danza delle ore : trois musées turinois célèbrent le centenaire d'une pionnière | marisa-merz-la-danza-delle-ore-2 |
| 2277 | AM Club \| In gioco: visita guidata con il curatore | am-club-in-gioco-visita-guidata-con-il-curatore |
| 3964 | 14 luglio 2026 a Nizza: dieci anni dopo l'attentato, una memoria che prende forma | 14-luglio-2026-a-nizza-dieci-anni-dopo-lattentato-una-memoria-che-prende-forma |

⚠️ **id 3964** traite de l'attentat de Nice (14 juillet) : sujet sensible, à rédiger avec
prudence éditoriale particulière (registre factuel et sobre, pas de sensationnalisme), pas
seulement un problème de langue.

---

## BUG 2 — ~52 fiches publiées avec contenu vide ou résidu RSS brut

Deux sous-types :
- **Résidu RSS** : contenu = `"The post [titre] appeared first on [site]"` (EN) ou
  `"L'article [titre] est apparu en premier sur [site]"` (FR) ou l'équivalent italien — un
  fragment technique généré par WordPress en fin de flux RSS, pas un article. Parfois précédé
  d'un fragment (ex. "Billetterie Weezevent").
  Certains contenus sont carrément une **manchette de presse copiée-collée** au lieu d'un
  résumé d'événement (ex. id 2188, 2192, 2201, 2209 : titres/contenus qui sont des titres
  d'articles de presse, pas des descriptions d'événement).
- **Contenu vide** (`longueur: 0`) : titre seul, aucun corps d'article.

Méthode : pour chaque id, identifier l'événement réel derrière le titre (recherche web sur le nom
propre + lieu + "2026"), vérifier les faits sur une source officielle (organisateur/lieu/mairie),
rédiger un vrai article court (2-4 paragraphes) respectant toutes les règles ci-dessus, avec une
section "Sources" ne citant que des organismes publics/organisateurs réels.

⚠️ **PRIORITÉ id 2188** : titre = manchette de presse sur l'anniversaire de l'attentat de Nice du
14 juillet, en italien, mal formatée comme événement (`"10 anni dell'attentato del 14 luglio a
Nice: visita di Emmanuel Macron, spettacolo di droni... Ecco il programma - Actu.fr"`). Sujet
sensible + attribution de source à traiter avec le plus grand soin (vérifier s'il s'agit d'une
cérémonie commémorative légitime à couvrir, et si oui la traiter sobrement, factuellement, sans
le style putaclic de la manchette copiée).

| ID | Titre actuel | Longueur contenu | Type de défaut |
|---|---|---|---|
| 835 | Grand Bal du 13 juillet | 101 | résidu RSS FR |
| 673 | Ciné plein air | 65 | résidu RSS EN |
| 681 | Festival Lyrique Aix les Bains | 115 | manchette presse (Nikita/Anglade) |
| 877 | Comédie Théâtrale : « Patience mon amour ! » | 127 | résidu RSS FR |
| 686 | Festival « les Éphémères alpines » | 0 | vide |
| 2036 | Lunedì 26 gennaio Guido Saracco presenta il suo nuovo libro al Teatro Alfieri | 0 | vide |
| 330 | au diapason | 138 | résidu RSS FR |
| 1928 | Festival SilverEco 2026 | 81 | à vérifier (court mais peut-être ok) |
| 1984 | EVO 2026 | 66 | à vérifier (court mais peut-être ok) |
| 1910 | Les feux de 1792 – Reconstitution historique | 0 | vide |
| 1917 | Chambéry. Sites insolites à bicyclette : le Vélotour... | 138 | à vérifier (court, titre presse) |
| 898 | COREOGRAFIE del POSSIBILE | 91 | résidu RSS IT |
| 917 | Face à face – Orlando | 104 | à vérifier |
| 921 | 60 minutes de violoncelle | 91 | à vérifier |
| 1209 | Gala des Excellences – Offert à tous – Entrée Gratuite | 138 | résidu RSS FR |
| 1212 | XII Monterosa Classica, quindici concerti gratuiti tra luglio e agosto | 133 | à vérifier |
| 736 | Charlie Winston | 46 | résidu ultra-court |
| 752 | CHANT SONG | 141 | résidu RSS FR |
| 754 | James carter | 140 | résidu RSS FR (+ doublon à vérifier) |
| 698 | Marion Rampal (quintette) | 78 | résidu RSS EN |
| 712 | Tournoi National Tennis Fauteuil | 0 | vide |
| 585 | VISITE A TEMA E INCONTRI | 62 | trop court |
| 590 | Festival des Jardins Alpestres | 0 | vide |
| 595 | MERCOLEDÌ D'ARTISTA | 46 | trop court |
| 601 | TORINO RINASCIMENTALE | 37 | trop court |
| 619 | L'été au centre socioculturel | 0 | vide |
| 653 | Concert de la Funky Académie | 137 | à vérifier |
| 795 | Visite au Château de Montrottier | 109 | résidu RSS EN |
| 809 | Programme du Cinéma en plein air du 4 au 22 juillet | 130 | résidu RSS FR |
| 1147 | Afterwork LifeSciences | 109 | à vérifier |
| 1856 | Jazz Art | 128 | à vérifier |
| 2188 | 10 anni dell'attentato del 14 luglio a Nice... | 132 | ⚠️ manchette presse, sujet sensible |
| 2192 | Chambéry. Circo, danza, teatro... | 112 | manchette presse |
| 2201 | Nice Jazz Fest | 126 | manchette presse |
| 2209 | Vinci i tuoi biglietti per Musilac ascoltando ICI Pays de Savoie | 71 | manchette presse |
| 2213 | Arte Povera et nouveaux aménagements dans la collection permanente | 122 | résidu RSS FR |
| 2267 | TJF PIEMONTE 2026 : lancement de la huitième édition | 119 | résidu RSS FR |
| 2273 | CAPAREZZA | 52 | trop court |
| 2275 | NOTE D'ARTE | 116 | à vérifier |
| 2311 | Visita al Castello di Montrottier | 131 | résidu RSS IT |
| 2331 | Vanessa Wagner (piano) | 89 | résidu RSS FR |
| 2350 | 60 minuti di violoncello | 95 | à vérifier |
| 2358 | Marion Rampal (quintetto) | 100 | résidu RSS IT |
| 2362 | Jazz Art | 125 | à vérifier |
| 3769 | Fénis: un été à vivre | 118 | contenu = template non rempli `[DATE]...[contenu factuel...]` |
| 3787 | MusiCogne, neuvième édition à partir du 15 juillet | 97 | à vérifier |
| 3815 | Ernia | 52 | trop court |
| 3819 | Gemitaiz | 59 | trop court |
| 3823 | Teenage Dream | 39 | trop court |
| 3969 | Les Chiens | 70 | trop court |
| 4117 | Cinema all'aperto | 94 | résidu RSS IT |

**id 702 (Yerai Cortés) déjà corrigé aujourd'hui, à exclure de cette liste.**

⚠️ **id 3769** est un cas particulier : le contenu contient littéralement un template non rempli
(`"Du [DATE] au [DATE], la Vallée d'Aoste propose... [contenu factuel, sans superlatifs, sans dark
patterns]"`) — probablement un prompt de génération resté en clair au lieu du texte généré. À
corriger en priorité, c'est visible tel quel sur la page publique.

## Bilan du batch multi-agents (nuit du 2026-07-29 au 30)

Exécuté : 85 fiches traitées (34 bug 1 + 51 bug 2). Résultat : 31/34 traduites (bug 1), 27/51
réécrites + 9/51 corbeillées (bug 2). Détail complet dans le journal du workflow
(`wf_ed4e4401-195`). Points notables :

- **Beaucoup de "échecs" bug 2 étaient en fait des faux positifs** : la liste avait été établie
  avant une exécution antérieure qui avait déjà corrigé une partie des fiches. Les agents ont
  vérifié chaque fiche avant d'écrire et n'ont rien cassé quand ce n'était pas nécessaire.
- **id 715/2285 (Palio Montis Regalis)** : corrigé cette nuit — mauvais organisateur (Franco
  Degrandis → en réalité Leonardo Degrandis depuis 2024) et mauvais lieu (parc Europa → CRB)
  dans le contenu d'origine. Dates 2026 non confirmées, volontairement laissées vagues plutôt
  que d'inventer.
- **id 1938/3713 (Aoste, aire mégalithique)** : corrigé cette nuit — le texte présentait une
  réouverture (en réalité survenue le 11 novembre **2023**, pas 2026) comme si elle allait avoir
  lieu en 2026. Reformulé en fête patronale annuelle du quartier Saint-Martin-de-Corléans
  (46e édition en 2024, événement solide et récurrent), sans fausse précision de date 2026.
- **id 786** : doublon non lié de l'événement déjà correctement traité sous l'id 2267 (TJF
  Piemonte). Mis en corbeille plutôt que réécrit une 3e fois.

## NOUVEAU chantier découvert : étiquettes de langue Polylang erronées

6 fiches ont un contenu français déjà correct et bien sourcé, mais une étiquette de langue
Polylang à `it` (donc une URL `/it/...`) au lieu de `fr`. Ce n'est PAS le bug 1 (le contenu n'est
pas à traduire, il est déjà bon) : c'est une erreur de taxonomie Polylang pure.

| ID | Titre | URL actuelle |
|---|---|---|
| 585 | La maïolique de la Renaissance... Museo Accorsi-Ometto | `/it/evenement/...` |
| 595 | Mercoledì d'Artista : atelier dessin Sodoma | `/it/evenement/mercoledi-dartista/` |
| 601 | Turin renaissance : visite guidée Sodoma | `/it/evenement/torino-rinascimentale/` |
| 2350 | 60 minutes de violoncelle, Opéra Nice | `/it/evenement/60-minuti-di-violoncello/` |
| 2362 | Jazz Art Lympia | `/it/evenement/jazz-art-2/` |
| 4117 | Cinéma en plein air, MJC Annemasse | `/it/evenement/...` |

**Pourquoi non corrigé cette nuit** : changer la langue Polylang change la structure d'URL
(`/it/...` disparaît), ce qui peut casser des liens déjà partagés/indexés par Google. Décision à
prendre les yeux ouverts : (a) juste recatégoriser en `fr` et accepter le changement d'URL
(avec ou sans redirection 301 de l'ancienne URL `/it/...`), ou (b) écrire une vraie traduction
italienne pour que la case `/it/...` soit légitimement occupée, et créer un nouveau post `fr` à
côté. Aucune écriture faite sur ces 6 fiches, juste identifiées et documentées ici. Requête pour
les retrouver si l'état a changé : voir section "Requêtes SQL" plus haut (même heuristique
FR/IT), 6 restants sur ce scan au 2026-07-30 vers 1h30.

## Recommandation de méthode pour la reprise

Vu le volume (34 + ~52 = ~86 fiches), ne pas tout traiter d'un coup à l'aveugle. Suggestion :
1. Trier avec l'agent de la nouvelle session : quels titres correspondent à un vrai événement
   récurrent solide (vs un one-shot passé/incertain qui ne vaut peut-être plus la peine d'être
   publié du tout — dans ce cas, corbeille plutôt que réécriture).
2. Traiter en lot (multi-agent si le volume le justifie), avec la même discipline que sur
   C2C/Yerai Cortés : recherche web sur source officielle, rédaction, backup avant écriture,
   vérification HTTP 200 après écriture.
3. Prioriser id 2188 (sujet sensible) et id 3769 (bug visible immédiatement, template en clair).
