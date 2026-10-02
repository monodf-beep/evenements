# GO / NO-GO — réactivation du cron de traduction FR↔IT

**Date de l'avis** : 2026-08-02 · **Objet** : `crontab.txt` ligne 49,
`scripts/translate_events.py --apply --cap 5`, en pause depuis le commit `6940d42`.

**Méthode** : chaque affirmation ci-dessous est marquée **PROUVÉ** (test exécuté sur
fixture, sortie reproductible) ou **SUPPOSÉ** (lecture de code, non exécuté). Les tests
sont dans le répertoire de travail de la session, pas dans le dépôt — ils sont repris
verbatim ci-dessous quand le résultat est décisif.

---

## Verdict

> ## 🔴 NO-GO EN L'ÉTAT — GO CONDITIONNEL après trois correctifs bornés
>
> Pas pour la raison qui avait motivé la pause. **La chaîne causale historique est
> réellement corrigée aux maillons 1 et 2**, et je l'ai vérifiée en refaisant tourner le
> cas d'origine. Le blocage vient de ce que la vérification a mis au jour :
>
> 1. un **amplificateur ACTIF** (`seo_batch`, cron 10h30, jamais suspendu) qui réécrit en
>    **français** le SEO de toute fiche traduite et la **republie** — donc chaque
>    traduction produite demain serait dégradée après-demain, mécaniquement ;
> 2. le **maillon 3 n'est corrigé qu'à moitié** : le texte parasite exact du cas
>    d'origine repasse encore le filtre d'`enrich.gather_material` ;
> 3. **aucun filet en aval** n'est branché sur le chemin de `translate_events` — ni le
>    portillon de justesse, ni la porte de complétude, et la relecture du site est
>    structurellement aveugle à ce type de faute.

Le correctif n°1 (`seo_batch`) est une ligne de SQL. Les deux autres sont bornés. Une
fois ces conditions remplies, le cron peut repartir à cap réduit.

---

## 1. Vérification maillon par maillon

### Maillon 1 — `dedupe.py` appariait deux titres sur des mots-outils

**Correctif en place** : `scripts/dedupe.py:74-78` (liste `_STOP` étendue aux adverbes /
pronoms FR+IT), consommée par `_sig_tokens` (`scripts/dedupe.py:87-93`) puis par
`cross_lang_same` (`scripts/dedupe.py:181-202`).

**PROUVÉ — le cas d'origine ne s'apparie plus, et c'est bien ce correctif qui le coupe** :

```
tokens theatre : ['semaine']
tokens gnews   : ['2026', 'annecy', 'cher', 'habitent', 'lac', 'paieront', 'spectateurs']
intersection   : []
cross_lang_same: False (attendu False)
same_story     : False (attendu False)
REGRESSION (ancien _STOP) cross_lang_same: True
```

La dernière ligne est le test qui compte : en réinjectant l'ancienne liste `_STOP` dans le
module, l'appariement redevient `True`. La correction est donc *causale*, pas
coïncidentielle.

**PROUVÉ — les vrais couples bilingues passent toujours** : « Fête du Jambon de Bosses » ↔
« Festa del Jambon de Bosses », « Sagra della Toma di Lanzo » ↔ « Fête de la Toma di
Lanzo », « Exposition Marc Chagall à Aoste » ↔ « Mostra Marc Chagall ad Aosta », « Nice
Jazz Festival 2026 » ↔ lui-même : tous `True`. `_groups()` de bout en bout sur le couple
d'origine rend **2 groupes** (pas de fusion), avec **et sans** `--cross-lang`.

**Trois réserves, à connaître :**

- **Le correctif n°1 corrige un chemin que le cron n'emprunte pas.** `cross_lang_same`
  n'est appelée dans `_groups` que si `--cross-lang` est passé (`scripts/dedupe.py:266-267`),
  et le cron de 8h30 ne le passe pas (`crontab.txt:31`). Sur le chemin du cron, la
  protection réelle contre l'appariement du cas d'origine est `same_story`
  (`utils/sources.py:98-118`), qui rendait déjà `False` — **PROUVÉ** ci-dessus. En
  revanche `cross_lang_same` **est** sur le chemin de `scripts/link_translations_as.py:84`
  (mécanisme B, lancé à la main) : le correctif y sert pleinement.
