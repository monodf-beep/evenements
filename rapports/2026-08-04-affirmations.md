# Affirmations non vérifiées — balayage du 2026-08-04

**Ce qui est cherché** : les phrases du dépôt qui affirment un fait qu'aucun code ne
contrôle. Motif observé trois fois dans la seule journée du 2026-08-04 (poids/maxima de
`deplacement`, fuseau du crontab, section « statique ») : une affirmation répétée que rien
ne teste finit par devenir vraie dans les têtes seulement.

**Méthode** : lecture des commentaires et docstrings des chemins de production, puis
vérification EXÉCUTÉE (`python3`) chaque fois que le dépôt suffit à trancher. Pas d'accès
au VPS, à `data/events.db` ni à WordPress — ce qui en dépend est rangé en
« invérifiable d'ici », avec le contrôle qui la trancherait.

Tri par gravité : ce qui est faux au-dessus d'une fonction de production d'abord.

---

## 1. FAUSSE — vérifiée et contredite

### 1.1 `utils/deplacement.py` — « 0-12 » : le score de tri monte à 16

Le fichier même qui portait l'affirmation fausse du matin en porte une autre, du même
genre, non corrigée.

- ligne 2 : `"""Score « ÇA VAUT LE DÉPLACEMENT » (0-12)`
- ligne 46 : « `as_deplacement_now` (0-12, relevée par le temps qui reste…) »
- ligne 219 (docstring de `deplacement_now`) : « **0-12**, ou None… »
- ligne 153 : « le maximum du bonus (**3**) reste inférieur à l'écart entre un bon et un
  mauvais score intrinsèque (0-12) »

Le code dit autre chose. `deplacement_now` fait `base + bonus`, où `base` vaut au plus 12
(4+3+2+1 pondérés, + 2 de langue) et où `bonus` est la fenêtre d'urgence (max 3) **plus**
le point de rareté ajouté juste après (`bonus += 1`, l. 256-259). Maximum réel : **16**.

Mesuré :

```
$ python3 -c "…deplacement_now(fiche parfaite, ponctuelle, dans 2 jours)…"
intrinseque = 12  (MAX_SCORE annonce 12)
now = 16
etat = (12, 16, "dans la section · 12 intrinsèque + 4 d'urgence")
```

Trois conséquences, dont une visible :

1. `app/templates/preview.html` l. 193 code en dur `{{ depl_now }}/12 au tri` : le
   back-office affiche « **16/12** » pour une fiche remarquable et imminente. C'est la
   note que Franck a demandé à voir le 2026-08-03 précisément pour pouvoir la contester.
2. L'argument de la ligne 153 (« le bonus ne peut pas renverser la qualité ») repose sur
   le chiffre 3. Avec 4, il tient encore — l'écart intrinsèque va jusqu'à 12 — mais il
   n'a jamais été revérifié après l'ajout du point de rareté.
3. **Le dépôt se contredit déjà lui-même** : `scripts/audit_deplacement.py` l. 173 écrit
   correctement « le bonus d'urgence de `deplacement_now` (**0-4**) ». Personne n'a
   rapproché les deux.

Aucun contrôle ne relie `MAX_SCORE` à ce que `deplacement_now` peut réellement rendre.
Un test de trois lignes le ferait : sur les bornes hautes de chaque critère, vérifier que
la sortie ≤ borne annoncée.

### 1.2 `scripts/publisher_as.py` l. 256 — « (0-8) » au-dessus de la méta publiée

```python
# Score « ÇA VAUT LE DÉPLACEMENT » (0-8, vide si non mesuré) — dérivé des critères
"as_deplacement": depl if depl is not None else "",
```

L'échelle est passée de 0-8 à 0-12 le 2026-08-04. Ce commentaire est **le seul texte qui
documente la méta réellement envoyée à WordPress**, et il annonce la mauvaise échelle.
Deux autres endroits répètent le « 0-8 » périmé :
`scripts/refresh_deplacement.py` l. 5 et `docs/ETATS_TERMINAUX.md` (§ « La même question,
posée aux VALEURS »). Gravité réelle : quelqu'un qui règle un tri côté site sur la foi de
ce commentaire posera un seuil deux fois trop permissif — exactement l'erreur que
l'échelle 0-12 avait été introduite pour empêcher (cf. l. 77-79 du même fichier).

### 1.3 `watchdog_crons.fuseau()` — contrôle l'OFFSET, pas le fuseau

Le correctif écrit ce matin pour l'incident nº 2 a lui-même un angle mort d'une heure.
Sa docstring annonce « (fuseau du serveur, **est-il celui attendu**) » et `crontab.txt`
affirme désormais « `watchdog_crons.py` contrôle désormais le fuseau RÉEL à chaque
passage ». Le code teste :

