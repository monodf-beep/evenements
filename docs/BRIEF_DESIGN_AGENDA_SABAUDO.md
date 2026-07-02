# BRIEF DESIGN — Agenda Sabaudo (site public de volume)

*Brief complet à destination de Claude Design. Rédigé le 02/07/2026 à partir de trois analyses
dédiées : dissection UX de guidatorino.com (pages réelles), fiche produit compilée depuis le
backoffice, architecture de l'information + SEO. Le brief couvre TOUT le site, pas seulement
la homepage.*

---

## 0. Ce qu'on attend de toi (Claude Design)

Tu conçois l'UX/UI du site public **Agenda Sabaudo**. Le modèle d'expérience est
**guidatorino.com** — un guide urbain qui « marche » depuis 15 ans — dont on reprend les
patterns structurels (détaillés §2) en les modernisant (responsive, accessibilité, sans la
densité publicitaire). **La direction artistique t'appartient** : tu appliques la charte
graphique Cultura Sabauda (tokens §3) comme tu l'entends — le brief fixe la structure, les
contenus et les interdits, pas les maquettes.

**Anti-slop, non négociable** : ce site doit ressembler à un guide édité par une rédaction,
pas à un template. Interdits absolus : dégradés violets/bleus génériques, glassmorphism,
blobs flottants, emoji en guise d'icônes dans l'UI publique, hero vide avec slogan centré,
sections « features » de SaaS, carrousels auto, animations décoratives, lorem ipsum. Chaque
pixel sert l'information : **une date, un lieu, un titre, une photo**. L'austérité éditoriale
EST le branding (c'est la leçon n°1 de GuidaTorino).

---

## 1. Le projet

### 1.1 Deux marques, deux niveaux

| | **Cultura Sabauda** (existant) | **Agenda Sabaudo** (à concevoir) |
|---|---|---|
| Nature | Média culturel bilingue FR/IT, curé, exigeant | **L'agenda exhaustif des sorties** de l'espace alpin occidental |
| Contenu | Événements score ≥ 7, validés un à un, articles rédigés | Événements score 4–6 automatiques + choix manuels : **catalogue de volume, cherchable** |
| Promesse | Profondeur, mise en perspective | **Exhaustivité** : « un vrai événement n'est jamais rejeté » |
| Rôle SEO | Autorité éditoriale | **Capter les requêtes « que faire à/en… »** |

Agenda Sabaudo assume la couverture large « à la manière de GuidaTorino » : expos, concerts,
sagre, marchés, sport, cinéma, fêtes populaires. Le footer le dit : *« Une sélection culturelle
proposée par la rédaction, en collaboration avec Cultura Sabauda »* — Agenda Sabaudo est la
marque grand public, Cultura Sabauda la caution éditoriale (logo éditeur discret, comme sur la
newsletter existante).

### 1.2 Le territoire (l'identité du site)

4 territoires transfrontaliers FR/IT — c'est LA différenciation vs tous les agendas
mono-ville :

| Valeur technique | Libellé public FR | Libellé public IT |
|---|---|---|
| `Savoie` | Savoie / Haute-Savoie | Savoia / Alta Savoia |
| `Piemonte` | Piémont | Piemonte |
| `Vallee-Aoste` | Vallée d'Aoste | Valle d'Aosta |
| `Nice` | Nice / Alpes-Maritimes | Nizza / Alpi Marittime |

Chaque territoire a déjà une couleur d'identification (héritée de la newsletter, réutilisable
en pilules/tags) : Savoie bleu (`#e6effb`/`#1a56b0`), Piémont rouge (`#fdeaea`/`#b3261e`),
Vallée d'Aoste vert (`#e7f6ea`/`#1e7d34`), Nice orange (`#fff1e0`/`#b25e00`).

### 1.3 Les 11 catégories (vocabulaire fermé)

Expositions & Patrimoine · Concerts & Musique · Spectacle vivant · Festivals ·
Gastronomie & Sagre · Marchés & Foires · Sport · Cinéma · Jeune public & Famille ·
Conférences & Rencontres · Fêtes & Traditions populaires.

### 1.4 Volumétrie & plateforme

