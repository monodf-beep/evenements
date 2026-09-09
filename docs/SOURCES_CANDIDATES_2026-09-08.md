# Sources candidates — Comté de Nice et Vallée d'Aoste (2026-09-08)

**Pourquoi.** Mesuré le 08/09 en base de production, sur trente jours : le Comté de Nice a
fourni 12 fiches approuvées (82 rejetées, surtout hors périmètre — arrondissement de Grasse)
et la Vallée d'Aoste 13, contre 132 au Piémont. Franck : « il faut aller chercher davantage
de flux RSS ou newsletters », et « éviter les doublons ».

**Ce que ce document est.** Une liste de flux et de newsletters **testés ce soir depuis ce
conteneur** (pas depuis le VPS), avec pour chacun ce que le téléchargement a montré. Rien
n'a été ajouté à `config/sources.txt` ni à `config/newsletters.txt` : Franck décide de
chaque ligne. Les lignes prêtes à coller sont en § 4.

**Comment lire les nombres.** Pour chaque flux téléchargé : `items` = nombre d'entrées dans
le flux tel que servi ; `dernier` = date de l'entrée la plus récente ; `30 j` / `90 j` =
entrées dont la date est dans les 30 / 90 jours précédant le 08/09/2026. La date lue est
`pubDate` (RSS) ou `updated` (Atom) — c'est la date de **publication** de la brève, sauf
pour trois flux qui y mettent la **date de l'événement** (Forte di Bard, Cap-d'Ail,
Musée des Beaux-Arts pour partie) ; c'est dit dans la colonne. La « part d'événements »
est une lecture des huit derniers titres, pas un comptage exhaustif.

**Séance interrompue.** Franck a demandé de conclure ; la mesure de la part de communes de
l'arrondissement de Nice dans le flux du Département (§ 2.1) a été coupée par une panne du
proxy réseau en cours d'exécution et **n'est pas disponible**. Tout ce qui n'a pas été
téléchargé est en § 5 « non vérifié », jamais dans les tableaux.

---

## 1. Constat préalable — le hors-périmètre vient d'abord de `config/sources.txt`

Avant de chercher de nouvelles sources, une lecture du fichier actuel : la section Nice
collecte encore **dix flux dont l'émetteur est dans l'arrondissement de Grasse**, hors
périmètre depuis l'arbitrage du 2026-08-02 (confirmé le 11/08 dans
`config/communes_comte_de_nice.json`) :

| Ligne active dans `sources.txt` | Commune | Arrondissement |
|---|---|---|
| `https://www.grasse.fr/feed/` — Ville de Grasse | Grasse | Grasse |
| `https://www.ville-grasse.fr/feed/` — Ville de Grasse (doublon du précédent) | Grasse | Grasse |
| `https://www.theatredegrasse.com/feed/` — Théâtre de Grasse | Grasse | Grasse |
| `https://scene55.fr/feed/` — Scène 55 | Mougins | Grasse |
| `https://mougins.fr/category/agenda/feed/` — Ville de Mougins | Mougins | Grasse |
| `https://vence-tourisme.com/feed/` — OT de Vence | Vence | Grasse |
| `https://www.nuitsdusud.com/feed/` — Nuits du Sud | Vence | Grasse |
| `https://www.ville-valbonne.fr/feed/` — Ville de Valbonne | Valbonne | Grasse |
| `https://www.fondation-maeght.com/feed/` — Fondation Maeght | Saint-Paul-de-Vence | Grasse |
| `https://jazzajuan.com/feed/` — Jazz à Juan | Antibes | Grasse |

Chaque item de ces flux entre en base, est évalué, puis rejeté sur la `ville` par
`scripts/evaluator.py`. C'est très probablement là que naissent la plupart des 82 rejets du
mois — hypothèse, pas mesure : je n'ai pas la base ici. **Les commenter** (comme l'ont été
les lignes radar le 05/08) ferait baisser le rejet sans rien coûter. Décision de Franck.

À noter aussi : `https://seances-speciales.fr/feed/` (Les Écrans du Sud) couvre toute la
région PACA sans être dans `config/broad_sources.txt` ; à vérifier séparément, hors de
cette mission.

---

## 2. Comté de Nice — flux téléchargés et lus

Périmètre : arrondissement de Nice uniquement (101 communes de
`config/communes_comte_de_nice.json`). Tout ce qui suit est dans ce périmètre, sauf les deux
sources « larges » signalées.

### 2.1 Candidats retenus

