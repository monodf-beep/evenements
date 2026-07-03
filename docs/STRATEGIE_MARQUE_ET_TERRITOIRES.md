# Stratégie — marque, domaines & lecture par territoire

*Décisions d'architecture à prendre AVANT la création du site. Répond à : la marque est-elle
bonne ? sous-domaines par ville ? comment ne pas noyer l'utilisateur sous 4 territoires ?*

---

## 1. La marque

- **« Sabaudo » = le bon socle** : seul mot couvrant les 4 territoires sans en privilégier un,
  relié à Cultura Sabauda, distinctif, libre en SEO. À **garder comme identité**.
- **Mais froid/savant** : le nom ne portera pas le trafic (il vient des requêtes « que faire à
  [ville] »). La chaleur viendra du **UX + d'une tagline claire**, pas du nom.
- **Décision** : réserver **`agendasabaudo.eu`** ce soir (l'ancre). Le **nom affiché** (logo +
  tagline) peut s'affiner plus tard **sans changer le domaine**. Ne pas bloquer le lancement.
- Tagline à tester (chaleur + clarté + transfrontalier) : ex. *« Les sorties des Alpes, d'un
  versant à l'autre »* / *« Que faire de Chambéry à Turin »*.

## 2. Domaines : sous-répertoires, JAMAIS de sous-domaines

- **Sous-domaines** (`annecy.agendasabaudo.eu`) = Google les traite comme des **sites séparés**
  → autorité **fragmentée**, chaque ville repart de zéro. + Multisite WordPress lourd. **Non.**
- **Sous-répertoires** (`agendasabaudo.eu/fr/ville/annecy/`) = toute l'autorité sur **un
  domaine**, et ce sont **les entrées par ville/province** voulues. **Un seul WordPress.**

## 3. Le modèle « cercles concentriques » (local d'abord, transfrontalier ensuite)

Le problème : 4 territoires à parts égales **noient** l'utilisateur (un Savoyard ne veut pas de
Nice). La réponse n'est pas de tout mélanger, mais de **hiérarchiser par proximité** :

```
   ┌─────────────────────────────────────────────┐
   │  4. Les autres territoires (accessibles,     │   ← au menu, jamais poussés
   │     jamais mis en avant)                     │
   │   ┌─────────────────────────────────────┐    │
   │   │ 3. TRANSFRONTALIER (curé, 2-3 pépites)│   │   ← la passerelle éditoriale
   │   │   ┌─────────────────────────────┐    │    │
   │   │   │ 2. TON TERRITOIRE (Savoie)  │    │    │   ← le cœur
   │   │   │   ┌─────────────────────┐   │    │    │
   │   │   │   │ 1. TA VILLE (Chambéry)│  │    │    │   ← le plus pertinent
   │   │   │   └─────────────────────┘   │    │    │
   │   │   └─────────────────────────────┘    │    │
   │   └─────────────────────────────────────┘    │
   └─────────────────────────────────────────────┘
```

1. **Ta ville** (Chambéry) — le plus pertinent. Un Chambérien ne veut pas forcément Thonon.
2. **Ton territoire** (Savoie/Haute-Savoie) — la région naturelle.
3. **Transfrontalier** — **2-3 pépites curées** de l'autre côté des Alpes (Piémont surtout,
   un peu de Vallée d'Aoste). **C'est l'atout unique du concept Sabaudo** : aucun agenda local
   ne dit « et ce week-end, de l'autre côté de la frontière… ». Curé, pas déversé.
4. **Les autres territoires** (Nice pour un Savoyard) — **accessibles au menu, jamais poussés**.

**La règle d'or** : le local **domine**, le transfrontalier est une **invitation choisie** (2-3
items éditorialisés), pas du volume. On sert la mission transfrontalière **sans** noyer le lecteur.

## 4. Comment ça se traduit dans le site

**La home n'est pas un déversoir des 4 territoires.** Trois options, de la plus simple à la plus riche :

- **A — Sélecteur de territoire mémorisé (reco pour le lancement)** : à la 1ʳᵉ visite, « Votre
  territoire ? » (ou géoloc). On mémorise (cookie). Ensuite la home est **territoire-first** :
  gros bloc de TON territoire + un petit bloc « **À voir aussi de l'autre côté des Alpes** »
  (2-3 pépites) + le reste au menu. Simple, efficace, respecte l'entonnoir.
- **B — Les hubs territoire comme vraies portes d'entrée** : le SEO amène les gens directement
  sur `/territoire/savoie/` (via « que faire en Savoie »). Chaque hub territoire = local-first +
  petit bloc transfrontalier. La home « / » reste un chapeau léger.
- **C (v2) — Tri par distance** : ordonner les événements par proximité de la ville de
  l'utilisateur (nécessite les coordonnées lieu — partiellement dispo). Puissant, mais plus tard.

**Reco : A + B ensemble.** Hubs territoire = colonne vertébrale SEO (indexables, local-first) ;
home = expérience personnalisée qui se souvient de ton territoire. Distance (C) en v2.

**SEO préservé** : la personnalisation (réordonner par cookie) **ne nuit pas** au SEO tant que
la home garde des **liens crawlables** vers tous les hubs. On personnalise pour l'humain, on
garde la structure de hubs pour Google. Les deux sont servis.

## 5. Le bloc « transfrontalier » — la signature à soigner