- **La famille de fusions à tort la plus massive n'est PAS couverte par `_STOP`.** Les
  rubriques récurrentes (« COSA FARE DAL 15 AL 21 GIUGNO… » ↔ « COSA FARE NEL FINE
  SETTIMANA… ») s'apparient toujours, par de vrais mots de contenu. Seule la garde de
  dates (`scripts/dedupe.py:140-178`, appliquée aux deux chemins ligne 264) les sépare —
  **et elle ne tranche que si les DEUX fiches sont datées** (`return False` ligne 164) :

  ```
  datées    : 2 groupe(s) (attendu 2)          <- garde efficace
  NON datées: 1 groupe(s) (fusion à tort)      <- garde inopérante
  NON datées, cross_lang=False: 1 groupe(s)    <- même sans --cross-lang
  ```

  **PROUVÉ.** La pré-datation gratuite de 8h25 (`crontab.txt:26`) n'est donc pas un
  confort : c'est **la** condition de fonctionnement de cette garde. Si `dates.py
  --no-fetch --no-llm` échoue un matin, la garde retombe silencieusement le même jour.
- **Perte de couverture assumée** : « Festival Berlioz 2026 » ne s'apparie plus avec
  lui-même (`festival` est dans `_STOP`, il ne reste qu'un seul mot distinctif, sous le
  seuil de 2). Ce n'est **pas** une régression du correctif du 2026-08-02 (`festival` y
  était déjà), mais ça limite le mécanisme B de `link_translations_as`.

**Conclusion maillon 1 : correctif RÉEL et vérifié, portée plus étroite que ce que dit la
reconstitution.**

---

### Maillon 2 — `merge_group` gardait la description la plus LONGUE

**Correctif en place** : `_text_len` (`scripts/dedupe.py:96-109`) mesure le texte visible
(balises et URLs retirées) ; `merge_group` l'utilise (`scripts/dedupe.py:304-306`).

**PROUVÉ** sur un item Google News RSS réaliste face à une vraie description :

```
brut   : gnews=403  vraie=256  -> GNEWS gagne  (ancienne règle)
visible: gnews=98   vraie=249  -> vraie gagne  (nouvelle règle)
après merge_group FORCÉ du groupe : description du gagnant = VRAIE (OK)
```

Le test force la fusion (il appelle `merge_group` sur un groupe construit à la main) pour
isoler le choix de description du choix d'appariement : même si un jour un mauvais
appariement repasse, la vraie description n'est plus écrasée par un lien creux.

**Réserve** : la règle reste un *comparatif*, pas un *filtre*. Si la vraie description est
plus courte que le titre d'article de l'item Google News (98 caractères visibles ici), le
lien creux gagne toujours. Cas non rare pour une fiche de catalogue laconique.

**Conclusion maillon 2 : correctif RÉEL, efficace sur le cas d'origine, non absolu.**

---

### Maillon 3 — `enrich.gather_material` agrège la matière des doublons

**Correctif en place** : `scripts/enrich.py:841-853` ignore la description d'un doublon
dont le texte visible est inférieur à `ENRICH_MATERIAL_MIN_VISIBLE` (défaut **60**,
`scripts/enrich.py:85`).

### 🔴 PROUVÉ — ce correctif ÉCHOUE sur le texte parasite exact du cas d'origine.

```
ENRICH_MATERIAL_MIN_VISIBLE = 60
visible(gnews long)=98   visible(gnews court)=34
« Fête du lac » dans la matière de rédaction ? OUI  <-- LE TITRE PARASITE PASSE
« se prépare » (gnews court) dans la matière ?  non (filtré, < seuil)

---- matière produite ----
[SIGNAUX FLUX / RADAR]
Une comédie grinçante de Clément Michel. Deux frères que tout oppose se retrouvent…

---

