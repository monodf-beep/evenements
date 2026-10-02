# Construction des pages du menu / carousel — réutiliser le gabarit liste

*Constat initial (2026-07-20) : la sidebar « Rechercher / Recent / Hello world! » apparaît sur
certaines pages de destination. On pensait que tout le menu tombait sur le gabarit WP par défaut.*

## ✅ Inventaire réel (session Novamira, 2026-07-20) — le vrai périmètre est BIEN plus réduit

Vérifié à l'écran, pas seulement dans le code : **la quasi-totalité des pages du menu ont déjà
un gabarit dédié** (Code Snippets `template_redirect`), propres, sans sidebar :

| Page | État | Gabarit |
|---|---|---|
| Aujourd'hui (929), Ce week-end (930), Cette semaine (931), Tout l'agenda (932) | ✅ propre | snippets dédiés, pattern `liste-evenements-template.php` |
| À propos (933), Proposer un événement (934, form OK) | ✅ propre | snippets dédiés |
| Hubs catégorie (×9) & territoire (×4) | ✅ propre | snippets 14+15 |

**Le vrai travail restant (réduit) :**
1. **Gabarit du CPT `selection`** (pages du carousel, ex. `/selections/quelle-sagre-ce-mois/`)
   → **seul vrai cas « sidebar par défaut / Hello world »**. C'est LE symptôme du screenshot.
2. **Bug de duplication** : sur les Hubs territoire/catégorie, chaque événement apparaît **2×**.
3. **« Hello world! » (article id 1)** → corbeille (source du « Recent Posts » dans la sidebar).
4. **(Décision)** Pages « Ce week-end × territoire » (`/ce-week-end/<terr>/`) : **n'existent pas
   (404) et ne sont liées de nulle part** — le switcher home pointe vers `/territoire/<terr>/`.
   Donc = fonctionnalité NOUVELLE (SEO), pas un lien cassé. **Reporté** sauf décision contraire.

Le gabarit liste réutilisable existe déjà de fait (pattern `liste-evenements-template.php`
dupliqué sur 4 pages + variante « carte pleine » pour les Hubs) — inutile d'en inventer un autre.

---

## (Spec initiale conservée pour référence — largement déjà réalisée)

*Constat de départ : les pages de destination tombaient sur le **gabarit WordPress par défaut**.
Réalité : seules les pages du CPT `selection` sont concernées (voir inventaire ci-dessus).*

---

## Pages cibles (par priorité de lancement)

| Page | URL | Requête | Gabarit |
|---|---|---|---|
| **Ce week-end** | `/fr/ce-week-end/` | événements du prochain sam.–dim., tri date ↑ | liste filtrable |
| …par territoire ×4 | `/fr/ce-week-end/<terr>/` | idem + Tax territoire | même gabarit |
| **Hub territoire** ×4 | `/fr/territoire/<terr>/` | à venir, Tax territoire, tri date ↑ | liste + intro + module « autre versant » |
| **Aujourd'hui** | `/fr/aujourdhui/` | _EventStartDate = aujourd'hui, tri date ↑ (`noindex`) | même gabarit dates |
| **Tout l'agenda** | `/fr/evenements/` | tous à venir, filtrable date·ville·cat·terr | liste filtrable |
| **À propos** | `/fr/a-propos/` | — (éditorial, texte déjà écrit) | page standard |
| **Proposer un événement** | `/fr/proposer-un-evenement/` | formulaire modéré (brouillon) | page + form |

Rappels : score = méta `as_score` ; date = `_EventStartDate` ; taxo `territoire`
(slugs `savoie-haute-savoie`, `piemont`, `vallee-d-aoste`, `nice-alpes-maritimes`) ;
langue forcée `lang => pll_current_language()`. Chaque page a sa jumelle `/it/…`.

---

## Prompt à coller dans la session Novamira

