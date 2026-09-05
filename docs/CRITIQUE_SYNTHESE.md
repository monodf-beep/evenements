# Synthèse critique — red-team 4 agents (UX · SEO · éditorial · business)

*4 agents adversariaux ont audité la stratégie et le prompt design. Ils convergent. Ce doc
tranche les contradictions et fixe le pivot. À lire AVANT de construire.*

---

## 0. Le signal fort : la convergence

Quatre lentilles indépendantes tombent sur **la même erreur racine** :

> **« Large et équilibré » (4 territoires, bilingue, curé, à parité) est intenable et
> contre-productif — pour un solo, sur tous les axes à la fois.**

- **Business** : le transfrontalier est un besoin d'éditeur, pas d'utilisateur ; battu par
  l'incumbent local sur chaque requête ; pas de moat ; pas de modèle de revenus.
- **UX** : « territoire primaire » contredit le modèle mental (temps + ville) ; la règle
  d'équilibre garantit ~75 % de bruit dans chaque rubrique ; la home curée **cache** l'exhaustivité
  qui est la promesse.
- **Éditorial** : **17-30 h/semaine en solo, indéfiniment** ; équilibre physiquement impossible
  (Vallée d'Aoste sous-sourcée) ; le site meurt à la 1ʳᵉ semaine d'absence.
- **SEO** : l'équilibre **bloque la seule tête de pont gagnable (Savoie)** ; volume auto = risque
  « scaled content » (spam) ; le mur d'autorité (backlinks) n'est adressé par aucun plan réaliste.

Quand UX, SEO, éditorial ET business disent « étroit et profond, pas large et équilibré », c'est
que le périmètre est le problème, pas les détails.

---

## 1. LE PIVOT central : marque large, profondeur étroite (Savoie d'abord)

L'erreur qu'on a faite : confondre **étendue de MARQUE** et **profondeur d'EFFORT**. On peut —
et on doit — **découpler** :

| Levier | Décision |
|---|---|
| **Marque / positionnement** | **4 territoires, bilingue, VISIBLES dès le jour 1** (nav, 4 hubs, fiches en langue d'origine, volume templaté). Coûte peu. Évite le pigeonhole « site savoyard » (le rejet de « Savoie d'abord » reste juste **sur ce plan**). |
| **Profondeur éditoriale + SEO + sourcing + liens** | **Concentrés sur la SAVOIE** les 12 premiers mois. C'est la seule tête de pont gagnable (là où tu sources le plus, où la concurrence est la moins SEO-agressive). On étend quand l'autorité est établie **quelque part**. |

→ « Savoie d'abord » n'était pas une connerie : c'était **vrai pour l'EFFORT, faux pour la
MARQUE**. On garde les 4 territoires affichés, on met les muscles sur la Savoie.

**Corollaire** : on **abandonne la règle « équilibre obligatoire, ≥1 par territoire »** dans les
rubriques curées. Qualité d'abord. Hiérarchie assumée : **Savoie/Piémont = profonds ; Vallée
d'Aoste/Nice = présents** (existent en nav + hubs pérennes + fiches, mais **pas** de promesse de
best-of hebdo). Un hub à moitié vide contamine la crédibilité des 4 — mieux vaut « présent et
honnête » que « équilibré et famélique ».

---

## 2. Les 3 contradictions internes — TRANCHÉES

Les agents ont trouvé que **nos docs se contredisent**. Décisions :

1. **Exhaustivité vs curation (home).** La promesse produit = « l'agenda exhaustif », or la home
   la cachait.
   → **La home garde l'orientation curée, MAIS l'exhaustivité est visible** : « Voir les 137
   événements du week-end → » (compteur vivant, au-dessus de la ligne de flottaison) + **champ de
   recherche visible** + chaque rubrique expose sa longue traîne (« …et 84 autres → »).

2. **Temps primaire vs territoire primaire.** Notre propre dissection GuidaTorino ET notre header
   disent **temps primaire** (« Ce week-end » en 1 clic) ; la stratégie disait « territoire
   primaire » sans preuve.
   → **Le TEMPS est l'axe primaire** (« Ce week-end » / « Aujourd'hui »). Le **territoire + la
   ville sont des FILTRES** dedans. Bonus : avec la tête de pont Savoie, la question « quel
   territoire » se dissout largement (c'est surtout de la Savoie). Et **la ville doit être
   filtrable dès le lancement** (au moins les 5 villes-ancres) — c'est l'unité mentale réelle, pas
   la région.

3. **Grille = territoires d'abord (PROMPT) vs catégories (PLAN).**
   → Séparer **deux zones étiquetées** : « QUAND ? » (temps, primaire) puis « OÙ ? » (territoires/
   villes) et « QUOI ? » (catégories) — et **tuer la redondance** (un emplacement canonique par
   axe, le footer en rappel discret).

---

## 3. Les risques SEO structurels — décisions

- **Ne PAS auto-publier la masse (score 4-6) dans l'index.** Volume pour la navigation ≠ volume
  pour Google. **`noindex` jusqu'à un seuil** de qualité/densité ; n'indexer que fiches + hubs à
  valeur réelle. (Sinon : profil « scaled content », pénalisable depuis mars 2024.)
- **Deux sites : segmenter par publication, PAS par canonical.** Un événement vit sur **UN** site :
  score ≥7 → **Cultura Sabauda uniquement** ; score <7 → **Agenda Sabauda uniquement**. Fini le
  canonical cross-domaine (fragile, il donne l'autorité à l'autre domaine, et le bug
  `wp_post_id_cs` propagerait des canonicals cassés). Un cheval par événement.
- **Réduire les pages « fraîcheur »** : garder « Ce week-end » (national + Savoie surtout) ;
  **`noindex` « Aujourd'hui » et « Cette semaine »** (utilitaires, impossibles à garder frais en
  solo). Trancher la page canonique pour « ce week-end en Savoie » (le hub temporel OU le hub
  territoire, pas les deux).
