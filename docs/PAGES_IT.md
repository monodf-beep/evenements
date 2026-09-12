# Pages & menu italien — miroir Polylang

*But : compléter la version **IT** du site (agendasabauda.eu) qui manque encore ses pages
de navigation et son menu. Le FR est en place ; chaque URL a sa jumelle `/it/…` (slugs
traduits). Trois pages prioritaires + le menu IT. À faire en session connectée à Novamira,
verify-first, réversible. Polylang FR/IT : chaque page IT est la **traduction liée** de sa
page FR (pas un doublon indépendant), et ses requêtes doivent forcer `lang => 'it'`.*

---

## Ce qui manque (rappel Franck)

| Page IT | Jumelle FR | Slug cible |
|---|---|---|
| **Questo weekend** | Ce week-end (`/fr/ce-week-end/`) | `/it/questo-weekend/` |
| **Eventi** (tout l'agenda) | Tout l'agenda (`/fr/evenements/`) | `/it/eventi/` |
| **Informazioni utili** | Infos utiles / hub Le projet | `/it/informazioni-utili/` |
| **Menu IT** | Menu principal FR | emplacement « menu principal » langue IT |

Symptôme observé : « Vale il viaggio » / « Nuove mostre » vides en IT → les Listing Grids
IT n'ont pas de requête en `lang => 'it'`, ou la page IT n'existe pas.

---

## Prompt à coller dans la session Novamira

```
On COMPLÈTE la version italienne d'agendasabauda.eu (Polylang FR/IT). Il manque 3 pages de
nav IT et le menu IT. Chaque page IT doit être la TRADUCTION LIÉE de sa page FR (via
Polylang), pas un doublon. Toutes les requêtes JetEngine des pages IT forcent lang => 'it'.
Verify-first, réversible, confirmation avant chaque écriture.

ÉTAPE 0 — INVENTAIRE (ne rien modifier)
Liste, pour /fr/ce-week-end/, /fr/evenements/ et la page « infos utiles » FR : leur ID,
leur statut de traduction Polylang (IT existe ? liée ?), et le nom du/des Listing Grid
qu'elles contiennent. Donne-moi ce tableau AVANT de créer quoi que ce soit.

ÉTAPE 1 — QUESTO WEEKEND (/it/questo-weekend/)
Crée la traduction IT de /fr/ce-week-end/, liée via Polylang. Reprends la même structure
(mêmes blocs / Listing Grids) mais chaque requête d'événements force lang => 'it'
(filtre jet-engine/query-builder/types/posts-query/args, comme convenu). Titre IT
« Cosa fare questo weekend ». Montre-moi le rendu avant de continuer.

ÉTAPE 2 — EVENTI (/it/eventi/)
Traduction IT liée de /fr/evenements/ (la liste filtrable). Titre « Eventi ». Le filtre /
la liste tirent en lang => 'it'. Vérifie qu'un événement traduit en IT y apparaît et qu'un
non-traduit n'y apparaît PAS (repli attendu, pas de fiche FR affichée en IT).

ÉTAPE 3 — INFORMAZIONI UTILI (/it/informazioni-utili/)
Traduction IT liée de la page « infos utiles » FR. Contenu éditorial (pas une requête
d'événements) : reprends les rubriques FR traduites. Si un texte IT de référence existe
dans docs/PLAN_DU_SITE_AGENDA_SABAUDO.md (section « informativa » italienne), réutilise-le.

ÉTAPE 4 — MENU IT
Crée un menu « Principale IT » (ou traduis le menu FR) avec les entrées IT pointant vers
les pages IT :
  Cosa fare questo weekend → /it/questo-weekend/
  Eventi                   → /it/eventi/
  Territori                → hubs territoire IT
  Categorie                → catégories IT (déjà traduites : cf. cs-taxo-it.php)
  Informazioni utili       → /it/informazioni-utili/
Assigne-le à l'emplacement « menu principal » pour la LANGUE IT dans Polylang (pas en
écrasant le menu FR). Commutateur FR|IT en texte. Montre-moi le menu IT rendu sur une
URL /it/.

RÈGLES : par étapes, confirmation avant chaque écriture, garde l'ID de chaque page créée
pour rollback. Commence par l'ÉTAPE 0 (inventaire) et donne-la-moi.
```

---

## Contenu prêt à coller (Novamira n'a qu'à exécuter)

### Menu « Principale IT »

| Libellé IT | Pointe vers | Note |
|---|---|---|
| **Cosa fare questo weekend** | `/it/questo-weekend/` | page créée à l'ÉTAPE 1 |
| **Eventi** | `/it/eventi/` | page créée à l'ÉTAPE 2 |
| **Territori** ▾ | 4 archives territoire IT | termes déjà traduits (`cs-taxo-it.php`) : Savoia/Alta Savoia · Piemonte · Valle d'Aosta · Nizza. Prendre l'URL réelle de chaque archive IT. |
| **Categorie** ▾ | 11 archives catégorie IT | déjà traduites — reprendre les URLs des archives IT existantes. |
| **Informazioni utili** | `/it/informazioni-utili/` | page créée à l'ÉTAPE 3 |

Commutateur FR\|IT en texte (pas de drapeau). Assigner à l'emplacement « menu principal »
**langue IT** (ne pas écraser le menu FR).

### Texte « Chi siamo » (si Informazioni utili est une page éditoriale de type À propos)

> **Chi siamo — Agenda Sabauda**
>
> Agenda Sabauda è l'agenda culturale dello spazio alpino occidentale — un territorio senza
> confini che unisce la Savoia e l'Alta Savoia, il Piemonte, la Valle d'Aosta e Nizza. Il nostro
> obiettivo: riunire in un unico luogo tutto ciò che c'è da fare, da vedere e da vivere in questi
> quattro territori che la storia, la lingua e la montagna hanno da sempre legato.
>
> Nato dalla convinzione che la cultura non si ferma ai confini amministrativi, Agenda Sabauda
> raccoglie ogni settimana mostre, concerti, spettacoli, festival, sagre, mercati, feste
> tradizionali, appuntamenti per le famiglie e grandi eventi sportivi — dalle istituzioni più
> prestigiose ai più piccoli comuni di paese.
>
> Agenda Sabauda si rivolge a tutti: al viaggiatore di passaggio per un weekend come all'abitante
> che vuole scoprire, o riscoprire, ciò che accade vicino a casa — da un versante all'altro delle
> Alpi. Vi troverete, settimana dopo settimana, una selezione viva e l'agenda completo del
> periodo: ciò che inizia, ciò che finisce e ciò da non perdere questo weekend.
>
> Ci impegniamo a verificare le nostre informazioni alla fonte ufficiale — il luogo,
> l'organizzatore —, a citare ogni fotografia e a non pubblicare mai altro che eventi reali e in
> programma. Agenda Sabauda è edito da **Cultura Sabauda**, testata culturale bilingue dello
> spazio alpino occidentale.

*Note : « Informazioni utili » peut être (a) une page éditoriale « à propos / infos pratiques »
— alors utiliser le texte ci-dessus — ou (b) un hub de liens (Chi siamo · Proporre un evento ·
Contatto · Crediti foto · Note legali · Privacy). L'ÉTAPE 0 tranche en regardant ce que
contient la page FR « infos utiles ».*

---

## Rappels techniques

- **Catégories & territoires IT** sont déjà traduits (`cs-taxo-it.php`, `cs-fix-terms-language.php`).
  Ne pas les recréer — juste les référencer dans le menu.
- **Fiche non traduite = n'existe pas en IT** (repli vers le hub parent) : c'est voulu,
  ne force pas l'affichage d'une fiche FR sur une URL IT.
- La qualité des pages IT dépend surtout du **contenu italien** (plus d'événements IT) :
  le câblage rend les pages vivantes, le sourcing les remplit.