Fête du lac 2026 : les spectateurs qui n'habitent pas Annecy paieront plus cher   Le Dauphiné Libéré
```

Le seuil ne mesure que le volume. Or dans un item Google News, le texte visible **est le
titre de l'article** — précisément l'élément trompeur, et **plus il est long et
spécifique, plus il est dangereux ET plus il passe le filtre**. Le filtre attrape les
stubs anodins (« Annecy : la Fête du lac se prépare », 34 caractères) et laisse passer la
phrase qui a fabriqué « Festa del Lago 2026 » (98 caractères).

Le commentaire du code le dit d'ailleurs lui-même (`scripts/enrich.py:838-840`) : « un
doublon légitime peut parfaitement rester un lien creux ». Le maillon reste ouvert.

**Atténuation** : ce chemin ne s'ouvre que si un item Google News est `duplicate_of` du
gagnant, donc après une fusion. Le maillon 1 réduit les fusions à tort, il ne les supprime
pas — et une fusion **correcte** peut parfaitement embarquer un item Google News.

**Conclusion maillon 3 : correctif PARTIEL, inopérant sur le cas d'origine. À corriger
avant réactivation.**

---

### Maillon 4 — `translate_events.py` traduit une matière déjà fausse

**Exact, et vérifié dans le code.** `_translate_one` traduit `ev["title"]` + `ev["description"]`
(`scripts/translate_events.py:434-435`) puis `ev["enrich_data"]` (`:442-452`). La fiche
traduite ne fabrique aucune donnée factuelle : lieu, ville, territoire, dates, image,
score sont **copiés** de l'original (`:475-496`), `date_source='copie-traduction'` est
posé, `enrich_status='enriched'` protège de `enrich.py`.

**Mais la reconstitution s'arrête trop tôt sur un point.** Le prompt de traduction
(`_charte_prompt`, `scripts/translate_events.py:139-144`) **autorise explicitement la
réécriture du titre** :

> « Si le titre ou le texte source viole une règle […] tu le **CORRIGES** dans la version
> cible »

et `translate_title_desc` reçoit **titre et description dans le même appel**
(`:180-184`). Rien, nulle part, n'ancre le titre traduit sur le titre source. C'est le
mécanisme précis par lequel une description polluée produit un titre faux — ce n'est pas
seulement « le traducteur révèle une pollution », c'est « le traducteur a la permission de
préférer la description au titre ». **SUPPOSÉ** (je n'ai pas fait d'appel LLM), mais c'est
la lecture la plus économique de WP#6798.

**Conclusion maillon 4 : exact ; s'y ajoute une permission de réécriture du titre qui
transforme une pollution de description en pollution de titre.**

### ✅ CONFIRMÉ SUR LA BASE RÉELLE, le 2026-08-04

Ce qui précède était marqué **SUPPOSÉ**. Ça ne l'est plus : la chaîne a été suivie fiche
par fiche, de la fusion jusqu'au post en ligne.

| Maillon | Constat en base |
|---|---|
| 1 · fusion | `[2762]` « Fête du lac 2026 … - ici.fr », fiche **radar** Google News : sa description n'est qu'un `<a href="news.google.com/…">` dont l'URL encodée fait plusieurs centaines de caractères |
| 2 · écrasement | `dedupe.merge_group`, **avant** le correctif du 2026-08-02, comparait les longueurs **brutes** — le lien gagnait toujours, et a écrasé la description de `[2153]` « Une semaine pas plus », spectacle à La Comédie des Alpes, Chambéry |
| 3 · évaluation | `llm_score=10` sur ce texte, avec **cinq justifications parlant d'Annecy** : « Lac d'Annecy, site emblématique », « Ville d'Annecy, grand événement organisé », « Fête du lac, rendez-vous historique et annuel majeur »… |
| 4 · traduction | WP#6798 « Festa del Lago 2026: tariffa maggiorata per chi non abita ad Annecy », avec le **lieu et les dates de la Comédie des Alpes** |

**Le traducteur n'a rien inventé** : il a fidèlement traduit une fiche déjà fausse. Le
défaut était en amont, exactement là où on le soupçonnait sans pouvoir le montrer.

Le mécanisme est **corrigé depuis le 2026-08-02** : `dedupe._text_len` compare le texte
VISIBLE, balises et URLs retirées, donc une description Google News ne peut plus gagner un
arbitrage de longueur.

**Ce que ça change pour le GO/NOGO, et ce que ça ne change pas.** Le motif « cause
inconnue » — celui qui a mis le cron en pause le 2026-08-01 — tombe.

⚠️ **Correction du 2026-08-04, même jour** : j'ai d'abord écrit ici que C4 et C5 restaient
ouverts. **C4 était fait depuis le 2026-08-03** (voir sa ligne plus bas) — l'affirmation
était fausse, dans le document qui sert précisément à décider. Corrigé plutôt que laissé.

### C5 est mesuré, et le trou était petit

C5 demandait l'« état du stock déjà pollué en base », jamais vérifié sur la production —
c'était, de l'aveu du document, *le vrai trou*. Mesuré le 2026-08-04 : **2 fiches vivantes
seulement** portent encore une description polluée par un lien Google News.

- `[2153]` « Une semaine pas plus » — **réparée le jour même**. Description vidée (la
  vraie est irrécupérable : 403 sur tout `agendaculturel.fr`, dix sauvegardes déjà
  polluées, aucune fiche sœur), puis ré-évaluée sur titre + lieu + ville seuls. Le score
  passe de **10 à 1**, et chaque justification décrit enfin le bon événement : « salle de
  théâtre locale peu connue », « spectacle ponctuel », « portée locale uniquement »,
  « spectacle générique, non identitaire ». La catégorie devient « Spectacle vivant ».
  Plus aucune mention d'Annecy. Elle sort de la section.
- `[2864]` « Sous la peau de Joséphine Baker » — **non publiée**, donc hors du vivier de
  `translate_events`.

Et sa traduction WP#6798, celle par qui l'incident est arrivé, est **à la corbeille**
(réversible) : le titre « Festa del Lago 2026 » posé sur un spectacle de Chambéry n'est
plus visible du public.

**Les six conditions sont donc remplies.** Ce qui reste n'est plus une inconnue technique
mais un arbitrage : réactiver la ligne de `crontab.txt`, à `--cap 2`, avec la relecture
humaine quotidienne des permaliens produits. Ce cap n'est pas une prudence de façade — deux
fiches par jour se relisent vraiment, cinq ne se relisent pas.

**Et il y a maintenant une raison de le faire, pas seulement l'absence d'obstacle** : le
vivier italien de « Ça vaut le déplacement » est tombé à **4 candidates pour 2 places**,
c'est-à-dire au seuil de rupture annoncé par le tableau du plancher. Deux fins d'événement
et la section se vide. Or ce vivier ne contient que des fiches TRADUITES : plus de
traduction est le seul levier qui l'élargisse — un plancher plus bas ne ferait qu'y
remettre des événements médiocres.

---

## 2. Maillons oubliés par la reconstitution

### 🔴 A. `seo_batch` réécrit les traductions EN FRANÇAIS et les republie — cron ACTIF

`scripts/seo_batch.py:38-54` sélectionne sur `statut`, `duplicate_of`, date, `llm_score` —
**sans aucune exclusion de `translation_of`**. Or `translate_events` copie `statut`,
`llm_score` et les dates de l'original (`translate_events.py:483-488`) : une traduction
est donc éligible dès le lendemain. Et `utils/seo.py:118` impose : « **Produis, en
français**, en JSON strict ».

**PROUVÉ** sur fixture, avec les paramètres exacts du cron (`--cap 10`, `min-score 7`) :

```
Sélection seo_batch :
  id= 2153 translation_of=None  « Une semaine pas plus »
  id= 4400 translation_of=2153 translated_lang='it'  « Festa del Lago 2026 »
  ==> 1 TRADUCTION(S) sélectionnée(s) pour une réécriture SEO
