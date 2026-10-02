# Curiosités — dossier de relecture du 16/09/2026 (sources, corrections, SEO du corps)

**D'où ça vient.** Franck, 16/09 : « il y a des choses dans les articles qu'il semble devoir
être modifié niveau SEO non ? ». Oui — et en cherchant les sources officielles à lier (règle
1 de `docs/CURIOSITES.md` : une source officielle par curiosité), la lecture des pages
sources a **contredit plusieurs faits publiés le 06/09**. Ce dossier liste, article par
article : les liens à poser, les faits à corriger (avec la citation de la source), les faits
sans source officielle (à trancher par Franck : sourcer ou retrancher), et la phrase
d'introduction qui porte l'expression clé exacte (densité Yoast).

**Ce qui est déjà fait (16/09, réversible, marqueurs `cs_cle_auto` / `cs_texte_auto`) :**
expression clé, titre SEO et méta-description sur les dix articles —
`deploy/wordpress/seo-articles-curiosites.php`. Recompté : 0 article sans clé, 0 sans
description.

**Appliqué le 16/09 au soir, sur « ok je te fais confiance »** — `deploy/wordpress/curiosites-corps-2026-09-16.php`,
73 remplacements ancrés sur les dix corps, relus en base après écriture : clé exacte dans les
dix introductions, 5 à 8 liens externes par article, zéro Wikipédia, zéro tiret cadratin,
zéro forme interdite, trois slugs italiens renommés (`curiosita-torino`, `curiosita-aosta`,
`curiosita-nizza`), une révision WordPress gardée par article.

