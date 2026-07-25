# Guide d'indexation — Agenda Sabauda

*Comment faire indexer, vite et proprement, des pages d'événements sur un site WordPress neuf.
Synthèse de 3 recherches web sourcées (doc officielle Google Search Central, analyse d'agrégateurs
à succès, éditeurs WordPress). Complète le brief de design, le plan du site et les règles
SEO/GEO/AEO. **Distinction stricte : [OFFICIEL Google] vs [communauté/observé].**

---

## 0. Trois vérités qui changent la stratégie

**1. Le « robot passe tous les 90 jours » est un mythe.** [OFFICIEL] Il n'existe aucun cycle fixe.
La fréquence de crawl dépend de la **crawl demand**, pilotée par la **popularité** (liens) et la
**fraîcheur** (staleness). Un site neuf à faible autorité est crawlé lentement au début
(~2-4 semaines pour l'indexation initiale, ordre de grandeur communautaire), et ça s'améliore
avec le contenu régulier et les premiers backlinks. On ne « force » pas un cycle : on **augmente
la crawl demand** des pages événements.
→ *Source : developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget*

**2. Il n'existe AUCUN bouton magique pour indexer sur Google.** [OFFICIEL]
- L'**Indexing API de Google est réservée aux `JobPosting` et aux `BroadcastEvent` (lives vidéo)**
  — **pas** aux événements culturels. Le mot « Event » dans « BroadcastEvent » est un piège :
  c'est de la diffusion vidéo en direct, pas un `Event` d'agenda.
- Les **services « d'indexation instantanée » payants** détournent cette API hors périmètre →
  indexation éphémère puis chute, et **risque de révocation d'accès**. John Mueller et Gary Illyes
  (Google) le déconseillent explicitement. **À proscrire.**
- Le **« ping » de sitemap est mort depuis fin 2023** (404). Ne plus compter dessus.
→ *Source : developers.google.com/search/apis/indexing-api/v3/using-api ; seroundtable.com/google-indexing-api-unsupported-content-39470.html*

**3. Le carrousel « Événements » de Google n'existe NI en France NI en Italie.** [OFFICIEL]
Les régions supportées sont : Australie, Brésil, Canada, Allemagne, Inde, Amérique latine,
Espagne, Royaume-Uni, États-Unis. **Nos 4 territoires ne sont pas couverts.** Le balisage
`Event` reste **très utile** — indexation propre, compréhension par Google, **moteurs IA/LLM
(GEO)**, validation, et le jour où Google élargit — mais **n'attends pas le widget événements
Google chez nous.** On balise pour le SEO/GEO, pas pour un carrousel qu'on n'aura pas.
→ *Source : developers.google.com/search/docs/appearance/structured-data/event (section régions)*

---

## 1. Faire indexer VITE un événement précis (ta question)

Il n'y a pas de raccourci unique : c'est une **combinaison** de leviers conformes. Pour un
événement important à faire indexer en quelques jours :

| # | Action | Effet | Qui/comment |
|---|---|---|---|
| 1 | **Le lier immédiatement depuis des pages fortes** (home « prochains événements » + hub « ce week-end » du territoire) | **Fort** — crée la crawl demand, Google le découvre via des pages souvent recrawlées | Automatique (gabarit) |
| 2 | **Sitemap à jour avec `lastmod` exact**, soumis en Search Console | Moyen-fort — signal de recrawl officiel | RankMath + GSC |
| 3 | **IndexNow** (soumission auto à la publication) | **Immédiat sur Bing/Yandex/Copilot** — nul sur Google | RankMath (gratuit) |
| 4 | **GSC → Inspection d'URL → Demander l'indexation** | Ponctuel, file prioritaire — **plafonné ~10-12 URL/jour/propriété** | Manuel, réservé aux temps forts |
| 5 | **Schema `Event` correct** | Qualité/compréhension (pas la vitesse) | Gabarit |

**La règle pratique :** les leviers 1-2-3 sont **automatiques et couvrent toute la masse**. Le
levier 4 (demande manuelle GSC) est **rare et précieux** : réserve-le aux **2-3 événements
phares de la semaine** — c'est exactement le périmètre de l'agent SEO du dashboard (voir la spec
dédiée). Pour un flux de dizaines de fiches/jour, la demande manuelle ne passe pas à l'échelle :
c'est l'architecture (leviers 1-2) qui fait le travail de fond.

**À NE PAS faire :** Indexing API pour événements · services « instant indexing » payants ·
ping de sitemap · re-soumettre en boucle une URL dans GSC (sans effet) · croire qu'IndexNow
indexe sur Google (faux).

---

## 2. L'architecture qui rend l'indexation rapide (la vraie solution durable)

L'indexation rapide se **gagne** par la structure. Modèle en **3 étages**, confirmé par les
agrégateurs à succès (Sortiraparis, Time Out, paris.fr) :

```
HUB EVERGREEN (URL fixe, recrawlé souvent)     ← capte le ranking + la crawl demand
   /fr/ce-week-end/, /fr/territoire/piemont/, /fr/agenda-du-mois/
        │  lien interne à chaque nouvel événement (lastmod du hub change → recrawl)
        ▼
FICHE ÉVÉNEMENT (1 URL unique par occurrence)  ← capte le rich snippet + l'indexation fraîche
   /fr/evenement/nom-ville/  + schema Event
        │  à sa date passée
        ▼
ARCHIVE (noindex ou eventStatus terminé)       ← jamais de 404 de masse
```

**Le pattern « URL evergreen recyclée »** (preuve directe : Sortiraparis réécrit chaque semaine
la MÊME URL `.../47103-week-end-...` avec les dates de la semaine). Pourquoi c'est décisif :
- l'autorité **s'accumule sur une URL stable** (une page du top 10 a en moyenne 3-5 ans) ;
- créer un **nouvel** article « ce week-end du 3 au 5 juillet » chaque semaine **dilue
  l'autorité** et crée de la cannibalisation + du futur index bloat.
- **Mais** evergreen ≠ figé : il faut **réellement réécrire** le hub à chaque cycle et mettre à
  jour son `lastmod`/`dateModified` (la fraîcheur est un signal).

→ C'est déjà dans notre plan du site (`/fr/ce-week-end/` fixe). Ce guide confirme et chiffre le
pourquoi.

---

## 3. La stack WordPress recommandée

| Brique | Choix | Pourquoi |
|---|---|---|
| Calendrier/événements | **The Events Calendar (TEC)** | Génère le **schema `Event` JSON-LD** automatiquement ; noindex d'office les vues mois/semaine |
| SEO + indexation | **RankMath** | **IndexNow inclus (gratuit)** + Instant Indexing + contrôle noindex fin. Le plus pertinent pour du contenu à durée de vie courte |
| Bilingue | **Polylang** (ou WPML) | hreflang FR↔IT propre ; slugs traduits ; chaque événement = une paire FR/IT liée |

**Pièges techniques documentés (à traiter à l'installation) :**
- TEC génère des URLs de vues (`/week/`, `/photo/`, `?eventDisplay=`, `?tribe-bar-date=`,
  `?eventDate=`) que Yoast/RankMath **ne voient pas** dans leur UI → il faut un snippet
  `functions.php` (`noindex` sur ces vues) + des `Disallow` robots.txt sur ces paramètres.
  Sinon : pagination quasi-infinie = index bloat.
- **Une seule source de schema** : désactive le schema `Event` de TEC **ou** celui du plugin SEO
  sur la fiche — jamais les deux (double markup).

> ⚠️ **Attention IndexNow ≠ Google.** RankMath propose aussi un « Instant Indexing » qui utilise
> l'**Indexing API de Google** — rappel : **valide uniquement pour JobPosting/BroadcastEvent**.
> N'active l'Instant Indexing Google **que** si tu balises des offres d'emploi/lives (pas notre
> cas). Pour nous : **IndexNow OUI** (Bing), **Instant Indexing Google NON**.

---

## 4. Anti-bloat : le piège mortel de tout agrégateur

Le risque n°1 d'un agenda = des milliers de fiches fines et périmées qui noient les bonnes pages
et gaspillent le crawl budget. Cas documenté : un site a généré 50 000 pages quasi-identiques →
**98 % désindexées par Google en 3 mois.** Et depuis mars 2024, le **« scaled content abuse »**
et le **contenu agrégé sans valeur ajoutée** sont explicitement du **spam** aux yeux de Google.

**Nos garde-fous (à intégrer dès la conception) :**
1. **Seuil de données minimum avant publication** : pas de fiche sans description propre + lieu +
   date + image. Pas de données = pas de page.
2. **Seuil sur les croisements** : pas de hub village × catégorie sous ~3-5 événements réels →
   `noindex` jusqu'au seuil (nos 4 territoires × quelques catégories = **dizaines** de hubs, le
   bon volume ; ne PAS descendre au village × micro-catégorie tant que la densité est faible).