```

Puis `scripts/seo_batch.py:129-133` **republie** ces fiches (`publish_batch_as --ids
--skip-media`), et `publisher_as.py:350-354` pousse `seo_title` / `seo_meta` /
`focus_keyword` dans Yoast. Résultat : **titre SEO, méta-description et mot-clé français
sur une fiche italienne en ligne** — c'est-à-dire ce que Google affiche.

Deux précisions honnêtes :
- `seo_slug` n'est **pas** repris dans le payload de `publisher_as` (aucune occurrence) :
  l'URL de la paire n'est pas cassée. Le dommage porte sur les métadonnées, pas sur le slug.
- À la republication, `force_lang` est absent, donc `publisher_as._lang` (`:178-186`)
  retombe sur `detect_lang`. Le texte italien devrait l'emporter, le territoire ne
  départageant qu'à égalité (`utils/lang.py:65-70`) : **risque de bascule de langue faible,
  SUPPOSÉ, non prouvé**.

**Ce défaut est actif aujourd'hui**, indépendamment de la pause — il abîme déjà les
traductions existantes. Mais il rend la réactivation absurde : on produirait chaque jour
5 fiches italiennes pour les dégrader le lendemain matin à 10h30.

### 🔴 B. Une traduction machine déliée redevient candidate à la traduction

`scripts/unlink_bad_translations.py:67-69` efface `translation_of` sur la fiche
« traduction ». Or la sélection de `translate_events` (`:552-561`) ne filtre que
`translation_of`, `translated_at`, `wp_post_id_as`, `duplicate_of` et le score : **aucun
garde-fou sur `url_source LIKE 'translated:%'`** (vérifié par `grep` sur tout `scripts/` —
seuls `recover_clobbered_translations`, `repair_translation_cycles` et
`repair_polluted_descriptions` connaissent ce marqueur).

**PROUVÉ** sur fixture, avec la requête de sélection extraite telle quelle du script :

```
état normal (lien intact) : aucun candidat
APRÈS unlink_bad_translations (translation_of effacé) :
  {'id': 2153, 'url_source': 'https://comediedesalpes.com/x'}
  {'id': 4400, 'url_source': 'translated:2153:it'}     <-- fiche MACHINE, redevenue candidate