Arbitrages pris au passage, en lisant les pages (voir ci-dessous pour le détail) :
la « partie manquante retrouvée en 2014 » de la fontaine des Éléphants est RETIRÉE
(Chambéry Montagnes : sculptés de face, jamais eu d'arrière-train) ; Sevesi 1810 et
Sciolli 1885 retirés (non portés) ; l'affaire de bigamie de Crispi GARDÉE et sourcée par
l'entrée Crispi de Treccani (mariage civil du 27 janvier 1878, démission) ; « dès le
treizième siècle » retiré de la socca ; « en zone frontalière » réécrit « dans la basse
vallée » (vocabulaire). Deux liens restent HORS liste admise, et c'est dit : la Revue de
géographie alpine (Frichelet) et l'Academia Nissarda (porte de Turin).

**Méthode.** Chaque source ci-dessous a été LUE (page ouverte, phrase citée), pas déduite
d'un résumé de recherche. Quand la page officielle ne dit pas ce que l'article affirme, c'est
écrit « non porté par la source » — ce n'est pas la même chose que « faux », et c'est à
Franck de trancher : trouver une autre source officielle, ou retrancher.

---

## Turin — 8227 (FR) · 8228 (IT)

**Liens.** La version française porte déjà six liens officiels (MuseoTorino ×4, musée du
Risorgimento, cultura.gov.it). La version italienne n'en a **aucun** : poser les mêmes six,
aux mêmes phrases (Piazza San Carlo, Porta Palatina, fetta di polenta, Mole Antonelliana,
Palazzo Carignano, Villaggio Leumann).

**Faits.** Rien à corriger : les six sont sourcés dans la version française.

**Phrase d'intro (clé exacte).** Remplacer la dernière phrase du premier paragraphe :
- FR : « Six curiosités de Turin à regarder avant d'aller voir ce qui s'y joue cette semaine. »
- IT : « Sei curiosità di Torino da guardare prima di scoprire cosa succede in città questa settimana. »

**Slug IT.** `curiosita-turin` → `curiosita-torino` (la clé dit Torino ; WordPress redirige
tout seul l'ancienne adresse ; zéro impression Search Console à ce jour).

---

## Chambéry — 8229 (FR) · 8230 (IT)

**Liens.** La version italienne a quatre liens, dont **deux Wikipédia** (fontaine, cathédrale)
— hors liste des sources admises. La française n'en a aucun. Poser dans les deux :
- fontaine des Éléphants → notice Mérimée https://pop.culture.gouv.fr/notice/merimee/PA00118233
  ou Chambéry Montagnes https://www.chamberymontagnes.com/en/fiche/elephants-fountain/
- grand carillon → https://www.chamberymontagnes.com/fiche/grand-carillon/ (déjà en IT)
- cathédrale, trompe-l'œil → https://www.chamberymontagnes.com/en/fiche/st-francis-de-sales-cathedral/
- les Charmettes → https://www.chambery.fr/302-les-charmettes.htm (déjà en IT)

**Faits non portés par les sources lues.**
- « environ six mille mètres carrés » de trompe-l'œil : Chambéry Montagnes dit « le plus
  vaste décor peint d'Europe », réalisé en 1834 par Casimir Vicario, **sans chiffre**. La notice
  Mérimée de la cathédrale (PA00118223) ne détaille ni surface ni peintres. Garder le chiffre =
  trouver la source qui le porte.
- Sevesi 1810 et Sciolli 1885 : mêmes sources, non mentionnés.
- restauration de la fontaine en 2014 et « partie manquante retrouvée » : non porté par les
  pages officielles ouvertes.

**Phrase d'intro (clé exacte).**
- FR : « Cinq curiosités de Chambéry à regarder avant d'aller voir ce qui se passe en ville cette semaine. »
- IT : « Cinque curiosità di Chambéry da guardare prima di scoprire cosa succede in città questa settimana. »

---

## Aoste — 8231 (FR) · 8232 (IT)

**Liens** (aucun aujourd'hui, dans les deux langues) :
- titsch / töitschu, école → https://www.lovevda.it/it/banca-dati/10/tradizioni/gressoney-la-trinite/il-titsch-il-dialetto-tedesco-di-gressoney/447
- Conseil des Commis 1536, neutralité 1537, 1560 → https://www.consiglio.vda.it/fr/storia/brevi-cenni-storici
  (**confirme** : institué le 7 mars 1536, traité de neutralité avec la France l'année suivante,
  renouvelé 1538, 1542, 1552, 1556 ; 1560, tous les pouvoirs au Conseil)
- Castel Savoia → https://www.lovevda.it/it/banca-dati/8/castelli-e-torri/gressoney-saint-jean/castel-savoia/873
- Arc d'Auguste, toit 1716 → https://www.regione.vda.it/cultura/patrimonio/siti_archeologici/augusta_praetoria/arco/approfondimenti_i.aspx
  (**confirme** : « Nel 1716 il Conseil des Commis decise di preservare il monumento dalle
  infiltrazioni d'acqua ricoprendolo con un tetto d'ardesia »)
- cryptoportique → https://www.comune.aosta.it/it/page/criptoportico-forense
- Porta Praetoria → https://www.lovevda.it/it/banca-dati/8/architettura-romana/aosta/porta-praetoria/730

**Faits À CORRIGER (source lue, citation).**
1. « Le roi Umberto Ier pose lui-même la première pierre en 1899 […] il meurt assassiné la
   même année. » — lovevda : « posa della prima pietra […] il 24 agosto 1899 alla presenza di
   re Umberto I, il quale, **assassinato a Monza un anno dopo**, non avrebbe visto la
   conclusione dei lavori ». → assassiné en **1900**, pas 1899. (Idem en italien.)
2. « un toit de tuiles d'ardoise depuis 1716 seulement, ajouté **trois siècles** après sa
   construction » — l'arc est augustéen (Augusta Praetoria, 25 av. J.-C.) : 1716, c'est
   **dix-sept siècles** plus tard. (Idem en italien.)
3. « la Porta Praetoria […] garde ses **deux** arches jumelles presque intactes, l'une pour
   les piétons, l'autre pour les chars » — lovevda : « Era dotata di **tre aperture**, ancor
   oggi visibili: quella centrale per i carri e quelle laterali per i pedoni ». → trois
   ouvertures, la centrale pour les chars, les deux latérales pour les piétons. (Idem IT.)

**Non porté par la source lue.** Le cryptoportique « parmi les rares vestiges de ce type
encore visitables en Europe, aux côtés d'Arles, de Reims et de Bavay » : la page de la
Commune décrit le monument sans cette comparaison.

**Phrase d'intro (clé exacte).**
- FR : « Six curiosités d'Aoste à comprendre avant d'aller voir ce qui s'y passe cette semaine. »
- IT : « Sei curiosità di Aosta da capire prima di scoprire cosa succede in città questa settimana. »

**Slug IT.** `curiosita-aoste` → `curiosita-aosta`.

---

## Annecy — 8233 (FR) · 8234 (IT)

**Liens** (aucun aujourd'hui, dans les deux langues) :
- Rosalie Montmasson → https://www.treccani.it/enciclopedia/rosalie-montmasson_(Dizionario-Biografico)/
- Amédée VIII / Félix V → https://www.treccani.it/enciclopedia/antipapa-felice-v_(Enciclopedia-dei-Papi)/
- François de Sales, Visitation → https://www.diocese-annecy.fr/le-diocese/les-saint-e-s-et-les-grandes-figures/saint-francois-de-sales/biographie-saint-francois-de-sales
  (l'institution elle-même ; confirme évêque ordonné le 8 décembre 1602, Visitation fondée
  à Annecy le 6 juin 1610)
- de Launay → https://www.treccani.it/enciclopedia/gabriele-de-launay_(Dizionario-Biografico)/
  (confirme : né à Duingt en 1786, vice-roi de Sardaigne 1843-1848, président du Conseil
  après Novare, cède la place à d'Azeglio le 7 mai 1849)
- Sommeiller → https://www.treccani.it/enciclopedia/germain-sommeiller/
  (confirme : Saint-Jeoire, tunnel du Fréjus/Mont-Cenis, moins de 13 ans de travaux,
  inauguré le 17 septembre 1871)
- chocolaterie des Marquisats → https://musees.annecy.fr/Patrimoines/Decouvrez-nos-patrimoines/Annecy/L-ancienne-Chocolaterie-des-Marquisats
  (confirme 1896 Maxime-Antoine Ruphy, cession 1905 à Charles Ruphy, arrêt pendant la
  guerre, fermeture 1953, terrains à la Ville 1954, démolition 1971)

**Faits À CORRIGER (Treccani, lu).** Rosalie Montmasson :
1. « Blanchisseuse » → Treccani : **stiratrice** (repasseuse), à Turin à partir de 1849.
2. « Elle épouse **ensuite** Francesco Crispi » (après 1860) → mariage le **27 décembre
   1854**, à La Valette, six ans AVANT les Mille. L'ordre est inversé.
3. « Rosalie meurt **pauvre** à Rome en 1904 » → Treccani : morte à Rome le 10 novembre 1904,
   après une rente puis un subside de la Maison royale et du gouvernement. « Pauvre » n'est
   pas porté.
4. « tentera […] de faire annuler ce mariage pour épouser une autre femme, un scandale » →
   l'entrée Treccani lue parle d'une **séparation consensuelle** négociée en 1875. L'affaire
   de bigamie de 1878 existe dans l'histoire de Crispi, mais la phrase doit s'appuyer sur une
   source qui la porte (l'entrée Crispi du même dictionnaire, à lire).
5. Félix V « élu en 1440 » → Treccani : élu le **5 novembre 1439** par le concile de Bâle,
   accepte début 1440 (renonce au duché le 6 janvier 1440). Écrire 1439.

**Sans source officielle trouvée.** Marguerite Frichelet-Avet : annecy.fr, musees.annecy.fr,
archives.hautesavoie.fr ne la mentionnent pas dans ce que la recherche remonte. Existe : un
article de la *Revue de géographie alpine* (OpenEdition, revue à comité de lecture) :
https://journals.openedition.org/rga/3229 — pas dans la liste admise, mais universitaire.
Ce qu'il confirme : servante lettrée de Thônes, ravitaille les insurgés, accusée d'avoir
sonné le tocsin, fusillée le 18 mai 1793 au Champ-de-Mars (le Pâquier). **Non porté** :
« soigne les blessés », et l'emprisonnement au palais de l'Île. Décision : sourcer par la RGA
et retirer « soigne les blessés », ou retrancher la curiosité (le titre passerait à « Six »).

**Détail.** « Rebaptisée Chocolaterie d'Annecy en 1907 » : la page des musées donne la
cession de 1905, pas l'année du nouveau nom. « cinq sortes de fèves », « centaine
d'ouvriers », « grand prix de Lyon 1913 » : non lisibles sur la page ouverte (contenu non
chargé par l'outil) — à vérifier sur place.

**Phrase d'intro (clé exacte).**
- FR : « Sept curiosités d'Annecy à regarder avant d'aller voir ce qui s'y joue cette semaine. »
- IT : « Sette curiosità di Annecy da guardare prima di scoprire cosa succede in città questa settimana. »

---

## Nice — 8235 (FR) · 8236 (IT)

**Liens** (aucun aujourd'hui, dans les deux langues) :
- siège de 1543, Catherine Ségurane → https://www.explorenicecotedazur.com/en/culture/stele-en-memoire-de-catherine-segurane/
  et https://www.nice.fr/agenda/heroique-catherine-segurane-figure-legendaire-de-nice/
- socca → https://www.explorenicecotedazur.com/en/explore/art-of-living/gastronomy-and-local-produce/nicoise-recipes/la-socca/
  (confirme l'origine ligure, farine de pois chiches)
- pissaladière → https://www.explorenicecotedazur.com/en/explore/art-of-living/gastronomy-and-local-produce/nicoise-recipes/la-pissaladiere/
- Consiglio d'Ornato → le PDF de la Ville « Le consiglio d'Ornato, créateur d'une Nice
  moderne » répond **404** aujourd'hui ; repli : le dossier des Archives départementales
  https://www.departement06.fr/documents/Import/decouvrir-les-am/rr158-ornato.pdf
  (confirme 1832, Charles-Albert, approbation des façades, modèle turinois)

**Faits non portés, ou contredits.**
1. « Nice célèbre depuis la **fin du seizième siècle**, par un premier monument » — les pages
   de la Ville et de l'Office : la figure apparaît sous la plume d'Honoré Pastorelli au **début
   du dix-septième siècle** ; la stèle de la rue Sincaire date de **1923**. Réécrire.
2. « La pissaladière descend de la pissa d'Andrea, **créée en 1490** en l'honneur de l'amiral
   génois Andrea Doria » — la Ville (cantines.nice.fr) : la *piscialandrea* est nommée
   d'après Doria ; l'Office : « pourrait être l'héritage d'une recette génoise, d'Imperia,
   fin du XVe siècle », premières traces écrites au XIXe. « Créée en 1490 » est trop précis
   pour ce que disent les sources.
3. « la porte de Turin, copiée sur une porte dessinée **un siècle et demi plus tôt par
   Filippo Juvarra** » — impossible : Juvarra (1678-1736) est actif à Turin à partir de 1714 ;
   un siècle et demi avant 1782, c'est 1632. La porte de Turin (1782, Bonvicini, démolie 1848)
   est attestée (Inventaire général, pss-archi, Academia Nissarda) ; c'est l'attribution du
   modèle qu'il faut refaire, ou retirer.

**Phrase d'intro (clé exacte).**
- FR : « Trois curiosités de Nice à comprendre avant d'aller voir ce qui s'y joue cette semaine. »
- IT : « Tre curiosità di Nizza da capire prima di scoprire cosa succede in città questa settimana. »

**Slug IT.** `curiosita-nice` → `curiosita-nizza`.

---

## Ce que ce dossier ne propose PAS

- **Un H2 portant la clé** (point Yoast « sous-titre ») : les H2 sont des titres éditoriaux,
  dans la voix ; en coller un « Curiosités de Turin » ferait un chapitre artificiel. Point
  laissé orange sciemment.
- **Une image dans le corps** : la vignette existe sur les dix, avec un alt ; Yoast ne regarde
  que le corps. Décision d'illustration, pas de SEO.
- **Les mots de transition** de la lisibilité Yoast : la voix interdit les connecteurs
  scolaires. Point laissé rouge sciemment.

## Après relecture

Une fois les décisions prises (corriger / sourcer / retrancher), les dix corps sont réécrits
en session, contrôlés (`utils.vocabulaire.trouver`, tirets, contamination FR/IT, clé exacte
dans l'intro), et mis à jour par Novamira — WordPress garde une révision de chaque version,
donc le geste se défait.
