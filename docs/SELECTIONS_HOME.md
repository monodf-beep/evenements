# Sélections — le carrousel éditorial de la home

*Modèle de données + formats de départ pour les « sélections » (articles regroupant
plusieurs événements) qui alimentent le carrousel du haut de home. Stack : CPT +
**relation/requête JetEngine** + Gutenberg (pas d'Elementor requis). Cohérent avec
`PILE_BUILD_WORDPRESS.md`. Chaque sélection = **une page rankable** + un item du
carrousel + une source pour la newsletter et le social.*

> **MISE À JOUR — état réel vérifié en live (2026-07-25).** Ce système n'est PLUS au
> stade « spec » : le CPT `selection` et le carrousel sont **construits et en ligne**.
> La home (thème **GeneratePress**, pas Elementor) pointe vers de vraies pages de
> sélection, brandées avec de vraies photos de couverture (pas la bannière Observatoire) :
> `/selections/ce-week-end/`, `/selections/que-faire-a-annecy-ce-week-end/`,
> `/selections/les-nouveautes/`, `/selections/ca-vaut-le-deplacement/`,
> `/selections/quelle-sagre-ce-mois/`. Les URLs réelles du site n'ont PAS de préfixe
> `/fr/` ni `/territoire/` : hubs catégorie en `/evenements/categorie/<cat>/`, accès
> temporels en `/aujourdhui/`, `/ce-week-end/`, `/tout-l-agenda/`.
> **Problème restant** : certaines sélections s'affichent VIDES (« Aucun événement à
> afficher ») — la tuyauterie de méta est bonne (`publisher_as` pousse `as_ville`,
> `as_score`, `_EventStartDate`), donc c'est surtout du **volume** (villes sous le
> seuil, ex. Annecy) et/ou du **réglage de filtre JetEngine**, pas un manque de CPT.
> Les docs `TODO_LANCEMENT.md` (§2c « carrousel non coché ») et `CONSTRUCTION_PAGES.md`
> sont donc **en retard** sur cet aspect.

---

## Principe : 2 modes de production
- 🤖 **auto (piloté par la donnée)** — la sélection **ne liste pas** les événements à la
  main : elle stocke des **filtres** (période + territoire + catégorie + ville) et la
  Listing Grid affiche une **requête dynamique**. Se rafraîchit tout seul, coût quasi nul.
- ✍️ **manuel (édito)** — le curateur **épingle** des événements précis via une **relation
  JetEngine** (sélection ↔ événements). Plus de valeur, cadence plus lente.
- **hybride** — une requête auto **+** quelques événements épinglés en tête.

Un **seul gabarit** de page « sélection » sert les trois modes. On change le filtre et le
titre, pas le gabarit.

---

## CPT « Sélection » (`selection`)
Créé dans **JetEngine → Post Types** (pas de `register_post_type` en PHP — cf. règle
JetEngine). Archive : `/selections/`. Traduit par **Polylang** (c'est un post → géré au
niveau du post ; les événements liés sont déjà étiquetés FR/IT).

**Champs (JetEngine Meta Box) :**
| Champ | Type | Rôle |
|---|---|---|
| `sel_intro` | wysiwyg | L'intro éditoriale (2-3 phrases) affichée en tête |
| `sel_mode` | select | `auto` · `manuel` · `hybride` |
| `sel_periode` | select | `ce-week-end` · `7-jours` · `ce-mois` · `a-venir` · `nouveautes` |
| `sel_territoire` | select/relation | terme `territoire` (ou « tous ») |
| `sel_categorie` | select | terme `tribe_events_cat` (ou « toutes ») |
| `sel_ville` | text/relation | filtre ville (pour les formats géo) |
| `sel_limite` | number | nb max d'événements affichés (déf. 8) |
| `sel_cover` | media | visuel de couverture (repli : photo du 1ᵉʳ événement) |
| `sel_home` | switcher | afficher dans le carrousel de la home (oui/non) |
| `sel_ordre` | number | ordre dans le carrousel |

**Taxonomie** `type_selection` (facultatif mais propre) : `hebdo` · `thematique` ·
`transfrontalier` · `ville` · `edito` — pour filtrer/archiver les sélections par genre.

