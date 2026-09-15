# Dédoublonnage — ce que les scripts font, ce qu'ils ratent, et pourquoi

Deux scripts, deux moments, deux gestes :

| | `scripts/dedupe.py` | `scripts/verifier_doublons_publies.py` |
|---|---|---|
| quand | cron 8h30, sur `statut='pending'` (le flux du matin) ; `--rescan` pour le stock retenu | cron 9h50, `--en-ligne --slack`, sur les fiches PUBLIÉES encore devant nous |
| geste | FUSIONNE : gagnant = meilleur `TIER_RANK` puis richesse ; perdants `statut='merged'`, `duplicate_of` ; réversible (`unmerge_data`, `scripts/unmerge.py`) | DÉSIGNE, ne fusionne rien : sortie lisible + Slack + commande `trash_by_ids` complète ; Franck tranche |
| dry-run | `--dry-run` (05/09) | toujours en lecture seule ; sans `--en-ligne`, aucun retrait proposé (règle 1) |

La définition de « même événement » est UNIQUE : `dedupe._groups`, importée par le second.
Deux définitions finiraient par se contredire, et c'est la plus bavarde qu'on croirait.

Ce document existe depuis le 2026-09-08 ; avant, la doctrine du dédoublonnage vivait dans
les en-têtes des deux scripts (qui restent la référence de détail) et dans
`docs/PIPELINE_COLLECTE.md` §8, `docs/ETATS_TERMINAUX.md` (la fusion et son rouvreur),
`docs/BACKLOG.md` (« contamination de contenu »).

---

## 2026-09-08 — la paire Pinocchio, et la règle de coïncidence lieu + dates + jeton

### Ce que Franck a vu

Hub Vallée d'Aoste, « L'agenda à venir », deux cartes côte à côte :

- WP#6413 « Pinocchio traverse les Alpes : quand un bicentenaire ravive la Vallée d'Aoste », 19–20/09, Bard ;
- WP#8193 « Pinocchio fait étape au Forte di Bard pour les 200 ans de Carlo Collodi », 19–20/09, Bard.

Plus tôt dans la journée, trois autres paires publiées en double avaient été corbeillées à
la main : Risò, Salone Auto Torino (FR « Salone Auto Torino 2026 : trois jours… » /
« …: tre giorni… »), Orlando. Franck : « si le travail sur les flux RSS pouvait éviter les
doublons ».

### La mesure — pourquoi la paire est passée

Rejoué sur le code tel qu'il était (`scratchpad/mesure_pinocchio.py`, sortie reproduite
dans `tests/test_dedupe_coincidence.py` §1) :

1. **`same_story` dit non** (`utils/sources.py:106-126`). Deux signaux seulement : un
   « nom propre à majuscule interne » partagé (RareEarth, Mont-Blanc) — ici `proper(A) =
   {"d'aoste"}`, `proper(B) = ∅` ; ou **≥ 3 mots significatifs communs** (ligne 126) — ici
   `{pinocchio}`, un seul. Deux journalistes qui écrivent chacun leur titre sur le même
   fait ne partagent souvent que le NOM de la chose.
2. **`cross_lang_same` dit non** (`scripts/dedupe.py`, `if len(shared_words) < 2`) : un
   jeton commun là où il en faut deux — et il n'est appelé qu'avec `--cross-lang`, que le
   cron ne passe pas.
3. **`_groups` ne lit ni `ville` ni `lieu`**, et la date n'y sert qu'en NÉGATIF :
   `_dates_incompatible` sépare deux fiches trop éloignées, elle ne rapproche jamais deux
   fiches qui coïncident. Il n'y avait donc aucun critère de lieu, et aucun critère de date
   positif.
4. **Le cron de 8h30 ne compare que `statut='pending'` entre elles** (`where` de `main`) :
   quand 8193 est arrivée, 6413 était déjà publiée depuis des semaines — elles ne se sont
   jamais rencontrées à cette étape, quel que soit le critère.
5. **`verifier_doublons_publies --en-ligne` (9h50) les a bien eues toutes deux en main**,
   publiées et devant nous — mais il appelle le même `_groups` (ligne 119), donc la même
   ressemblance de titres, donc le même non. Il a tourné chaque matin sans rien dire, et
   son « 0 » avait la tête d'un site sain.

Salone Auto Torino, en revanche, est bien apparié par le chemin des titres
(`same_story` = True, `cross_lang_same` = True — mesuré) : cette paire-là n'est pas passée
par manque de critère mais parce que la jumelle est LÉGITIME quand elle est liée par
Polylang (`translation_of`), et que `verifier_doublons_publies` écarte ces paires-là à
raison. Si c'étaient deux fiches françaises non liées, il les signalait déjà.