```python
attendu = heures in (1, 2)          # CET = +1, CEST = +2
```

C'est-à-dire : l'offset est-il plausible. Un serveur épinglé sur un fuseau à offset FIXE
passe toute l'année :

```
Europe/Paris   2026-01-15  UTC+1  -> OK      Europe/Paris   2026-08-04  UTC+2  -> OK
Etc/GMT-2      2026-01-15  UTC+2  -> OK  ← 1 h d'écart avec Paris, non détecté
Africa/Lagos   2026-08-04  UTC+1  -> OK  ← 1 h d'écart avec Paris, non détecté
UTC            2026-01-15  UTC+0  -> ALERTE
```

Le cas UTC — celui qui inquiétait — est bien attrapé. Le cas « DST absente » ne l'est pas,
et c'est le plus vicieux : le décalage n'apparaît qu'à la moitié de l'année, sans
changement de configuration entre-temps.

Le contrôle exact tient en une ligne, sans dépendance nouvelle :

```python
from zoneinfo import ZoneInfo
attendu = datetime.now().astimezone().utcoffset() == datetime.now(ZoneInfo(FUSEAU_ATTENDU)).utcoffset()
```

### 1.4 « 14 crons » — il y en a 19

`CLAUDE.md` l. 5 : « 14 crons quotidiens/hebdomadaires ». `watchdog_crons.py` l. 4-5 :
« Quatorze automatisations font vivre ce site (seize depuis le 2026-08-04) », et l. 17
« Seuls 7 crons sur 14 appellent `record_run()` ».

Compté sur `crontab.txt` : **19 lignes actives, 18 scripts distincts**. Le « 7 » est
exact — sept scripts appellent bien `record_run()` (`homepage_health`, `weekly_audits`,
`translate_events`, `site_audit`, `weekly_digest`, `daily_batch`, `seo_batch`) — c'est le
dénominateur qui est resté figé.

**Ce n'est pas qu'une coquille** : la table `ATTENDUS` du chien de garde couvre 16
scripts sur 18. Il manque `watchdog_crons` lui-même (normal) et **`audit_calibrage`**
(`5 8 * * 1`, `logs/calibrage.log`). Ce cron hebdomadaire envoie sur Slack et n'est
surveillé par rien : s'il s'arrête, personne ne le saura — la panne silencieuse que ce
fichier existe pour attraper.

```
$ python3 (comparaison crontab.txt ↔ ATTENDUS)
19 lignes actives; 18 scripts distincts — ATTENDUS: 16
dans crontab mais PAS surveillés : ['audit_calibrage', 'watchdog_crons']
surveillés mais PAS dans crontab : []
```

Rien ne compare ces deux listes. Ce diff est un test unitaire de six lignes.

### 1.5 `scripts/refresh_deplacement.py` l. 22 — « tous les jours, à 11h »

`crontab.txt` l. 138 : `50 10 * * *`. `docs/ETATS_TERMINAUX.md` dit 10h50, `utils/deplacement.py`
dit 10h50. Seule la docstring du script concerné dit 11h. Sans conséquence, mais c'est
littéralement le format de dérive recherché.

### 1.6 Les tests ne testent plus — 10 échecs sur 16

`CLAUDE.md` : « Vérifier sur fixture avant de committer un correctif ». Le seul harnais du
dépôt est rouge :

- **`tests/test_eval.py` (8 échecs, `SystemExit: 2`)** — les tests appellent
  `evaluator.main()` sans argv ; `argparse` lit alors `sys.argv[1:]`, c'est-à-dire les
  arguments de `pytest`, et sort en erreur. Sa docstring annonce vérifier la bifurcation
  des seuils de score : **aucune assertion n'est atteinte**. Correctif : `main([])`.
- **`tests/test_gmail.py` (2 échecs)** — dérive de fixture, pas de bug de production,
  vérifié : `parse_message` préfère désormais délibérément la partie HTML (pour garder les
  liens) alors que le test attend encore le `text/plain` ; et le faux client du test
  précède la gestion des blocs de raisonnement (`type == "text"`) ajoutée à
  `extract_events`. Le chemin réel gère bien le JSON précédé de prose.

Les six tests qui passent sont ceux de `test_radar_gate.py`.

### 1.7 `purge_past` ignore la règle 5 sur les récurrents

`CLAUDE.md` règle 5 : les événements récurrents « n'ont pas de date unique et ne sont donc
jamais “passés” ». `purge_past._select` ne filtre PAS sur `recurring` — il ne regarde que
`date_event_end`/`date_event_start`.