| Institution | URL du flux (téléchargée le 08/09) | Dernier item | Volume | Part d'événements (8 derniers titres) | Tier proposé | Risque de doublon avec |
|---|---|---|---|---|---|---|
| **Ville de Nice — agenda « conférences »** | `https://www.nice.fr/agenda/type/conference/feed/` | 2026-09-07 | 24 items ; **15 / 30 j**, 22 / 90 j | 8/8 (conférences des bibliothèques, musées, Centre du patrimoine) | institution | `nice.fr/feed/` (×2 déjà en base : actus municipales, 0 item / 30 j) — même domaine, flux différent, URL d'items différentes → pas de doublon d'entrée |
| **Ville de Nice — agenda « concerts »** | `https://www.nice.fr/agenda/type/concert/feed/` | 2026-08-14 | 24 items ; 4 / 30 j, 17 / 90 j | 8/8 | institution | idem |
| **Ville de Nice — agenda « expositions »** | `https://www.nice.fr/agenda/type/exposition/feed/` | 2026-09-08 | 24 items ; 3 / 30 j, 14 / 90 j | 8/8 (galeries municipales, archives, Butor) | institution | idem ; recoupe partiellement MAMAC/Matisse déjà en base (les expos des musées y sont annoncées aussi) |
| **Ville de Nice — agenda « spectacles »** | `https://www.nice.fr/agenda/type/spectacle/feed/` | 2026-08-14 | 24 items ; 18 / 30 j, 19 / 90 j | 8/8, mais **7 des 8 sont le même spectacle** (une entrée par date) : le volume réel est ~3 spectacles distincts | institution | idem ; la dédup par titre devra absorber les répétitions |
| **Musée des Beaux-Arts Jules Chéret (Nice)** — agenda | `https://www.musee-beaux-arts-nice.org/agenda/feed/` | 2026-08-26 | 10 items ; 5 / 30 j, 9 / 90 j | 8/8 (JEP, visites-dégustations) ; entrées **en double** (une par date) | officielle ; lieu = Musée des Beaux-Arts Jules Chéret ; Nice | aucun (Matisse et MAMAC sont en base, pas Chéret). NB : `/feed/` racine est vide, c'est bien `/agenda/feed/` |
| **Musée d'Archéologie de Nice-Cimiez** | `https://www.musee-archeologie-nice.org/feed/` | 2026-08-31 | 10 items ; 1 / 30 j, 3 / 90 j | 7/8 (JEP, Festival de tragédies, cycle de conférences, Nuit des musées) | officielle ; lieu = Musée d'Archéologie de Nice-Cimiez ; Nice | aucun. NB : `/agenda/feed/` est vide ici, c'est la racine qui porte les événements |
| **Ville de Menton** (SPIP) | `https://www.menton.fr/spip.php?page=backend` | 2026-09-08 | 10 items ; **10 / 30 j** | 3/8 (Fête patronale Saint-Michel, JEP, Coupe du monde d'eFoil ; le reste = rentrée scolaire, travaux) | institution ; ville = Menton | newsletter « Menton, Riviera & Merveilles » (OT, statut *attente*) — autre émetteur, mêmes grands événements (Fête du Citron, Festival de musique). Risque modéré, la dédup par titre s'en charge |
| **Musée Jean Cocteau — le Bastion (Menton)** (SPIP) | `https://www.museecocteaumenton.fr/spip.php?page=backend` | 2026-07-22 | 10 items ; 0 / 30 j, 7 / 90 j | 7/8 (une exposition annoncée sous cinq titres successifs ; « Le secret d'Honorine ») | officielle ; lieu = Musée Jean Cocteau - le Bastion ; Menton | aucun ; recoupe Ville de Menton ci-dessus sur les mêmes expos |
| **Ville de Cap-d'Ail — événements** | `https://www.cap-dail.fr/events/feed/` | 2027-04-23 (**date de l'événement**, pas de publication) | 8 items, tous à venir (oct. 2026 → avr. 2027) | 8/8 (concerts, humour, spectacle jeune public — saison du Château des Terrasses) | institution ; ville = Cap-d'Ail | aucun |
| **Ville de La Turbie** | `https://www.ville-la-turbie.fr/feed/` | 2026-09-08 | 10 items ; 10 / 30 j | 3/8 (Fête patronale ×2, Forum des associations ; le reste = arrêtés de circulation) | institution ; ville = La Turbie | aucun |
| **Département des Alpes-Maritimes — agenda** ⚠️ source LARGE | `https://www.departement06.fr/agenda.xml` | 2026-09-08 | **3 154 items** (archive complète depuis 2020) ; 11 / 30 j, **462 / 90 j** (dates de publication) | 8/8 événements — mais **tout le département** : Régates royales de Cannes, championnats de voile… La part arrondissement de Nice n'a pas pu être mesurée (panne proxy) | institution | newsletter `departement06.fr` déjà *active* (Gmail) — **même émetteur, autre canal** : les mêmes événements arriveront deux fois, par deux entrées différentes. Et les musées départementaux (MAA, Merveilles à Tende, Mercury) n'ont pas de flux propre : ils passent par celui-ci |
| **Parc national du Mercantour** ⚠️ source LARGE (06 + Alpes-de-Haute-Provence) | `https://www.mercantour-parcnational.fr/fr/rss.xml` | 2026-09-05 | 10 items ; 10 / 30 j | 7/8 (sorties nature, ciné-débat gypaète, rencontre berger, week-end écotourisme) | institution | aucun ; les vallées du périmètre (Tinée, Vésubie, Roya) sont dans `config/perimeter_keywords.txt`, le filtre large les gardera et écartera la Bonette/Ubaye côté 04 |

**Trois précautions avant de coller `agenda.xml` du Département :**

1. `scripts/scraper_events.py` n'a **aucune coupure d'âge** : au premier passage il insérera
   les 3 154 items, dont ~2 700 événements terminés depuis des mois ou des années, que
   `dates.py`, `venues.py` et l'évaluation tenteront ensuite de compléter un par un (le
   scénario agendaculturel.fr du 04/08, en pire). Il faut soit une coupure sur `pubDate`
   dans le scraper (un paramètre, à écrire), soit un premier passage en dry-run qui marque
   les items anciens sans les traiter.
