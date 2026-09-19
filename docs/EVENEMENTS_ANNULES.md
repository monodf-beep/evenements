# Événements annulés et reportés — proposition

**Proposition du 2026-08-04.** Question de Franck : « comment gérer les événements
annulés ? » Vérifié dans le code le jour même : le mot « annulé » n'apparaissait NULLE
PART — ni détection, ni statut, ni affichage. Un événement annulé restait en ligne comme
si de rien n'était jusqu'à ce que sa date passe.

**Mise à jour du 2026-08-05 — le canal 2 est implémenté**, décision validée par Franck :
« alerte Slack seulement, je confirme moi-même ». Voir `utils/annulation.py`,
`scripts.dedupe._porte_annulation` et `scripts/audit_annulations.py`.

**Mise à jour du 2026-08-05 (suite) — le canal 3 est implémenté** aussi, même doctrine,
mêmes colonnes. Voir `scripts.dates.signale_annulation_page` (partagée avec
`scripts/venues.py`) ci-dessous.

**Mise à jour du 2026-08-05 (suite) — le canal 1 est implémenté**, LE PREMIER DES TROIS
posé (comme prévu : « sans lui, les canaux automatiques n'auraient nulle part où déposer
leur trouvaille »). C'est le geste MANUEL de Franck : un bouton sur `/preview/<id>`
(`app/app.py`, routes `/action/<id>/annuler` et `/action/<id>/annuler_off`), pour une
annulation apprise par un autre moyen que ce dépôt (email, coup de fil, site officiel) —
il ne détecte rien, il PROPAGE ce que Franck sait déjà. Voir « Côté WordPress » ci-dessous
pour le choix fait sur l'affichage (préfixe de titre, pas de bandeau natif TEC) et
« Effets de bord » pour ce qui a été traité en même temps. Fixture :
`tests/test_action_annuler.py`.

## La doctrine proposée, avant la mécanique

**Une annulation ne se cache pas, elle s'affiche.** Supprimer ou corbeiller la fiche
serait le pire service : le lecteur qui avait prévu d'y aller, qui a envoyé le lien à des
amis, qui retombe dessus par une recherche, doit trouver « ANNULÉ » en travers de la page
— pas une 404. La page annulée rend service jusqu'à la date prévue, puis suit
l'archivage normal. C'est aussi la seule option honnête vis-à-vis de Google : la page
existe, son statut a changé.

**Un report n'est pas une annulation.** « Rinviato/reporté » = même événement, autre
date : on met à jour les dates quand la nouvelle est connue, et tant qu'elle ne l'est
pas, la fiche s'affiche « reporté, nouvelle date à venir » — jamais supprimée, jamais
datée au hasard.

## Les trois canaux de détection, du plus sûr au plus fin