```

Conséquence : la fiche italienne fabriquée par la machine serait **re-traduite vers le
français**, produisant une troisième fiche — traduction d'une traduction, doublon de
l'original, avec la dérive de titre du maillon 4 appliquée deux fois.
`recover_clobbered_translations.py:74-75` ne restaure le lien que pour les fiches ayant un
`enriched_at` : les autres restent exposées. Ce n'est pas théorique — `unlink_bad_translations`
existe justement parce qu'il a été passé sur 72 paires.

### 🟠 C. `dates.py` passe 4 écrase les dates de toute fiche portant `translation_of`

`scripts/dates.py:501-540` réaligne de force `date_event_start/end` de toute fiche
`translation_of != 0` sur celles de son original, **y compris une paire NATIVE** liée par
`link_translations_as` — dont les deux côtés ont été scrapés séparément et ont chacun des
dates légitimes. Or ce liage-là peut se faire sur la **seule** foi d'une image commune
(`link_translations_as.py:78-80`), sans aucun contrôle de date. Un mauvais jumelage par
image efface donc de vraies dates. **SUPPOSÉ** (code lu, non exécuté : il faudrait la base
réelle pour montrer une occurrence). Atténuation : `link_translations_as` n'est **pas** au
cron, et `_norm_image` exclut déjà les bannières de repli (`:45-59`) — le faux jumelage
restant demanderait deux événements partageant une photo de lieu réutilisée.

### 🟠 D. Ce que l'existence des scripts de réparation documente

- `repair_translation_cycles.py:11-15` : les cycles A↔B venaient de
  `link_translations_as` réappariant une paire déjà établie par `translate_events`, avec
  une direction contradictoire. **Corrigé à la source** — le filtre est bien présent
  (`link_translations_as.py:272-274`) et exclut les deux côtés d'une paire existante. Dans
  un cycle, les deux fiches passent pour des traductions, donc **ni l'une ni l'autre** n'est
  jamais enrichie ni datée : famine durable, pas contamination.
- `recover_clobbered_translations.py` : `enrich` écrasait une traduction par un article
  français. **Corrigé deux fois** : exclusion `COALESCE(translation_of,0)=0` dans
  `enrich.select_events` (`scripts/enrich.py:1142`) **et** `enrich_status='enriched'` posé
  à l'insertion (`translate_events.py:489`) — ceinture et bretelles, la seconde survivant
  même à un déliage. Vérifié en lecture.
- `unlink_bad_translations.py` : voir **B**. Le remède a créé une exposition.

---

## 3. Protections en aval : ce qui arrêterait une traduction fausse demain

### `translate_events` publie-t-il directement ? OUI.

`scripts/translate_events.py:465` appelle `publish_to_as(new_ev)` **directement**. Il ne
passe **pas** par `publish_batch_as`, donc pas par sa porte de complétude
(`publish_batch_as.py:113-117`, `comp.is_complete`). Vérifié en lecture, sans supposition.

### Le portillon de justesse est-il sur ce chemin ? NON.

`batch_report._row_report` n'est importé et appelé que par `scripts/daily_batch.py:33,121,140`
(`grep` exhaustif sur le dépôt ; `site_audit` et `repair_polluted_descriptions` n'en
importent que des *helpers* lexicaux). **Il n'est jamais exécuté sur une traduction.**

### Et si on l'y branchait tel quel ? Il ne verrait rien.

**PROUVÉ** — `_row_report` appliqué à une traduction reproduisant WP#6798 (titre « Festa
del Lago 2026 », lieu La Comédie des Alpes, Chambéry, dates copiées) :

```
· titre publié : « Festa del Lago 2026, gli spettatori pagheranno di più » (cohérent avec la fiche)
· traduction   : de l'id 2153 (langue=it)
==> verdict COMPLET=True  -> PASSE le portillon
```

**Pourquoi** : le contrôle n°3 (`batch_report.py:272-284`) compare le titre publié à un
ancrage qui inclut `r["title"]` — et pour une traduction, `r["title"]` **est le titre
produit par le traducteur**. Le contrôle se confirme lui-même. Il fonctionne sur un
original FR (où `title` est le titre scrapé) ; il est aveugle sur une traduction.

**Ce qui marche, en revanche** : le contrôle n°4 des dates (`batch_report.py:304-312`).
Même fiche avec une date décalée :

```
✗ date début   : 2026-10-12 ≠ 2026-08-12 chez l'original
==> verdict COMPLET=False
```

Ce filet-là est réel et bloquant. Il n'est simplement branché nulle part sur le chemin de
la traduction.

### La relecture du site de 14h l'attraperait-elle ? NON.

`site_audit` compare le **site** à la **base** (`site_audit.py:198-255`). Si la base est
fausse et que le site la reflète fidèlement, il n'y a rien à voir. **PROUVÉ** avec une
réponse HTTP simulée servant un JSON-LD parfaitement cohérent avec la base contaminée :

```
anomalies détectées : AUCUNE
==> le site est conforme à une base déjà fausse
```

`site_audit` attrape une republication perdue, un 404, une date qui diverge, une image de
partage manquante. Il n'attrape **pas** une contamination cohérente — c'est-à-dire
exactement WP#6798 tel que décrit. C'est une limite de conception, pas un bug : il est
honnête sur ce qu'il couvre (`site_audit.py:264-276` le dit déjà pour le territoire).

### Bilan aval

**Sur le chemin de `translate_events`, il n'existe aujourd'hui aucun contrôle de justesse,
aucune porte de complétude, et aucune relecture capable de voir le défaut.** La seule
protection est l'absence de pollution en amont. C'est le point qui décide de l'avis.

---

## 4. Conditions de réactivation

### Bloquantes (à faire avant de décommenter)

| # | Correctif | Fichier | Effort | État |
|---|-----------|---------|--------|------|
| **C1** | Exclure les traductions du SEO : ajouter `"COALESCE(translation_of,0)=0"` à la liste `where` de `_select` | `scripts/seo_batch.py:39-44` | 1 ligne | ✅ **FAIT** |
| **C2** | Contrôle de justesse **non auto-confirmant** avant `publish_to_as` : comparer les tokens du titre traduit à ceux du titre de **l'ORIGINAL** + lieu + ville (jamais à sa propre description ni à son propre titre) ; refuser la publication si aucun mot commun. C'est le seul contrôle qui attrape « Festa del Lago » sur « Une semaine pas plus » | `scripts/translate_events.py` avant `:465`, en réutilisant `batch_report._partagent_un_mot` / `dedupe._sig_tokens` | ~15 lignes | ✅ **FAIT**, avec un signal plus fin que « aucun mot commun » — voir §7 |
| **C3** | Garde-fou anti-retraduction : ajouter `AND COALESCE(url_source,'') NOT LIKE 'translated:%'` à la sélection | `scripts/translate_events.py:552-561` | 1 ligne | ✅ **FAIT** — voir §7 |

### Fortement recommandées

- **C4** — ✅ **FAIT le 2026-08-03**, et le diagnostic d'origine était incomplet.
  L'exclusion par provenance existait déjà, mais **elle ne portait que sur la matière des
  DOUBLONS** : la description PROPRE de la fiche était versée sans aucun filtre. On
  surveillait la porte de service en laissant l'entrée principale ouverte — alors que
  l'enquête conclut précisément que « la pollution est dans la description de l'ORIGINAL,
  la traduction la recopie fidèlement ». Une seule définition, `_materiau_pollue()`, est
  désormais appelée aux **deux** endroits où de la matière entre.
  S'y ajoute un portillon que le cahier des charges ne prévoyait pas : quand écarter la
  description polluée ne laisse **plus rien** (ni dossier de presse, ni page officielle
  lisible), l'enrichissement est **refusé** — statut `matiere_polluee`, compté dans le
  bilan et nommé dans les logs. Rédiger depuis un titre seul, ce serait demander au modèle
  d'inventer un article : le mécanisme exact de WP#6798, mais sciemment.
  Volontairement étroit : une fiche simplement sans matière n'est PAS bloquée (la page
  officielle la rattrape au run suivant), seulement celle dont la matière propre a été
  écartée pour pollution.
- **C5** — ✅ **FAIT le 2026-08-04.** Mesuré sur la base réelle : **2 fiches vivantes**
  seulement portent une description polluée par un lien Google News. `[2153]` a été vidée
  et ré-évaluée le jour même (score 10 → 1, plus aucune mention d'Annecy) ; `[2864]` n'est
  pas publiée, donc hors du vivier de `translate_events`. Le stock pollué n'était pas la
  masse redoutée — mais il ne pouvait pas se deviner, il fallait le compter.
- **C6** — brancher `batch_report._row_report` sur la fiche traduite juste après
  l'insertion (le contrôle n°4 des dates est déjà bloquant et **PROUVÉ** efficace) ;
  dépublier ou signaler si `complet=False`.

### Réglages du premier redémarrage

- **`--cap 2`** au lieu de `--cap 5` les **trois premiers jours**, avec relecture humaine
  des paires produites (2 fiches/jour se relisent en cinq minutes).
- Puis `--cap 5` si rien de suspect au bout de trois jours.
- Ne **pas** lancer `link_translations_as --apply` pendant cette fenêtre (mécanisme B :
  seconde source de `translation_of`, et point d'entrée du problème C).

### Ligne exacte à décommenter — `crontab.txt`, ligne 49

Remplacer :

```
#45 10 * * * cd /root/evenements && .venv/bin/python scripts/translate_events.py --apply --cap 5 >> logs/translate.log 2>&1
```

par (période d'observation, cap réduit) :

```
45 10 * * * cd /root/evenements && .venv/bin/python scripts/translate_events.py --apply --cap 2 >> logs/translate.log 2>&1
```

puis, après trois jours sans incident, remonter `--cap 2` à `--cap 5`.

⚠️ **L'ordre du cron compte** : la traduction (10h45) tourne **après** le SEO (10h30). Une
traduction créée un jour J est donc reprise par `seo_batch` à J+1 10h30 — **avant** toute
relecture humaine. C1 n'est pas négociable.

---

## 5. Ce qui reste NON vérifié, et pourquoi

| Point | Pourquoi non vérifié |
|---|---|
| **État réel du stock en base** | `data/` est dans `.gitignore` ; aucune base dans le dépôt. Je ne sais **pas** combien de fiches encore en ligne portent une description polluée, ni si `repair_polluted_descriptions --apply` a été passé en production. Les seules traces (`logs/repair_polluted_descriptions_2026-08-01.log`, ids 1, 2, 5 ; `logs/audit-dedupe-damage_2026-08-01.log`, « 7 fusions scannées ») viennent visiblement d'une base de test, pas de la production. **C'est le trou de vérification le plus important de cet avis** — et c'est précisément l'objet de C5. |
| **Comportement réel du LLM de traduction** | Aucun appel API n'a été fait (coût, et pas de clé). La dérive de titre du maillon 4 est déduite du prompt, pas observée. |
| **WP#6798 lui-même** | Ni la fiche ni le site n'ont été consultés. Je me fie à sa description dans `crontab.txt`, `docs/BACKLOG.md` et les commentaires de code. |
| **Point C (dates.py passe 4 sur paires natives)** | Demanderait une paire native réelle mal jumelée par image. Non reproduit. |
| **Bascule de langue à la republication** | `detect_lang` devrait tenir sur un texte italien ; non testé sur des textes réels courts. |
| **Le lien Polylang côté WordPress** | `unlink_bad_translations.py:14-19` prévient que le déliage ne touche que SQLite : des paires peuvent être liées sur le site sans l'être en base. Invisible depuis le dépôt. |

---

## 6. Le signal à surveiller les premiers jours

**Un seul signal, à regarder chaque jour, dans cet ordre :**

1. **Le message Slack « 🌍 Traduction quotidienne »** (`translate_events.py:611-615`) :
   ouvrir **chaque** permalien produit. Avec `--cap 2`, c'est deux pages. On cherche une
   seule chose : **le titre italien parle-t-il du même événement que le lieu affiché ?**
   C'est la signature exacte de WP#6798, et c'est le seul contrôle qu'aucun script ne sait
   faire aujourd'hui.

2. **Le signal automatisable, en attendant C2** — une requête à passer chaque matin, qui
   reproduit hors ligne le contrôle non auto-confirmant :

   ```sql
   -- traductions du jour dont le titre ne partage AUCUN mot avec l'ancrage de l'original
   SELECT t.id, t.wp_post_id_as, t.title, o.title AS titre_original, o.lieu, o.ville
   FROM events_raw t JOIN events_raw o ON o.id = t.translation_of
   WHERE t.translated_lang IS NOT NULL
     AND date(t.published_as_date) >= date('now','-1 day');
   ```

   Puis, sur chaque ligne :
   `_partagent_un_mot(_sig_tokens(t.title), _sig_tokens(o.title) | _sig_tokens(o.lieu) | _sig_tokens(o.ville))`.
   **Faux ⇒ à relire immédiatement.** C'est le contrôle que `batch_report` croit faire et
   ne fait pas sur une traduction (§3).

3. **Signaux secondaires, moins spécifiques** :
   - `⚠ description : contient un lien Google News` dans un rapport `batch_report` —
     signature d'une fusion, donc du maillon 3 encore ouvert.
   - Toute alerte 🔴 de `site_audit` (14h) contenant `DATE DE DÉBUT affichée … ≠ … en base`
     sur une fiche `translated_lang` renseignée — signe que la passe 4 de `dates.py` et la
     copie de `translate_events` divergent.
   - Le compteur `errors` du message Slack de traduction : un pic signale des troncatures
     `max_tokens` (`translate_events.py:192,281`), qui produisent des fiches amputées.

**Fenêtre de détection actuelle si on ne fait rien** : `site_audit` tourne par rotation de
40 fiches ; une régression peut donc vivre plusieurs jours — mais surtout, **la
contamination cohérente n'y est de toute façon pas détectable** (§3). Tant que C2 n'est
pas fait, la seule fenêtre de détection est l'œil humain sur deux pages par jour. C'est
pour ça que `--cap 2`.

---

## 7. Addendum 2026-08-03 — C2 et C3 réalisés

**Méthode** : mêmes conventions que ci-dessus (**PROUVÉ** = test exécuté sur fixture,
sortie reproduite verbatim). La fixture reconstruit une base au VRAI schéma du dépôt
(`scraper_events.init_db` + `translate_events._ensure_cols`) avec le cas WP#6798 et quatre
paires bilingues réelles du catalogue. `data/events.db` étant absent du dépôt, rien n'a été
exécuté sur la production.

### C3 — une traduction machine n'est plus jamais re-traduite

Ajouté à la sélection de `translate_events.main` :
`AND COALESCE(url_source,'') NOT LIKE 'translated:%'`. `url_source` est le **seul**
marqueur qui survit à `unlink_bad_translations` (la colonne est `UNIQUE`, jamais réécrite).

**PROUVÉ**, avec la requête d'avant correctif extraite de git et rejouée sur la même base :

```
=== ÉTAT NORMAL (liens de traduction intacts) ===
  candidats du main() CORRIGÉ : []
  candidats de la requête AVANT correctif : []

