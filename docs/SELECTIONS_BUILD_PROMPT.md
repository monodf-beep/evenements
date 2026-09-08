# Build des « Sélections » — prompt exécutable + checklist manuelle

*Ordre de construction de la structure décrite dans `SELECTIONS_HOME.md`. Deux voies :
(A) un prompt à coller dans une session connectée à **Novamira / MCP JetEngine** ;
(B) une checklist **UI JetEngine** en repli (toujours faisable à la main).*

---

## (A) Prompt pour une session connectée à Novamira / JetEngine

```
Tu es connecté à mon WordPress (agendasabauda.eu) via Novamira / le MCP JetEngine.
On construit la structure des « Sélections » (articles regroupant plusieurs
événements) pour le carrousel de la home. Stack : JetEngine + Gutenberg, PAS
d'Elementor. Procède PAR ÉTAPES, confirme chaque étape avant la suivante, et
vérifie ce que tu crées. Ne touche à rien d'autre.

CONTEXTE : les événements sont le CPT « tribe_events » (The Events Calendar), déjà
étiquetés FR/IT (Polylang) et rangés dans les taxonomies « territoire » et
« tribe_events_cat ». Date de début d'un événement = meta « _EventStartDate ».

ÉTAPE 1 — CPT « Sélection »
Crée (via JetEngine → Post Types) un CPT :
- Slug : selection · Libellé : Sélections · avec archive, éditeur Gutenberg, support
  titre + éditeur + image à la une.

ÉTAPE 2 — Meta box « Sélection » (champs JetEngine sur ce CPT)
- sel_intro (wysiwyg) — intro éditoriale
- sel_mode (select) : auto | manuel | hybride
- sel_periode (select) : ce-week-end | 7-jours | ce-mois | a-venir | nouveautes
- sel_territoire (select) : options = tous, savoie-haute-savoie, piemont,
  vallee-d-aoste, nice-alpes-maritimes
- sel_categorie (select) : options = toutes + les 11 catégories (slugs de
  tribe_events_cat)
- sel_ville (text)
- sel_limite (number, défaut 8)
- sel_home (switcher) — afficher dans le carrousel de la home
- sel_ordre (number) — ordre dans le carrousel

ÉTAPE 3 — Taxonomie « type_selection » sur le CPT selection
Termes : hebdo, thematique, transfrontalier, ville, edito.

ÉTAPE 4 — Relation JetEngine
Crée une relation many-to-many : selection  ⇄  tribe_events
(pour épingler des événements en mode manuel/hybride).

ÉTAPE 5 — Query Builder : « evenements-ce-week-end »
Custom query, type Posts Query sur tribe_events :
- Date Query sur la meta _EventStartDate, du samedi au dimanche de la semaine
  courante (utilise les valeurs dynamiques de date de JetEngine ; si indisponible,
  propose-moi la meilleure méthode plutôt que de coder une date en dur).
- Tri : _EventStartDate croissant. Limite : 8.
- Ne remonte que les événements de la langue courante (Polylang).

ÉTAPE 6 — Sélection test « Ce week-end »
Crée un post « selection » intitulé « Ce week-end » :
- sel_mode = auto, sel_periode = ce-week-end, sel_territoire = tous,
  sel_home = oui, sel_ordre = 1, intro courte de 2 phrases.
- Dans son contenu Gutenberg, place une Listing Grid qui affiche la query
  « evenements-ce-week-end », chaque carte liant vers la fiche de l'événement.

ÉTAPE 7 — Vérification + test Polylang (IMPORTANT)
- Confirme que la page « Ce week-end » affiche bien les événements du week-end.
- Crée/associe la traduction ITALIENNE de cette sélection (Polylang) et vérifie
  qu'elle remonte les événements ITALIENS. C'est LE test à valider avant d'aller
  plus loin (Crocoblock est certifié WPML, pas Polylang). Dis-moi franchement si
  le dynamique JetEngine ne suit pas correctement Polylang.

RÈGLES : par étapes, confirmation avant chaque écriture, une phrase d'explication
avant d'agir. Rollback documenté à chaque étape. Ne construis PAS encore le
carrousel de la home ni les autres formats : on valide d'abord cette sélection test.
```

---

## (B) Checklist UI JetEngine (repli manuel)
1. **JetEngine → Post Types → Add New** : `selection` (archive ON, Gutenberg).
2. **Meta Fields** du CPT : ajouter les 10 champs de l'étape 2.
3. **JetEngine → Taxonomies** : `type_selection` (5 termes).
4. **JetEngine → Relations** : `selection ⇄ tribe_events` (many-to-many).
5. **JetEngine → Query Builder** : `evenements-ce-week-end` (Posts Query tribe_events,
   Date Query `_EventStartDate` week-end courant, tri date ASC, limite 8).
6. **JetEngine → Listings** : un Listing Item « carte événement » (si pas déjà là).
7. **Pages → Ajouter** : post `selection` « Ce week-end » + Listing Grid (query ci-dessus).
8. **Polylang** : dupliquer en IT, vérifier que les événements IT remontent.

---

## Ce qu'on fait APRÈS validation de la sélection test
- Bâtir le **carrousel de la home** (Listing Grid des `selection` où `sel_home=oui`,
  tri `sel_ordre`, langue courante).
- Décliner les autres formats (`SELECTIONS_HOME.md` : Que faire à Annecy, Nouveautés,
  Ça vaut le déplacement, Sagre du mois) — même gabarit, filtres différents.
- Schema `ItemList` sur la page de sélection (SEO).