1. **✅ Le bouton du back-office** — le canal sûr : Franck apprend l'annulation, un clic la
   propage (base + republication + retrait des vitrines). Construit en premier, comme
   prévu : sans lui, les canaux automatiques n'auraient nulle part où déposer leur
   trouvaille.
   Implémenté le 2026-08-05 : `/action/<id>/annuler` (et son symétrique
   `/action/<id>/annuler_off`, pour défaire une erreur de clic — CLAUDE.md, « réversible =
   seul ») dans `app/app.py`, câblées sur le bouton 🚫 de `/preview/<id>`
   (`app/templates/preview.html`). Ce que fait un clic :
     - pose `annule_le` (timestamp, colonne `events_raw` — SEULE source de vérité de
       l'état « annulé », déclarée dans `scripts.scraper_events.init_db` pour que tout
       script qui ne charge que `init_db` la trouve, même sans jamais importer `app.py` —
       la leçon de `wp_deleted_at`, reproduite en écrivant CE correctif :
       `scripts/seo_batch.py` filtrait déjà dessus et sa fixture plantait sur une base
       construite hors `app.py`) ;
     - préfixe le TITRE, en base ET republié — cf. « Côté WordPress » plus bas ;
     - republie IMMÉDIATEMENT si `wp_post_id_as` est renseigné, via `publish_to_as(...,
       skip_media=True)` (même fonction que `/action/<id>/publish_as`, même motif
       `skip_media` que `scripts/seo_batch.py` : seul le titre change, la photo ne bouge
       pas) ; si la fiche n'est pas encore publiée, la base change quand même — Franck
       peut savoir avant même que le pipeline ait publié ;
     - **ne touche PAS `statut`** : pas de dépublication, pas de corbeille — la doctrine
       exactement ;
     - **jumelle FR/IT incluse** : `translation_of` relié (dans les deux sens, comme le
       fait déjà `/preview` pour afficher la paire) → les deux langues annulent ensemble,
       chacune avec SON préfixe (`_lang_fiche` : `translated_lang` si la fiche est une
       traduction, sinon `utils.lang.effective_lang`, qui préfère l'article déjà rédigé au
       titre scrapé brut) ;
     - idempotent (recliquer ne double pas le préfixe, ne republie pas pour rien) et
       n'efface jamais l'état posé en base si la republication WordPress échoue — un échec
       réseau reste visible en base (`annule_le` posé, à republier), jamais perdu en
       silence (CLAUDE.md règle 6).
   Fixture : `tests/test_action_annuler.py` — pose, idempotence, réversibilité, jumelle,
   fiche non publiée, échec de republication, retrait des vitrines (§ Effets de bord).

2. **✅ Le flux entrant, via la déduplication — et c'est le hameçon élégant.** Quand un
   festival est annulé, la presse écrit « Festival X annulé » : cet article partage ses
   mots avec la fiche du festival, donc `dedupe` les apparie — et aurait FUSIONNÉ, la
   dépêche d'annulation devenant matière de la fiche (le mécanisme WP#6798, en pire).
   Implémenté le 2026-08-05 : quand le TITRE entrant porte un marqueur d'annulation
   (`config/annulation_keywords.txt` — annulé, annulation, report(é), annullato,
   rinviato, cancelled, postponed…), `dedupe._porte_annulation` bloque la fusion et
   alerte sur Slack une fois. Zéro bandeau posé automatiquement. `scripts.
   audit_annulations` recompte ce qui reste EN ATTENTE à chaque passage hebdomadaire, et
   `--resolu <id>` clôt une suspicion vérifiée à la main. Vérifié dans crontab.txt : le
   dedupe quotidien tourne SANS `--rescan`, donc la plupart des suspicions naissent
   AVANT publication (deux fiches encore `pending`) — la porte s'applique quel que soit
   le statut du gagnant, pas seulement le cas d'une fiche déjà en ligne. Fixture :
   `tests/test_annulation.py`, les deux scénarios (avant/après publication).

