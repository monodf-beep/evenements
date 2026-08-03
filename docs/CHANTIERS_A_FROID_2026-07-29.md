# Chantiers à froid — reprise après la session du 2026-07-29

Session longue (SEO, sitemap, commune sur cards, migration /fr/ tentée puis rollback après
panne). Quatre points restent à traiter **à tête reposée**, chacun cadré ci-dessous. Ne pas
bricoler l'allocateur/hub à chaud : c'est la pièce délicate, elle a déjà mordu deux fois.

## RÈGLE ÉDITORIALE — Sources et organisateurs des événements (posée le 2026-07-29)

**Un lien public sur une fiche événement (bouton/texte « Source » ou champ « Organisateur ») ne
doit désigner QUE : (a) un organisme public (mairie, office de tourisme, fondation publique,
musée) ou (b) l'organisateur réel de l'événement.** Jamais un site tiers (guide, blog, agrégateur
comme guidatorino.com), et jamais un nom de domaine ou un email brut collé sans vérification.

**Trouvé et corrigé le 2026-07-29 :**
1. **3 fiches** citaient `guidatorino.com` (site guide privé, ni institution ni organisateur) comme
   unique source en bas d'article (`<h3>Sources</h3><ul><li><a>URL brute</a></li></ul>`, format
   homogène sur 72 fiches au total, 44 domaines cités — 43 légitimes/publics, 1 seul fautif). Bloc
   Sources retiré sur les 3 fiches (ids 1905, 902, 2287). Backups `cs_bk_sources_<id>`.
2. **Fuite de données personnelles plus grave, trouvée en creusant** : le champ TEC
   `_EventOrganizerID` pointait, sur **18 fiches publiées**, vers un CPT `tribe_organizer` dont le
   NOM était en fait un nom de domaine ou un **email personnel** (`gerard.colletta@serre-editeur.fr`
   ×5, `redazione@piemontedalvivo.it` ×4, `marco@camilli.it` ×2, `guidatorino.com` ×7) — exposé
   publiquement dans le JSON-LD Schema.org (`organizer.name`), indexable par Google. Erreur
   d'import : contact/source collé dans le champ organisateur. **Détaché sur les 18 fiches**
   (`delete_post_meta(_EventOrganizerID)`), vérifié disparu du JSON-LD sur 4 échantillons, home 200.
   Backups `cs_bk_organizer_<id>` (valeur de `_EventOrganizerID` avant suppression).

**À faire pour que ça ne revienne pas** : la génération vient du pipeline Python
(`scripts/publisher_as.py` ou `evaluator.py`, à identifier), pas d'un template WP — le fix WP
d'aujourd'hui est rétroactif. Ajouter au pipeline une validation avant publication : un organisateur
ne doit jamais être un email (regex `@`) ni un nom de domaine seul (regex `\.\w{2,4}$` sans espace) ;
la liste blanche de domaines sources publics/organisateurs (les 43 identifiés) peut servir de base
pour valider automatiquement les nouvelles sources à l'import plutôt que de les accepter telles
quelles.

**Résidu sans rapport repéré au passage** : l'événement id 14 (Matisse/YSL, Nice) a une URL en
`/evenement/__trashed/` — reste d'un passage en corbeille jamais nettoyé côté slug (post bien
`publish`, juste l'URL moche). À renommer le slug quand on y repense.

## 1. Doublons d'événements — RÉSOLU le 2026-07-29 (8 fiches en corbeille)

**FAIT.** Scan complet des 315 événements publiés (regroupés par titre normalisé + date de début),
puis distinction cruciale : **paires FR/IT = traductions Polylang légitimes (garder les deux)** vs
**paires MÊME LANGUE = vrais doublons**. Un ré-import ~26-27/07 avait recréé des fiches déjà là
depuis le 20/07. 8 vrais doublons (même langue) mis en corbeille (réversible) :
681↔2315, 729↔2279, 754↔2323, 702↔2356, 2229↔3811, **Chagall 2020↔3977 (fr)**,
**Chagall 2017↔3981 (it)**, 2289↔2301. Gardé l'original/id le plus bas à chaque fois.
Re-scan final : **0 doublon même-langue restant**, 307 publiés, home 200.

