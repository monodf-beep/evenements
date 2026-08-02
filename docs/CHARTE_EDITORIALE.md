# Charte éditoriale — écosystème Cultura Sabauda

> **Portée** : ce document est **commun aux projets** de l'écosystème (Observatoire
> économique Sabaudo, Agrégateur d'événements, futur Shopping Guide). Il a vocation
> à être **extrait dans `cultura-core`** (dépôt partagé / miroir Obsidian) comme
> source unique de vérité éditoriale. Toute amélioration se fait ici puis se
> resynchronise. — v1 (2026-06-30), à enrichir (voir `docs/BACKLOG.md`).

## 1. Mission & positionnement

Cultura Sabauda = « *Internazionale* + *Le Monde Diplomatique* » appliqués à l'espace
alpin occidental (Savoie · Piémont · Vallée d'Aoste · Nice). Éditorial **sérieux,
evergreen, exigeant** — l'inverse d'un annuaire touristique (« anti-GuidaTorino »).

**Principe de l'escalier** : partir d'un ancrage local concret (un événement, un lieu)
pour monter vers une **question qui dépasse le territoire** (mémoire, transmission,
identité alpine, art, langue). Un bon article relie le particulier à l'universel.

## 2. Périmètre géographique (strict)

Savoie/Haute-Savoie · Piémont · Vallée d'Aoste · **Comté de Nice**. **Tout le
reste = hors périmètre** (un événement en Lombardie, à Paris… → score 0 / rejet).
Le territoire doit toujours être nommé : **ville → province/département → territoire**.

**Comté de Nice ≠ Alpes-Maritimes** (arbitrage Franck, 2026-08-02). Le quatrième
territoire n'est pas le département mais l'**arrondissement de Nice** : Nice, Menton,
Villefranche, la Roya, la Vésubie, la Tinée… Les communes de l'**arrondissement de
Grasse** — Cannes, Antibes, Grasse, Cagnes-sur-Mer, Vence, Saint-Paul-de-Vence,
Mandelieu-la-Napoule, Mouans-Sartoux, Saint-Laurent-du-Var — sont **hors périmètre**,
pas seulement sans étiquette : *« on ne devrait pas avoir d'événements sur ces
territoires pour le moment »*. La frontière est le Var, et elle correspond exactement
au découpage administratif.

Référence vérifiable : `config/communes_comte_de_nice.json` (101 communes pour Nice,
62 pour Grasse — total 163, le compte exact du département, donc listes complètes et
disjointes), lue par `utils/sources.est_comte_de_nice()` et
`est_arrondissement_grasse()`. On ne filtre PAS sur des mots-clés : « Vence » est
contenu dans « Provence », « Grasse » dans « grasse matinée ». La comparaison se fait
sur le champ `ville`, où elle est exacte.

## 3. Critères de sélection (rappel du scoring)

**Définition d'un événement.** Une manifestation à laquelle le **public peut assister**,
à une **date à venir** (ou en cours), dans un lieu. On couvre **large** (à la manière de
GuidaTorino) : expos, concerts, spectacles, festivals, **sagre & gastronomie**, **marchés**
(fleurs, antiquaires, brocante, artisanat), sport, cinéma, fêtes populaires… **N'est PAS un
événement** (→ rejet) : actualité institutionnelle (réunion, convention, subvention,
nomination, communiqué), inauguration/remise de prix **déjà passée**, infrastructure/voirie,
consultation publique — tout ce à quoi on ne peut pas **assister à une date**.

**Public VISÉ, pas seulement public ADMIS** (arbitrage Franck, 2026-08-02). Le critère
« le public peut assister » ne suffit pas : un congrès scientifique ou un salon B2B a
souvent une inscription ouverte, et n'intéresse pourtant pas nos lecteurs. Agenda
Sabauda s'adresse à des **habitants et des visiteurs**, pas à des **congressistes**.
→ **Hors périmètre** : congrès et colloques professionnels ou scientifiques, salons
B2B, conventions d'entreprise, séminaires sectoriels, journées d'étude d'une filière —
*même ouverts sur inscription*. Cas réels écartés le 2026-08-02 : *IASP World
Conference*, *Colloque International Villes et Santé Mentale*, *EVO 2026*.
→ **Dans le périmètre**, en revanche : les manifestations à destination du grand public
même quand elles portent un nom de « salon » ou de « rencontre » — Salon du livre,
foire artisanale, salon des vins, rencontre avec un auteur, conférence grand public
d'un musée. La catégorie « Conférences & Rencontres » reste donc pleinement active.
Le partage se fait sur **à qui ça s'adresse**, pas sur le format ni sur le titre.

**Le score = IMPORTANCE, pas profondeur culturelle.** On mesure si l'événement va *réunir du
monde* / *compte dans le territoire*. Somme de 5 critères (0-10) :
- **Notoriété du lieu** (0-3) — lieu emblématique très cité vs local modeste (pondéré par la
  taille de la commune) ;
- **Organisateur & moyens** (0-2) — institution / gros opérateur / grand festival vs petit ;
- **Édition & tradition** (0-2) — rendez-vous historique, édition élevée, anniversaire ;
- **Rayonnement** (0-2) — international / transfrontalier FR-IT > régional > local ;
- **Spécificité territoriale** (0-1) — identitaire vs générique/franchise.

**Deux niveaux de valorisation** (comme GuidaTorino : « cosa fare » mis en avant + catalogue) :
- score **≥ 7** → **mise en avant** (home, **article LONG** rédigé + recherche web — file « À valider ») ;
- score **< 7** mais vrai événement → **catalogue** (site dédié, cherchable) — *jamais rejeté*.
  Le catalogue reçoit lui aussi un **article COURT** (1-2 paragraphes, sans recherche web),
  **jamais la description brute** — avec les **faits structurés** obligatoires (§5 bis :
  programme en liste, horaires, tarifs). Le choix long/court est **automatique par score**
  (réglage `auto`, `utils/settings`).
- non-événement → **rejeté**.

La **profondeur / l'escalier** (§1, §5) n'est **plus un filtre** : c'est un **principe de
RÉDACTION** (comment on traite un sujet) et un atout pour choisir les mises en avant.

## 4. Structure d'un article événement

1. **Titre** — informatif et incarné, pas racoleur (voir §7 anti-dark-pattern).
2. **Chapô** (1-2 phrases) — l'essentiel + l'angle (l'escalier).
3. **Contexte géographique** — lieu précis, **ville, province/département, territoire**.
4. **Corps** — le savoir transmis, le regard ; relie au territoire et au-delà.
5. **Encadré pratique** — dates, lieu, accès, tarif/gratuité, lien officiel.
   ⚠️ **Sur le site (The Events Calendar), l'encadré pratique est rendu NATIVEMENT**
   (Quand / Où / Tarif / Catégorie, via les champs `as_*`). On ne le **répète donc PAS**
   en prose dans le corps de l'article : le corps reste **éditorial** (chapô + corps +
   programme en liste). Les faits pratiques alimentent les **champs structurés**, pas un
   second bloc texte (sinon doublon à l'affichage).
6. **Crédit source** — voir §8.

## 5. Enrichissement (recherche d'information)

Un titre RSS brut ne suffit pas : on **enrichit** avant rédaction. Règles de ce qu'on
va chercher (web/sources officielles) **selon la nature** de l'événement :

| Élément déclencheur | Information à aller chercher |
|---|---|
| **Lieu** (théâtre, musée, château, abbaye…) | histoire/identité du lieu, importance patrimoniale |
| **Artiste / groupe de musique** | origine (local ? de territoires proches ? renommée), genre |
| **Conférencier / auteur** | qui il/elle est, pourquoi ça compte |
| **Plat / produit** (si intérêt culturel local) | origine, tradition, ce qu'il raconte du territoire |
| **Œuvre / exposition** | artiste, période, intérêt |
| **Date / récurrence** | s'agit-il d'un rendez-vous historique, d'une édition anniversaire ? |

Garde-fous d'enrichissement :
- **Ne jamais inventer** : si une info n'est pas trouvée/sourcée, on ne l'écrit pas.
- **Pertinence territoriale** : un groupe local ou de territoire proche est un angle ;
  un groupe sans lien n'est pas mis en avant pour lui-même.
- **Coût maîtrisé** : l'enrichissement web a un coût API → réservé aux événements
  retenus (score ≥ seuil), pas à toute la collecte.

**Matière : le maximum, par des moyens qui tiennent juridiquement.** L'objectif est
d'avoir la matière la plus riche possible. Trois leviers, dans l'ordre de valeur :

1. **Dossier de presse (source primaire, prioritaire)** — en tant que média, on obtient
   des organisateurs, gratuitement et avec droits d'usage, le dossier complet + photos
   HD (canal `press_kits`, label Gmail « Presse »). C'est **plus** et **mieux** que tout
   article payant. À privilégier partout où c'est disponible → viser l'**accréditation**
   auprès des lieux clés (opéras, musées, festivals).
2. **Faits vs expression** — les **faits** (dates, lieu, programme, distribution, tarifs)
   ne sont **pas protégés** : on les récupère **partout**, y compris en lisant la presse
   (même payante, via extraits/recherche). En revanche on **ne recopie jamais
   l'expression** d'un article (phrases, formules, l'analyse d'un journaliste) et on **ne
   crédite pas** la presse : l'attribution et la citation vont à la **source officielle**.
3. **Source officielle libre** — page de l'organisateur/du lieu, agenda, billetterie :
   c'est là qu'on vérifie les faits et qu'on prend l'expression réutilisable.

On **ne contourne pas** un mur d'accès par des moyens techniques (login, ripper) : le
risque juridique retomberait sur l'éditeur nommé. Le bon canal pour « passer le
paywall » légalement, c'est l'**accréditation presse** (levier 1). Si un événement
n'a **aucune** source libre et **aucun** dossier, il reste mince et n'est pas mis en avant.

## 5 bis. Faits structurés obligatoires (selon le type)

L'enrichissement ne produit pas qu'une prose : il doit **garantir la présence des faits
que l'abonné cherche**, faits que §5 (levier 2) nous autorise justement à récupérer partout
(ils ne sont pas protégés). La prose peut être maigre (1-2 paragraphes pour un score < 7,
c'est acceptable) ; **les faits, eux, sont obligatoires dès que la matière les contient**,
quel que soit le score, et **quel que soit le mode** (court comme long).

Règle de forme : **un programme, un line-up, un déroulé de séances = une LISTE**, jamais un
paragraphe qui les noie. C'est de la structure, pas de l'expression — on la préserve telle
quelle. (Côté code, la liste passe par un champ dédié du schéma d'enrichissement pour ne
jamais être perdue à la compression, même en mode court.)

| Type d'événement | Faits obligatoires (si présents dans la matière) | Piège fréquent à ne pas rater |
|---|---|---|
| **Exposition** | **horaires d'ouverture**, tarif/gratuité, artistes, plage de dates | les **horaires ≠ la plage de dates** : « du 5 juin au 30 août » ne suffit pas |
| **Concert / série** | **line-up + horaires**, salle, billetterie | — |
| **Spectacle** | distribution/casting, durée, réservation | — |
| **Festival / multi-jours** | **programme par jour** (liste), line-up complet | ne pas résumer le programme en prose : le rendre en liste |
| **Sagra / gastronomie** | ce qu'on **mange/boit**, dates, prix | — |
| **Marché** (fleurs, antiquaires, brocante, artisanat) | **récurrence** (« chaque 1er dimanche »), horaires, type d'exposants | une date unique alors que c'est un rendez-vous récurrent |
| **Conférence** | intervenant, sujet, **langue (FR/IT)**, inscription | — |
| **Sport** (course, match, compétition) | discipline, **horaire de départ**, parcours/lieu, catégories | **deux publics** : *spectateurs* (venir voir, souvent gratuit) ≠ *participants* (s'inscrire, payer) — ce sont deux infos pratiques distinctes |
| **Cinéma** (séance, festival, plein air) | film(s) + **horaires de séance**, lieu, tarif, invité éventuel | **VO/VF / langue** (capital sur territoire bilingue, §6) ; plein air : gratuité + heure (tombée de nuit) |
| **Fêtes populaires** (fête patronale, carnaval, feux) | **programme multi-jours** (temps forts : défilé, feu d'artifice, bal), gratuité | **récurrence** (annuelle, date fixe ou mobile) |

Principe transverse : **une info pratique manquante que la matière contenait est une
erreur**, pas une simplification. Mieux vaut deux paragraphes honnêtes + une liste de faits
complète qu'un bel article qui a perdu les horaires.

## 6. Ton & langue

Registre soutenu mais accessible, phrases claires, pas de jargon gratuit. Bilingue
**FR/IT** assumé (la langue du territoire est une valeur). Pas de superlatifs creux
(« incontournable », « magique », « à ne pas manquer »).

**Casse — jamais de TOUT EN CAPITALES.** Un titre, un intertitre ou un nom d'événement
ne s'écrit **jamais entièrement en majuscules**, même quand la source (affiche, flux RSS,
billetterie) le fournit ainsi — ex. « COREOGRAFIE DEL POSSIBILE » → « Coreografie del
Possibile ». Les capitales intégrales, c'est **crier** ; c'est illisible et mauvais pour le
SEO. On **normalise en casse normale** : capitale à l'initiale + noms propres, en
respectant la langue (règles FR/IT). On **préserve** les sigles/acronymes réels (FIAF, MAO,
ONU) et la casse voulue d'une marque (iMac, PSG). En cas de doute, casse de phrase.

**Signaux d'écriture IA à éviter.** Le **tiret cadratin** (« — », « – ») en incise est la
signature n°1 d'un texte généré : on l'évite, on préfère la **virgule**, la **parenthèse**,
le **deux-points** ou le **point**. Idem pour les autres tics : « il ne s'agit pas seulement
de X, mais de Y », les triades systématiques (« rythme, mémoire et transmission »), les chutes
en « une invitation à… ». Écris **simple et incarné**, pas « augmenté ».

## 6 bis. Italien & bilinguisme (FR/IT)

Le site est **bilingue** : chaque contenu a une version FR et une version IT (pages
jumelles Polylang, `scripts/translate_events.py`). **Règle mère : la version IT obéit à
la MÊME charte que la version FR** (escalier §1, périmètre §2, ton §6, casse §6, dark
patterns §7, images §9). **Traduire n'est pas recopier** : on *ré-applique* la charte en
italien, on ne translittère pas un titre racoleur ou tout-capitales. Une mauvaise version
FR ne doit pas produire une mauvaise version IT.

- **Registre** : soutenu mais accessible, comme en FR. Boussole : *Internazionale* (le
  média italien de référence de notre positionnement §1). Pas de calques du français.
- **Superlatifs creux interdits (équivalents IT)** : « imperdibile », « da non perdere »,
  « evento clou », « magico », « unico/straordinario » (quand c'est vide), « il migliore ».
  Même bannissement qu'en FR (« incontournable », « magique »…).
- **Dark patterns en italien** (§7) : fausse urgence (« ultimi posti! », « solo oggi »,
  « affrettati »), clickbait (« non crederai… »), confirmshaming — **interdits** aussi.
- **Casse** : casse de phrase, **jamais** le *title case* anglais (Chaque Mot En Majuscule)
  ni le tout-capitales. Mois et jours en **minuscule** (« 5 luglio », « domenica »). Sigles
  réels et marques préservés.
- **Toponymes dans la langue de l'article** *(décidé)* : FR = Turin, Aoste, Nice, Verceil ;
  IT = **Torino, Aosta, Nizza, Vercelli**. On nomme dans la langue du lecteur, et on garde
  la chaîne **ville → province → territoire** (§2/§3) traduite en conséquence (Savoia,
  Piemonte, Valle d'Aosta, Contea di Nizza).
- **Faits vs expression** (§5) : les faits (dates, programme, lieu) sont identiques dans les
  deux langues ; seule l'**expression** est réécrite. Un `programme` en liste se traduit
  ligne à ligne, sans en perdre.

Enforcement : `scripts/translate_events.py` doit porter ces règles dans son prompt (pas une
traduction littérale) — même logique que le garde-fou casse ajouté à `scripts/enrich.py`.

## 7. Éthique & UX — dark patterns proscrits

L'écosystème **n'utilise aucun dark pattern**. Sont **interdits** :
- **Urgence/rareté factices** (« plus que 2 places ! » non vérifié, comptes à rebours).
- **Titres-pièges / clickbait** (« vous n'allez pas croire… »).
- **Confirmshaming** (culpabiliser un refus).
- **Cases pré-cochées**, opt-in déguisé, **inscriptions difficiles à annuler**.
- **Publicité déguisée** en contenu éditorial (tout partenariat est signalé).
- **Collecte de données** non nécessaire ; respect RGPD, consentement clair.
Principe : **le lecteur d'abord**. La confiance prime sur le clic.

## 8. Attribution des sources

- Sources **institutionnelles/officielles** : créditées et liées (logo + lien).
- Sources **presse** (radar) : servent à détecter, **jamais créditées/liées** dans le
  rendu (pas de publicité aux médias concurrents) ; l'info est attribuée à l'acteur primaire.
- Images : voir §9.

### Plusieurs sources pour un même événement — priorité & fusion
Un même événement peut arriver par **plusieurs flux** (institutionnel + radar + office
de tourisme). On **ne garde PAS la version la plus pauvre** : on **déduplique** les
candidats (même sujet via `same_story`, même territoire, dates proches) et on
**fusionne vers la source la plus riche et la plus autoritaire**.

Ordre de priorité : **source primaire/officielle** (lieu, organisateur) > office de
tourisme / institution > **radar (presse)**. À information égale, la version **avec
photo** et au **contenu le plus complet** l'emporte. Le radar ne « gagne » jamais :
il détecte, il ne fournit pas le contenu. La fusion récupère le meilleur de chaque
source (image de l'un, texte complet de l'autre, lien officiel d'un troisième).

## 9. Images

- Priorité : **vraie photo de l'événement** fournie par la source (institutionnelle).
- **Jamais** d'image servie par un CDN de presse/agrégateur (voir
  `config/blocked_image_domains.txt`).
- Si **aucune image** : ne rien afficher pour l'instant. L'**alternative** (image OG
  de la page source, ou visuel culturel généré par territoire/catégorie — **pas** la
  bannière « Observatoire économique ») est une **tâche à définir** (`docs/BACKLOG.md`).
- Toujours respecter les droits (légende/crédit quand requis).

## 10. Gouvernance

- **Franck = responsable de la conformité (RC)** : validation humaine obligatoire.
- **Tout part en brouillon** (WordPress `draft`) — rien ne se publie automatiquement
  sur la home Cultura Sabauda.
- Le **site dédié** (volume/SEO) peut auto-publier des fiches **enrichies et relues**,
  jamais l'écho brut d'un flux.

## 11. Rythme de la newsletter (canal automatique)

La newsletter est le seul canal **entièrement automatique** : aucun humain ne rattrape une
édition ratée. Sa règle d'or est donc **la fraîcheur**. Les retours des éditeurs de
newsletters d'événements locaux qui tiennent dans la durée convergent : *ce qui fait
revenir l'abonné n'est pas un thème qui change, c'est une voix constante + des événements
qui, eux, changent* — la fraîcheur vient de la **fenêtre temporelle courte**, pas d'un
habillage éditorial renouvelé.

**Axe par défaut = temporel, pas thématique.** Un tri par score seul est un piège : un
événement long (une expo sur 3 mois) chevauche chaque fenêtre hebdomadaire et **squatte la
tête de la newsletter pendant toute sa durée**. On structure donc par **statut temporel** :

- **héros / « à la une » = ce qui *ouvre* cette semaine** (le neuf) ;
- **« ça continue » = les événements longs déjà annoncés**, rétrogradés en liste compacte —
  jamais repris en héros ;
- **« dernière chance » = ce qui *ferme* bientôt** — service réel et **factuel** (donc pas
  un dark pattern §7, contrairement à une urgence inventée).

Ainsi un événement de 3 mois apparaît **à son ouverture**, puis discrètement, puis à sa
fermeture — jamais douze fois en tête.

**Autres règles :**
- **Tri assumé, pas déversement.** Une sélection resserrée (poignée d'événements réellement
  mis en avant) vaut mieux qu'une liste exhaustive : la rareté est un signal de qualité.
- **Passe de fraîcheur avant génération.** On vérifie que les événements retenus sont
  encore **à venir et non annulés** — l'abonné ne doit pas ouvrir sur du périmé ou du complet.
- **Pas de fuite de texte interne.** Le résumé d'une carte n'affiche jamais la
  *justification de scoring* du LLM (texte écrit pour le back-office, pas pour un lecteur) :
  à défaut de chapô rédigé, on retombe sur une description propre, pas sur du texte technique.
- Le **thème** (« spécial sagre d'été ») reste possible comme **variante ponctuelle**
  assumée, jamais comme mécanique de base.

## Cinéma — que garde-t-on ? (règle du 27 juillet 2026)

Le cinéma est admis, mais **PAS la programmation de projections en salle**. On distingue :

- **GARDÉ** : les vrais **festivals de cinéma** (événement multi-films à identité de
  festival : nom, édition, sélection — ex. Torino Film Festival, un festival dédié à
  Marilyn) **et** le **cinéma en plein air** (projections estivales en extérieur portées
  par une ville, une association ou un lieu culturel — un rendez-vous événementiel).
- **EXCLU** (score 0), même en salle d'art et d'essai ou en lieu institutionnel : les
  **rétrospectives, cycles et hommages** à un réalisateur (ex. « Les films de Bong
  Joon-ho » au Cinema Massimo), les **projections d'un film en salle** (commerciale ou
  non), séances uniques, ciné-clubs, avant-premières isolées.

Le critère : *festival ou plein air → garder ; simple programmation de projections
(aussi culturelle soit-elle) → exclure*. En cas de doute hors plein air, **exclure**.
Une source qui ne promeut que du cinéma commercial n'entre pas (couvert par cette règle,
puisque non-festival). Implémenté à l'évaluation (`scripts/evaluator` — piège cinéma) et
en nettoyage rétroactif (`scripts/cleanup_cinema`, tri par organisateur, jumeaux FR/IT
traités ensemble, réversible via la corbeille WordPress `cs/v1/trash`).
