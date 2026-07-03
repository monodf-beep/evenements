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

Le « quel territoire ? » se pose pour la **home** (trafic de marque/habitude — non négligeable :
beaucoup tapent le nom du site directement) et pour tout premier visiteur sans contexte d'URL.

**Le principe (corrigé) : aucun signal n'est fiable seul — ils se contredisent.** Le Savoyard à
Turin a une **IP italienne** (position) et un **téléphone en français** (langue) : les deux
signaux pointent des territoires opposés. Conclusion : **on ne « devine » pas en dur**. On :
1. propose un **défaut raisonnable**,
2. rend le **contexte visible** (« Vous voyez : Savoie »),
3. rend le **changement trivial** (sélecteur 1 tap, toujours dans le header),
4. quand deux signaux **se contredisent**, on **suggère en douceur** au lieu de trancher en
   silence.

### ⚠ L'IP ne dit PAS la position (roaming « home routing »)
Vérifié (sources ci-dessous) : en itinérance, la plupart des forfaits **tunnellent le trafic
jusqu'au pays d'origine** → une **SIM française à Turin sort en IP française**. L'IP géolocalise
donc au **domicile**, pas à la position réelle. **Conclusion : l'IP n'est PAS un signal fiable de
position** pour notre cas (le voyageur sur son forfait). On l'abandonne comme défaut.

### Ce qui est vraiment fiable, du plus au moins
- **Le choix explicite de l'utilisateur** (sélecteur + mémoire cookie) = **le seul signal
  fiable**. Il nous dit son coin. Toujours juste. C'est le cœur.
- **Le bouton opt-in « 📍 Près de moi »** = la SEULE position fiable : il déclenche la
  **géoloc GPS du navigateur** (précise), **quand l'utilisateur le décide** (pas de popup à
  l'arrivée). Le Savoyard à Turin tape « Près de moi » → GPS = Turin → événements du Piémont
  autour de lui. Il choisit d'être localisé, c'est exact, et non intrusif.
- **Langue de l'appareil / IP-pays** = **hints faibles seulement** : pour pré-ordonner le
  sélecteur ou déclencher une suggestion douce. Jamais autoritaires (l'IP se trompe en roaming,
  la langue ne distingue pas Savoie de Nice).
- **Rien** → **home neutre best-of** + « Votre coin ? ».

### La bannière de conflit (validée par Franck) — mais c'est un BONUS
Quand un hint (IP-pays fiable : wifi local, eSIM locale…) diffère de la préférence, un bandeau
discret et **dismissible** :
> *« Vous semblez être en Piémont — voir les événements à Turin ? [Oui] [Rester en Savoie] »*
Un tap résout, jamais faux en silence. **Mais** comme le signal (IP) est faible/absent en
roaming, la bannière ne se déclenchera pas toujours → c'est un plus, **pas** le mécanisme
principal. Le mécanisme principal reste : **choix explicite + « Près de moi » opt-in.**

### Les cas concrets (tes scénarios)
- **Toi, habitué, tu tapes le nom du site** : home → ton **dernier coin mémorisé** (cookie), le
  sélecteur juste à côté. Habitude respectée.
- **Savoyard à Turin** : son IP reste **française** (roaming) → aucune détection auto fiable.
  Il tape **« 📍 Près de moi »** (GPS = Turin) → Piémont autour de lui ; OU 1 tap sur Piémont
  dans le sélecteur. Il agit, c'est exact. On ne lui sert PAS de la Savoie en silence, et on ne
  se fie pas à une IP menteuse. (Ta correction, réglée.)
- **Touriste de n'importe où** : **home neutre** best-of + « Votre coin ? » (+ « Près de moi »
  s'il veut le local). Ou il arrive par Google sur une page lieu → contexte déjà posé.
- **Jamais d'inscription pour naviguer** — l'inscription = newsletter uniquement (opt-in).

### SEO / technique
- **Google** (sans cookie, IP US) voit la **home neutre** + les liens vers TOUS les hubs → il
  indexe tout. Perso pour l'humain, structure pour Google. **Pas de cloaking** (mêmes liens,
  seul l'ordre change).
- **Mise en œuvre par phases** :
  - **Phase 1 (lancement, la plus honnête)** : home **« choix d'abord »** — un sélecteur de coin
    clair et chaleureux + un best-of ; on **mémorise le choix** (cookie) ; sélecteur toujours
    visible. **On ne devine pas → on ne se trompe jamais.** C'est ta « landing qui te fait
    choisir ». Simple, robuste, zéro dépendance géo.
  - **Phase 2** : ajouter le bouton **« 📍 Près de moi »** (géoloc GPS opt-in → tri par distance)
    + la **langue** pour pré-ordonner le sélecteur + la **bannière de conflit** (bonus, quand un
    signal IP fiable existe). PAS de défaut automatique par IP (roaming = peu fiable).

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