~90 sources, des dizaines de nouveaux événements/jour, 50–200 événements actifs simultanés.
Plateforme : **WordPress** (2ᵉ site, alimenté en brouillons par le backoffice existant).
Domaine pressenti : agendasabaudo.eu (à confirmer — n'existe pas encore en config).

---

## 2. La référence : GuidaTorino — ce qu'on reprend, ce qu'on modernise

*(Issu de la dissection page par page du site réel.)*

### 2.1 Les 8 patterns à REPRENDRE (c'est le cœur du brief)

1. **Le temps est l'architecture n°1.** Chez GuidaTorino, Oggi / Domani / Weekend / le mois
   courant existent comme items de menu, chips de filtres, sections de home ET pages SEO
   dédiées. L'utilisateur d'un agenda entre par « quand », pas par « quoi ».
2. **URLs evergreen recyclées.** Leur page « week-end » est la même URL depuis 2019, mise à
   jour chaque semaine → autorité SEO cumulée + un favori stable pour le lecteur. On fait
   pareil : `/ce-week-end/` fixe, contenu roulant.
3. **Double registre articulé** : sélection narrative (listicle « Les 10 choses à faire ce
   week-end ») ↔ fiches structurées ↔ liste chronologique exhaustive. La curation en vitrine,
   l'exhaustivité à un clic, le listicle redistribue vers les fiches (maillage en étoile).
4. **Une seule grammaire de carte** : image ratio fixe + titre gras + **date toujours en
   première métadonnée**. Pas d'extrait sur les cartes événement : date + lieu suffisent.
   Zéro variation gratuite → scan ultra-rapide.
5. **Bloc pratique standardisé** à position fixe sur chaque fiche (Quand / Où / Prix /
   Infos / Carte) : le site se comporte comme une base de données habillée en magazine.
6. **Identité « guide papier »** : typo éditoriale affirmée (eux : Georgia serif partout),
   palette sobre avec UN accent fonctionnel, cartouches de rubrique en petites capitales.
   La crédibilité vient de la retenue.
7. **Relance de navigation systématique** : rangée de tuiles-catégories illustrées en pied de
   chaque page, sidebar/blocs répétant agenda + populaires + newsletter. Aucune impasse.
8. **Tagline de preuve** permanente (« La guida più amata dai torinesi »). Notre équivalent à
   trouver : ex. *« L'agenda des 4 territoires alpins, de Chambéry à Turin »*.

### 2.2 Ce qu'on MODERNISE (leurs faiblesses, constatées)

- Layout fixe 950 px, floats, GIFs → **responsive fluide, mobile-first** (leur trafic est
  mobile, leur design ne l'est pas).
- Densité publicitaire agressive (anchor + 2 skyscrapers + in-content) → **pas de pub au
  lancement** ; prévoir seulement 2 emplacements réservés à taille fixe (leaderboard sous H1,
  1 in-content) pour plus tard, sans layout shift.
- Recherche = un lien de menu → **loupe dans le header, overlay de recherche**.
- Newsletter à 2 clics via bannière-image → **formulaire inline 1 champ** répété (home,
  fin de fiche, footer).
- 154 événements sur une page sans pagination → **pagination crawlable** (§7.2).
- Aucun auteur/date de publication → nous : « Vérifié le JJ/MM » sur les fiches (confiance).
- Filtres = pages liées non combinables → nous : **filtres combinables AJAX + URL** (§8.2).

---

## 3. Charte graphique — tokens et règles (la DA reste à Claude Design)

**Tokens existants** (newsletter + backoffice, à respecter comme base) :

- **Marine profond** `#1a2b4a` (variante backoffice `#1f3a63`) — couleur de marque : masthead,
  titres, footer.
- **Rouge de Savoie** `#c8102e` — LE seul accent : CTA, point final du logotype
  (« Agenda Sabaudo**.** »), filets d'intertitres, états d'urgence (« dernier week-end »).
  Règle GuidaTorino : l'accent est rare, donc signifiant.
- Neutres : encre `#16202c`, gris `#6b7280`, bordures `#e5e7eb`, fond doux `#eef1f5`.
- Pilules territoires : les 4 duos pastel/foncé du §1.2.
- Logotype : wordmark « Agenda Sabaudo » + point rouge ; mention éditeur « Cultura Sabauda »
  discrète (logo 24 px, comme sur la newsletter).
- Intention déclarée de la charte : **« chaleureux, grand public »** — c'est un agenda de
  sorties, pas une revue savante.

**Liberté de Claude Design** : typographie (une piste : serif éditoriale pour titres — l'esprit
guide — avec une sans lisible pour les données pratiques ; à toi de trancher), échelle,
grilles, iconographie (trait simple, pas d'emoji), traitement des cartes, dark mode éventuel.
Contrainte : tout texte est du **texte HTML réel** (jamais de titres/dates en image — leçon
inverse de GuidaTorino dont le slider embarque le texte dans les visuels).

---

## 4. Architecture du site (inventaire complet)

URLs en FR ; miroir IT traduit (`/it/oggi/`, `/it/evento/...`). Détail bilinguisme §9.

### MVP

| Page | URL | Rôle / requête SEO cible |
|---|---|---|
| Home | `/fr/` | Vitrine de flux + distribution. « agenda culturel alpes » |
| Aujourd'hui | `/fr/aujourdhui/` | « que faire aujourd'hui à turin/annecy » |
| **Ce week-end** | `/fr/ce-week-end/` | **La requête reine.** URL fixe, contenu roulant |
| Ce week-end × territoire (×4) | `/fr/ce-week-end/piemont/` … | « que faire ce week-end à turin » |
| Cette semaine | `/fr/cette-semaine/` | |
| Territoire (×4) | `/fr/territoire/piemont/` … | Hub géographique, intro pérenne 150–250 mots |
| Catégorie (×11) | `/fr/evenements/concerts-musique/` … | Hub thématique, intro 100–150 mots |
| Croisements cat.×terr. (~12–16) | `/fr/evenements/concerts-musique/piemont/` | Seulement si ≥10 événements actifs (sinon simple filtre). Au lancement : Expositions×4, Concerts×4, Festivals×4, Sagre×Piémont+Savoie, Marchés×Piémont, Jeune public×Savoie |
| Fiche événement | `/fr/evenement/nom-ville/` | Sans millésime pour les récurrents (la fiche annuelle cumule l'autorité) |
| Listicle hebdo | `/fr/les-10-du-week-end/` | Le « 10 cose » à la GuidaTorino : URL fixe recyclée chaque semaine |
| Recherche | overlay + `/fr/recherche/` (noindex) | |
| Newsletter | `/fr/newsletter/` | Conversion — l'actif n°1 |
| À propos / Contact-Proposer un événement / Mentions / Confidentialité / **Politique crédits photos** | | Le formulaire « Proposez votre événement » = machine à contenu, à promouvoir partout |
| 404 | | Jamais une impasse : recherche + hubs + 4 cartes à venir |
| Flux RSS publics | `/fr/feed/` + par territoire/catégorie | Pour OT et médias locaux |

### V2

Archives mensuelles `/fr/agenda/2026/07/` · pages ville (seuil : ≥15 événements actifs —
Turin, Nice, Annecy, Chambéry, Aoste d'abord) · vue carte Leaflet/OSM togglable sur les hubs ·
météo contextuelle sur fiche (événements extérieurs, J-3) · facettes de recherche · badge
« Complet ».

---

## 5. Navigation

### Header (sticky, compact au scroll)

```
[Agenda Sabaudo.]   Aujourd'hui | Ce week-end | Catégories ▾ | Territoires ▾ | Agenda ▾ | 🔍 | FR|IT
```

- **Aujourd'hui** et **Ce week-end** : liens directs SANS sous-menu (les 2 actions les plus
  fréquentes = 1 clic). C'est l'arbitrage GuidaTorino : le temporel d'abord.
- **Catégories ▾** : les 11, avec pictos trait, 2 colonnes + « Toutes ».
- **Territoires ▾** : 4 entrées (+ villes principales en 2ᵉ niveau, v2).
- **Agenda ▾** : Cette semaine, mois courant (libellé dynamique « Juillet »), Les 10 du
  week-end.
- Commutateur **« FR | IT » en texte — JAMAIS de drapeaux** (un drapeau est un pays, pas une
  langue : le piège exact d'un site transfrontalier).

### Mobile
Header sticky : logo + loupe + burger. Burger plein écran : Aujourd'hui / Ce week-end en très
gros d'abord, puis accordéons Catégories, Territoires, FR|IT. Sur les pages de liste : barre de
chips temporelles scrollable sous le header (Aujourd'hui · Week-end · Semaine · Dates…).
Pas de bottom-tab-bar.

### Breadcrumb
Toutes pages sauf home, balisé `BreadcrumbList`. Fiche : `Accueil > Concerts & Musique >
Piémont > Nom` (chemin canonique = catégorie > territoire, quel que soit le chemin d'arrivée).

### Footer riche (outil SEO, contrairement au footer maigre de GuidaTorino)
4 colonnes : **Explorer** (temporels) · **Catégories** (11) · **Territoires** (4 + villes) ·
**Le projet** (À propos, Proposer un événement, Newsletter, Crédits photos, Mentions, RSS,
FR|IT). + ligne légale + mention « édité par Cultura Sabauda ».

---

## 6. Gabarits page par page

### 6.1 Home — une gare de tri, pas une vitrine vide

Ordre vertical (aéré, PAS la mosaïque dense 3 colonnes de GuidaTorino, mais son esprit) :

1. Header + **barre de raccourcis temporels** (chips : Aujourd'hui · Ce week-end · Cette
   semaine · Choisir des dates).
2. **Héro éditorial** : 1 événement à la une (sélection manuelle ; repli : meilleur score de
   la semaine) — grande image, kicker catégorie, titre, date en gros, pilule territoire +
   2–3 secondaires en cartes compactes à droite.
3. **« Ce week-end »** : cartouche de rubrique (petites capitales, à la GuidaTorino) +
   8–12 cartes standard + lien « Tout le week-end → ».
4. **« Le tour des territoires »** : 4 blocs (un par territoire, sa couleur en pilule),
   4–6 cartes compactes chacun + « Tout le Piémont → ». (Reprend la rubrique existante de la
   newsletter — cohérence de marque.)
5. **Rail catégories** : 11 tuiles illustrées horizontales scrollables (l'équivalent moderne
   des 6 tuiles GIF de GuidaTorino — LE pattern de relance).
6. **« Dernière chance »** : expositions/événements qui se terminent ≤ 14 jours (badge rouge).
7. **Bloc newsletter** inline : promesse datée « Le vendredi matin : le week-end des
   4 territoires » + 1 champ email.
8. **« Les 10 du week-end »** : carte large vers le listicle hebdo.
9. Footer.

H1 home : accroche éditoriale (« Que faire dans les Alpes, de Chambéry à Turin »), pas le nom
du site seul.

### 6.2 Hubs temporels (Aujourd'hui / Ce week-end / Cette semaine)

- H1 dynamique avec dates réelles : « Ce week-end dans les Alpes : 4–6 juillet ».
- **Chapô éditorial 2–3 phrases réécrit chaque semaine** (contenu unique, anti thin-content —
  c'est ce que fait GuidaTorino sur sa page week-end).
- Chips de sous-nav territoriales (« Ce week-end : Savoie · Piémont · Vallée d'Aoste · Nice »).
- Barre de filtres (territoire + catégorie — pas de filtre date : la page EST la date).
- Grille de cartes standard, paginée. Section séparée en bas : **« Expositions et événements
  en cours »** (les longues durées, pour ne pas noyer le flux daté).
- Cross-links de fin : autres hubs temporels + 4 territoires.

### 6.3 Pages territoire & catégorie

- H1 + **texte d'intro pérenne** (150–250 mots territoire, 100–150 catégorie) — indexable,
  au-dessus du flux.
- Chips de croisement (sur Piémont : ses catégories actives ; sur Concerts : ses 4
  territoires).
- « Ce week-end en/à X » en tête (4–8 cartes), puis flux chronologique complet paginé.
- Territoire : bloc « villes » (liens) + « dans les territoires voisins » en pied.

### 6.4 Fiche événement (LE gabarit critique — 2 niveaux de richesse)

**⚠ Contrainte produit majeure** : la masse des événements (score 4–6) n'a **PAS d'article
rédigé** (l'enrichissement est réservé au score ≥ 7). La fiche doit être **excellente en mode
minimal** : titre + dates + lieu + catégorie + description courte + image (ou bannière
territoire). Concevoir le mode minimal D'ABORD, le mode riche comme extension.

Ordre vertical (mobile-first) :

1. Breadcrumb.
2. **Héro** 16:9 (ou bannière territoire de repli — elles existent déjà, 1 par territoire) ;
   **crédit photo obligatoire** en 10–11 px sous l'image ; badges d'état ; kicker catégorie
   cliquable ; **H1** ; sous-titre lieu · ville · pilule territoire.
3. **Bloc pratique** (le « Quando/Dove/Prezzo » de GuidaTorino, mais AVANT le corps —
   desktop : colonne latérale sticky ; mobile : carte pleine largeur) :
   - 📅 Dates humanisées (« Du 4 juillet au 30 août », « Ce soir », « Tous les samedis
     jusqu'au 26 sept. ») ; 🕐 horaires ; 📍 lieu + adresse + lien itinéraire ;
   - 💶 prix — **« Gratuit » très visible** ;
   - 🎟 bouton « **Réserver — site officiel** » (lien sortant explicite, jamais déguisé en
     action interne) ; « Ajouter au calendrier » (.ics).
4. **Corps** : mode riche = article complet (chapô, corps, intertitres H2) ; mode minimal =
   description courte réécrite. Largeur de lecture ~660–700 px.
5. **Encadré « En pratique »** (mode riche : accès, parking, réservation, accessibilité,
   repli pluie).
6. **Bloc confiance** : « Informations : site de l'organisateur » + **« Vérifié le
   28/06/2026 »** — notre différenciateur d'agrégateur.
7. **Crédits** : photo ©, source des informations.
8. **3 rails de cartes liées**, dans CET ordre d'intention : **« Aux mêmes dates près
   d'ici »** → « Dans le même territoire » → « Même catégorie » (chacun avec « voir tout → »
   vers son hub).
9. Rail des 11 tuiles catégories (relance systématique, pattern GuidaTorino).

### 6.5 Listicle hebdo « Les 10 du week-end »

URL fixe recyclée chaque vendredi. H1 avec dates. Grammaire par item (calquée GuidaTorino) :
H2 nom court → image → paragraphe de synthèse → « **En savoir plus →** » vers la fiche.
Clôture : « Ce ne sont que quelques-uns des rendez-vous… » + lien vers `/ce-week-end/`.
C'est le contenu à partager (newsletter, réseaux) — soigner l'OpenGraph.

### 6.6 Recherche, newsletter, éditoriales, 404

- Recherche : overlay depuis la loupe ; résultats en cartes compactes ; « 0 résultat » propose
  TOUJOURS un élargissement (autres dates, territoire voisin).
- Newsletter : promesse + exemple de numéro (le gabarit magazine existe : hero « À la une »,
  « Aussi cette semaine », « Le tour des territoires ») + formulaire 1 champ + RGPD.
- À propos : le récit transfrontalier (E-E-A-T) ; Contact : formulaire + « Proposez votre
  événement » en avant.
- 404 : message court + recherche + liens temporels + 4 cartes à venir.

---

## 7. Le traitement du temps (le cœur d'un agenda)

### 7.1 Affichage des dates — règles fermes

- Ponctuel : « **Samedi 4 juillet, 21h** » (toujours jour de semaine). Relatif quand utile :
  « Ce soir », « Demain ».
- Longue durée : avant → « Du 15 mai au 30 août » ; pendant → « **En cours · jusqu'au
  30 août** » ; fin ≤ 14 j → « **Plus que 12 jours** » ; badge « **Dernier week-end** ».
  Dans les hubs temporels, les événements en cours vivent dans leur section dédiée (pas mêlés
  au flux daté) ; ce qui presse, c'est leur FIN.
- Récurrent : « Tous les samedis jusqu'au 26 sept. » + « Prochaine date : sam. 5 juillet »
  (c'est la prochaine occurrence qui classe).
- **« Date à confirmer »** : badge neutre, mois pressenti (« Septembre 2026 — date à
  confirmer »), exclu des hubs temporels, en fin de liste territoire/catégorie.

### 7.2 Expiration (tranché)

- Fin de l'événement → **éviction immédiate de toutes les listes** (le tueur de confiance n°1
  d'un agenda, c'est l'événement passé qui traîne).
- La fiche reste en 200 avec bandeau « ⏹ Cet événement est terminé » + 4 suggestions à venir.
  Jamais de redirection, jamais de 410.
- **Récurrents annuels** (sagre, festivals — l'essentiel de la valeur SEO) : fiche pérenne
  sans millésime, jamais noindexée ; entre deux éditions : « Édition 2027 : dates à
  confirmer » + capture email « être prévenu ».
- Ponctuels sans lendemain : `noindex,follow` à J+60, page conservée.

---

## 8. Composants (système à designer)

### 8.1 Carte événement — LE composant, 4 variantes

Invariants absolus : image (ratio unique ~3:2 partout, comme GuidaTorino), **date lisible sans
clic et sans survol**, titre 2 lignes max, lieu + ville, badge catégorie, pilule territoire
(sa couleur), badges d'état, « Gratuit » si applicable, carte entièrement cliquable.

1. **Héro** (home, tête de hub) : image dominante, date en gros, chapô 1 ligne.
2. **Standard** (grilles) : verticale, date en pastille-datebloc (« SAM 4 JUIL ») ou
   surimpression sobre.
3. **Compacte/liste** (mobile, recherche, listes denses) : horizontale, vignette carrée,
   datebloc à gauche — l'esprit de la liste chronologique GuidaTorino (100 % factuelle,
   pas d'extrait).
4. **Dernière chance** : standard + bandeau d'urgence rouge (« Plus que 3 jours »).

### 8.2 Barre de filtres (hubs)

3 dimensions max : Date (chips) · Territoire · Catégorie — la dimension du hub courant
disparaît. Application **AJAX sans rechargement MAIS avec URL mise à jour** (partageable,
back OK). Compteur de résultats, chips actives supprimables, « Réinitialiser ».
Mobile : bouton « Filtrer (2) » sticky → bottom sheet → « Voir les 34 événements ».

### 8.3 Badges d'état (vocabulaire fermé, max 2 par carte)

`En cours` · `Dernier week-end` / `Plus que X jours` (rouge accent) · `Date à confirmer`
(gris neutre) · `Gratuit` (indispensable — critère n°1 du public familial) · `Annulé` /
`Reporté` (écrase tout) · `Complet` (v2).

### 8.4 Blocs récurrents

Newsletter inline (1 champ, promesse datée ; **pas de pop-up d'entrée**) · rail des 11 tuiles
catégories en pied de page (partout) · bloc « territoires voisins ».

---

## 9. Bilinguisme FR/IT

- **Un domaine, sous-répertoires `/fr/` + `/it/`**, Polylang (ou WPML), hreflang par paires +
  `x-default`. Une fiche non traduite n'existe pas dans l'autre langue (jamais de page
  mi-FR mi-IT) ; les hubs sont toujours bilingues.
- Le switch **FR | IT mène à la page équivalente** (repli : hub parent + micro-message
  « Questo evento non è ancora tradotto »).
- Design : prévoir chaînes IT +10–15 % (boutons, badges), formats de date différents, badges
  traduits (« Ultimo weekend »), gabarits STRICTEMENT identiques dans les deux langues.
- La langue est une valeur du territoire (charte éditoriale) : le bilinguisme se montre
  (baseline, à-propos), il ne se cache pas dans un coin.

---

## 10. SEO structurel (à intégrer au design, pas après)

- **Pagination classique crawlable** (`/page/2/`), JAMAIS de scroll infini pur. Compromis
  autorisé : bouton « Voir plus » AJAX qui met à jour l'URL, avec liens de pagination dans le
  HTML initial.
- **JSON-LD par gabarit** : `Event` complet sur chaque fiche (startDate/endDate ISO avec
  fuseau, `location` avec adresse postale complète — requis pour le rich result Google —,
  image en 3 ratios 16:9/4:3/1:1, `offers` avec prix — `0` balisé si gratuit —,
  `eventStatus`, `organizer`) ; multi-dates non contiguës = un objet Event par occurrence ;
  pas de `startDate` inventée pour les « date à confirmer » (pas de balisage Event du tout).
  `BreadcrumbList` partout ; `ItemList` sur les hubs ; `WebSite`+`SearchAction` sur la home ;
  `Organization` (éditeur : Cultura Sabauda).
- **Titles types** : hubs temporels avec dates réelles (« Que faire ce week-end dans les
  Alpes (4–6 juillet 2026) — Agenda Sabaudo ») ; fiche « [Événement] — [Ville], [dates] —
  Agenda Sabaudo ».
- Maillage : chaque fiche renvoie vers 4–6 hubs (breadcrumb + 3 rails + tuiles). Sitemaps
  séparés fiches/hubs, `lastmod` fiables.

---

## 11. Règles éditoriales NON NÉGOCIABLES (héritées de la charte)

1. **Sources radar (presse) jamais créditées, jamais liées.** Un événement détecté via la
   presse est publié avec ses FAITS et sa source OFFICIELLE (organisateur/lieu) uniquement.
   Aucun encart « vu dans Le Dauphiné ». Le design du bloc source ne prévoit QUE la source
   officielle.
2. **Crédit photo affiché sur chaque image** (photos Commons créditées « Auteur / Wikimedia
   Commons · CC BY-SA » ; bannières territoire = visuels de marque). Page « Politique crédits
   photos » liée en footer, avec procédure de retrait.
3. **Aucun événement passé visible** dans les listes (éviction automatique).
4. **Zéro dark pattern** : pas d'urgence factice (les badges d'urgence reflètent des dates
   réelles), pas de clickbait, pas de superlatifs creux (« incontournable », « magique »
   sont bannis des textes générés), RGPD propre, pop-ups interdits à l'arrivée.
5. **Géographie nommée** : toujours ville → département/province → territoire.
6. Textes : registre accessible mais jamais racoleur ; le lecteur d'abord.

---

## 12. Anti-patterns interdits (liste de contrôle finale)

1. Calendrier-widget à cases comme page d'accueil (illisible mobile, zéro édito).
2. Carte sans date visible, ou date en gris 10 px au survol.
3. Filtres qui rechargent la page — OU filtres AJAX sans URL. Les deux.
4. Scroll infini sans pagination crawlable.
5. Carrousels à défilement automatique.
6. Événements passés dans les listes.
7. URLs datées pour les hubs (`/week-end-4-juillet/`) ; fiches millésimées pour les
   récurrents.
8. Description = copier-coller du communiqué.
9. Pop-up newsletter à l'arrivée ; interstitiels empilés.
10. Drapeaux comme sélecteur de langue.
11. « 0 résultat » sec.
12. Texte dans les images (titres, dates) — tout est du texte HTML réel.
13. Emoji comme système d'icônes de l'UI publique.
14. Design slop générique (dégradés SaaS, glassmorphism, blobs, hero vide) — cf. §0.

---

## 13. Livrables attendus de Claude Design

1. **Système** : palette appliquée (à partir des tokens §3), typographie, grille responsive,
   la carte événement en 4 variantes + tous ses états (avec photo / bannière territoire,
   avec/sans horaire, gratuit, badges), badges, filtres desktop+mobile, header/footer.
2. **Gabarits** (desktop + mobile) : Home · Ce week-end (hub temporel type) · Territoire ·
   Catégorie · **Fiche événement en mode MINIMAL** (le cas majoritaire !) · Fiche en mode
   riche · Listicle « Les 10 du week-end » · Recherche (overlay + résultats) · Newsletter ·
   404.
3. **Micro-états** : bandeau « événement terminé », « date à confirmer », 0-résultat avec
   élargissement, fiche non traduite (repli IT).
4. Priorité de rendu : d'abord la carte + la fiche minimale + le hub « Ce week-end » —
   si ces trois-là sont justes, le site est juste.
