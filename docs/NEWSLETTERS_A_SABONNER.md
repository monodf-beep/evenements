# Newsletters culturelles à identifier — checklist d'abonnement

Recherche multi-agents du 2026-07-01. Chaque entrée a une **page d'inscription
vérifiée** (champ email présent). ⭐ = les meilleures (agenda des sorties, cadence
régulière, peu de bruit) : à faire **en premier**.

## Mode d'emploi
1. S'abonner avec le **compte Gmail** qui alimente le canal (celui lu par `gmail_collect`).
2. Dans Gmail, appliquer le **libellé `Agenda`** aux mails reçus (le label est le
   sélecteur principal — c'est la curation).
3. Le territoire est **deviné automatiquement** : les domaines expéditeurs sont
   déjà dans `config/whitelist_gmail.txt`. Si un mail n'est pas classé, relever le
   domaine expéditeur réel du 1er email (souvent un ESP : Brevo/Mailchimp/Mailjet)
   et l'ajouter à la whitelist.
4. Lancer `scripts/gmail_collect.py` (ou attendre le cron) → les événements entrent
   avec le badge **📬 newsletter**.

Rappel : les billetteries (Fnac, Ticketmaster, Dice, TicketOne, Vivaticket…) n'ont
**aucun flux ouvert** (API à clé uniquement) — inutile de chercher de ce côté.

---

## Contacts presse — gros événements sans newsletter grand public accessible

Recherche du 2026-08-18. Pour ces gros événements, aucune newsletter grand
public n'a pu être trouvée/confirmée (site anti-bot, ou rien du tout). Mais
Cultura Sabauda est un **média**, pas juste un agrégateur (CHARTE §5, §8) :
le bon canal est une **demande d'accréditation presse**, distincte de
`docs/PIPELINE_COLLECTE.md` §4 (le canal `press_kits.py`, label Gmail
`Presse`) — ça donne accès aux dossiers de presse, photos avec droits, info
avant le public. **Action manuelle requise : écrire un mail de présentation
du média** à chaque contact, ce n'est pas automatisable ni une simple case à
cocher comme les newsletters ci-dessus.

- ⭐ **Palio di Asti** — https://www.fondazionepalio.org/stampa/ —
  `comunicazione@fondazionepalio.org`, formulaire d'accréditation PDF
- ⭐ **Carnaval de Nice** — https://www.nicecarnaval.com/en/journalists/ —
  `christophe.viale@nicecotedazur.org`, formulaire d'accréditation en ligne
- ⭐ **Fête du Citron (Menton)** — https://www.fete-du-citron.com/-Presse-.html
  et `+demande-accreditation-presse+.html` — formulaire officiel, service Presse
  Ville de Menton
- **Torino Design City** — https://www.torinodesigncity.it/en/press-2/ —
  `design@comune.torino.it` (Ufficio Stampa Città di Torino), pas de
  formulaire, contact direct par email

Pistes plus faibles, à recouper avant d'écrire :
- Foire de Saint-Ours (Aoste) — page « Per i giornalisti » trouvée
  (regione.vda.it) mais contenu qui semble dater d'une édition passée
  (2010 dans l'extrait récupéré) — vérifier que l'URL sert bien l'édition
  courante avant d'écrire.
- Salone del Vino di Torino — une page « Area stampa e media » existe
  (salonedelvinotorino.it/area-stampa/) mais aucun email/formulaire capturé
  (site probablement en JS) — à revérifier au navigateur.
- Grandi Langhe — site protégé anti-bot, aucun contact presse confirmé par
  accès direct ; les consortiums organisateurs (Barolo/Barbaresco/Langhe)
  ont probablement une dégustation presse dédiée, à chercher autrement
  (contact direct des consortiums plutôt que le site de l'événement).

---

## ⚡⚡ Priorité — zones à 0-4 événements vues dans « Intentions de recherche » (18/08)

Recherche complémentaire du 2026-08-18, sur les zones que la page *Outils >
Intentions de recherche* signale comme sous le seuil. **Vérifié : pas de flux
RSS exploitable chez ces organismes** (post-type événement absent du flux
WordPress standard, ou pages non-WordPress) — testé par curl réel sur ~25
sites avant de conclure. La newsletter est donc la seule voie côté source
officielle pour ces zones-là, avec le même mode d'emploi que le reste de cette
page (label Gmail `Agenda`, jamais une automatisation directe).

- [ ] **Courchevel Tourisme** — https://www.courchevel.com/en/form/newsletter (Savoie, 0 évén.)
- [ ] **Maurienne Tourisme** (couvre Saint-Jean-de-Maurienne, 0 évén.) — http://www.maurienne-tourisme.com/inscription-newsletter-destination-maurienne/
- [ ] ⭐ **ATL Terre dell'Alto Piemonte** (*hebdo* — couvre EN UNE FOIS Biella, Vercelli, Novara et Valsesia, toutes à 0-1 évén.) — https://www.atl.biella.it/newsletter/dettaglio/-/d/newsletter-settimanale
- [ ] **Mairie de Villefranche-sur-Mer** (Nice, mentionne explicitement les événements à venir) — https://www.villefranche-sur-mer.fr/newsletter/
- [ ] **Sallanches Mont-Blanc Tourisme** (page dédiée, distincte de Savoie Mont Blanc) — https://sallanchesmontblanc.com/newsletters
- [ ] **Distretto dei Laghi** (VCO/Verbano-Cusio-Ossola, 0 évén.) — https://www.distrettolaghi.it/it/newsletter
- [ ] **Alexala** (Alessandria, 0 évén. — formulaire en page d'accueil, pas d'URL dédiée) — https://www.alexala.it/it
- [ ] **Visit Cuneese** (province de Cuneo) — https://www.visitcuneese.it/newsletter
- [ ] **Cœur de Tarentaise Tourisme** (Moûtiers) — https://www.coeurdetarentaise-tourisme.com/ (formulaire Mailchimp en page d'accueil)
- [ ] ⭐ **Explore Nice Côte d'Azur** (territoire Comté de Nice entier) — https://www.explorenicecotedazur.com/newsletter/
- [ ] **Destination Léman** (Chablais, couvre aussi Évian) — https://www.destination-leman.com/newsletter/
- [ ] **Turismo Torino e Provincia** couvre explicitement Ivrea et le Canavese — déjà listé plus haut, à cocher pour cette zone aussi, pas de source séparée nécessaire.

Vérifié le 18/08 mais **incertain** — bloc « Newsletter » présent en page
mais aucun champ email statique capturé (rendu JavaScript), à confirmer à la
main avant de compter dessus :
- **Visit Asti** (province d'Asti) — https://visit.asti.it/ ; `provincia.asti.it` reste bloqué (403).
- **VisitPiemonte DMO** (région Piémont) — `/newsletter/` répond 404, aucun
  formulaire d'inscription trouvé sur la page d'accueil : **à écarter** tant
  que non prouvé, ne pas cocher en l'état.

Non résolu, à rechercher plus loin (blocage technique, pas une absence
prouvée) :
- **Annemasse** — le site bloque systématiquement les accès automatisés
  (reset de connexion sur tous les user-agents testés) ; une page
  `annemasse.fr/Annemasse/Newsletter` est mentionnée par la recherche web
  mais invérifiable depuis cet environnement — à tester depuis un poste non
  filtré.
- **Aoste (ville)** — `aostalife.it` a renvoyé une erreur de proxy réseau
  (pas une preuve d'absence) ; rien trouvé sur `comune.aosta.it` — à
  retester. La Vallée d'Aoste reste couverte à l'échelle régionale par
  **LoveVDA**, déjà listé plus bas.
- **Cluses / Thonon-les-Bains / Aix-les-Bains / Chamonix / Megève** — déjà
  `[x]` plus haut (Musiques en Stock, Maison des Arts du Léman, OT
  Aix-les-Bains, OT Chamonix, Megève Tourisme) : si ces zones restent à 0
  évén., ce n'est **pas un manque de source** mais un problème de flux
  (label Gmail non appliqué, ou domaine expéditeur absent de
  `config/whitelist_gmail.txt`) — à diagnostiquer, pas à re-sourcer (même
  logique que le cas Menton ci-dessous).
- **Province du VCO / Verbano-Cusio-Ossola** — organisme identifié
  (Distretto dei Laghi, distrettolaghi.it), site refondu récemment, aucune
  page newsletter dédiée trouvée en recherche web — à vérifier directement
  sur le site.
- **Alessandria / Asti** — Alexala (alexala.it) a un formulaire d'inscription
  en page d'accueil mais pas d'URL dédiée stable trouvée ; Visit Asti a
  renvoyé une erreur d'accès lors de la vérification — à revisiter à la main.
- **Alba / Monferrato** — déjà couvert par **Ente Turismo Langhe Monferrato
  Roero** `[ ]` plus bas (section Piémont) : à cocher en priorité, c'est déjà
  identifié comme *le* pivot Langhe/Roero/Monferrato/Alba.
- **Courmayeur** — déjà listé `[ ]` plus bas (section Vallée d'Aoste) : à
  cocher, et **LoveVDA** `[ ]` (même section) couvre aussi Courmayeur en plus
  du reste de la VdA — la source la plus rentable, à faire en 1er.

---

## ⚡ Priorité — combler les trous vus dans « Couverture géo » (21/07)

La page **Couverture géo** a chiffré les zones à ZÉRO. La bonne nouvelle : les sources
existent déjà ci-dessous, elles sont juste **non abonnées** `[ ]`. À faire **maintenant**,
dans l'ordre, pour alimenter les pages P1 qui manquent d'offre :

**Piémont hors-Turin** (aujourd'hui 72 % Turin ; Langhe/Monferrato/Alba = 0) :
- **Ente Turismo Langhe Monferrato Roero** (Cuneo/Asti) — *le* pivot Langhe/Roero/Monferrato.
- **Collisioni** (Alba/Barolo) · **Fiera del Tartufo Bianco d'Alba** — gros événements Alba.
- Vérifier que **Piemonte dal Vivo** (déjà abonné) laisse bien passer le hors-Turin (filtre géo).

**Vallée d'Aoste** (Courmayeur/Cervinia = 0) :
- **LoveVDA — Office Régional du Tourisme** ⭐ — l'agenda régional bilingue, couvre TOUT
  (Courmayeur, Cervinia, vallées) : **la source la plus rentable de la VdA**, à faire en 1er.
- **Courmayeur Mont Blanc** · **Cervino / Cervinia**.

**Menton = 0 alors que « Menton, Riviera & Merveilles » est déjà `[x]`** → ce n'est PAS un
manque de source, mais un **problème de flux** : soit le label `Agenda` n'est pas appliqué à
ces mails, soit le domaine expéditeur (souvent un ESP) n'est pas dans `config/whitelist_gmail.txt`,
soit la newsletter mensuelle porte peu d'événements datés. **À diagnostiquer** (pas à re-sourcer).

**Annecy faible (5) malgré Bonlieu `[x]`** : probablement des dates de saison lointaines (théâtre
démarre en septembre) + agglo comptée à part (Cran-Gevrier, La Ravoire). À re-regarder après la
prochaine collecte.

---

## Savoie / Haute-Savoie
- [x] ⭐ **Bonlieu Scène Nationale** (théâtre/danse/musique, Annecy) — https://www.bonlieu-annecy.com/inscription-newsletter
- [x] ⭐ **Espace Malraux Scène Nationale** (théâtre/danse, Chambéry) — https://billetterie.malrauxchambery.fr/3web_mailing_cherche?template=11720
- [x] ⭐ **Cité des Arts Chambéry** (expos/ateliers, *hebdo*) — https://www.chambery.fr/522-newsletter-de-la-cite-des-arts.htm
- [x] ⭐ **OT Lac d'Annecy** (sorties/événements) — https://www.lac-annecy.com/newsletter/
- [x] ⭐ **Chambéry Montagnes** (Grand Chambéry Tourisme) — https://www.chamberymontagnes.com/newsletter/
- [ ] Le Dôme Théâtre (Albertville) — https://www.dometheatre.com _(form en pied de page)_
- [ ] Le Brise Glace / MJC Annecy (concerts) — https://www.le-brise-glace.com
- [ ] Château Rouge (Annemasse) — https://www.chateau-rouge.net/newsletters/
- [ ] Maison des Arts du Léman (Thonon) — https://mal-thonon.org/inscription-newsletter/
- [ ] La Turbine (Cran-Gevrier, cinéma/sciences) — https://cinema-laturbine.fr/FR/72/newsletter-la-turbine-cran-gevrier.html
- [x] Festival Musilac (Aix-les-Bains) — https://www.muhsilac.com/
- [x] Guitare en Scène (St-Julien-en-Genevois) — https://www.guitare-en-scene.com/
- [x] Musiques en Stock (Cluses) — https://musiquesenstock.fr/
- [x] Le Grand Bivouac (Albertville) — https://www.grandbivouac.com/fr
- [x] OT Aix-les-Bains Riviera des Alpes — https://www.aixlesbains-rivieradesalpes.com/newsletter/
- [x] Maison du Tourisme Pays d'Albertville (*Hebdo*) — https://www.pays-albertville.com/
- [x] Musées d'Annecy (Château / Palais de l'Île) — https://musees.annecy.fr/Newsletters/Newsletter-Annecy/Newsletter-Utilisateurs
- [x] Musées de la Ville de Chambéry (*mensuel*) — https://www.chambery.fr/536-newsletter-des-musee-de-la-ville-de-chambery.htm
- [x] Savoie Mont Blanc (magazine — plutôt tourisme) — https://www.savoie-mont-blanc.com/newsletter
- [x] OT Chamonix-Mont-Blanc — https://www.chamonix.com/newsletter,500,fr.html
- [x] _(2e rideau, généraliste)_ Grand Chambéry · Grand Annecy · Ville de Chambéry · Ville d'Annecy

## Nice / Alpes-Maritimes
- [ ] ⭐ **Explore Nice Côte d'Azur** (OT Nice, agenda sorties) — https://www.explorenicecotedazur.com/
- [x] ⭐ **Palais des Festivals Cannes** (*mensuel*) — https://en.palaisdesfestivals.com/newsletter-subscribe/
- [x] ⭐ **Côte d'Azur France** (CRT / Dépt 06) — https://cotedazurfrance.fr/sabonner_aux_newsletters/
- [x] ⭐ **Menton, Riviera & Merveilles** (*mensuel*) — https://www.menton-riviera-merveilles.fr/sinscrire-a-la-newsletter/
- [ ] ⭐ **Sortir à Cannes** (SEMEC) — https://www.sortiracannes.com/agenda
- [x] Opéra Nice Côte d'Azur — https://www.opera-nice.org/newsletter/
- [ ] Théâtre National de Nice (TNN) — https://www.tnn.fr/fr/
- [ ] Anthéa (Antibes) — https://www.anthea-antibes.fr/
- [ ] Fondation Maeght (Saint-Paul-de-Vence) — https://www.fondation-maeght.com/
- [ ] Théâtre de Grasse — https://www.theatredegrasse.com/
- [ ] Forum Jacques Prévert (Carros) — https://forumcarros.com/
- [ ] MAMAC Nice — https://www.mamac-nice.org/
- [ ] Musée Matisse Nice — https://www.musee-matisse-nice.org/
- [ ] Villa Arson (Nice) — https://villa-arson.fr/newsletter/
- [ ] Nice Jazz Festival — https://www.nicejazzfest.fr/
- [ ] Jazz à Juan (Antibes) — https://jazzajuan.com/
- [ ] Nuits du Sud (Vence) — https://www.nuitsdusud.com/
- [ ] Antibes Juan-les-Pins Tourisme — https://www.antibesjuanlespins.com/
- [ ] Cannes.com (Ville de Cannes) — https://www.cannes.com/
- [x] Forum Sirius (billetterie / agenda spectacles Nice) — https://www.forumsirius.fr/orion/tdn.phtml?fiche=news

## Piémont
- [x] ⭐ **GuidaTorino** (agenda *hebdo*, Turin + environs) — https://www.guidatorino.com/iscrizione-newsletter/
- [ ] ⭐ **Mentelocale Torino** (agenda *hebdo*) — https://www.mentelocale.it/torino/
- [x] ⭐ **Turismo Torino e Provincia** (*mensuel*) — https://turismotorino.org/it/iscrizione-newsletter
- [ ] ⭐ **Fondazione Torino Musei** (GAM + Palazzo Madama + MAO) — https://www.fondazionetorinomusei.it/it/newsletter
- [x] ⭐ **Fondazione Piemonte dal Vivo** (*mensuel*, tout le Piémont) — https://piemontedalvivo.it/newsletter/
- [ ] Museo Nazionale del Cinema (*hebdo*) — https://www.museocinema.it/it/newsletter/subscribe
- [ ] Museo Egizio — https://www.museoegizio.it/newsletter/
- [ ] Teatro Regio Torino — https://www.teatroregio.torino.it/newsletter
- [ ] Fondazione Circolo dei Lettori — https://www.circololettori.it/newsletter/
- [ ] OGR Torino — https://ogrtorino.it/newsletter
- [ ] Salone del Libro — https://www.salonelibro.it/info/form-newsletter-pubblico-generico.html
- [ ] MITO SettembreMusica — https://www.mitosettembremusica.it/it
- [ ] Kappa FuturFestival — https://www.kappafuturfestival.it/en/newsletter
- [ ] Collisioni (Alba/Barolo) — https://www.collisioni.it/
- [ ] Fiera del Tartufo Bianco d'Alba — https://www.fieradeltartufo.org/
- [ ] Ente Turismo Langhe Monferrato Roero (*mensuel*, Cuneo/Asti) — https://www.enteturismolmr.it/newsletter/
- [ ] Torinodanza Festival — https://www.torinodanzafestival.it/
- [ ] Teatro Stabile di Torino — https://www.teatrostabiletorino.it/
- [ ] VisitPiemonte DMO (plutôt corporate) — https://www.visitpiemonte-dmo.org/newsletter/
- [ ] Reggia di Venaria — https://lavenaria.it/it

## Vallée d'Aoste
- [x] ⭐ **Forte di Bard** (mostre/concerti, top venue) — https://www.fortedibard.it/iscrizione-newsletter/
- [x] ⭐ **Fondation Grand Paradis** (festival/castelli, *max 3/mois*) — https://www.grand-paradis.it/it/fondation-grand-paradis/newsletter
- [ ] ⭐ **LoveVDA — Office Régional du Tourisme** (agenda régional, bilingue) — https://www.lovevda.it/it
- [x] ⭐ **Musicastelle Outdoor** (festival musique altitude) — https://www.musicastellevda.it/contatti/
- [x] ⭐ **Aosta Classica** (festival musique classique) — https://aostaclassica.it/
- [ ] AperòNews (AostaSera, *hebdo weekend*) — http://eepurl.com/hoVAyj
- [ ] Breuil-Cervinia / Cervino Tourism — https://cervinia.it/
- [ ] Courmayeur Mont Blanc — https://www.courmayeurmontblanc.it/
- [ ] OT régional (liste PRO) — https://turismo.vda.it/iscrizione-alla-newsletter/

## Types nouveaux (cinéma art & essai, traditions, instituts culturels)
- [ ] Cinema Massimo (Torino, art & essai) — https://www.cinemamassimotorino.it/ _(form home)_
- [ ] Les Écrans du Sud (réseau art & essai PACA, 06) — https://seances-speciales.fr/ _(form home)_
- [x] LoveLanghe (traditions/sagre Langhe-Cuneo) — https://www.langhe.net/newsletter/
- [ ] Institut français Italia (antenne Torino) — https://www.institutfrancais.it/ _(form pied de page)_

---

## À savoir
- Certaines envoient via un **ESP** (Brevo/Sendinblue, Mailchimp, Mailjet…) → le
  domaine expéditeur réel peut différer du domaine du site. Si un mail n'est pas
  auto-classé, ajouter ce domaine à `config/whitelist_gmail.txt`.
- Sur certains formulaires (Courmayeur, offices « pro »), **décocher** les options
  MICE / tour-opérateurs pour ne recevoir que l'agenda culturel.
- Pistes **sans newsletter dédiée** (couvertes autrement) : Saison Culturelle VdA,
  Teatro Splendor, Comune di Aosta → passent par LoveVDA ; Fête du Lac d'Annecy →
  Ville d'Annecy ; provinces piémontaises isolées → couvertes par Piemonte dal Vivo
  (filtre géo) et Ente Turismo LMR.