2. Le domaine doit entrer dans `config/broad_sources.txt` en même temps que la ligne,
   sinon Cannes, Antibes et Grasse reviennent par la grande porte.
3. Les items contiennent le **nom du lieu** (« Espace Laure Ecard ») mais pas toujours la
   commune ; le filtre positif sur le texte libre laissera passer des items sans commune
   nommée, à trier ensuite sur `ville`.

### 2.2 Téléchargés et écartés — Comté de Nice

| Source | URL testée | Ce que le téléchargement a montré | Pourquoi écarté |
|---|---|---|---|
| Ville de Nice — agenda racine | `https://www.nice.fr/agenda/feed/` | 24 items, dernier 14/08, 3 / 30 j (ateliers d'écriture, comités de lecture des bibliothèques) | plafonné à 24 entrées toutes catégories : les flux par type ci-dessus sont plus riches et se recoupent avec lui |
| Ville de Nice — « animations » | `https://www.nice.fr/agenda/type/animation/feed/` | 24 items, 12 / 30 j : aquabike, gym douce, pickleball, « Rentrée des seniors » | hors sujet (sport/loisirs municipaux, pas culture) |
| Ville de Nice — « visites guidées » | `https://www.nice.fr/agenda/type/visite-guidee/feed/` | 24 items, 0 / 30 j, 2 / 90 j ; Tour Bellanda répétée ×6 | dormant, redondant avec expositions/musées |
| Département 06 — actualités | `https://www.departement06.fr/actualites.xml` | 10 items, 10 / 30 j ; 2/8 événements (Quinzaine des Seniors, VTT Trial Valberg) | fil d'actu générale (santé, collèges), pas un agenda |
| Villa Arson (Nice) | `https://villa-arson.fr/feed/` | 10 items, dernier 11/08, 1 / 30 j, 7 / 90 j ; 2/8 événements (une expo), le reste = appels à candidatures, nécrologie | trop peu d'événements ; la newsletter (déjà *candidat* dans `newsletters.txt`) est le bon canal |
| Opéra de Nice — blog | `https://www.opera-nice.org/feed/` | 5 items, 0 / 30 j (interview, carte cadeau, hommage) | l'agenda `opera-nice.org/agenda/feed/` est déjà en base ; ce flux-ci est de la communication |
| Palais des Expositions (Nice) | `https://palaisdesexpos.nice.fr/feed/` | 4 items, 0 / 30 j : Salon du Mariage, Hyrox, EVO Nice, Salon des Grandes Écoles | public visé : salons commerciaux et B2B ; EVO 2026 est cité nommément comme cas écarté dans la charte |
| Ville de Tende — agenda | `https://www.tende.fr/agenda/feed/` | 10 items, 10 / 30 j, **tous des séances de cinéma** (Pat' Patrouille, Fjord…) | programme du cinéma communal : pas de matière éditoriale. `/feed/` racine = conseil municipal, sécheresse (1 / 30 j) |
| Ville de Sospel | `https://www.sospel.fr/feed/` | 10 items, 5 / 30 j : fermeture de route, vigilance orange, rentrée | 0 événement sur 8 |
| Saint-Étienne-de-Tinée | `https://saintetiennedetinee.fr/feed/` | 10 items, 4 / 30 j : fermeture de route, coupure d'électricité, horaires postaux | 0 événement sur 8 |
| Beaulieu-sur-Mer (commune) | `https://beaulieusurmer.fr/feed/` et `/evenements/feed/` | RSS valide, **0 item** | vide ; l'OT `destination.beaulieusurmer.fr/feed/` est déjà en base |
| Èze Tourisme (Joomla) | `https://www.eze-tourisme.com/fr/?format=feed&type=rss` | 1 item, daté 2020-03-17 (« Changement d'adresse ») | mort |
| Isola 2000 | `https://isola2000.com/feed/` | 2 items, 2018 | mort |
| Valberg — agenda | `https://www.valberg.com/agenda/feed/` | RSS valide, 0 item | vide |
| Écomusée de la Roudoule (Puget-Rostang) | `https://roudoule.com/feed/` | 10 items, dernier 06/05/2026, 0 / 90 j ; 3 expos par an | trop lent pour un flux ; à revoir si le pays de Puget-Théniers reste à zéro |
| Villa Ephrussi de Rothschild — RSS | `https://www.villa-ephrussi.com/fr/rss.xml` | 10 items, dernier 17/02/2025 : revue de presse (BFM TV, Jardinez.com) | ce n'est pas un agenda ; **la newsletter existe**, voir § 3 |
| Villa Kérylos — RSS | `https://www.villakerylos.fr/feed/` | 1 item : « Bonjour tout le monde ! » (20/11/2025) | WordPress jamais alimenté |
| Conservatoire de Nice (CRR) — RSS | `https://www.conservatoire-nice.org/feed/` | RSS valide, 0 item | vide ; page newsletter repérée, voir § 5 |
| Forum Sirius | `https://forumsirius.com/feed/` (repéré, non téléchargé) | — | billetterie/agrégateur : serait tier radar (désactivé). La newsletter est déjà *active* |
| Aucun flux aux chemins classiques (accueil joignable) | `tnn.fr`, `nicejazzfest.fr`, `menton.fr` (hors backend SPIP), `menton-riviera-merveilles.fr` (CMS Cloudly), `festival-musique-menton.fr` (SPIP, backend repéré non téléchargé → § 5), `cinematheque-nice.com` (CMS maison, ni RSS ni newsletter trouvés), `theatre-francis-gag.org` (newsletter seulement), `roquebrune-cap-martin.fr`, `roquebilliere.fr`, `espacemagnan.com` (Oxatis), `maa.departement06.fr` (404 sur /feed), `museedusport.fr` (404), `univ-cotedazur.fr/rss` (404), `cotedazurfrance.fr/feed/` (404), `nicemusiclive.fr` (→ page HTML nice.fr), `palaisnikaia.fr` (→ 403, redirige vers un magazine) | | pas de RSS |
| Domaines injoignables depuis ce conteneur (DNS/timeout/proxy) | `musee-chagall.fr`, `www.villa-arson.fr` (le flux vit sur `villa-arson.fr` sans www), `saintjeancapferrat.fr`, `roquebrune-cap-martin-tourisme.com`, `breil-sur-roya.fr`, `ville-levens.fr`, `ville-contes.fr`, `ville-la-trinite.fr`, `villedecapdail.fr`, `pugettheniers.fr`, `tourrette-levens.fr`, `drap.fr`, `forumurbanisme.nice.fr`, `crr-nice.fr`, `nice-jazz-festival.fr`, `museedelaphotographie.nice.fr`, `theatre-de-la-cite.fr`, `orchestre-philharmonique-nice.org`, `auron.com`, `www.bmvr.nice.fr`, `lentrepont.com`, `sospel-tourisme.com`, `tpi-nice.org` (522) | | rien à conclure : ni vivant ni mort. Les 6 pistes Savoie de 2026-06-30 étaient dans le même cas et se sont avérées mortes depuis le VPS — à retester de là |

---

## 2 bis. Vallée d'Aoste — flux téléchargés et lus

Périmètre : toute la région autonome. Résultat net : **les institutions valdôtaines ne
publient presque pas de RSS**. Sur 70 pages d'accueil sondées et 26 sites communaux testés
sur les deux chemins du CMS régional (`/it/events/feed`, `/it/news/feed`), un seul émetteur
donne un flux vivant et lisible : la Ville d'Aoste. Le levier pour la VdA est ailleurs :
newsletters (§ 3) et deux flux **non vérifiés** parce que bloqués depuis ici (§ 5 :
Bibliothèque régionale, Cittadella dei Giovani).

### 2 bis.1 Candidats retenus

| Institution | URL du flux (téléchargée le 08/09) | Dernier item | Volume | Part d'événements | Tier proposé | Risque de doublon avec |
|---|---|---|---|---|---|---|
| **Comune di Aosta — notizie** | `https://www.comune.aosta.it/it/news/feed` | 2026-09-04 | 5 items (le CMS Municipium ne sert que **les 5 dernières** ; 5 / 30 j) | 2/5 (San Grato : fête patronale des 6-7/09 ; Semaine européenne de la mobilité) ; reste = piscine, eau potable, concours | institution ; ville = Aosta | aucun : ni le Comune ni ses fêtes (San Grato, Sant'Orso, Marché Vert Noël) n'ont de flux en base. Le cron quotidien suffit à ne rien rater malgré la fenêtre de 5 |
| **Comune di Aosta — eventi** | `https://www.comune.aosta.it/it/eventi/feed` | — | RSS valide, **0 item au 08/09** (« In questo momento non sono previsti eventi ») ; la page des événements passés en montre 14 entre déc. 2024 et janv. 2026 : Fiera di Sant'Orso, Marché Vert Noël, Solstizio d'inverno, Capodanno, Foire des Alpes | 14/14 quand il y en a | institution ; ville = Aosta | aucun. À coller quand même : le scraper ignore un flux vide sans erreur, et il se remplira à l'approche de Noël et de Sant'Orso — les deux moments où la VdA compte |

C'est court. Les autres pistes ci-dessous ont toutes été téléchargées et ne tiennent pas.

### 2 bis.2 Téléchargés et écartés — Vallée d'Aoste

| Source | URL testée | Ce que le téléchargement a montré | Pourquoi écarté |
|---|---|---|---|
| **Regione VdA — bureau de presse (VdA Comunicazione)** | `https://pressevda.regione.vda.it/it/news/feed` et `/it/events/feed` | les deux : RSS valide, `<channel>` correct, **0 `<item>`** (le flux annonce « le ultime 5 news » et n'en sert aucune) | flux cassé côté serveur. La page `/it/eventi` dit aussi « nessun evento previsto » |
| **LoveVDA (Office régional du tourisme)** | `https://www.lovevda.it/rss?projection=34945` (IT) et `?projection=33596` (FR) — seuls `<link rel=alternate>` du site | 8 items, tous datés 2023-08-04 : les huit « aree turistiche » (Gressoney, Cervino, Gran Paradiso…), pas un événement | flux statique, mort. La newsletter reste le canal (statut *attente*) — URL directe du formulaire en § 3 |
| Regione VdA — `regione.vda.it`, `/cultura/`, `/cultura/eventi_spettacoli/` | pages d'accueil et portail événements | aucun `<link rel=alternate>`, aucun chemin classique ; le portail renvoie vers lovevda, valledaostaheritage (déjà en base) et rendezvous-vda (déjà en base) | pas de RSS ; **newsletter « mostre ad Aosta » trouvée**, § 3 |
| Saison Culturelle | `https://saisonculturellevda.it/feed/` (404) ; accueil lu | CMS maison (`/site/templates/`), ni RSS ni newsletter ; un seul spectacle publié (Loredana Bertè, 09/10, CVA Dome) | rien à brancher ; couverte indirectement par Rendez-Vous VdA / Heritage déjà en base |
| Fiera di Sant'Orso (Joomla) | `https://www.fieradisantorso.it/index.php?option=com_content&format=feed&type=rss` | 4 items datés 2015-12-21 (« Il programma », « Come arrivare ») | mort. `lasaintours.it` (site programme cité par la Regione) → 503 maintenance |
| Office régional du tourisme (site institutionnel) | `https://turismo.vda.it/feed/` | 7 items, dernier 27/04/2026 : PIAO, avvisi, concours | administratif, 0 événement |
| Musicastelle | `https://www.musicastellevda.it/feed/` | RSS valide, 0 item | WordPress sans articles ; la newsletter est déjà *active* |
| Comune di Châtillon | `https://www.comune.chatillon.ao.it/feed/` | 4 items : « Avviso ai creditori » ×3, « Ciao mondo! » | administratif |
| Visit Cogne | `https://www.visitcogne.it/feed/` | RSS valide, 0 item | vide |
| Visit Monterosa (Gressoney/Ayas) | `https://visitmonterosa.com/rss.xml` | RSS valide, 0 item | vide |
| Parco Mont Avic | `https://montavic.it/feed/` | 10 items, dernier 04/04/2023, tout « amministrazione trasparente » | mort/administratif |
| Fondazione Courmayeur Mont Blanc | `https://www.fondazionecourmayeur.it/feed/` | RSS valide, 0 item ; l'objet de la fondation est juridique/économique (« Incontri di Courmayeur ») | vide, et public visé hors périmètre (colloques) |
| Parco Nazionale Gran Paradiso | `https://www.pngp.it/rss.xml` | 10 items, 4 / 30 j : 2 événements (In-Equilibrio Festival, journée biodiversité), 2 « determinazioni » numérotées, puis des items de 2013-2015 | moitié administratif, moitié Piémont (Locana, Eataly Torino) ; source large à faible rendement |
| Université de la Vallée d'Aoste | `https://www.univda.it/feed/` (`/eventi/feed/` = 0 item) | 50 items, 2 / 30 j, 20 / 90 j : concours, masters, inscriptions | académique, ~1 événement sur 10 |
| Comune de La Thuile (Municipium) | `https://www.comune.la-thuile.ao.it/it/news/feed` | RSS valide, 5 items — **titres non lus** (la passe a été interrompue) | reporté en § 5 |
| Communes testées sur `/it/events/feed` + `/it/news/feed` (26) | Courmayeur, Cogne, Gressoney-Saint-Jean (×2 graphies), Saint-Pierre, Sarre, Bard, Morgex, Pont-Saint-Martin, Verrès, Donnas, Nus, Ayas, Valtournenche, Gignod, Quart, Saint-Vincent, Étroubles, Pré-Saint-Didier, Villeneuve, Aymavilles, Introd, Gressoney-La-Trinité, Fénis, Issogne | aucune réponse RSS, sauf Châtillon et Saint-Christophe (RSS valide, 0 item) et La Thuile (ci-dessus) | pas de flux |
| Accueil joignable, aucun flux | `gressoney.it`, `cervinia.it`, `aostaclassica.it` (newsletter déjà active), `comune.etroubles.ao.it`, `etroubles.it`, `aostavalley.com`, `lathuile.it`, `comune.bard.ao.it`, `comune.ayas.ao.it`, `comune.saint-vincent.ao.it`, `institutfrancais.it` (404 sur /feed), `celtica.vda.it` (404), `patoisvda.org` (404), `fondazionemontagnasicura.org` (404) | | pas de RSS |
| Presse (exclue par `config/non_institutional_sources.txt`) | `aostasera.it/feed/` (flux vivant repéré, non téléchargé) | | presse : jamais source |
| Injoignables depuis ce conteneur | `aostacultura.it`, `museoarcheologicoregionale.it`, `saisonculturelle.vda.it`, `saintvincentturismo.it`, `chatillon-tourism.it`, `cervino.it`, `biblioteca.vda.it`, `cittadelladeigiovani.it`, `turismo.la-thuile.it`, `pila.it`, `gressoneyonline.it`, `monterosa-ski.com`, `celva.it`, `cvadome.it`, `ivat.org`, `stradedelcinema.it` (TLS), et 14 sites `comune.*.ao.it` | | rien à conclure ; à retester depuis le VPS |

**Deux sources VdA déjà en base à surveiller** (vues en passant, même passe de test) :
`https://www.grand-paradis.it/it/rss.xml` (Fondation Grand Paradis) a pour dernier item le
**2025-08-04** — 0 item sur 90 j, le flux est dormant depuis un an alors que la ligne est
active ; `https://www.fortedibard.it/eventi/feed/` va bien (5 événements à venir jusqu'en
mai 2027) ; `https://www.courmayeurmontblanc.it/feed/` va bien (5 / 30 j, dont Lo Matsòn).

---

## 3. Newsletters sans RSS — pages d'inscription (Franck s'inscrit lui-même)

Format de `config/newsletters.txt` : `nom;domaine;territoire;statut;url_inscription`.
Le statut est `candidat` = à s'abonner ; rien n'a été fait.

| Institution | Page d'inscription (vue le 08/09) | Ce qui a été vérifié | Ligne prête |
|---|---|---|---|
| **Regione autonoma VdA — « newsletter mostre ad Aosta »** (Assessorat culture : expositions régionales, MAR, Centre Saint-Bénin, châteaux) | `https://a7h3i9.mailupclient.com/frontend/forms/Subscription.aspx?idList=8&idForm=9&guid=BB07B556-1603-46C7-8055-0A665F8A2DD9` | lien lu sur `regione.vda.it/cultura/mostre_musei/default_i.aspx` ; formulaire MailUp non ouvert | `Regione VdA — newsletter mostre ad Aosta (Assessorat culture, expositions régionales);regione.vda.it;Vallee-Aoste;candidat;https://a7h3i9.mailupclient.com/frontend/forms/Subscription.aspx?idList=8&idForm=9&guid=BB07B556-1603-46C7-8055-0A665F8A2DD9` |
| **LoveVDA** (déjà *attente* dans le fichier, URL générique `lovevda.it/it`) | `https://a2c8h4.emailsp.com/frontend/forms/Subscription.aspx?idList=7&idForm=2&guid=d2e24cb3-7cac-45ad-8d2c-e3c964cdbe47` | lien « Iscriviti » lu sur `lovevda.it/it/eventi` | remplacer l'URL de la ligne existante par celle-ci — c'est le formulaire lui-même |
| **Villa Ephrussi de Rothschild** (Culturespaces, Saint-Jean-Cap-Ferrat — Jeudis de la Villa, JEP, expos) | `https://www.villa-ephrussi.com/fr/newsletter` | page ouverte : formulaire « Newsletter Grand Public » / « Scolaires », traitement Culturespaces | `Villa Ephrussi de Rothschild (Culturespaces, Saint-Jean-Cap-Ferrat);villa-ephrussi.com;Nice;candidat;https://www.villa-ephrussi.com/fr/newsletter` |
| **Théâtre Francis-Gag (Nice)** | `https://www.theatre-francis-gag.org/#gotonewsletter` (bloc en pied de page d'accueil) | ancre repérée dans le HTML ; formulaire non testé | `Théâtre Francis-Gag (Nice, saison théâtrale);theatre-francis-gag.org;Nice;candidat;https://www.theatre-francis-gag.org/#gotonewsletter` |
| **Musée national Marc Chagall** | `https://musees-nationaux-alpesmaritimes.fr/chagall/agenda` (formulaire « Inscrivez-vous ! » sur la page) | le fichier dit `inactif` : c'est **faux**, un formulaire existe (vu le 08/09) ; son `action` n'a pas été extrait | passer la ligne existante à `candidat` avec cette URL |
| Conservatoire de Nice (CRR) | `https://www.conservatoire-nice.org/newsletter/` | lien présent dans le HTML de l'agenda ; page **non ouverte** | § 5 |
| Festival de Musique de Menton | — | SPIP ; aucun formulaire newsletter trouvé sur l'accueil ; un backend RSS existe (§ 5) | — |
| Cinémathèque de Nice | — | ni RSS ni newsletter trouvés | — |
| TNN, Nice Jazz Festival, Villa Arson, Menton R&M, Forte di Bard, Musicastelle, Aosta Classica | — | déjà dans `newsletters.txt` (actif/attente/candidat) | rien à ajouter |

---

## 4. Lignes prêtes à coller dans `config/sources.txt`

Format : `url_rss;territoire;nom_source;tier[;lieu;ville]` — `;;Ville` = ville seule.
Toutes téléchargées le 08/09 depuis ce conteneur, RSS valide, items réels. Le tier suit
l'en-tête du fichier : `officielle` = le lieu ou l'organisateur lui-même ; `institution` =
collectivité.

```
# ═════════════════════════════════════════════════════════════════════════════
# AJOUT 2026-09-08 — Comté de Nice et Vallée d'Aoste à 12 et 13 fiches/mois contre 132
# au Piémont. Flux téléchargés et lus le 08/09 (docs/SOURCES_CANDIDATES_2026-09-08.md).
# ═════════════════════════════════════════════════════════════════════════════
# -- Ville de Nice : l'agenda municipal par TYPE (le flux racine /agenda/feed/ plafonne à
#    24 entrées toutes catégories ; « animation » et « visite-guidee » écartés : sport,
#    doublons). Un même spectacle donne une entrée PAR DATE : la dédup par titre absorbe.
https://www.nice.fr/agenda/type/conference/feed/;Nice;Ville de Nice - Agenda conférences;institution;;Nice
https://www.nice.fr/agenda/type/concert/feed/;Nice;Ville de Nice - Agenda concerts;institution;;Nice
https://www.nice.fr/agenda/type/exposition/feed/;Nice;Ville de Nice - Agenda expositions;institution;;Nice
https://www.nice.fr/agenda/type/spectacle/feed/;Nice;Ville de Nice - Agenda spectacles;institution;;Nice
# -- Musées de Nice sans flux en base (Matisse et MAMAC y sont déjà)
https://www.musee-beaux-arts-nice.org/agenda/feed/;Nice;Musée des Beaux-Arts Jules Chéret (Nice) - Agenda;officielle;Musée des Beaux-Arts Jules Chéret;Nice
https://www.musee-archeologie-nice.org/feed/;Nice;Musée d'Archéologie de Nice-Cimiez;officielle;Musée d'Archéologie de Nice-Cimiez;Nice
# -- Menton (SPIP : le flux est spip.php?page=backend, pas /feed/)
https://www.menton.fr/spip.php?page=backend;Nice;Ville de Menton;institution;;Menton
https://www.museecocteaumenton.fr/spip.php?page=backend;Nice;Musée Jean Cocteau - le Bastion (Menton);officielle;Musée Jean Cocteau - le Bastion;Menton
# -- Communes de l'arrondissement de Nice avec un vrai flux (rare : 5 sur 20 testées)
https://www.cap-dail.fr/events/feed/;Nice;Ville de Cap-d'Ail - Événements;institution;;Cap-d'Ail
https://www.ville-la-turbie.fr/feed/;Nice;Ville de La Turbie;institution;;La Turbie
# -- Vallée d'Aoste : la seule collectivité avec un flux vivant. Le flux « eventi » est
#    vide hors saison (0 item le 08/09) et se remplit pour Noël et Sant'Orso : le garder.
https://www.comune.aosta.it/it/news/feed;Vallee-Aoste;Comune di Aosta - Notizie;institution;;Aosta
https://www.comune.aosta.it/it/eventi/feed;Vallee-Aoste;Comune di Aosta - Eventi;institution;;Aosta
```

**Deux lignes à part, à ne coller QU'AVEC leur domaine dans `config/broad_sources.txt`**
(sources larges : le Département couvre l'arrondissement de Grasse, le Parc couvre les
Alpes-de-Haute-Provence) — et pour le Département, **pas avant d'avoir réglé le premier
passage à 3 154 items** (§ 2.1) :

```
# -- Sources LARGES : domaine à ajouter dans config/broad_sources.txt EN MÊME TEMPS.
# ⚠️ agenda.xml sert l'archive complète depuis 2020 (3 154 items le 08/09) et le
#    scraper n'a pas de coupure d'âge : prévoir la coupure AVANT le premier passage.
https://www.departement06.fr/agenda.xml;Nice;Département des Alpes-Maritimes - Agenda;institution
https://www.mercantour-parcnational.fr/fr/rss.xml;Nice;Parc national du Mercantour;institution
```

et dans `config/broad_sources.txt` :

```
departement06.fr
mercantour-parcnational.fr
```

---

## 5. Non vérifiés — repérés mais PAS téléchargés (bloqués depuis ce conteneur ou séance interrompue)

Ne pas les compter comme des sources. À tester depuis le VPS avec, par exemple,
`curl -sSL -A "Mozilla/5.0" <url> | head -c 2000`.

| Piste | URL | Ce qui bloque ici | Pourquoi ça vaudrait le coup |
|---|---|---|---|
| **Portail des théâtres de Nice** (Ville de Nice — « la programmation de tous les théâtres municipaux, privés ou associatifs ») | `https://theatres.nice.fr/` puis `/feed/` | chaîne TLS incomplète (« unable to get local issuer certificate ») et 503 au fetch | probablement la source la plus riche du Comté de Nice pour le spectacle vivant ; un CMS WordPress y est probable (même hébergement que nice.fr) |
| **Le 109** (pôle de cultures contemporaines, Ville de Nice) | `https://le109.nice.fr/feed/` | même chaîne TLS que ci-dessus | expos et concerts |
| **Bibliothèques de Nice (BMVR)** — agenda | `https://bmvr.nice.fr/default/agenda.aspx?_lg=fr-FR` (« Obtenir le flux RSS » annoncé sur la page) | la page répond 500 ; aucun lien rss dans le HTML servi | conférences, lectures, ateliers |
| **Bibliothèque régionale / Sistema Bibliotecario Valdostano** — événements | `https://biblio.regione.vda.it/events/` (« Feed RSS » annoncé) → `/events/feed/` | 403 avec ou sans user-agent navigateur (WAF) | la seule institution culturelle régionale VdA qui annonce un RSS d'événements |
| **Cittadella dei Giovani (Aoste)** | `http://www.cittadelladeigiovani.ao.it/feed/` | 503 | concerts, festa della Cittadella |
| Teatro Giacosa (Aoste, « casa delle arti » municipale) | `https://teatrogiacosa.vda.it/` | trouvé par recherche, non sondé | scène municipale rouverte |
| Fondation Émile Chanoux (Aoste) | `https://www.fondchanoux.org/feed/` | 429 (rate limit) | conférences, publications |
| CVA Dome (Saint-Vincent), IVAT (Foire de Saint-Ours), Strade del Cinema (Aoste) | `cvadome.it`, `ivat.org`, `stradedelcinema.it` | erreurs proxy / TLS | organisateurs directs |
| Comune de La Thuile — notizie | `https://www.comune.la-thuile.ao.it/it/news/feed` | RSS valide, 5 items, **titres non lus** | commune de station |
| Festival de Musique de Menton (SPIP) | `https://www.festival-musique-menton.fr/spip.php?page=backend` | backend repéré par lecture de page, non téléchargé | 77e édition, juillet-août ; organisé par l'OT de Menton |
| Agenda de Menton (site dédié de la Ville) | `https://www.agenda-menton.fr` | lien trouvé sur `menton.fr/-Agenda-.html`, non sondé | pourrait porter un flux plus propre que le backend SPIP |
| Conservatoire de Nice — newsletter | `https://www.conservatoire-nice.org/newsletter/` | page non ouverte | concerts gratuits de saison |
| Musée Chagall — formulaire newsletter | `https://musees-nationaux-alpesmaritimes.fr/chagall/agenda` | `action` du formulaire non extrait | corrige le statut `inactif` du fichier |
| Mesure « part arrondissement de Nice » dans `departement06.fr/agenda.xml` | script `dep06.py` (scratchpad) | proxy tombé pendant l'exécution (21 connexions coupées) | conditionne l'intérêt réel du flux du Département |

---

## 6. Bilan chiffré (périmètre : cette séance, depuis ce conteneur, le 08/09/2026)

- **Pages d'accueil sondées** : 59 (Nice) + 70 (VdA), plus 26 sites communaux VdA sur deux
  chemins chacun.
- **URL de flux téléchargées avec réponse RSS/Atom valide** : **62** — 37 Nice, 25 VdA
  (dont 4 déjà en base, retestées : `nice.fr/feed/`, Forte di Bard, Courmayeur, Grand
  Paradis). Les URL en 404/HTML/erreur réseau sont listées dans les tableaux « écartés »
  et « injoignables », pas comptées ici.
- **Retenus** : **14 lignes** — 12 Comté de Nice (dont 2 sources larges sous condition),
  **2 Vallée d'Aoste** (Comune di Aosta ×2). Plus **4 newsletters** nouvelles (Regione VdA
  mostre, Villa Ephrussi, Francis-Gag, Chagall à corriger) et une URL de formulaire à
  substituer (LoveVDA).
- **Écartés après téléchargement** : 33 flux — Nice 19 (tableau § 2.2), VdA 14 (tableau
  § 2 bis.2). Motifs : 11 vides (RSS valide, 0 item), 6 morts (dernier item entre 2015 et
  2025), 11 sans événements (administratif, académique, revue de presse), 2 hors public
  visé ou hors sujet (Palais des Expositions, cinéma de Tende), 3 redondants avec une
  ligne déjà en base ou avec un flux retenu (agenda racine de nice.fr, visites guidées,
  blog de l'Opéra).
- **Non vérifiés** : 13 pistes (§ 5), dont 3 qui pourraient changer la donne (portail des
  théâtres de Nice, Bibliothèque régionale VdA, BMVR).
- **Objectif de 10 à 20 candidats sérieux par territoire** : atteint pour Nice (12),
  **pas pour la Vallée d'Aoste (2)** — non par manque de recherche mais parce que la
  matière n'est pas en RSS : la Regione, LoveVDA, la Saison Culturelle, la Foire de
  Saint-Ours et les stations ont toutes été téléchargées et ne servent rien ou du mort.
  Pour la VdA, le prochain pas n'est pas un flux : c'est s'abonner aux deux newsletters
  régionales (§ 3) et retester depuis le VPS les deux pistes bloquées (§ 5).