3. **✅ La page source** — quand `dates.py`/`venues.py` relisent une page en mode web, un
   marqueur d'annulation dans le texte pose le même signal. Second filet, même bac.
   Implémenté le 2026-08-05, en s'appuyant fidèlement sur le canal 2 : `dates.py` capture
   le texte réellement téléchargé au fil de ses deux relectures de page —
   `fetch_event_dates` (passe JSON-LD/`<time>`) et `fetch_page_text` (passe LLM) —
   `venues.py` fait de même via `fetch_event_venue` (passe JSON-LD `location`) et le
   même `fetch_page_text`. Les deux modules appellent alors la fonction PARTAGÉE
   `scripts.dates.signale_annulation_page(conn, fiche, texte, regex)` : si
   `utils.annulation.marqueur_annulation` trouve un marqueur dans ce texte, elle pose la
   suspicion sur les MÊMES colonnes que le canal 2
   (`scripts.dedupe.ensure_annulation_columns`, appelée en tête de `main()` des deux
   scripts — aucun schéma parallèle) et alerte sur Slack une fois.

   Différence avec le canal 2 : là-bas, la fiche VISÉE (le festival) et la fiche qui
   PORTE le marqueur (l'article d'annulation) sont deux fiches distinctes. Ici c'est LA
   MÊME fiche — sa propre page dit qu'elle est annulée. `annulation_fiche_visee_id`
   pointe donc vers SON PROPRE id, et `annulation_visee_etait_publiee` capture son
   propre `wp_post_id_as` au moment du signal. Conséquence directe : `scripts.
   audit_annulations` fonctionne SANS AUCUNE MODIFICATION pour ce canal — sa requête
   relit la fiche visée par id, qu'elle soit une autre fiche (canal 2) ou elle-même
   (canal 3), et ses deux rouvreurs (auto si elle était publiée et ne l'est plus, manuel
   sinon via `--resolu`) s'appliquent identiquement. Vérifié par fixture, pas supposé.

   NE BLOQUE RIEN D'AUTRE : la détection est un AJOUT après une relecture de page qui a
   de toute façon eu lieu pour dater/situer l'événement — la date/le lieu continuent
   d'être extraits et écrits normalement, marqueur trouvé ou non. Le texte cherché est
   débarrassé de `<script>`/`<style>`/`<noscript>` (`scripts.dates._sans_script`) avant
   la recherche du marqueur : un mot comme « report » traîne facilement dans un
   identifiant d'analytics ou un bandeau cookies, et l'y chercher aurait fabriqué de
   fausses alertes sans rapport avec l'événement. Pas de spam : une fois
   `annulation_detectee_at` posé, silence — et en pratique une fiche déjà datée/située
   n'est de toute façon plus jamais resélectionnée pour une nouvelle relecture de page
   (elle ne redevient éligible qu'au réarmement automatique après cooldown — dates.py/
   venues.py, `DATE_COOLDOWN_DAYS`/`VENUE_COOLDOWN_DAYS`), donc la page n'est pas
   re-téléchargée avant longtemps. Fixture : `tests/test_annulation_canal3.py`, sections
   A (dates.py) et B (venues.py).

**✅ Tranché le 2026-08-05 :** alerte seulement — afficher « annulé ? » sur la foi d'un
titre de presse serait pire que le retard.

## Côté WordPress

**✅ Tranché le 2026-08-05, en implémentant le canal 1 : préfixe de titre, pas la
fonctionnalité native.** The Events Calendar gère nativement un statut d'événement
« annulé / reporté » avec bandeau (fonction *Event Status*) — vérifié dans le CODE de ce
dépôt (`deploy/wordpress/cs-publish.php` et l'ensemble des mu-plugins PHP) : AUCUNE trace
d'utilisation, ni meta `_EventCancelled` posée, ni lue. Mais ce n'est pas une preuve
d'ABSENCE côté plugin — sa disponibilité dépend de la version/édition de The Events
Calendar installée en PRODUCTION, invérifiable depuis ce dépôt. Écrire du code qui pose ce
statut sans savoir si l'admin WordPress sait l'afficher aurait été un pari : soit un
bandeau invisible (le statut posé, rien à l'écran), soit une erreur REST silencieuse selon
que le champ existe ou non pour ce type de post.

Repli retenu : un préfixe de titre — « ANNULÉ — » (FR) / « ANNULLATO — » (IT) — posé en
base ET republié. Il ne dépend d'AUCUNE fonctionnalité de plugin, se lit partout (listes,
archives, fil RSS, partages sociaux, résultats Google) sans une ligne de CSS, et reste
100 % réversible (`/action/<id>/annuler_off` retire le préfixe et republie — cf. canal 1
ci-dessus). Le jour où la disponibilité d'*Event Status* sur l'installation PROD est
confirmée, le bandeau natif peut s'AJOUTER par-dessus (meilleur rendu visuel) sans rien
retirer : les deux ne s'excluent pas, et le préfixe reste le filet qui marche partout.

## Les quatre questions, répondues d'avance

- **Qui rouvre ?** Une annulation confirmée est un fait, pas un état à rouvrir — mais un
  report l'est : la fiche reportée sans date reste dans une file visible (« reportés sans
  nouvelle date : N » au digest), et `dates.py` la re-date normalement quand la nouvelle
  date paraît. Le canal 1 échappe quand même à la question « qui rouvre » posée par
  CLAUDE.md pour tout état terminal : ce n'est PAS un état terminal, puisque
  `/action/<id>/annuler_off` défait exactement ce que pose `/action/<id>/annuler` — un
  clic pour corriger une erreur (fausse annulation, mauvaise fiche cliquée), sans attendre
  qu'un script y repasse.