**Relation JetEngine** `selection ⇄ tribe_events` (many-to-many) — utilisée en mode
`manuel`/`hybride` pour épingler des événements.

---

## Le gabarit de page « sélection »
1. Couverture (`sel_cover`) + titre + `sel_intro`.
2. **Une Listing Grid d'événements** qui, selon `sel_mode` :
   - `manuel` → affiche les événements **liés** (relation) ;
   - `auto` → affiche une **requête** construite depuis les filtres (voir ci-dessous) ;
   - `hybride` → les épinglés d'abord, puis la requête.
3. Chaque carte événement **mène à la fiche événement** (`tribe_events` single).
4. **SEO** : émettre un schema `ItemList` (liste ordonnée des événements) — la page vise
   « que faire à [ville] ce week-end », « sagre [mois] piémont »…

Le **carrousel de la home** = une Listing Grid de `selection` où `sel_home = oui`,
triée par `sel_ordre`, filtrée sur la **langue courante** (Polylang).

---

## La requête dynamique (mode auto) — mécanique
JetEngine **Query Builder** (Posts Query sur `tribe_events`) :
- **Date** : Meta Query sur `_EventStartDate` (date de début TEC), bornée selon
  `sel_periode` :
  - `ce-week-end` → samedi 00:00 → dimanche 23:59 de la semaine courante ;
  - `7-jours` → aujourd'hui → +7 j ; `ce-mois` → 1ᵉʳ → dernier jour du mois ;
  - `a-venir` → ≥ aujourd'hui ;
  - `nouveautes` → tri par **date d'ajout** (`post_date` DESC), horizon à venir.
- **Territoire / catégorie / ville** : Tax Query (`territoire`, `tribe_events_cat`) +
  filtre ville, seulement si le champ est renseigné (sinon on ne filtre pas).
- **Langue** : la requête ne remonte que les événements de la langue de la sélection
  (les événements sont déjà taggés FR/IT).
- **Tri / limite** : par date de début croissante, limité à `sel_limite`.

> ⚠️ Rappel `PILE_BUILD_WORDPRESS.md` : Crocoblock est certifié **WPML**, pas Polylang.
> Ici on reste jouable car : le **texte** (titre + intro) est traduit au niveau du **post**
> (Polylang gère), et les **événements** sont déjà étiquetés par langue. À vérifier
> empiriquement sur les macros de date multilingues.

---

## Les formats de départ (filtres prêts)
| Sélection | Mode | `sel_periode` | Filtres | Intent SEO |
|---|---|---|---|---|
| **Ce week-end** | 🤖 auto | `ce-week-end` | tous territoires | « que faire ce week-end alpes » |
| **Que faire à Annecy ce week-end** | 🤖 auto | `ce-week-end` | ville = Annecy | « que faire à annecy ce week-end » |
| **Les nouveautés** | 🤖 auto | `nouveautes` | tous | fraîcheur / retour régulier |
| **Ça vaut le déplacement** | ✍️ manuel | — | événements voisins épinglés | marque / transfrontalier |
| **Quelle sagre ce mois** | 🤖 auto | `ce-mois` | cat = gastronomie-sagre · terr = Piémont | « sagre piemonte [mois] » |

Carrousel au lancement : **1 → 2 → 3 → 4** (ajouter **5** dès que le Piémont est sourcé).

---

## Workflow de production (tenable)
1. Le **pipeline** score et étiquette les événements (déjà en place).
2. Pour une sélection 🤖 : créer le post, choisir les filtres, écrire l'intro (2-3
   phrases, brouillon **IA** possible → **validation Franck**), cocher `sel_home`. Fini.
3. Pour une sélection ✍️ : idem + épingler les événements via la relation.
4. **Réemploi** : la même sélection nourrit **home + newsletter + post social** (une
   production, trois canaux).

*Piste future : le back-office génère le brouillon (intro + événements suggérés) et le
pousse en « à valider » — même logique que Cowork. À cadrer plus tard.*

---

## À trancher (rappel)
- CPT dédié `selection` **(recommandé ici)** vs simples articles + relation — le CPT
  donne des archives et un type propre, sans polluer le blog.
- Traduction du **dynamique** JetEngine sous Polylang : valider sur une sélection test
  avant de généraliser (cf. point WPML/Polylang).
