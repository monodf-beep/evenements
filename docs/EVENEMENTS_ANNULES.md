# Événements annulés et reportés — proposition

**Proposition du 2026-08-04, RIEN N'EST IMPLÉMENTÉ.** Question de Franck : « comment
gérer les événements annulés ? » Vérifié dans le code le jour même : le mot « annulé »
n'apparaît NULLE PART — ni détection, ni statut, ni affichage. Aujourd'hui, un événement
annulé reste en ligne comme si de rien n'était jusqu'à ce que sa date passe.

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

2. **Le flux entrant, via la déduplication — et c'est le hameçon élégant.** Quand un
   festival est annulé, la presse écrit « Festival X annulé » : cet article partage ses
   mots avec la fiche du festival, donc `dedupe` va les apparier — et aujourd'hui il les
   FUSIONNERAIT, la dépêche d'annulation devenant matière de la fiche (le mécanisme
   WP#6798, en pire). La proposition retourne le piège : quand le titre entrant porte un
   marqueur d'annulation (`annulé`, `annulation`, `annullato`, `cancellato`, `rinviato`,
   `reporté`, `postponed`), dedupe NE fusionne PAS — il pose un SIGNAL sur la fiche
   appariée (« annulation suspectée, source : <url> ») et alerte. Un humain confirme d'un
   clic. La détection est gratuite : elle réutilise l'appariement qui existe déjà.

3. **La page source** — quand `dates.py`/`venues.py` relisent une page en mode web, un
   marqueur d'annulation dans le texte pose le même signal. Second filet, même bac.

⚖️ Le signal déclenche-t-il une alerte simple, ou une mise en « suspicion » visible sur
la fiche publiée ? Proposition : alerte seulement — afficher « annulé ? » sur la foi d'un
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
- **Où se voit le compte ?** Digest du lundi : annulés encore affichés, reportés sans
  date.
- **Le rouvreur est-il branché ?** `dates.py` tourne déjà chaque matin — rien de neuf à
  brancher, c'est le critère qui a fait préférer cette conception.

## Effets de bord à traiter le jour de l'implémentation

- `deplacement_now` → None pour un annulé (il ne vaut plus aucun déplacement) ;
- exclusion des sections vitrines et du SEO (ne pas « optimiser » une annulation) ;
- la traduction jumelle hérite du statut (les deux langues annulent ensemble) ;
- `site_audit` doit savoir qu'un bandeau « annulé » est CONFORME, pas une anomalie de
  titre.