- **Bilingue** : `noindex` les hubs de la langue minoritaire tant qu'ils n'ont pas de contenu
  natif réel (évite de flaguer tout `/it/` comme thin). Valider le **hreflang sur les hubs et
  gabarits maison**, pas seulement les fiches.

---

## 4. Survie sans Franck (bus factor = 1)

Le site meurt à la 1ʳᵉ absence si les blocs curés figent sur du passé.
- **Expiration automatique** des blocs curés : passé un délai, bascule sur le **flux auto templaté**
  (« Voir tout l'agenda du week-end ») plutôt que d'afficher du périmé.
- **Purge des passés à l'affichage** (rejouer la datation déterministe qui existe déjà).
- **UNE seule cadence curée hebdo** (« Ce week-end » + « Les 10 »), **FR d'abord, IT différé**.
  Tuer « Aujourd'hui »/« Cette semaine » au MVP.
- **Semi-automatiser le best-of** : le pipeline propose les N meilleurs par territoire (SQL),
  Franck valide/réordonne en 10 min. Passer de « rédacteur » à « éditeur ».
- **Sauvegarde de la base** (déjà faite : `scripts/backup_db.py` + cron — l'activer).

---

## 5. Les deux risques existentiels (à regarder en face)

Ceux-là ne se « corrigent » pas par une feature — c'est une décision d'ambition :

- **Pas de moat.** Data publique, curation solo = anti-moat. Le seul moat durable = **les
  organisateurs qui poussent leurs événements chez toi en premier** (effet réseau, façon
  Eventbrite). → piste : faire de « Proposer un événement » un vrai outil pour organisateurs +
  un **widget agenda embeddable** (chaque intégration = un backlink + un pas vers l'effet réseau,
  et ça remplace l'outreach OT à rendement quasi nul).
- **Pas de modèle de revenus nommé.** SEO/newsletter/social = des canaux d'audience, pas des
  revenus. **Décision d'ambition à prendre** : Agenda Sabauda est-il (a) un **actif de marque au
  service de Cultura Sabauda** (barre basse, effort mesuré, pas de pression revenus) ou (b) un
  **business autonome** (alors il faut un modèle : mises en avant payantes organisateurs,
  partenariats OT, billetterie affiliée — et le moat ci-dessus) ? Les arbitrages d'effort en
  dépendent entièrement.

---

## 6. Ce que je DÉFENDS malgré les critiques (je ne capitule pas en bloc)

- **Garder le concept transfrontalier « Sabaudo »** — mais comme **angle éditorial/narratif**
  (récits, comparaisons, « de l'autre côté des Alpes ») porté par Cultura Sabauda, **pas** comme
  promesse de service agenda. C'est un territoire de marque défendable que ni GuidaTorino ni les
  OT n'occupent (les 4 agents le concèdent en creux).
- **Garder les 4 territoires visibles** (contre le « Savoie-only » de certains agents) : le
  pigeonhole de marque est réel. C'est la PROFONDEUR qu'on rétrécit, pas la marque.
- **La rigueur éditoriale** (anti-hallucination, tout en draft, refus de la trad machine) est un
  vrai différenciateur de **confiance** — à garder.

---

## 7. Décisions à acter AVANT de construire ce soir

1. **Périmètre** : 4 territoires visibles (marque) + **profondeur Savoie d'abord** (effort). Pas
   d'équilibre forcé.
2. **Home** : temps primaire · exhaustivité visible (compteur + recherche) · pas de règle
   d'équilibre · une seule rubrique curée hebdo.
3. **Ville filtrable dès le lancement** (5 villes-ancres) ; « 📍 Près de moi » opt-in dès le
   lancement (sert le voyageur, sans les défauts de l'IP).
4. **Index** : masse en `noindex` jusqu'au seuil ; **un site par événement** (pas de canonical
   cross-domaine) ; « Aujourd'hui »/« Cette semaine » en `noindex`.
5. **Survie** : expiration auto des blocs curés + purge des passés + sauvegarde base active.
6. **Ambition** : trancher (a) actif de marque vs (b) business — ça conditionne tout le reste.
7. **Moat/liens** : prévoir le **widget embeddable** au lieu de miser sur l'outreach OT.

*Le projet n'est pas mort : c'est le PÉRIMÈTRE DE LANCEMENT qui l'était. « Marque large,
profondeur Savoie, temps primaire, exhaustivité visible, volume non indexé, survie automatisée »
= une version qu'un solo peut lancer, tenir, et faire ranker quelque part.*