- Sur chaque hub territoire, un encart **« De l'autre côté des Alpes »** : 2-3 événements
  **choisis à la main** (le bouton « À la une / choix manuel » du backoffice le permet déjà).
- Priorité de voisinage à définir : pour la Savoie → surtout **Piémont** (Turin proche) + un peu
  **Vallée d'Aoste** (Mont-Blanc/tunnel) ; **Nice en dernier** (loin, peu pertinent au quotidien).
- C'est éditorial : on ne pousse pas 200 événements niçois à un Chambérien, on lui glisse **la**
  belle expo de Turin du week-end. C'est ce qui rend le concept Sabaudo vivant plutôt qu'abstrait.

## 6. Implications data / backoffice

- On a déjà **territoire + ville** par événement → suffisant pour A et B dès maintenant.
- **Coordonnées (lat/lng)** du lieu à fiabiliser pour le tri par distance (C, v2).
- Le **choix manuel** (À la une) sert à alimenter le bloc transfrontalier curé — déjà en place.
- Prévoir un champ « ville » propre et normalisé (pour les hubs ville des grandes villes).

## 7bis. Comment on détecte le territoire (sans forcer personne)

**Le réflexe à corriger : la home n'est PAS la porte d'entrée principale.** Sur un agenda local,
la majorité du trafic vient de Google sur une requête précise (« que faire à Annecy », « eventi
Torino ») → l'internaute **atterrit directement sur un hub** (`/ville/annecy/`, `/territoire/
piemont/`). **La page d'arrivée encode déjà le territoire.** Donc pour le plus gros du trafic,
on n'a **rien à deviner** : l'URL le dit.

Le « quel territoire ? » ne se pose donc que pour la **home** (trafic direct, marque, newsletter).
Réponse : une **cascade de signaux, aucun bloquant**, du plus fiable au moins fiable :

1. **Choix explicite mémorisé** (cookie) — le plus fort. Dès que quelqu'un choisit ou navigue un
   territoire, on s'en souvient. Un visiteur qui revient retrouve son coin.
2. **Géoloc par IP** (silencieuse, côté serveur/edge — PAS le popup navigateur) — juste un
   **défaut** pour un premier visiteur sans cookie. Approximatif mais suffisant pour un défaut.
3. **Home neutre « best-of »** — si aucun signal (touriste, IP étrangère) : une home accueillante
   (les pépites de chaque territoire) + une **bande « Votre coin ? »** douce. On invite, on ne
   bloque pas.

Et **toujours** : un **sélecteur de territoire en un clic** dans le header (comme un sélecteur de
langue) → n'importe qui corrige une mauvaise devinette instantanément.

**Ordre de priorité : cookie > IP > neutre.** (Le cookie AVANT l'IP : c'est ce qui gère le
Savoyard en vacances — voir ci-dessous.)

### Les cas concrets (tes scénarios)
- **Savoyard chez lui** : arrive via Google sur une page Savoie (contexte posé) ; ou home + IP
  Rhône-Alpes → Savoie ; ou son cookie dit Savoie. Tous les chemins mènent à Savoie ; si faux,
  1 clic.
- **Savoyard en vacances à Turin** : son **cookie « Savoie » l'emporte sur l'IP** → il retrouve
  la Savoie. Et s'il veut du Turin pour son séjour, 1 clic sur Piémont (ou l'IP Piémont le lui
  propose déjà). Les deux besoins sont servis.
- **Touriste de n'importe où** : IP étrangère → **home neutre best-of** + « Votre coin ? ». Il
  choisit sa destination. Ou il est arrivé par Google sur une page lieu → contexte déjà posé.
- **Jamais d'inscription obligatoire.** On ne demande JAMAIS de créer un compte pour naviguer.
  L'inscription = newsletter uniquement (opt-in, échange de valeur), jamais une barrière.

### SEO / technique
- **Google** n'a ni cookie ni IP locale → il voit la **home neutre** (best-of + liens vers TOUS
  les hubs). Il indexe la home neutre + tous les hubs. Les humains ont la perso. **Aucun risque**
  de cloaking (mêmes liens pour tous, seul l'ordre change).
- **Mise en œuvre par phases** (important pour ce soir) :
  - **Phase 1 (lancement, simple)** : PAS d'IP. Home neutre best-of + **sélecteur header** +
    **mémoire du dernier territoire visité (cookie)** → au retour sur la home, un petit JS
    réordonne vers le coin mémorisé. Zéro dépendance géo. Suffisant.
  - **Phase 2 (plus tard)** : ajouter le **défaut par IP** (en-tête pays Cloudflare, ou service
    géo) pour le tout premier visiteur sans cookie.

---

## 7. Décisions à trancher (avant/pendant la création)

1. **Marque** : garder « Agenda Sabaudo » + affiner logo/tagline plus tard (reco) ? ou explorer
   un autre nom maintenant ?
2. **Domaines** : sous-répertoires sur un WordPress (reco ferme) — validé ?
3. **Modèle géo** : cercles concentriques, local-first + transfrontalier curé (reco) — validé ?
   Ça impacte **directement la maquette** (la home n'est pas un dump 4-territoires).
4. **Personnalisation** : sélecteur de territoire mémorisé dès le lancement (option A) — ok ?
5. **Voisinages** : confirmer les priorités transfrontalières par territoire (Savoie→Piémont ;
   etc.).