=== APRÈS unlink_bad_translations (translation_of effacé sur la fiche machine) ===
  candidats de la requête AVANT correctif : [(1, 'https://comediedesalpes.com/…'), (2, 'translated:1:it')]
  candidats du main() CORRIGÉ : [1]

  fiche machine (url_source='translated:1:it') = id 2
  -> RÉSULTAT : OK, exclue
```

La dernière ligne du bloc « avant » est le test qui compte : sans le correctif, la fiche
machine **était** candidate. La correction est causale, pas coïncidentielle.

### C2 — le signal retenu, et pourquoi celui-là

Un contrôle « le titre traduit partage-t-il un mot avec son original ? » est **inutilisable** :
la charte (`_charte_prompt`) autorise la réécriture du titre, et « NOTE D'ARTE » est publié
en français sous « À Turin, la musique entre en dialogue avec les arts décoratifs » — zéro
mot commun, et c'est le travail bien fait. Le signal retenu se lit en **trois temps**, et sa
pièce maîtresse est l'**abstention** :

1. le titre traduit **cite-t-il un élément d'identité de l'ORIGINAL** — son titre scrapé,
   son lieu, sa ville, son organisateur, son territoire — modulo exonymes déclarés par la
   charte et racines romanes (`_meme_racine_bilingue`) ? → oui : rien à dire ;
2. sinon, le titre **nomme-t-il quelque chose de précis** : un nom propre **ailleurs qu'en
   tête de phrase**, ou un millésime ? → non : **ABSTENTION**. Un titre entièrement
   générique (« Una settimana, non di più ») n'est pas recoupable ; prétendre le juger,
   c'est fabriquer du bruit ;
3. il nomme quelque chose de précis et **rien** de ce qu'il nomme n'appartient à
   l'événement d'origine → **suspect**.

Ce qui fait la différence, c'est le **nom propre** : il ne se traduit pas (Chagall, Sodoma,
Accorsi, Bard), sauf les toponymes — dont la liste est courte, fermée, et **déjà déclarée
par la charte de traduction du dépôt**. C'est ce qui sauve « Turin » ← « Torino ».

Deux pistes ont été évaluées **et écartées** :
- **les millésimes seuls** : ils ne discriminent pas le cas réel. « Festa del Lago 2026 »
  porte l'année de l'événement (2026-08-12) ; une règle « année du titre absente des dates
  de l'original » ne se déclenche pas. L'année n'est retenue que comme *token distinctif*
  à l'étape 2, jamais comme preuve à elle seule ;
- **la comparaison au lieu/ville par égalité lexicale** : « Turin »/« Torino » ne partagent
  ni préfixe de 5 ni le mot « tori » (Turin ne contient pas cette chaîne). C'est le
  **squelette consonantique** (`trn` = `trn`) et la table d'exonymes qui les rapprochent.

#### PROUVÉ — les deux sens, sur des cas réels

```
[OK ] FR→IT  WP#6798 — LE CAS À ATTRAPER                    -> suspect    (attendu suspect)
          original  : « Une semaine pas plus » · La Comédie des Alpes, Chambéry
          traduit   : « Festa del Lago 2026 »
          motif     : le titre nomme « 2026 · lago » — rien de tout cela n'appartient à l'événement d'origine