En pratique le chemin normal protège : `app.py` l. 3074 ne pose `recurring=1` que quand la
date manque déjà. Mais l'action manuelle du back-office (`app.py` l. 3836-3844,
`action == "recurring"`) écrit `recurring=1` **sans toucher aux dates**. Une fiche marquée
récurrente à la main sur un événement daté sera rejetée par `purge_past` au premier
passage. Réversible (statut), donc bénin — mais l'invariant « récurrent ⇒ pas de date »
est affirmé partout et garanti nulle part. Ajouter `AND COALESCE(recurring,0)=0` au
`WHERE` referme le cas.

---

## 2. INVÉRIFIABLE D'ICI — et le contrôle qui trancherait

### 2.1 Le mu-plugin `cs-cvld-dynamique.php` — troisième affirmation d'affilée sur le même fichier absent

`utils/deplacement.py` l. 30-50 porte, en **LE POINT QUI COMPTE**, l'affirmation dont
dépend tout le travail des deux derniers jours :

> ce mu-plugin trie sur `as_deplacement` — la note intrinsèque 0-8, FIGÉE — et non sur
> `as_deplacement_now`. […] Trier sur `as_deplacement_now != ''` les applique tous les
> trois d'un coup.

`wp-content/mu-plugins/cs-cvld-dynamique.php` **n'est pas dans le dépôt** (seuls
`wordpress/design-system/*.php` sont versionnés ; `docs/DIAGNOSTIC_BUGS_SITE.md` l. 53 le
confirme : « des blocs absents du dépôt (`cs-cvld-grid`…) »). C'est la troisième
affirmation successive au sujet de ce fichier dans cette docstring ; les deux précédentes
étaient fausses, à quelques heures d'intervalle. Elle est écrite avec plus de prudence,
mais elle reste invérifiable d'ici — et elle porte, au passage, le « 0-8 » périmé du § 1.2.

**Contrôles proposés, par ordre de coût :**

1. **Versionner le mu-plugin** dans `wordpress/design-system/` (ou `wordpress/mu-plugins/`).
   Il décide de la vitrine ; il est le seul morceau du chemin qui n'est nulle part.
   Un `git diff` remplacerait alors trois affirmations successives.
2. **Étendre `homepage_health`** à la section « Ça vaut le déplacement » : elle n'est pas
   dans `_SECTIONS` (qui ne surveille que « À la une », « En évidence », « Les 7 prochains
   jours »). Une carte vide y est pourtant un résultat ATTENDU du plancher à 10 — donc
   indistinguable d'une panne, aujourd'hui, pour qui que ce soit.
3. **Le contrôle qui prouve la clé de tri** : comparer les événements réellement servis
   dans `.cs-cvld-grid` au sommet de `as_deplacement_now` par territoire, calculé en base.
   S'ils divergent, la section ne trie pas sur ce qu'on croit.

### 2.2 Les chiffres de calibrage — mesurés une fois, jamais re-mesurés

`utils/deplacement.py` l. 166-174 justifie `DEPLACEMENT_MIN = 10` par un relevé du stock :
« 8/12 → 81 fiches », « 10/12 → 31 fiches, et chaque territoire en garde au moins 4 »,
« 11/12 → le vivier ITALIEN tombe à 4 pour 2 places ». Idem pour les 44 % de
`notoriete_lieu` (l. 65-66).

Ces mesures sont bien plus honnêtes que « suffisant » — c'est le bon réflexe. Mais elles
datent d'un instant et **le stock bouge tous les jours** : c'est précisément la nature du
catalogue. Le seuil de rupture annoncé (« 11 » vide la colonne italienne) peut être
franchi par 10 sans qu'aucun signal ne parte.

**Contrôle proposé** : `scripts/audit_deplacement.py` existe déjà et produit exactement ce
tableau. Le brancher dans `weekly_audits` avec une alerte quand un territoire descend
sous 2 candidates au plancher courant — l'affirmation devient alors une mesure vivante.

### 2.3 `homepage_health` — « les cartes sont dans le HTML servi »

Docstring : « Zéro coût API, zéro JS exécuté (pas besoin : les cartes sont dans le HTML
servi, confirmé en pratique le 2026-08-01) ». Invérifiable d'ici (nécessite la home).
Défaut **bénin** : si le thème passait au rendu JS, le script crierait « section vide »
plutôt que de se taire — le contrôle échoue du bon côté. À laisser tel quel, en sachant
qu'une alerte « sections vides » simultanée sur les trois signifie probablement ça et non
un trou de contenu.

### 2.4 `CLAUDE.md` règle 1 — « `/?p=<id>` répond 404 pour tout `tribe_events` »

