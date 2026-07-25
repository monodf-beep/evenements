# Agenda Sabauda : état d'avancement (fait / à faire)

> Document de suivi vivant. Recense ce qui est **construit et live**, ce qui
> reste **à finir**, et ce qui **attend une décision ou un tiers**. Mis à jour
> au fil des sessions. Pour le détail technique de chaque brique, voir les docs
> dédiés référencés en regard.
>
> Dernière mise à jour : 2026-07-26.

---

## Comment lire ce document

- ✅ **Fait** : construit, vérifié en direct sur le site, documenté.
- 🔧 **À finir** : tâche concrète, réalisable sans décision extérieure.
- 🤔 **Décision attendue** : le prochain pas dépend d'un choix de Franck.
- 🌍 **Éditorial / tiers** : ne dépend pas du code (contenu, comptes externes).

---

## ✅ Fait (et vérifié en direct)

### Homepages
| Sujet | Détail | Doc |
|---|---|---|
| Gabarit unifié FR/IT | 1 page source (928) déclinée par langue + territoire | `REGLES_HOMEPAGES_AGENDA_SABAUDA.md` |
| URLs propres | `/explore/<t>/`, `/it/scopri/<t>/`, `/choisir/<t>/` | idem §3 |
| Allocateur des sections | Répartition sans doublon, budget de réutilisation = 2 | idem §5.2 |
| Breakpoint responsive 900px | Abaissé de 1024 à 900px (tolérance fenêtres étroites) | idem §6 |
| Fix arrondi `jour` → 0 | « 7 prochains jours » = 4 ou 8 uniquement | idem §5.2 |
| **Fix arrondi `ala-une`/`weekend`** (2026-07-25) | Ne jettent plus à tort un stock < 1 ligne (bug IT Savoia : 0 au lieu de 3) | idem §5.2 |
| Section 3 colonnes responsive | Empilée en 1 colonne sur mobile | idem §6 |
| Images de repli | 48 visuels (4 territoires × 12 catégories), repli auto partout | `SPECS_VISUELS_FALLBACK.md` |

### Fiche événement
| Sujet | Détail | Doc |
|---|---|---|
| Gabarit as-built | Snippet 56, hors Boucle | `FICHE_EVENEMENT_AGENDA_SABAUDA.md` |
| Date « événement en cours » | « Jusqu'au {fin} » au lieu de « du {début} au {fin} » | idem §3 |
| **3e rail « Près d'ici, mêmes dates »** (2026-07-24) | Fenêtre début → +3 jours | idem §5 |
| **Badges statut** (2026-07-24) | « Dernier jour » / « En cours » ; « Complet » exclu (meta non fiable) | idem §4 |
| Instagram par événement | Territoire de l'événement, Savoie FR uniquement sinon masqué | idem §6 |
| **Bouton Facebook mort masqué** (2026-07-26) | Lien `href="#"` retiré (snippet 56), réactivable comme Instagram | idem §6 |
| **Gabarit 404 sur-mesure** (2026-07-26) | Vrai HTTP 404, bilingue, recherche + 4 portes territoires (snippet 99) | — |

### Ajouter à mon agenda
| Sujet | Détail | Doc |
|---|---|---|
| Google / Outlook / .ics | Date effective si événement en cours | `AJOUTER_AU_CALENDRIER_AGENDA_SABAUDA.md` |
| **Rappels J-7 / J-1** (2026-07-25) | VALARM dans le .ics, anti-rappel-passé. Pas possible via liens directs Google/Outlook (aucun paramètre fiable) | idem |