[OK ] FR→IT  la MÊME fiche, correctement traduite (piège du faux positif) -> abstention
          traduit   : « Una settimana, non di più »
          motif     : titre entièrement générique — aucun nom propre ni millésime à recouper

[OK ] IT→FR  NOTE D'ARTE (Museo Accorsi-Ometto, Torino)      -> ok
          traduit   : « À Turin, la musique entre en dialogue avec les arts décoratifs »
[OK ] IT→FR  TORINO RINASCIMENTALE (Musei Reali, Torino)     -> ok
          traduit   : « Turin renaissance : une visite guidée sur les pas de Sodoma »
[OK ] IT→FR  Marc Chagall (Centro Saint-Bénin, Aosta)        -> ok
[OK ] FR→IT  Marc Chagall, sens inverse                      -> ok
[OK ] FR→IT  Château de Montrottier (ids 795/2311)           -> ok  « Visita al Castello di Montrottier »
[OK ] FR→IT  Fête du Jambon de Bosses                        -> ok
[OK ] IT→FR  Sagra della Toma di Lanzo                       -> ok
[OK ] IT→FR  Forte di Bard — ne nomme que le saint           -> ok  (« françois » ↔ « francesco »)
[OK ] IT→FR  FAUX POSITIF assumé — artiste hors ancrage      -> suspect
[OK ] IT→FR  …le même, nom propre en tête de phrase          -> abstention
[OK ] FR→IT  contamination SANS nom propre ni millésime      -> abstention  (NON détectable)
[OK ] FR→IT  titre d'un AUTRE événement nommé (Annecy)       -> suspect
=== 15/15 cas conformes ===
```

#### PROUVÉ — le portillon est bien AVANT la publication

`_translate_one` joué avec un traducteur simulé et `publish_to_as` espionné :

```
--- FR→IT, la sortie LLM qui a produit WP#6798 ---
  ERROR | [1] REFUS — titre traduit incohérent avec l'original : « Festa del Lago 2026 »
        | le titre nomme « 2026 · lago » … Rien n'a été publié.
    -> _translate_one = 'refus' · publish_to_as appelé : NON
--- FR→IT, la traduction CORRECTE de la même fiche ---
    -> _translate_one = 'done'  · publish_to_as appelé : OUI
