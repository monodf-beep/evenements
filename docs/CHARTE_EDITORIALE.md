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

Savoie/Haute-Savoie · Piémont · Vallée d'Aoste · Nice/Alpes-Maritimes. **Tout le
reste = hors périmètre** (un événement en Lombardie, à Paris… → score 0 / rejet).
Le territoire doit toujours être nommé : **ville → province/département → territoire**.

## 3. Critères de sélection (rappel du scoring)

**Définition d'un événement.** Une manifestation **culturelle** à laquelle le **public
peut assister**, à une **date à venir** (ou en cours), dans un lieu — expo, concert,
spectacle, conférence, rencontre, atelier, visite, projection, festival. On y va pour
découvrir/apprendre/se cultiver. **N'est PAS un événement** (→ rejet) : l'actualité
institutionnelle (réunion de conseil, convention, subvention, nomination, communiqué),
une inauguration ou remise de prix **déjà passée**, un sujet d'infrastructure/voirie —
bref tout ce à quoi on ne peut pas **assister à une date**.

Un événement mérite la mise en avant s'il :
- **transmet un savoir rare** (architectural, historique, linguistique, gastronomique,
  scientifique — pas du tout-venant) ;
- **engage un regard** (point de vue, thèse — pas seulement divertir) ;
- **connecte le local à l'universel** (escalier) ;
- bonus : **bilingue FR/IT** ou en langue de territoire (savoyard, piémontais…).

Exclusions automatiques : exercices civils/militaires, sagres génériques, concerts de
masse sans ancrage, foires/salons commerciaux, comédie de boulevard / humour généraliste.

## 4. Structure d'un article événement

1. **Titre** — informatif et incarné, pas racoleur (voir §7 anti-dark-pattern).
2. **Chapô** (1-2 phrases) — l'essentiel + l'angle (l'escalier).
3. **Contexte géographique** — lieu précis, **ville, province/département, territoire**.
4. **Corps** — le savoir transmis, le regard ; relie au territoire et au-delà.
5. **Encadré pratique** — dates, lieu, accès, tarif/gratuité, lien officiel.
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

## 6. Ton & langue

Registre soutenu mais accessible, phrases claires, pas de jargon gratuit. Bilingue
**FR/IT** assumé (la langue du territoire est une valeur). Pas de superlatifs creux
(« incontournable », « magique », « à ne pas manquer »).

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
