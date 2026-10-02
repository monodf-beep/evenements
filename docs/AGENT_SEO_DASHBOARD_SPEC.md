# Spec — Agent(s) SEO du dashboard (backoffice Agenda Sabauda)

*Cadrage critique de l'idée « un agent SEO dans le dashboard pour l'utiliser sur les principaux
événements ». Écrit après recherche (voir `GUIDE_INDEXATION_AGENDA_SABAUDO.md`). Ton : franc,
comme demandé.*

---

## 0. Le recadrage critique (à lire avant tout)

**Agent SEO ≠ agent d'indexation.** C'est LA confusion à éviter. Deux problèmes distincts :

- **Optimiser une fiche** (titre, méta, schema, FAQ, maillage) → **un LLM le fait très bien.**
- **Forcer Google à indexer** → **aucun agent ne peut le faire.** L'Indexing API de Google est
  réservée aux offres d'emploi et aux lives vidéo ; il n'existe **aucune API** pour soumettre à
  l'indexation Google du contenu générique. La seule action « pousser vers Google » est la
  demande **manuelle** dans Search Console (~10-12/jour, non automatisable).

**Conséquence :** l'agent du dashboard est un **optimiseur de contenu/balisage**, pas un
« bouton indexer maintenant ». Si on lui promet d'indexer, on ment à l'utilisateur.

**Et surtout — ne le fais PAS tourner sur toute la masse.** Les événements score 4-6 (le gros du
volume) doivent être **parfaits par le gabarit** (le template WordPress génère automatiquement
title/méta/schema/FAQ corrects). Un agent LLM par fiche sur des dizaines/jour = coût + temps
ingérables. **L'agent SEO se réserve aux 5-15 événements phares** — précisément ceux que tu
pousses déjà vers Cultura Sabauda.

---

## 1. Ce que l'agent SEO FAIT (par événement phare, à la demande)

Un bouton **« ✨ Optimiser SEO/GEO/AEO »** sur la fiche, qui lance une passe et **propose** (tu
valides avant enregistrement) :

1. **`title` (50-60 car.) + `meta description` (150-160 car.)** optimisés, avec date et lieu.
2. **Slug** propre (sans millésime pour un récurrent).
3. **Bloc « réponse directe » (40-60 mots)** — le levier AEO, réutilisable en chapô.
4. **FAQ** (3-5 Q/R : quand ? où ? gratuit ? réserver ?) → balisable en `FAQPage`.
5. **Le JSON-LD `Event`** rempli depuis les champs de la base + **validé** (dates ISO+fuseau,
   adresse complète, `offers`…).
6. **Audit de la fiche** contre la grille SEO/GEO/AEO (score + ce qui manque).
7. **Suggestions de liens internes** (événements liés : mêmes dates/territoire/catégorie).

**Sortie** : stockée sur la fiche (nouveaux champs `seo_title`, `seo_desc`, `seo_answer`,
`seo_faq`, `seo_checked_at`), poussée dans le brouillon WordPress à la publication.

---

## 2. Ce que l'agent NE FAIT PAS (et pourquoi)

| Tentation | Réalité |
|---|---|
| « Bouton : indexer sur Google maintenant » | **Impossible.** Pas d'API. Au mieux : préparer l'URL pour que TU la soumettes manuellement en GSC. |
| Faire tourner l'agent sur les 1 900 événements | **Non.** Coût + inutile : le gabarit s'en charge. Réservé aux phares. |
| Indexing API / Instant Indexing Google | **Interdit hors JobPosting/BroadcastEvent.** Risque de sanction. |
| Générer 15 variantes de titres « pour tester » | Bruit. Un bon titre, pas quinze. |

**Nuance IndexNow (Bing) :** ça, un bouton/automatisme PEUT le faire (soumettre l'URL à Bing dès
publication). Mais c'est un simple appel d'API, **pas du travail d'« agent »** — à câbler dans le
plugin (RankMath le fait tout seul), pas dans un agent LLM.

---

## 3. Deux « agents », deux rôles (ne pas confondre)

**Agent A — l'optimiseur par fiche** (§1) : LLM, à la demande, sur les événements phares.
**Agent B — l'auditeur de gabarit** (one-shot, pas par fiche) : passe le **template** au Rich
Results Test + la grille SEO/GEO/AEO, une fois à la conception puis 1×/trimestre. Corrige la
source (le gabarit), donc **répare 1 900 fiches d'un coup**. C'est le meilleur ROI SEO — bien
plus que l'agent A.

> Ordre de priorité : **B avant A.** Un gabarit parfait rend l'agent A presque superflu, sauf
> pour la touche éditoriale des phares (réponse directe, FAQ, angle).