3. **noindex des vues techniques** (mois/semaine/photo/paginées vides) — cf. §3.
4. **Événements passés = archive `noindex` ou `eventStatus: EventCompleted`**, jamais 404 de
   masse (ça détruit les liens accumulés).
5. **Pruning à 6 mois** : une page sans aucune impression après 6 mois → améliorer, consolider
   ou supprimer.
6. **Versions IT = vraie localisation**, pas de traduction automatique à l'échelle (la
   « traduction comme obfuscation » est citée dans la politique spam de Google).

→ *Sources : Google spam policies (mars 2024) ; getpassionfruit.com ; seomatic.ai*

---

## 5. Le Schema Event chez nous (avec la nuance France/Italie)

- **Baliser en JSON-LD `Event` chaque fiche** (une URL par occurrence). Requis : `name`,
  `startDate` (ISO-8601 **avec fuseau** `+01:00`/`+02:00`), `location` + `address` complète.
  Recommandé : `endDate`, `image` (720 px+, idéal 1920), `offers` (avec `priceCurrency` EUR),
  `organizer`, `eventStatus`, `performer`.
- **Expo longue** = 1 `Event` avec `startDate` **et** `endDate`. **Multi-dates** = 1 `Event` par
  occurrence. Pas de `T00:00:00` par défaut si l'heure est inconnue (date seule).