**Chagall (liens de traduction croisés) : réparé.** Les 2 « bonnes » fiches (2020 fr lieu FR 2019 /
2017 it lieu IT 2015) étaient chacune liées à la copie ré-importée. Re-liées entre elles
2020↔2017. **PIÈGE : `pll_set_post_translations()` N'EST PAS disponible dans le contexte
Novamira `execute-php`** (contrairement à `pll_get_post_language`/`pll_get_post_translations` qui,
elles, marchent). Utiliser `PLL()->model->post->save_translations($id, ['fr'=>$idFr,'it'=>$idIt])`.
Ne PAS corbeiller les copies avant d'avoir re-lié les gardes (sinon les gardes pointent vers des
fiches en corbeille).

## (Archive) Doublon Chagall FR/IT — c'est de la DONNÉE, pas du code

Sur les vues territoire (Vallée d'Aoste), l'expo Chagall d'Aoste apparaît **deux fois**. Cause
identifiée : **doublon d'événements en base**, pas un filtre de langue manquant (l'allocateur
#44 ET le hub #61 filtrent bien par `'lang' => $lang`).

Événements concernés (même expo d'Aoste) :
- **2020** (fr) venue « Musée Archéologique Régional d'Aoste » — trad fr:2020 ↔ it:3981
- **3977** (fr) venue « Museo Archeologico Regionale di Aosta » — trad fr:3977 ↔ it:2017
- **2017** (it) venue « Museo Archeologico Regionale di Aosta » — trad it:2017 ↔ fr:3977
- **3981** (it) venue « Musée Archéologique Régional d'Aoste » — trad it:3981 ↔ fr:2020

Il y a donc **deux événements `fr`** (2020 et 3977) pour la même expo → les deux s'affichent sur
une vue FR. Venues croisés FR/IT + liens de traduction mélangés (import/sync foireux).

**Fix : dédoublonnage de données**, pas de patch de code. Outils déjà dans le repo :
`scripts/dedupe.py` et `scripts/cleanup_as_dupes.py`. Lancer en dry-run sur le VPS d'abord
(Chagall n'est sûrement pas le seul doublon), puis nettoyer + recoller les traductions.

## OUTIL DE DIAGNOSTIC (posé le 2026-07-29) — snippet #104 « CS - DEBUG allocation (a la demande) »

Inspecteur d'allocateur **permanent et gaté** : inerte pour les visiteurs, s'active seulement si
on ajoute `?cs_dbg=sabauda` à l'URL. Il injecte en pied de page un commentaire HTML
`<!-- CS_ALLOC_DBG ala-une:4 | jour:8 | weekend:6 | ... -->` = le **vrai `count(post__in)` par
grille JetEngine**, dans l'ordre de rendu. Usage : ouvrir p.ex.
`https://agendasabauda.eu/explore/piemont/?cs_dbg=sabauda`, puis « afficher le code source »,
chercher `CS_ALLOC_DBG`. Zéro écriture DB, zéro coût visiteur. **C'est l'outil de référence pour
tout diagnostic d'allocateur** — ne plus compter les cartes à la main dans le HTML (source d'erreur
avérée).

## 2. « 7 prochains jours » — RÉSOLU sur Savoie/Nice/Haute-Savoie, reste Piémont (`jour:0`)

**Le fix overlap du snippet #44 (next7 = `start<=d7 AND end>=todayStart`) MARCHE.** Vérifié au
rendu réel via l'outil #104 : Savoie/Nice/Haute-Savoie affichent bien `jour:8`. Le « vide » qu'on
voyait avant venait d'un **comptage HTML erroné de ma part** (mauvais découpage de grille → je lisais
2 au lieu de 8), pas d'un bug de données. Ne pas ré-ouvrir ce point pour ces territoires.

**Piémont → `jour:0` : DÉCISION PRISE = garder « 4 ou 8 » strict (pas de fix).** Diagnostic confirmé :
`cs_home_row_size('jour')=4` + `floor(count/4)*4` met délibérément à 0 un stock de 1-3 (commentaire
du code : « on préfère 0/No data qu'un affichage partiel »). Piémont a 1-3 événements dans la fenêtre
7 jours → mis à 0 volontairement. L'utilisateur a arbitré (2026-07-29) : **on garde la règle stricte**,
Piémont reste vide quand il n'a pas de quoi remplir une ligne pleine. Ne pas ré-ouvrir.

**RÉGRESSION trouvée et corrigée le 2026-07-30.** Entre le 07-29 (où `'jour' => 4` était bien dans
`$sizes`, comme documenté ci-dessus) et le 07-30, cette entrée avait disparu du tableau
`cs_home_row_size()` (snippet #44) — cause inconnue, probablement écrasée par une édition
intermédiaire du snippet. Conséquence concrète, vérifiée via l'outil #104 sur les 10
langue×territoire : `jour` affichait 7 (FR Piémont, IT Valle d'Aosta), 5 (FR Vallée d'Aoste) ou 1
(IT Contea di Nizza) — violant la règle 4-ou-8, visible aussi en desktop (7 cartes réellement
rendues, testé). Remis `'jour' => 4` dans `$sizes`. Revérifié sur les 10 combinaisons après fix :
toutes à 0/4/8, zéro régression sur les 6 qui étaient déjà correctes. Backup avant correctif :
option WordPress `cs_bk_snippet44_avant_fix_jour`.

## 3. « Agenda à venir » vide en Vallée d'Aoste — RÉSOLU (réutilisation dédiée)

Diagnostiqué via #104 sur le **vrai** hub `vallee-d-aoste` (attention : `val-d-aoste` et
`vallee-aoste` ne sont PAS des hubs, ils retombent sur la home globale). Petit catalogue : les
sections prioritaires consommaient tout le stock → `venir:0 | venir-bottom:0`.

**Arbitrage utilisateur (2026-07-29) : autoriser la réutilisation.** Fix appliqué dans le snippet
#44 (backup option `cs_s44_reuse_venir_bk_*`) : le closure `$take` prend un 4e param `$max_reuse`
(défaut `null` = ancien budget global de 2, inchangé). Les sections `venir` et `venir-bottom`
reçoivent un budget de réutilisation **dédié de 4**, indépendant du budget global — elles se
remplissent depuis les événements déjà `claimed` (mais toujours filtrés « upcoming », donc
sémantiquement corrects) uniquement en cas de manque. `$reused` empêche qu'un même événement soit
réutilisé deux fois → pas de doublon entre `venir` et `venir-bottom`.

Vérifié : VdA passe à `venir:4 | venir-bottom:4` (rendu réel = 4 + 3 cartes distinctes, zéro
chevauchement). Savoie/Nice/Haute-Savoie **inchangés** (pas de manque → pas de réutilisation).
Home 200.

## 4. Date « en évidence » — RÉSOLU (se rend correctement)

Le champ date du listing **1688** (`_EventStartDate`, classe `cs-card-date`) **se rend** bien.
Vérifié au rendu réel sur `/explore/savoie/` (section evidence, 3 cartes) : affiche `30/08`,
`11/09–21/09`, `11/09–12/09`, `17/09` — y compris les **plages** start–end pour les multi-jours
(séparateur = tiret demi-cadratin « – », PAS un cadratin « — »). Rien à ajuster.

---

## Repères « déjà fait » utiles pour la reprise

- **Commune sur cards** : filtre backend = **snippet Code Snippets #102** (« CS - Commune sur les
  cards »). Il lit la clé depuis `dynamic_field_post_meta_custom` OU `dynamic_field_post_meta`,
  sans exiger `source=meta`, et gère : `_cs_commune` → commune seule ; `_EventVenueName` →
  « lieu · commune ». Champs ajoutés aux listings : 1696 (éditeur), 969/1690/1688 (`_cs_commune`),
  976 (`_EventVenueName`). Format de bloc qui marche :
  `<!-- wp:jet-engine/dynamic-field {"dynamic_field_post_meta_custom":"_cs_commune","className":"cs-card-commune"} /-->`.
  CSS `.cs-card-commune` / `.cs-card-date` dans le **snippet #77**.
- **Bouton Facebook** retiré du snippet #27 (Instagram conservé). Backup `cs_snippet27_backup_fb_*`.
- **Migration /fr/** : reverté (`hide_default=1`). Voir `docs/MIGRATION_URL_FR_PREFIXE.md` (chantier
  staging, ne pas refaire en live).
- **Sitemap** : `territoire` exclu + 8 pages `ce-week-end` en noindex (snippet #101). Health-check
  à 0 problème.
- Backups d'options laissés en base : `cs_s44_*`, `cs_listing*_bk_*`, `cs_s77_bk_commune_*`, etc.
