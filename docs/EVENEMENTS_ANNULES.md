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
`scripts/venues.py`) ci-dessous. Le canal 1 (bouton back-office) et l'affichage lui-même
(bandeau côté WordPress) restent à faire — ⚖️ ci-dessous.

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

1. **Le bouton du back-office** — le canal sûr : Franck apprend l'annulation, un clic la
   propage (base + republication + retrait des vitrines). À construire en premier : sans
   lui, les canaux automatiques n'auraient nulle part où déposer leur trouvaille.

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

The Events Calendar gère nativement un statut d'événement « annulé / reporté » avec
bandeau (fonction *Event Status*) — **à vérifier sur l'installation** avant d'écrire quoi
que ce soit : si `cs-publish.php` peut poser ce statut, l'affichage est réglé sans une
ligne de gabarit. Sinon, un préfixe de titre « ANNULÉ — » est le repli rustique mais
lisible partout (listes, partages, Google).

## Les quatre questions, répondues d'avance

- **Qui rouvre ?** Une annulation confirmée est un fait, pas un état à rouvrir — mais un
  report l'est : la fiche reportée sans date reste dans une file visible (« reportés sans
  nouvelle date : N » au digest), et `dates.py` la re-date normalement quand la nouvelle
  date paraît.
- **À quelle condition ?** L'arrivée d'une nouvelle date, ou la date prévue passée
  (archivage normal).
- **Où se voit le compte ?** Pour les canaux 2 et 3 (✅ faits, mêmes colonnes) :
  `scripts.audit_annulations`, branché en lecture seule dans `weekly_audits`, recompte
  les deux sans distinction de canal. Pour l'affichage lui-même (à faire) :
  digest du lundi, annulés encore affichés + reportés sans date.
- **Le rouvreur est-il branché ?** `dates.py` tourne déjà chaque matin — rien de neuf à
  brancher, c'est le critère qui a fait préférer cette conception.

## Effets de bord à traiter le jour de l'implémentation

- `deplacement_now` → None pour un annulé (il ne vaut plus aucun déplacement) ;
- exclusion des sections vitrines et du SEO (ne pas « optimiser » une annulation) ;
- la traduction jumelle hérite du statut (les deux langues annulent ensemble) ;
- `site_audit` doit savoir qu'un bandeau « annulé » est CONFORME, pas une anomalie de
  titre.