- **Annulation/report** : ne pas supprimer `startDate`/`location` ; changer `eventStatus`
  (+ `previousStartDate` si `EventRescheduled`).
- **Rappel** : le balisage **ne remplit pas** un « index événementiel » et **n'accélère pas** le
  crawl ; il rend la page **éligible** aux rich results (là où ils existent) et **lisible par les
  moteurs IA**. Chez nous (France/Italie), pas de carrousel Google → le bénéfice est
  indexation propre + GEO/AEO.
- **Valider** chaque gabarit au **Rich Results Test**, puis **surveiller** le rapport
  « Événements » de Search Console (Valide / Avertissement / Erreur).

*(Le JSON-LD complet prêt à coller est dans `REGLES_SEO_GEO_AEO_AGENDA_SABAUDA.md` §4.)*

---

## 6. La vraie priorité des 6-18 mois : les backlinks locaux

Toutes les sources convergent : pour un agenda neuf, **le levier n°1 n'est pas le volume de
fiches, ce sont les backlinks locaux et la régularité.** Concrètement, sur nos 4 territoires :
- se faire **lister et lier** par les **offices de tourisme** (vallées de Savoie/Haute-Savoie,
  Piémont, Vallée d'Aoste, Côte d'Azur), **mairies**, **syndicats d'initiative**, agendas de
  villes, **presse régionale** ;
- **réciprocité organisateurs** : quand on relaie un événement, demander un lien depuis la page
  officielle du lieu/organisateur ;
- **cohérence NAP** et présence sur les annuaires touristiques du territoire ;
- **régularité éditoriale** (fraîcheur des hubs).

C'est le vrai travail des premiers mois — bien plus rentable que d'empiler des fiches.

---

## 7. Checklists

### À la mise en place (une fois)
- ☐ WordPress : The Events Calendar + RankMath + Polylang installés
- ☐ Snippet `functions.php` + robots.txt qui `noindex`/`Disallow` les vues techniques TEC
- ☐ Une seule source de schema `Event` (pas de doublon)
- ☐ **IndexNow activé** (RankMath) — **Instant Indexing Google désactivé**
- ☐ Sitemaps propres (fiches à venir / hubs / pages), `lastmod` fiable, soumis en GSC
- ☐ hreflang FR↔IT vérifié (chaque page s'auto-référence + pointe sa jumelle)
- ☐ robots.txt autorise GPTBot / PerplexityBot / Google-Extended (GEO)
- ☐ Gabarit Event validé au **Rich Results Test**
- ☐ Seuils anti-bloat codés (données mini, seuil croisements, noindex vues vides)

### À chaque cycle (hebdo)
- ☐ Réécrire les hubs « ce week-end » (contenu + `lastmod`)
- ☐ Nouveaux événements liés depuis home + hubs
- ☐ **Demande d'indexation GSC pour les 2-3 temps forts** de la semaine
- ☐ Archiver/`noindex` les événements passés
- ☐ (mensuel) surveiller le rapport Événements + la couverture GSC ; pruning à 6 mois

---

## 8. Sources principales
- Crawl budget : developers.google.com/search/docs/crawling-indexing/large-site-managing-crawl-budget
- Indexing API (restrictions) : developers.google.com/search/apis/indexing-api/v3/using-api
- Sitemaps / lastmod / ping déprécié : developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping
- Event structured data (+ régions) : developers.google.com/search/docs/appearance/structured-data/event
- Spam policies / scaled content (mars 2024) : developers.google.com/search/blog/2024/03/core-update-spam-policies
- The Events Calendar SEO : liquidweb.com/help-docs/software/events-calendar/site-management/events-seo/
- RankMath IndexNow : rankmath.com/kb/how-to-use-indexnow/
- Preuve URL evergreen (Sortiraparis) : sortiraparis.com/.../47103-week-end-...
- Backlinks locaux événementiel : lseo.com/blog/.../leveraging-local-events-for-seo/

*Fiabilité : tout est [OFFICIEL Google] sauf — (a) délai d'indexation site neuf 2-4 semaines et
(b) quota GSC ~10-12 URL/jour, qui sont des ordres de grandeur communautaires non publiés par
Google, signalés comme tels.*