### La règle ajoutée — `dedupe.coincidence_lieu_date`

Un troisième chemin dans `_groups(events, cross_lang=False, coincidence=False)`, EN PLUS
des deux existants (`_memes_titres`, qui isole le chemin historique sans le changer).
Cinq conditions, toutes exigées — chacune seule est banale :

| condition | comment | pourquoi |
|---|---|---|
| même territoire | déjà imposé par `_groups` | perf et sens |
| **mêmes dates** | `date_event_start` égales ET `date_event_end` égales (fin absente = début) ; les deux fiches datées | une fiche sans date est une donnée manquante (règle 5), pas un doublon ; **pas d'inclusion** : l'exposition de mai à septembre « contient » chaque visite guidée qu'on y donne |
| **même ville OU même lieu** | ville via `utils.lieux.canon` (Aosta = Aoste) ; lieu via `utils.lieux.plie`, refusé s'il est GÉNÉRIQUE (`utils.lieux.GENERIQUES` : « salle des fêtes ») | cent communes ont une salle des fêtes |
| **un jeton distinctif commun** | ≥ 5 lettres, alphabétique, hors `_NON_DISTINCTIFS` | voir ci-dessous |
| **jamais une paire `translation_of`** | `dedupe.paire_de_traduction` (déplacée depuis `verifier_doublons_publies`, qui l'importe) | deux langues, pas deux doublons |

`_NON_DISTINCTIFS` réunit ce qui existait déjà — `dedupe._STOP` (mots-outils FR/IT +
génériques d'événement : festival, concert, mostra, salone…), `utils.sources._STORY_PLACES`
(savoie, torino, aoste…), les mots de `utils.lieux.GENERIQUES` — et une liste écrite ce
jour : types d'activité (visite, teatro, museo, ville, saison, atelier, conferenza…), mots
de lieu (castello, palais, forte, parco…), mois, jours, saisons, fêtes calendaires,
épithètes de gabarit (grande, nouveau, prima…), l'occasion (anniversaire, bicentenaire).
Et, par paire, **les mots du lieu et de la ville des deux fiches** : « forte » et « bard »
partagés par deux événements au Forte di Bard ne disent rien.

La règle rend un **motif en clair** (« ville « bard », 2026-09-19→2026-09-20, jeton
« pinocchio » »), jamais un booléen : ce motif est affiché à l'humain qui tranche, parce
qu'une recommandation sans son critère se lit comme une certitude.

### Ce qu'elle produit — un candidat, pas une fusion

Le dépôt ne distingue pas « certain » et « à confirmer » dans `dedupe` : tout ce que
`_groups` renvoie est fusionné, et une fusion à tort coûte plus qu'un statut — la matière
du perdant nourrit la rédaction du gagnant (`docs/BACKLOG.md`). Une règle qui tient par UN
mot commun mérite un regard. Donc :

- **`dedupe.py` sans option (le cron)** : comportement inchangé pour la fusion ; les groupes
  que seule la coïncidence forme sont **listés** dans le log (« CANDIDAT par coïncidence
  (non fusionné sans --coincidence) : ids …, motif ») et comptés dans la ligne de bilan,
  même à zéro ;
- **`dedupe.py --dry-run`** : section « CANDIDATS par coïncidence lieu + dates + jeton »
  sous les groupes fusionnables, avec titres et motif ;
- **`dedupe.py --coincidence`** : les fusionne aussi (pour qui a lu le dry-run) ;
- **`verifier_doublons_publies`** : active `coincidence=True` — c'est le circuit fait pour
  ça (il désigne, Franck tranche). Le groupe formé ainsi porte la ligne « ↔ appariées par
  COÏNCIDENCE, pas par le titre : … », le compteur « …dont par coïncidence » est à côté
  de son périmètre, la commande `trash_by_ids … --statut rejected` est la même qu'avant,
  et le message Slack porte le motif.

**Qui rouvre (règle 3)** : le cron de 9h50. Un candidat pending suit son chemin (évaluation,
publication) et, s'il est publié en double, remonte le matin même sur Slack avec le mot
qui l'a formé. C'est là que la paire Pinocchio aurait dû remonter ; c'est là qu'elle
remonte désormais (mesuré sur fixture, §5).

### La fixture — `tests/test_dedupe_coincidence.py` (43 contrôles, verte le 08/09)

Les cas qui doivent PASSER, choisis près de la frontière, parce qu'une fixture qui ne
contient que ce que la règle attrape prouve seulement qu'elle attrape :

- deux spectacles différents le même soir au même théâtre, le nom de la salle dans les
  deux titres (« Le Malade imaginaire au Théâtre Charles Dullin » / « Orchestre des Pays
  de Savoie au Théâtre Charles Dullin ») : **pas appariés** par la coïncidence ;
- deux expositions au même musée aux mêmes dates, mot commun « mostra » : **non** ;
- une fiche FR et sa traduction IT liée (`translation_of`) : **jamais** ;
- même mot, deux jours différents ; inclusion de périodes ; sans ville ni lieu ; lieu
  générique partagé sans la même ville : **non** ;
- la paire Pinocchio (titres réels) : **détectée**, motif « pinocchio » ;
- Orlando (« Face à face – Orlando », titre réel de la fiche 917, et un second titre
  INVENTÉ vraisemblable) : **détectée** ;
- `dedupe.main` : rien fusionné par défaut, listé en dry-run, fusionné avec `--coincidence` ;
- `verifier_doublons_publies --en-ligne --slack` : la paire publiée remonte avec le motif,
  la paire passée n'est pas une tâche, la paire FR/IT est comptée écartée.

### Les limites, mesurées

1. **Risò n'est pas couvert.** « riso » a quatre lettres, le plancher `JETON_MIN_LETTRES`
   en veut cinq (titres de la fixture INVENTÉS : seul « Risò 2026 » est attesté,
   `docs/MESURES_2026-09-06.md`). Abaisser à 4 ouvrirait « jazz », « rock », « arte »,
   « film »… La fixture l'affiche comme LIMITE CONNUE, sans le compter.
2. **Une paire FR/IT NON liée n'est pas vue par la coïncidence** : ses seuls noms propres
   communs sont la ville et le lieu, exclus par construction, et le reste change de langue
   (trois/tre, jours/giorni). Elle reste l'affaire du chemin des titres, qui la voit
   (Salone Auto Torino : mesuré True).
3. **Une fiche sans date, ou récurrente, n'est jamais appariée par ici.** Voulu (règle 5),
   mais à savoir : les deux Pinocchio le sont parce que `dates.py` les avait datées.
4. **Le cron de 8h30 ne compare toujours pas le flux du matin au stock publié** (point 4
   de la mesure). La règle ne change pas cette architecture ; c'est le 9h50 qui couvre.
5. **Le chemin historique a un faux positif que ce travail a révélé sans le corriger** :
   `same_story` apparie « Le Malade imaginaire au Théâtre Charles Dullin » et « Orchestre
   des Pays de Savoie au Théâtre Charles Dullin » par les mots du LIEU (theatre, charles,
   dullin = 3 mots significatifs). Deux fiches pending le même jour avec le nom de la salle
   dans le titre fusionnent donc à 8h30. Mesuré (`_memes_titres` = True), affiché par la
   fixture, non corrigé ici : le correctif appartient à `utils/sources.same_story`, hors
   du périmètre de ce lot. Le lieu-dans-le-titre est fréquent dans les flux d'offices de
   tourisme — à traiter.
6. **La recommandation « GARDER / retirer » n'applique pas la règle de Franck « garder le
   premier ».** `_valeur` classe d'abord par article rédigé, puis longueur, puis permalien
   propre, et seulement ensuite par ancienneté (cas Chagall du 13/08, où c'était voulu).
   Sur Pinocchio, si 8193 porte l'article le plus fourni, le script proposera de garder
   8193. Le choix reste éditorial ; l'ordre des critères aussi — non changé ce soir.

### Les commandes (VPS, une fois la branche déployée : `merge && push && bash deploy/update.sh`)

```bash
# (a) lister les doublons EN LIGNE avec la nouvelle règle — lecture seule, rien ne bouge
cd ~/evenements && .venv/bin/python -m scripts.verifier_doublons_publies --en-ligne

# (b) corbeiller la seconde page Pinocchio en gardant la première (6413) — RÉVERSIBLE.
#     L'id LOCAL de WP#8193 est celui entre crochets sur sa ligne dans la sortie de (a) ;
#     trash_by_ids veut l'id local, pas le numéro WordPress. D'abord sans --apply, LIRE, puis :
cd ~/evenements && .venv/bin/python -m scripts.trash_by_ids <ID_LOCAL_DE_8193> \
    --statut rejected --motif "doublon de WP#6413 (Pinocchio, Forte di Bard) — garder le premier"
cd ~/evenements && .venv/bin/python -m scripts.trash_by_ids <ID_LOCAL_DE_8193> \
    --statut rejected --motif "doublon de WP#6413 (Pinocchio, Forte di Bard) — garder le premier" --apply

# aperçu côté flux du matin (rien n'est écrit) : ce que la règle fusionnerait
cd ~/evenements && .venv/bin/python scripts/dedupe.py --dry-run --rescan
```

`--statut rejected` n'est pas un ornement : sans lui, `trash_by_ids` refuse, et il a raison —
une fiche `published_sub` corbeillée sans statut est le profil exact que `publish_batch_as`
republie le lendemain.
