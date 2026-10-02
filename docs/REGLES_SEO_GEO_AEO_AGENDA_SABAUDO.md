# Règles SEO / GEO / AEO — Agenda Sabauda

*Playbook de construction du site public (pas un audit : le site n'existe pas encore). Cadre
repris et adapté du skill **SNLabat/SEO-GEO-AEO-Skill** (github.com/SNLabat/SEO-GEO-AEO-Skill),
appliqué au cas précis d'un agenda culturel bilingue FR/IT sur 4 territoires. À lire avec le
brief de design (§10 SEO) et le plan du site.*

---

## 0. Les trois disciplines — et pourquoi un agenda est un cas en or

- **SEO** (Search Engine Optimization) : être bien classé dans Google/Bing classiques.
- **GEO** (Generative Engine Optimization) : être **cité** par les moteurs génératifs
  (ChatGPT Search, Perplexity, Google AI Overviews, Gemini) quand ils *synthétisent* une réponse.
- **AEO** (Answer Engine Optimization) : être la réponse extraite — featured snippets, « Autres
  questions posées » (PAA), assistants vocaux.

**Pourquoi ça nous concerne plus que la moyenne.** Un agenda d'événements est structurellement
idéal pour le GEO/AEO : les moteurs IA répondent en continu à « que faire ce week-end à Annecy »,
« expos à Turin en ce moment », « sortie en famille dimanche à Nice ». Ces réponses réclament
**exactement** ce qu'on produit : des faits datés, localisés, tarifés, catégorisés. Si nos pages
sont structurées proprement (Schema Event + réponse directe + entités nommées), on devient la
**source que l'IA cite** — et sur le périmètre transfrontalier FR/IT, personne ne couvre les
4 territoires comme nous (signal d'originalité fort).

Corollaire : nos règles GEO/AEO ne sont pas un supplément, elles sont **au cœur** du gabarit
fiche et des hubs temporels.

---

## 1. SEO — les fondamentaux, par gabarit

### 1.1 Titles & meta descriptions (title 50-60 car., meta 150-160 car.)

| Gabarit | `title` (modèle) | `meta description` (modèle) |
|---|---|---|
| Home | Agenda Sabauda — Que faire dans les Alpes : Savoie, Piémont, Vallée d'Aoste, Nice | L'agenda culturel des 4 territoires alpins. Expositions, concerts, festivals, sagre : tout ce qu'il y a à faire ce week-end et cette semaine. |
| Ce week-end | Que faire ce week-end dans les Alpes (4–6 juillet 2026) — Agenda Sabauda | Les sorties de ce week-end en Savoie, Piémont, Vallée d'Aoste et à Nice : concerts, expos, festivals, marchés. Sélection + agenda complet. |
| Territoire | Événements et sorties en Piémont — Agenda Sabauda | Que faire en Piémont : expositions, concerts, festivals et sagre à Turin, Cuneo, Alba… L'agenda mis à jour en continu. |
| Catégorie | Concerts & musique dans les Alpes : Savoie, Piémont, Aoste, Nice — Agenda Sabauda | Tous les concerts à venir sur les 4 territoires alpins. Dates, lieux, tarifs — agenda actualisé. |
| Croisement | Concerts en Piémont : l'agenda des prochains concerts — Agenda Sabauda | Les concerts à venir en Piémont, de Turin aux Langhe. Dates, lieux et infos pratiques. |
| Fiche | [Événement] — [Ville], [dates] — Agenda Sabauda | [1 phrase factuelle : quoi, où, quand, gratuit/tarif]. |

Règles : la **date dans le title** des hubs temporels et des fiches (booste le CTR), jamais deux
titles identiques, marque « Agenda Sabauda » en suffixe partout. En IT : title/meta traduits,
`inLanguage` cohérent.

### 1.2 Structure & technique

- **1 seul H1** par page, hiérarchie H2/H3 logique (voir AEO §3 pour la formulation en question).
- **URLs propres** (déjà définies dans le plan du site : `/fr/ce-week-end/`, sans millésime pour
  les récurrents).
- **Canonical auto-référent** sur chaque page ; pages paginées auto-canoniques (pas de canonical
  vers la page 1).
- **hreflang** FR/IT par paires + `x-default` (voir §6).
- **Open Graph + Twitter Card** sur toutes les pages (image 1200×630) — critique pour le partage
  du listicle « Les 10 du week-end » et des fiches.
- **alt d'image descriptif** : « [Nom de l'événement], [lieu], [ville] » — pas « image1.jpg ».
- **Pagination crawlable** (`/page/2/`), jamais scroll infini pur (cf. brief §10).
- **Sitemaps** séparés : fiches à venir + récurrents / hubs / pages éditoriales, `lastmod`
  fiables, hreflang inclus. Fiches passées noindexées retirées du sitemap.
- **robots.txt** : autoriser le crawl, référencer les sitemaps ; **ne pas** bloquer les crawlers
  IA (GPTBot, PerplexityBot, Google-Extended) — on VEUT être lu par eux (choix assumé, cf. §2.5).

### 1.3 Maillage interne (hub-and-spoke)

Chaque fiche renvoie vers 4-6 hubs (breadcrumb catégorie + territoire, 3 rails « liés », lien
ville). Chaque hub liste ses fiches et pointe ses croisements. Footer = filet de sécurité du
maillage. C'est ce qui fait remonter les pages de liste.

---

## 2. GEO — être cité par les moteurs génératifs

### 2.1 E-E-A-T : l'entité éditoriale doit être limpide

- **Éditeur nommé** : « Agenda Sabauda, édité par **Cultura Sabauda** » présent en footer + page
  À propos + schema `Organization`/`publisher`. Une IA cite plus volontiers une source dont
  l'entité et la ligne éditoriale sont claires.
- **Page À propos** substantielle (le texte bilingue est prêt : `PLAN_DU_SITE…` §4) : qui, quoi,
  pourquoi le périmètre transfrontalier.
- **Contact réel** accessible (page Contact + `ContactPoint` schema).
- **Signaux de confiance** : « **Vérifié le JJ/MM/AAAA** » sur chaque fiche (date de dernière
  vérification à la source officielle) — c'est notre différenciateur d'agrégateur, et un signal
  de fraîcheur/fiabilité que les moteurs IA valorisent.
- **Politique crédits photos** liée (rassure + protège) — cf. règles éditoriales.

### 2.2 Clarté d'entité (entity clarity) + `sameAs`

- Nommer **toujours** de la même façon : événement, lieu, ville, organisateur (ville → province/
  département → territoire).
- **`sameAs` vers Wikidata/Wikipedia** pour les lieux et grands équipements récurrents (ex. le
  lieu « Museo Egizio » → sa page Wikidata ; ville « Chambéry » → Wikidata). Ça désambiguïse
  l'entité pour les moteurs IA (Chambéry-en-Savoie, pas un homonyme).
- **`Organization` avec `sameAs`** vers les profils sociaux d'Agenda Sabauda (une fois lancés).

### 2.3 Densité factuelle (le point fort naturel d'un agenda)

Chaque fiche affiche en clair, en texte HTML réel (jamais en image) : **dates, horaires, lieu +
adresse, ville, tarif (ou “Gratuit”), catégorie, organisateur**. Ce sont des faits que l'IA peut
extraire et citer tels quels. Règle : la donnée pratique est du texte, structurée aussi en
JSON-LD (§4) — jamais uniquement dans une image ou un PDF.

### 2.4 Originalité & couverture

- **Angle unique** : la couverture des 4 territoires transfrontaliers FR/IT en un seul lieu
  n'existe pas ailleurs. À énoncer explicitement (À propos, intros de hub) — c'est un signal
  d'originalité que les moteurs génératifs recherchent.
- **Réponse synthétique** en tête de hub (voir AEO §3.2) : une IA peut la reprendre presque
  telle quelle.

### 2.5 GEO technique

- **HTTPS**, crawl propre, temps de réponse corrects.
- **Ne pas bloquer** GPTBot / PerplexityBot / Google-Extended dans robots.txt (choix assumé :
  on veut être cité ; le contenu radar n'est de toute façon jamais republié, donc rien de
  sensible n'est exposé).
- **`llms.txt`** (standard émergent, à la racine) : un index texte des pages/hubs clés à
  destination des LLM. Statut expérimental et support inégal — **optionnel**, faible coût, à
  poser en v2 si le temps le permet. Ne pas en attendre d'effet garanti.
- **Schema riche** (§4) : `Event`, `Organization`, `BreadcrumbList`, `ItemList`, `FAQPage`,
  `SpeakableSpecification`.

---

## 3. AEO — featured snippets, « Autres questions », vocal

### 3.1 Titres formulés en question

Sur les hubs et les FAQ, doubler le H1/H2 d'une formulation interrogative naturelle :
- Hub territoire → un H2 « **Que faire en Piémont ce week-end ?** »
- Hub catégorie → « **Où voir une exposition en Savoie ?** »
- Fiche → « **L'événement est-il gratuit ? À quelle heure ? Comment s'y rendre ?** »
Ce sont les formulations que tapent/dictent les gens et que les moteurs mettent en avant.

### 3.2 Le bloc « réponse directe » (40-60 mots) en tête de hub

Juste sous le H1 d'un hub temporel/territoire, un paragraphe de **40-60 mots** qui répond
directement, réécrit à chaque période :

> *Ce week-end en Savoie et Haute-Savoie, une quarantaine d'événements : festival de musique au
> bord du lac d'Annecy, marché des potiers à Chambéry, expositions à Aix-les-Bains et fêtes de
> village en Tarentaise. Voici la sélection et l'agenda complet, du vendredi au dimanche.*

C'est le format que les featured snippets et les IA reprennent. Il fait aussi office de chapô
éditorial (double usage : lecteur + machine).

### 3.3 FAQ schema — sur la fiche et les hubs

Questions/réponses courtes, marquées en `FAQPage` (§4.2). Exemples par gabarit :
- **Fiche** : « Quand a lieu [événement] ? » · « Où se déroule-t-il ? » · « Est-ce gratuit ? » ·
  « Faut-il réserver ? »
- **Hub territoire** : « Que faire en Piémont ce week-end ? » · « Quels sont les grands festivals
  du Piémont ? »

> ⚠️ **Nuance honnête** : depuis 2023, Google n'affiche plus les *rich results* FAQ que pour de
> rares sites (gouvernementaux/santé). Le balisage FAQPage reste néanmoins utile pour l'AEO
> (autres moteurs, assistants, IA génératives) et **n'est pas pénalisant** — on le garde, sans
> en attendre l'étoile FAQ chez Google.

### 3.4 Formats extractibles

- **Listes** (l'agenda EST une liste — la baliser `ItemList`).
- **Tableaux** pour les comparatifs (ex. « les marchés de Noël des 4 territoires » : ville /
  dates / spécialité).
- **Phrases-définition** (« La Foire de Saint-Ours est… ») en tête de fiche récurrente.

### 3.5 Vocal & longue traîne locale

- Langage **conversationnel**, requêtes longues : « que faire avec les enfants dimanche à
  Chambéry », « marché aux truffes ce week-end dans les Langhe ».
- **Signaux locaux** forts : NAP (nom-adresse-téléphone du lieu), `Place`/`PostalAddress`,
  mentions explicites de la ville et du territoire dans le texte.
- **`SpeakableSpecification`** sur le bloc réponse directe des hubs (spec Google pour le vocal ;
  support limité mais peu coûteux).

---

## 4. Le balisage concret (JSON-LD prêt à brancher)

### 4.1 `Event` (sur chaque fiche) — le plus important

```json
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "Cinéma en plein air au château",
  "startDate": "2026-07-04T21:30:00+02:00",
  "endDate": "2026-07-04T23:30:00+02:00",
  "eventStatus": "https://schema.org/EventScheduled",
  "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
  "location": {
    "@type": "Place",
    "name": "Château des Ducs de Savoie",
    "sameAs": "https://www.wikidata.org/wiki/Q1499541",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "Place du Château",
      "postalCode": "73000",
      "addressLocality": "Chambéry",
      "addressRegion": "Savoie",
      "addressCountry": "FR"
    },
    "geo": { "@type": "GeoCoordinates", "latitude": 45.564, "longitude": 5.917 }
  },
  "image": ["…/hero-16x9.jpg", "…/hero-4x3.jpg", "…/hero-1x1.jpg"],
  "description": "Projection en plein air dans la cour du château.",
  "offers": {
    "@type": "Offer",
    "url": "https://billetterie-officielle…",
    "price": "7.00", "priceCurrency": "EUR",
    "availability": "https://schema.org/InStock",
    "validFrom": "2026-05-01"
  },
  "organizer": { "@type": "Organization", "name": "Ville de Chambéry", "url": "…" },
  "inLanguage": "fr",
  "isAccessibleForFree": false,
  "publisher": {
    "@type": "Organization", "name": "Agenda Sabauda",
    "url": "https://agendasabauda.eu",
    "parentOrganization": { "@type": "Organization", "name": "Cultura Sabauda" }
  }
}
```
Requis pour le rich result « Événements » de Google : `name`, `startDate`, `location.address`
complète. Gratuit → `price: "0"` + `isAccessibleForFree: true`. Multi-dates non contiguës = un
objet `Event` par occurrence. « Date à confirmer » → **pas** de balisage Event (pas de date
inventée).

### 4.2 `FAQPage` (fiche + hubs)

```json
{
  "@context": "https://schema.org", "@type": "FAQPage",
  "mainEntity": [
    {"@type": "Question", "name": "L'événement est-il gratuit ?",
     "acceptedAnswer": {"@type": "Answer", "text": "L'entrée est de 7 € (5 € tarif réduit)."}},
    {"@type": "Question", "name": "Où se déroule l'événement ?",
     "acceptedAnswer": {"@type": "Answer", "text": "Au Château des Ducs de Savoie, à Chambéry (Savoie)."}}
  ]
}
```

### 4.3 `ItemList` (hubs de liste — les événements)

```json
{
  "@context": "https://schema.org", "@type": "ItemList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1,
     "url": "https://agendasabauda.eu/fr/evenement/…"},
    {"@type": "ListItem", "position": 2, "url": "…"}
  ]
}
```

### 4.4 `BreadcrumbList` (toutes pages internes) · `Organization` (éditeur) · `WebSite`+`SearchAction` (home)

```json
{"@context":"https://schema.org","@type":"WebSite",
 "name":"Agenda Sabauda","url":"https://agendasabauda.eu",
 "inLanguage":["fr","it"],
 "publisher":{"@type":"Organization","name":"Cultura Sabauda"},
 "potentialAction":{"@type":"SearchAction",
   "target":"https://agendasabauda.eu/fr/recherche/?q={q}","query-input":"required name=q"}}
```

---

## 5. Grille d'auto-audit (adaptée du skill, score 1-10 par gabarit)

Score : **1-3** critique · **4-5** insuffisant · **6-7** correct, à améliorer · **8-9** solide ·
**10** exemplaire. À faire tourner sur chaque gabarit avant mise en ligne, puis 1×/trimestre.

**SEO** — ☐ title 50-60 car. unique & daté (hubs) ☐ meta 150-160 ☐ 1 H1 + hiérarchie
☐ URL propre ☐ canonical ☐ hreflang FR/IT ☐ OG/Twitter + image 1200×630 ☐ alt descriptifs
☐ pagination crawlable ☐ sitemap à jour ☐ maillage 4-6 liens sortants/fiche.

**GEO** — ☐ éditeur nommé (Cultura Sabauda) partout ☐ À propos substantielle ☐ Contact réel
☐ « Vérifié le… » sur les fiches ☐ entités nommées de façon cohérente ☐ `sameAs` villes/lieux
majeurs ☐ densité factuelle (dates/lieu/tarif en texte) ☐ angle transfrontalier énoncé
☐ crawlers IA autorisés ☐ schema Event+Organization valides.

**AEO** — ☐ un H2 en question par hub ☐ bloc réponse directe 40-60 mots ☐ FAQPage (fiche+hub)
☐ listes/tableaux extractibles ☐ NAP + Place/adresse ☐ langage conversationnel/longue traîne
☐ Speakable sur le bloc réponse.

---

## 6. Bilinguisme & mesure

- **hreflang** : chaque URL s'auto-référence et pointe sa jumelle (`fr`↔`it`) + `x-default`.
  `inLanguage` cohérent dans chaque JSON-LD. Une fiche non traduite n'émet pas de hreflang vers
  une page inexistante.
- **Mesure SEO** : Google Search Console (2 propriétés ou filtres FR/IT), suivi des requêtes
  « que faire… », des pages hubs, du sitemap.
- **Mesure GEO/AEO** (émergent, imparfait) : surveiller les mentions dans les réponses IA
  (tester manuellement « que faire ce week-end à Turin » sur Perplexity/ChatGPT Search), suivre
  le trafic référent depuis les moteurs IA dans l'analytics, surveiller les featured snippets
  gagnés dans la GSC.

---

## 7. Ce qui exige des outils externes (à ne pas bâcler « à la main »)

Ces dimensions ne se mesurent pas dans le HTML — les nommer, ne pas les inventer :
- **Core Web Vitals / vitesse réelle** → PageSpeed Insights, Lighthouse.
- **Backlinks / autorité de domaine** → Ahrefs, Semrush.
- **Indexation réelle & couverture** → Google Search Console.
- **Validation du balisage** → Rich Results Test de Google, Schema.org validator.

---

*Cadre de référence : SNLabat/SEO-GEO-AEO-Skill (audit SEO/GEO/AEO pour Claude), adapté ici en
règles de construction pour un agenda culturel bilingue. Ce document est un playbook amont : il
se combine au brief de design (gabarits, composants) et au plan du site (arborescence, URLs).*