### État d'avancement (mis à jour le 2026-08-12)

**L'agent A tourne depuis des semaines, l'agent B n'avait jamais tourné** — l'inverse exact
de l'ordre recommandé ci-dessus. `seo_batch.py` est en cron quotidien (10h30, cap 10, score
≥ 7) ; rien ne relisait le gabarit.

| | État | Où |
|---|---|---|
| Agent B — passe n°1 | **faite le 2026-08-12** | `docs/AUDIT_SEO_2026-08-12.md` — score 58/100 |
| Trouvailles | 13 défauts de gabarit versés dans `/seo` | `docs/audit_seo_2026-08-12_findings.json` + `scripts/seo_findings_import.py` |
| Surveillance entre deux passes | 7 signaux de site, alerte sur BASCULE | `scripts/gabarit_health.py` (cron quotidien) |
| Agent B — passe n°2 | à faire **1×/trimestre** ou après un gros changement de gabarit | — |

La passe n°1 confirme le pari de cette spec : **tout ce qu'elle a trouvé de coûteux est du
gabarit** — l'en-tête de cache, l'entité `Organization` absente, `offers` manquant du schéma
`Event`, `Place` absent des pages lieu. Aucune fiche à retoucher une par une.

Sur la périodicité, ne pas céder à la tentation d'un audit hebdomadaire : deux rapports en
prose sur le même site disent la même chose avec d'autres mots, et on ne peut pas les
comparer. Le trimestre de cette spec est le bon rythme ; le quotidien est couvert par
`gabarit_health`, qui est déterministe et ne parle que quand une valeur change.

---

## 4. Découpe déterministe vs LLM (règle maison `LLM_OU_CODE.md`)

| Tâche | Code (déterministe) | LLM |
|---|---|---|
| JSON-LD `Event` (dates, lieu, prix) | ✅ généré depuis la base | — |
| Validation format (ISO, fuseau, adresse) | ✅ | — |
| Slug | ✅ (translittération) | — |
| Titre, méta, réponse directe, FAQ, angle | — | ✅ (langage/jugement) |
| Score d'audit checklist | ✅ (règles) + ⚪ LLM pour les points qualitatifs | mixte |
| Suggestions de liens internes | ✅ (requête base : même territoire/catégorie/dates) | — |

Le schema et les liens = **code** (fiables, gratuits). Seule la langue passe par le LLM. Ça
limite le coût à quelques centimes par fiche phare.

---

## 5. Intégration concrète dans le dashboard

- **Où** : bouton sur la fiche (aperçu) + une colonne/badge « SEO ✓ » dans la liste, visible
  seulement sur les événements retenus (`published_cs`/`evaluated`).
- **Flux** : clic → passe LLM (haiku/sonnet selon le budget) → panneau de **propositions
  éditables** → tu valides → enregistré + injecté au brouillon WP.
- **Coût** : réservé aux phares (5-15/semaine) → négligeable. Kill-switch de coût déjà en place
  (le bandeau crédit).
- **Réutilise l'existant** : même pattern SDK anthropic direct que `evaluator.py`/`enrich.py` ;
  le JSON-LD se construit depuis `events_raw` (dates, lieu, territoire, offers/tarif si connu).

---

## 6. Ce qu'il ne faut PAS construire (récap des fausses bonnes idées)

- ❌ Un bouton « indexer sur Google » (n'existe pas).
- ❌ L'agent SEO en batch sur toute la base (coût, inutile).
- ❌ L'Indexing API / « Instant Indexing » Google pour nos événements (interdit, risqué).
- ❌ Un générateur de dizaines de variantes (bruit).
- ✅ À la place : **gabarit parfait (agent B) + optimiseur éditorial sur les phares (agent A) +
  IndexNow auto (plugin) + demande GSC manuelle pour 2-3 temps forts/semaine.**

---

## 7. Recommandation finale

1. **D'abord le gabarit** (agent B + le travail d'intégration WordPress) : c'est 90 % du gain
   SEO, appliqué à toute la base.
2. **Ensuite l'agent A** (optimiseur éditorial) sur les seuls événements phares : la touche qui
   distingue une fiche « Cultura Sabauda » d'une fiche de catalogue.
3. **L'indexation reste un problème d'architecture** (hubs evergreen maillés + sitemap + backlinks
   locaux), traité dans le guide d'indexation — **pas** un problème que l'agent résout.

*Le vrai levier de visibilité des 6-18 mois, ce sont les backlinks des offices de tourisme et de
la presse locale des 4 territoires — aucun agent ne remplace ce travail de terrain.*
