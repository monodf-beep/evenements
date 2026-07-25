# Agenda Sabauda : la fiche événement (as-built)

> Document de référence technique. Décrit **ce qui est réellement construit et
> live** pour la fiche événement (page single d'un événement), par opposition
> au plan d'intention de `docs/TEMPLATES_WORDPRESS.md` (§B.7), qui date du
> 2026-07-06 et n'est plus exact sur ce point (voir §0 ci-dessous).
>
> Dernière mise à jour du code décrit : 2026-07-24.

---

## 0. ⚠️ Piège : deux snippets actifs, un seul réellement exécuté

Il existe **deux implémentations concurrentes** de la fiche événement dans
Code Snippets, toutes les deux actives, sur le même hook :

| Snippet | Nom | Priorité `template_redirect` | Statut réel |
|---|---|---|---|
| **56** | CS · Gabarit Fiche Événement (tribe_events) | **1** | **LIVE** — celui qui s'affiche |
| 13 | CS · Fiche événement (meta) | 5 | **MORT** — ne s'exécute jamais |

Les deux font `get_header()` + rendu + `get_footer()` + `exit` sur
`is_singular('tribe_events')`. Comme WordPress exécute les callbacks de même
hook dans l'ordre de priorité croissante, le snippet 56 (priorité 1) s'exécute
et sort (`exit`) **avant** que le snippet 13 (priorité 5) ait la moindre
chance de s'exécuter. Le code du snippet 13 est donc **totalement inerte**,
bien que marqué actif — un piège pour quiconque (humain ou IA) lit le snippet
13 en le prenant pour la vérité live (ça a failli arriver en écrivant ce
document).

**Conséquence concrète** : le snippet 13 documente/prévoit **3 rails**
(Au même endroit → Même catégorie → Près d'ici, mêmes dates). Le snippet 56,
le seul réellement affiché, n'en a que **2** (Au même endroit → Même
catégorie). Voir §5.

**Action recommandée (non faite) : désactiver ou supprimer le snippet 13**
pour éviter toute confusion future. Ce document ne décrit que le snippet 56.

---

## 1. Où et comment c'est rendu

- **Snippet 56**, hook `template_redirect` priorité 1, condition
  `is_singular('tribe_events')`.
- Même méthode que la home (§1 de `REGLES_HOMEPAGES_AGENDA_SABAUDO.md`) :
  `get_header()` + rendu manuel + `get_footer()` + `exit`, donc **hors de La
  Boucle WordPress** — mêmes précautions (`in_the_loop()` toujours faux ici).
- Traduction FR/IT **intégrée directement dans le snippet** (pas de traduction
  automatique façon page 928→1717) : un tableau `$LB` de libellés + une
  fonction `$tr()`, activés si `pll_get_post_language($event_id) === 'it'`.

```mermaid
sequenceDiagram
  participant U as Visiteur
  participant WP as WordPress core
  participant S56 as Snippet 56 (LIVE, prio 1)
  participant S13 as Snippet 13 (MORT, prio 5)

  U->>WP: GET /evenement/mon-evenement/
  WP->>S56: template_redirect (prio 1)
  Note over S56: get_header() + rendu complet + get_footer() + exit
  S56-->>U: HTML final
  Note over S13: Jamais atteint (exit deja appele)
```

---

## 2. Structure de la page (ordre réel d'affichage)

1. Fil d'Ariane (Accueil > Catégorie > Ville)
2. `<h1>` titre
3. Barre d'ancres « Dans cette fiche » (Quand / Où & prix / Carte) — seulement
   les ancres pertinentes (affichées seulement si la donnée existe)
4. Image mise en avant (3:2) + crédit photo, **ou image de repli** si absente
   (voir `REGLES_HOMEPAGES_AGENDA_SABAUDO.md` §7 — même mécanisme, snippet 87)
5. Description (contenu natif TEC, `post_content`)
6. Section **Quand** (`#as-quand`) : date(s), horaire
7. Section **Où & prix** (`#as-ou`) : lieu, adresse, prix, billetterie, source
   officielle, catégorie, « Vérifié le »
8. Section **Carte** (`#as-carte`) : Google Maps embarqué (via Complianz,
   consentement cookie) + lien « Ouvrir dans Maps »
9. Rail **« Au même endroit »** (voir §5)
10. Rail **« Même catégorie »** (voir §5)
11. Bouton Instagram (territoire de l'événement, voir §6)
12. Bouton Facebook (**toujours `href="#"`, jamais corrigé** — voir §6)
13. Formulaire de recherche
14. Bloc « Ajouter à mon agenda » (voir `AJOUTER_AU_CALENDRIER_AGENDA_SABAUDO.md`)
15. Bandeau newsletter (texte adapté à la ville de l'événement si connue)

---

## 3. Section « Quand » : logique événement en cours

Corrigé le 2026-07-24 (demande explicite, voir aussi §8 du doc homepages) :

```php
$as_in_progress = ($as_s_day < $as_today && $as_e_day >= $as_today);
```

- Si l'événement est **en cours** (a commencé, pas encore fini) : affiche
  « Jusqu'au {fin} » (FR) / « Fino al {fin} » (IT).
- Sinon : affiche « Date : {début}[ - {fin}] » (format classique), comme avant.

Corrige le cas d'un événement long (ex. avril → octobre) consulté en cours de
route, qui affichait auparavant « Date : 01/04/2026 - 31/10/2026 » — trompeur
(laisse croire que c'est fini ou pas commencé).

---

## 4. Badges de statut

Fonction `cs_event_badges()` (snippet 13 — **cette fonction-là est bien
utilisée par le snippet 56**, contrairement au reste du snippet 13, car elle
est définie avec `function_exists()` et appelée depuis ailleurs). Règles :

1. **`as_statut` = complet/annulé/reporté** → **écrase tout le reste**, badge
   unique (« Complet », « Annulé » en accent rouge, « Reporté »).
2. Sinon, si la fin est dans ≤ 2 jours : « Dernier jour » (si ≤ 0) ou
   « Plus que N jour(s) » — accent rouge.
3. Sinon, si l'événement a déjà commencé (fin > 2 jours mais début ≤
   maintenant) : badge « En cours » (neutre).
4. En plus, indépendamment : badge « Gratuit » si `_EventCost` vide, "0" ou
   littéralement "gratuit".

---

## 5. Les rails contextuels

Remplacent un ancien bloc générique « En vedette », jugé trop imposant et sans
rapport avec ce que l'utilisateur regarde (retour Franck, 2026-07-20).

| Rail | Critère | Exclusions |
|---|---|---|
| **Au même endroit** | même `_EventVenueID`, à venir (`_EventStartDate` ≥ maintenant), 6 max | l'événement courant |
| **Même catégorie** | même terme `tribe_events_cat` principal, à venir, 6 max | l'événement courant + tout ce qui est déjà dans « Au même endroit » (pas de répétition entre les 2 rails) |

Un rail **ne s'affiche pas du tout** si sa requête ne retourne aucun résultat
(`$render_rail` retourne silencieusement si `!$query->have_posts()`) — pas de
« No data was found » ici, contrairement aux sections home (§5.2 du doc
homepages). Différence de comportement assumée : ces rails sont secondaires,
une section vide n'est pas un signal utile ici.

**Rappel** : le snippet 13 (mort) prévoyait un 3e rail « Près d'ici, mêmes
dates » (même fenêtre de ±3 jours). **Non implémenté dans le code live.** À
construire si souhaité — cf. §0.

---

## 6. Réseaux sociaux : Instagram corrigé, Facebook toujours mort

- **Instagram** : corrigé le 2026-07-24. Réutilise `cs_instagram_account()`
  (snippet 88, voir doc homepages §9), mais avec le territoire de **cet
  événement précis** (via sa taxonomie `territoire`), pas le cookie/GET
  site-wide — nouvelle fonction `cs_instagram_canon_for_event($event_id)`
  (snippet 88). Le libellé du bouton précise le compte suivi (« Suivre Agenda
  Sabauda Savoie sur Instagram »).
- **Facebook** : **toujours `href="#"`, non corrigé.** Aucun compte Facebook
  par territoire n'existe/n'a été fourni à ce jour. À traiter le jour où un
  compte Facebook existera (même mécanique que Instagram, à dupliquer).

---

## 7. Traduction FR/IT

Contrairement à la home (traduction automatique 928→1717 via dictionnaire
`str_replace`, voir doc homepages §2), la fiche événement est **bilingue par
construction** : chaque événement est un post WordPress distinct par langue
(Polylang), et le même snippet 56 s'exécute pour les deux, en changeant
simplement de libellés via `$tr()`. Il n'y a donc **pas de page "source
unique"** ici — chaque traduction d'événement est éditée séparément dans TEC/
Polylang, comme n'importe quel autre custom post type traduit.

---

## 8. Dépendances

- `cs_fallback_visual()`, `cs_event_venue_line()`, `cs_event_territory_pill()`,
  `cs_pill_class()` — snippet 21 (« CS · Composants carte (partagé) »).
- `cs_atc_render()` — snippet 69, voir `AJOUTER_AU_CALENDRIER_AGENDA_SABAUDO.md`.
- `cs_instagram_account()`, `cs_instagram_canon_for_event()`,
  `cs_terr_canon_data()` (via mu-plugin `cs-territoire-persistant.php`) —
  snippet 88.
- `cs_event_badges()` — snippet 13 (fonction seule, réutilisée malgré le reste
  du snippet mort — voir §0/§4).

---

## 9. Écarts connus avec le plan d'origine (`TEMPLATES_WORDPRESS.md` §B.7)

| Prévu (2026-07-06) | Réalité (2026-07-24) |
|---|---|
| 3 rails (même lieu / catégorie / dates) | 2 rails seulement (dates non implémenté) |
| — | Section badges (« Dernier jour », « Complet »…), non détaillée dans le plan d'origine |
| — | Ancres de navigation « Dans cette fiche » (Quand / Où & prix / Carte), non prévues dans le plan |