--- IT→FR, vraie paire du catalogue (NOTE D'ARTE) ---
    -> _translate_one = 'done'  · publish_to_as appelé : OUI
```

#### PROUVÉ — le contrôle de `batch_report` n'est plus auto-confirmant

```
=== l'ANCIEN contrôle n°3, sur la fiche WP#6798 ===
  titre publié : « Festa del Lago 2026, gli spettatori pagheranno di più »
  ancrage de la fiche ELLE-MÊME : ['2026', 'alpes', 'chambery', 'comedie', 'lago']
  -> partagent un mot ? True   <- le titre du traducteur est DANS son propre ancrage

=== AVEC le contrôle 3 bis (ancrage sur l'ORIGINAL) ===
  ⚠ titre traduit: « Festa del Lago 2026, gli spettatori pagheranno di più » — le titre
    nomme « 2026 · lago » — rien de tout cela n'appartient à l'événement d'origine
    (original : « Une semaine pas plus » · La Comédie des Alpes, Chambéry)
  => verdict COMPLET=True
```

Et le filet des dates, lui, est intact :

```
  ✗ date début   : 2026-10-12 ≠ 2026-08-12 chez l'original
  => verdict COMPLET=False
```

Enfin, une vraie paire bilingue ne produit **aucun** avertissement (`0 avertissement(s)`,
`COMPLET=True`).

### Bloquant ou avertissement ? Une asymétrie assumée

Le verdict est **bloquant dans `translate_events`** et **simple ⚠ dans `batch_report`** :

- refuser dans `translate_events`, ce n'est pas retenir une fiche, c'est ne pas en **créer**
  une. L'original n'est pas marqué (`translated_at` reste vide), il se represente au run
  suivant, et le LLM étant stochastique un titre correctement ancré passera. Coût d'un faux
  refus : un appel API et un jour de retard. Coût d'un faux passage : WP#6798 ;
- un ✗ dans `batch_report` retiendrait au contraire une fiche **déjà produite**, sans
  recours — et le diagnostic n'est pas *certain* (un nom propre légitime peut ne vivre que
  dans la description de l'original). La règle de l'en-tête de `batch_report` s'applique :
  ⚠, pas ✗.

### Ce que ce contrôle NE couvre PAS

1. **Le CORPS de la fiche traduite n'est pas contrôlé.** Seul le titre l'est. Une fiche
   dont le titre est juste mais dont la description traduite parle d'un autre événement
   passe. C'est exactement le résidu du **maillon 3** (C4 non fait) : la pollution est dans
   la description de l'ORIGINAL, la traduction la recopie fidèlement.
2. **Une contamination sans nom propre ni millésime n'est pas détectable** — prouvé
   ci-dessus (« I biglietti costeranno più cari quest'estate » → abstention).
3. **Un nom propre en tête de phrase est ignoré** (sa majuscule est grammaticale). Un faux
   titre commençant par le nom parasite passe donc en abstention.
4. **Faux positif résiduel** : un titre traduit qui nomme un artiste ou une œuvre présents
   seulement dans la *description* de l'original — l'ancrage factuel ne peut pas les
   expliquer. Prouvé ci-dessus. Conséquence opérationnelle ci-dessous.
5. **Un refus répété consomme un créneau de `--cap`.** L'original refusé reste en tête de
   file. C'est voulu (un refus répété signale une fiche à réparer, pas à traduire), mais
   avec `--cap 2`, **deux** refus persistants arrêtent la traduction. Le message Slack les
   nomme (`⛔ N refusée(s) … id X « … »`) : c'est bruyant, pas silencieux.
6. **Rien de tout cela ne remplace C5.** Traduire une fiche dont la description est encore
   polluée en base reste le scénario le plus probable de récidive, et ce contrôle n'en
   attrape que la moitié (celle qui remonte jusqu'au titre).
7. **Un titre de moins de 2 tokens significatifs n'est JAMAIS jugé** (`_MIN_TOKENS = 2`) —
   limite ajoutée à la relecture du 2026-08-03, non signalée par l'agent. Elle est plus
   large qu'elle n'en a l'air, parce que `_sig_tokens` retire les mots vides des deux
   langues : « Festa del Lago » ne pèse qu'**un** token (`lago`). **PROUVÉ** :

   ```
   Festa del Lago         tokens=['lago']           -> abstention
   Rothko in mostra       tokens=['rothko']         -> abstention
   Lago di Como           tokens=['como', 'lago']   -> suspect
   ```

   Autrement dit : **le cas WP#6798 lui-même n'aurait PAS été attrapé si son titre avait
   été « Festa del Lago » sans le millésime.** Ce qui l'a fait tomber, c'est le `2026`, qui
   apporte le deuxième token. Le portillon a donc bien attrapé l'incident réel, mais par
   une marge d'un seul token — il ne faut pas en conclure qu'il attrape sa famille.
   La faute va dans le sens sûr (abstention = on publie, pas de blocage à tort), ce qui est
   le bon biais pour un portillon qui interdit ; mais c'est une raison de plus de ne pas
   lâcher la relecture humaine des deux permaliens quotidiens.

### Avis sur la réactivation

Les **trois conditions bloquantes C1, C2, C3 sont remplies**. La ligne 49 du `crontab.txt`
peut être décommentée **à `--cap 2`**, avec la relecture humaine des deux permaliens
quotidiens que le §6 prescrit — elle reste nécessaire, pour la raison n°1 ci-dessus : le
contrôle regarde le titre, l'œil regarde la fiche.

Deux réserves à garder en tête, **inchangées depuis le 2026-08-02** :
- ~~**C5 reste le vrai trou**~~ — mesuré et refermé le 2026-08-04, voir sa ligne ;
- ~~**C4 reste ouvert**~~ — fait le 2026-08-03. Ce qui suit décrit l'état d'AVANT :
  `gather_material` laissait alors passer le texte parasite exact du
  cas d'origine. Le portillon C2 est un filet en aval, pas une réparation de la source.