Propriété de The Events Calendar + du thème, sur le site réel. Invérifiable d'ici.
Contrôle : depuis le VPS, `curl -o /dev/null -w '%{http_code}'` sur `/?p=<id>` pour un
post **public connu**, comparé à la réponse REST du même id. Une ligne dans
`site_health_check` figerait le constat au lieu de le reconduire de mémoire.

---

## 3. VÉRIFIÉE — elle tient

Dites explicitement, parce qu'une vérification négative se perd aussi.

| Affirmation | Où | Vérification |
|---|---|---|
| Pondération : 33 / 25 / 17 / 8 % + langue 17 % | `utils/deplacement.py` l. 81-89 | Exacte. 4+3+2+1+2 = 12, et chaque pourcentage tombe juste. `MAX_SCORE = 12` est correct **pour la note intrinsèque** (c'est `deplacement_now` qui déborde, § 1.1). |
| `force=True` de `cleanup_as_trash.trash_one` passe par la route MAISON `cs/v1/trash`, réversible | `CLAUDE.md` § autonomie | Exacte. `cleanup_as_trash.py` l. 84 : `f"{wp_url}/?rest_route=/cs/v1/trash"`. `trash_by_ids.py` l. 39 importe bien `trash_one` et l'appelle avec `force=True` l. 136. Aucune route `wp/v2/…` sur ce chemin. |
| `--hard` SUPPRIME les lignes au lieu de les rejeter | `CLAUDE.md` § interdit | Exacte : `purge_out_of_zone.py` l. 153-154 `DELETE FROM events_raw`. Nuance : c'est le **seul** `--hard` du dépôt — `purge_past` et `purge_uncompletable` n'en ont pas. Le pluriel de `CLAUDE.md` sur-couvre, donc il se trompe du côté prudent. |
| Périmètre : 101 communes (Nice) + 62 (Grasse) = 163, « complètes et disjointes » | `utils/sources.py` l. 706 | Exacte, mesurée sur `config/communes_comte_de_nice.json` : 101 + 62 = 163 entrées distinctes après normalisation, **intersection vide**. `est_arrondissement_grasse` classe correctement Cannes/Antibes/Vence/Villeneuve-Loubet → hors périmètre, Nice/Tende → dedans. |
| Le tableau des « qui rouvre » | `docs/ETATS_TERMINAUX.md` | Toutes les colonnes « Rouvert par » vérifiées présentes dans le code : `repair_polluted_descriptions` efface bien `matiere_polluee` (l. 459) ; `VENUE_COOLDOWN_DAYS`, `DATE_COOLDOWN_DAYS` et `ENRICH_RETRY_DAYS` lisent bien `WEB_COOLDOWN_DAYS` en repli avec 7 pour défaut ; `weekly_digest` liste bien `home_override='excluded'` (l. 45). |
| Dry-run par défaut sur les scripts destructifs | `CLAUDE.md` règle 4 | Tient. Balayage de tout ce qui pose `rejected`/`merged` ou fait `DELETE` : chaque script d'intervention a `--apply` ou `--execute`. Les seules exceptions écrivent sans garde **par conception** (`evaluator`, `dedupe`, `enrich`, `scraper_events` : ce sont les crons du pipeline, pas des outils de réparation). |
| Le matching de `homepage_health` est insensible à la casse | `scripts/homepage_health.py` l. 41-43 | Exacte : `re.IGNORECASE` bien présent dans `_section_counts`, sur `finditer` comme sur les bornes. |
| « Les `.svg` sont toujours écartés » | `utils/sources.is_logo_image` | Exacte : `path.endswith(".svg")` après `lower()`, et sur le `path` seul — donc `img.svg?v=2` est bien attrapé, comme le commentaire l'annonce. |

---

## Ce qui se referme le moins cher

Par rapport gravité / effort, dans l'ordre :

1. **`fuseau()` : deux lignes** (§ 1.3) — le contrôle écrit ce matin a un angle mort d'une
   heure, la moitié de l'année.
2. **`audit_calibrage` dans `ATTENDUS`, + un test qui diffe `ATTENDUS` contre
   `crontab.txt`** (§ 1.4) — sinon la table divergera encore.
3. **`main([])` dans `test_eval.py`** (§ 1.6) — huit tests qui n'assertent rien
   redeviennent huit tests.
4. **Les « 0-12 » et « 0-8 »** (§ 1.1, § 1.2) — plus un test de bornes, pour que la
   prochaine échelle ne se contredise pas en silence.
5. **Versionner `cs-cvld-dynamique.php`** (§ 2.1) — le seul morceau du chemin de la
   vitrine qui n'existe nulle part ici, et déjà à l'origine de deux erreurs en un jour.

Aucun fichier du dépôt n'a été modifié : ce rapport est le seul écrit.