### Hubs, recherche, nommage
| Sujet | Détail | Doc |
|---|---|---|
| Hubs territoire/ville + sous-pages datées | Moteur `cs_hub_ville_render` | `HUB_TERRITOIRE_VILLE_AGENDA_SABAUDA.md` |
| Recherche contextuelle 2 niveaux | Ville → territoire, catégorie → plein texte | `RECHERCHE_AGENDA_SABAUDA.md` |
| Nettoyage snippets morts | 13 et 18 désactivés (doublons inertes) | `FICHE_EVENEMENT` §0, `RECHERCHE` §0 |
| Nommage pages + redirections legacy | Colonne « Rôle » admin, 8 pages « Ce week-end » redirigées 301 | `REGLES_HOMEPAGES` §11bis |
| Renommage docs SABAUDO → SABAUDA | 13 fichiers alignés sur le nom du domaine | — |
| **Doc §9 Instagram corrigée** (2026-07-25) | Décrit le vrai comportement « Savoie FR uniquement » | `REGLES_HOMEPAGES` §9, `FICHE_EVENEMENT` §6 |
| **« No data was found » traduit** (2026-07-25) | FR/IT selon Polylang, snippet 98 | `REGLES_HOMEPAGES` §10 |

### Pipeline d'import (repo)
| Sujet | Détail |
|---|---|
| Retrait bannière territoire générique | `publisher_as.py` : le site gère son propre repli désormais |
| Diagnostic couverture photo (corrigé 2026-07-26) | Les images de repli sont bakeées comme `_thumbnail_id` : détecter « sans vraie photo » = tester le slug `fallback-`, pas un thumbnail vide. Réel : 19 FR + 23 IT événements futurs sur image de repli. Voir `PHOTOS_MANQUANTES_EVENEMENTS.md` |
| Liste Cuisine Nissarde 2025/26 | 29 établissements labellisés récupérés (dossier de presse officiel OT Nice), structurés dans `CUISINE_NISSARDE_DONNEES.md` |

---

## 🔧 À finir (actionnable sans décision)

*(F1, F2, F3 traités le 2026-07-25 — voir section « Fait » ci-dessus.)*

Rien d'actionnable sans décision à ce stade. Les items restants attendent un
choix (section suivante) ou dépendent d'un tiers.

---

## 🤔 Décision attendue (le prochain pas dépend d'un choix)

| # | Sujet | État au 2026-07-26 | Choix à faire |
|---|---|---|---|
| D2 | Cuisine Nissarde | **Préparé** : dataset + brouillon de page guide dans le repo (`docs/CUISINE_NISSARDE_DONNEES.md`, `docs/CUISINE_NISSARDE_PAGE_GUIDE.md`). Reco : **une page guide evergreen dans « Le Fil »** (pas des fiches événement, ce sont des établissements permanents) | (a) publier la page guide, (b) autre forme, (c) attendre. **+ vérifier le décompte 29 vs 30** (Socca du Cours / Chez Marie Thé = 1 ou 2 établissements ?) |
| D1 | Photo par événement | **Diagnostic corrigé + liste actionnable prête** (`docs/PHOTOS_MANQUANTES_EVENEMENTS.md`) : 19 FR + 23 IT événements futurs affichent une image de repli. Le sourcing d'une vraie photo est un travail humain (pas automatisable sans risque) | Sourcer les visuels (humain), en priorité les 6 événements sans source. Ou : accepter le repli comme état permanent |

### ✅ Décision résolue

- **D3 — Priorité « Ce week-end »** : simulation chiffrée sur les 10 variantes ×
  3 scénarios d'ordre. Conclusion : rétrograder « Ce week-end » n'apporte
  **aucun gain le week-end** (pools disjoints) et **au mieux 1-2 sections vides
  en moins en semaine, uniquement en Vallée d'Aoste**, sans **jamais** afficher
  un seul événement de plus. Les trous sont de la **vraie pénurie de contenu**
  (surtout IT), qu'aucun ré-ordonnancement ne corrige. **Recommandation retenue :
  ne rien changer** (garder « Ce week-end » en premier, section SEO phare).

---

## 🌍 Éditorial / tiers (hors code)

| # | Sujet | Nature |
|---|---|---|
| E1 | Comptes Instagram Piémont / VdA / Nice | À créer (réseaux sociaux). Le code les branchera automatiquement dès qu'ils existeront (compléter `cs_instagram_territoire_map`) |
| E2 | Volume de traductions IT | Vrai facteur limitant des trous (ex. 8 événements IT pour la Savoie). Travail éditorial |