```
On CONSTRUIT les pages où mènent le carousel et le menu d'agendasabauda.eu. Elles tombent
aujourd'hui sur le gabarit WP par défaut (sidebar « Recent / Hello world! » visible). Objectif :
réutiliser UN gabarit liste agenda (pleine largeur, sans sidebar) et y brancher la bonne
requête par page. Stack The Events Calendar + JetEngine + Gutenberg + Polylang. Verify-first,
réversible, confirmation avant chaque écriture, page par page.

ÉTAPE 0 — INVENTAIRE (ne rien modifier)
Pour chaque entrée du menu (Aujourd'hui, Ce week-end, Catégories, Territoires, Agenda, À
propos, Proposer un événement) et chaque cible du carousel : dis-moi si la page EXISTE, quel
GABARIT elle utilise (défaut avec sidebar ? un gabarit agenda ?), et si un gabarit « liste
agenda » réutilisable existe déjà quelque part. Donne-moi ce tableau AVANT de construire.
Signale aussi l'article de démo « Hello world! » (à mettre à la corbeille).

ÉTAPE 1 — LE GABARIT LISTE (la brique réutilisable)
S'il n'existe pas déjà, crée UN gabarit « liste agenda » : pleine largeur, SANS la sidebar
blog, avec un en-tête (H1 + intro) + un Listing Grid d'événements (carte événement au format
constant) + pagination. C'est lui qu'on réutilisera pour toutes les pages dates/territoire.
Montre-le-moi sur une page de test avant de le dupliquer.

ÉTAPE 2 — CE WEEK-END (/fr/ce-week-end/)
Assigne le gabarit liste à cette page. Requête : tribe_events dont _EventStartDate tombe sur
le prochain samedi 00:00 → dimanche 23:59, tri _EventStartDate ASC, lang courante. H1
« Ce week-end », intro pérenne. Vérifie qu'il n'y a plus de sidebar et que la liste se remplit.

ÉTAPE 3 — CE WEEK-END PAR TERRITOIRE (×4)
Même page/gabarit + Tax Query territoire = le terme voulu, pour :
/fr/ce-week-end/savoie-haute-savoie/, …/piemont/, …/vallee-d-aoste/, …/nice-alpes-maritimes/.
(Ce sont les cibles du switcher « Changer : Piémont / Vallée d'Aoste / Comté de Nice ».)

ÉTAPE 4 — HUBS TERRITOIRE (×4, /fr/territoire/<terr>/)
Gabarit liste + intro pérenne du territoire + requête « à venir dans ce territoire » (Tax
territoire, tri date ASC). Ajoute en bas l'encart « De l'autre côté des Alpes » = 2 événements
du versant opposé (règle déjà définie dans CABLAGE_HOME.md étape 6, réutilise-la).

ÉTAPE 5 — AUJOURD'HUI (/fr/aujourdhui/) + TOUT L'AGENDA (/fr/evenements/)
Aujourd'hui : gabarit dates, _EventStartDate = aujourd'hui, tri date ASC, page en noindex.
Tout l'agenda : gabarit liste filtrable (date · ville · catégorie · territoire), tous à venir.

ÉTAPE 6 — PAGES ÉDITORIALES
À propos (/fr/a-propos/) : gabarit page standard, colle le texte « À propos » (docs/
PLAN_DU_SITE_AGENDA_SABAUDO.md §4, FR + jumelle IT « Chi siamo »). Proposer un événement :
page + formulaire qui crée un BROUILLON à modérer (jamais auto-publié).

RÈGLES : par étapes, confirmation avant chaque écriture, chaque page a sa jumelle /it/ (mêmes
requêtes en lang=it), garde de quoi rollback. Commence par l'ÉTAPE 0 (inventaire) et donne-la.
```

---

## Notes

- **Ne pas dupliquer 20 gabarits** : un gabarit liste + Tax/Date Query en paramètre couvre
  toutes les pages dates & territoire. C'est le principe de `TEMPLATES_WORDPRESS.md`.
- La **sidebar « Recent / Hello world! »** = gabarit par défaut. La corriger = assigner le
  gabarit pleine largeur + mettre l'article de démo à la corbeille.
- La qualité des listes dépend du **contenu** (assez d'événements par territoire/date) : le
  gabarit rend la page propre, le sourcing la remplit.