- **À quelle condition ?** L'arrivée d'une nouvelle date, ou la date prévue passée
  (archivage normal).
- **Où se voit le compte ?** Pour les canaux 2 et 3 (✅ faits, mêmes colonnes) :
  `scripts.audit_annulations`, branché en lecture seule dans `weekly_audits`, recompte
  les deux sans distinction de canal. **✅ Pour le canal 1, ajouté le 2026-08-05** :
  `scripts.weekly_audits._annules_encore_affiches` compte les fiches `annule_le` posé
  ET encore en ligne (`wp_post_id_as`), filtrées sur « devant nous » (règle 5 —
  récurrent, sans date, ou pas encore passées) ; ligne « Annulés encore affichés »
  dans le digest du lundi. **⚖️ Reste à faire, PAS ENCORE DE MÉCANISME** : « reportés
  sans nouvelle date ». Un report (rinviato) n'est aujourd'hui pas distingué d'une
  annulation confirmée — les canaux 2/3 les détectent avec le MÊME marqueur
  (config/annulation_keywords.txt mélange « annulé » et « reporté ») et le canal 1 n'a
  qu'un bouton « annuler », pas de geste « reporter » séparé qui viderait la date. Une
  vraie distinction suppose une décision de conception (un second bouton ? vider
  `date_event_start` au clic ?) qui n'a pas été prise — proposé, pas construit.
- **Le rouvreur est-il branché ?** `dates.py` tourne déjà chaque matin — rien de neuf à
  brancher, c'est le critère qui a fait préférer cette conception.

## Effets de bord — traités le 2026-08-05 en implémentant le canal 1

- **✅ `deplacement_now` → None pour un annulé** (il ne vaut plus aucun déplacement) —
  et `deplacement_etat` avec lui (même garde, en tête des deux fonctions,
  `utils/deplacement.py`), pour que l'affichage back-office et le tri qui alimente
  `as_deplacement_now` (poussé au republish par `publisher_as.py`) ne divergent jamais ;
  le motif « annulé — retiré des vitrines » se lit directement dans `/preview`.
- **✅ exclusion du SEO** (ne pas « optimiser » une annulation) — `scripts/seo_batch.py`
  filtre désormais `annule_le IS NULL` dans sa sélection quotidienne. Pas d'exclusion
  symétrique côté « sections vitrines » du site : c'est `as_deplacement_now` vide
  (ci-dessus) qui en tient déjà lieu, la home ne lit que cette clé de tri.
- **✅ la traduction jumelle hérite du statut** (les deux langues annulent ensemble) —
  `/action/<id>/annuler` retrouve la jumelle via `translation_of` (dans les deux sens) et
  lui applique le même geste, avec SON préfixe de langue.
- **✅ vérifié, aucun changement nécessaire : `site_audit` et le bandeau « annulé ».**
  `scripts/batch_report._partagent_un_mot` (utilisé par `scripts/site_audit.py`) compare
  le titre EN LIGNE au titre VOULU par recoupement de MOTS, pas par égalité stricte : un
  titre « ANNULÉ — Festival X » partage tous les mots significatifs de « Festival X » sauf
  le préfixe lui-même, donc le contrôle passe déjà sans faux positif. Vérifié en lisant le
  code, pas supposé — aucune ligne touchée dans `site_audit.py`/`batch_report.py`.
