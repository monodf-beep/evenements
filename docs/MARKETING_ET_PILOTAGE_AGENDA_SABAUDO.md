# Marketing & pilotage — Agenda Sabaudo (solo, effort minimal)

*But : piloter la croissance en ~15 min/semaine, sans rien coder de fragile, sans vanity metrics.
Synthèse de deux recherches (repères GuidaTorino + bonnes pratiques growth solo 2025-2026).*

> **Mantra** : tu possèdes ta **newsletter** et ton **réseau de widgets** ; tu ne possèdes pas
> Google. Construis les deux premiers pendant que le troisième t'envoie du trafic gratuit.

---

## 1. Repères GuidaTorino (ordre de grandeur — PAS un objectif)

| | Ordre de grandeur | Source / fiabilité |
|---|---|---|
| Trafic | **≈ 600 000 visites/mois** (500–700k) | Semrush, nov. 2025 — estimation tierce ±50 % |
| Origine | ~65 % organique · ~23 % direct · ~12 % social/mail | Semrush |
| Facebook | ≈ 274 000 abonnés | fiche FB |
| Instagram | ≈ 132 000 abonnés | fiche IG |
| Ancienneté | lancé ~2011-2013 (≈ 10-13 ans) | indices (à confirmer WHOIS/archive.org) |
| Pages | des milliers (stock éditorial profond) | observé (/page/24/…) |
| Modèle éco | publireportages · mises en avant payantes lieux/orga · newsletter sponsorisée · AdSense/display · affiliation billetterie (ticketone) | page *pubblicità* |

**À retenir : ces 600k/mois = une décennie + ~400 000 abonnés sociaux.** Ce n'est pas un point de
départ, c'est un point d'arrivée. Ne jamais benchmarker un site neuf contre ça.

## 2. Cibles réalistes pour un solo (domaine neuf, marché alpin bilingue, plus étroit)

| Horizon | Trafic organique réaliste | Remarque |
|---|---|---|
| **6 mois** | **500 – 3 000 / mois** | Organique ~nul les 3-4 premiers mois (indexation + zéro autorité). Le trafic vient du **social + direct**. Ne pas juger le projet sur l'organique ici. |
| **12 mois** | **3 000 – 15 000 / mois** | La longue traîne locale commence à payer. Très dépendant de la cadence + des backlinks presse/OT. |
| **24 mois** | **15 000 – 60 000 / mois** | ~5-10 % de GuidaTorino. Dépasser 100k en 2 ans en solo = exceptionnel, pas un plan. |

## 3. Instrumentation — coût zéro, ZÉRO maintenance (ne rien coder)

**Décision : ne PAS coder de dashboard de trafic.** L'API Search Console est gratuite mais une
intégration maison casse silencieusement (token OAuth) = « projet dev déguisé en marketing ».

Stack retenue :
1. **Google Search Console** (vérif DNS → couvre `/fr/` + `/it/`) — source de vérité SEO.
2. **RankMath Analytics** (module gratuit) — branche déjà l'API GSC dans l'admin WP. Souvent
   suffisant pour un solo.
3. **GA4** (gratuit) — audience, récurrence, source. *(Alternative RGPD : Plausible cloud ~9€/mois
   si le cookie-less devient un argument ; sinon rester GA4.)*
4. **Looker Studio** (gratuit, Google) — connecteurs **GSC + GA4 natifs**, dashboard construit
   **une fois** (1-2 h), se met à jour tout seul. → **C'est ça, le "dashboard marketing".**
5. **IndexNow** via RankMath (ON) — feu-et-oubli, ne pas lire les logs à la main.

**Ce qui reste dans le dashboard maison (Flask)** : uniquement ce que Looker ne peut pas voir et
qui est **déjà en base** (voir §6) — la santé éditoriale/couverture. Zéro intégration externe.

## 4. Les 6 métriques qui comptent (le reste = bruit)

**Acquisition (Google me trouve-t-il ?)** — toutes dans GSC :
1. **Pages indexées vs non-indexées** (pages éditoriales) — viser >60-70 %. Alerte si
   « Explorée/Découverte, non indexée » grimpe sur de l'éditorial → signal qualité (§5).
2. **Impressions organiques** (tendance 12 sem.) — c'est la **pente** qui compte, pas la valeur.
3. **Position moyenne** — repérer les pages en **position 11-20** (les quick wins).
4. **Clics organiques** segmentés **FR vs IT** (pays) — la seule métrique = trafic réel.
5. **CTR** sur requêtes à fortes impressions — alerte si >500 impressions & <1,5 % CTR → réécrire
   title/meta (10 min, gros levier).

**Engagement / rétention :**
6. **Abonnés newsletter + taux d'ouverture** — **LA métrique de survie** (audience qu'on possède).
   Croissance nette positive/semaine ; ouverture >35-40 % ; 1er palier 500-1 000 abonnés.
   *(Bonus : % visiteurs récurrents GA4, viser >25-30 % hors pic de nouveauté.)*

**Vanity à NE PAS suivre** : pageviews brutes, followers sociaux, bounce/temps-sur-page isolés,
**nombre d'événements/articles publiés** (mesure l'activité, pas le résultat), backlinks en volume.

## 5. Le risque réel : "scaled content" (un agenda est PILE dans la cible)

Google (spam updates 2025) chasse le contenu de masse à faible valeur. Un agenda = des centaines
de fiches qui se ressemblent → danger réel. Règles de survie :
- **Événements passés → `noindex`** (pas suppression). Baisse d'indexation pour cette raison =
  sain, pas un problème.
- **Valeur ajoutée sur le top ~20 %** (gros événements) : contexte local, vraie photo, « pourquoi
  y aller ». Le reste = listing simple mais honnête.
- **Soumissions organisateurs → TOUJOURS modérées**, jamais d'auto-publication (sinon ferme à contenu).
- **Check-up santé hebdo** = le ratio « non indexée » sur l'éditorial dans GSC. Pas « combien j'ai publié ».

## 6. Les 5 leviers de croissance, classés ROI (impact/effort)

1. 🥇 **Widget agenda embeddable** — le levier n°1 (ce qui a fait GuidaTorino). Les OT/salles/hôtels
   l'intègrent → chaque intégration = **backlink local + distribution + effet réseau**. Effort
   ponctuel, rendement composé. *(Piste produit à développer post-lancement.)*
2. 🥈 **« Proposer un événement »** (formulaire modéré, TEC Community Events) — les organisateurs
   produisent le contenu + ont une raison de te lier/partager.
3. 🥉 **Backlinks locaux ciblés** — se lister dans les agendas/partenaires des OT des 4 territoires
   + 2-3 titres de presse (Le Dauphiné, La Stampa locale). **10 bons > 200 annuaires.**
4. **Newsletter** — actif anti-fragile ; hebdo « Que faire ce week-end » semi-automatisée depuis la base.
5. **Google Discover + GEO (IA)** — quasi aucune action dédiée : le socle (schema Event, grandes
   vraies photos >1200px, titres datés/spécifiques) que tu construis déjà EST le format idéal.

**À ignorer sans culpabilité (perte de temps solo)** : TikTok/Reels/X ; dashboard de trafic codé
maison ; outils GEO payants ; audit SEO à 500€ ; annuaires génériques ; blog « longue traîne »
hors zone. Pour le social local, **Facebook (groupes locaux + Events)** vaut mieux que tout le reste.

## 7. L'onglet « Pilotage » du dashboard maison (ce qui a du sens à coder — DB only)

**Uniquement des chiffres déjà en base `events_raw`** (aucune API externe, rien à casser) :

| Tuile | Calcul | Action déclenchée |
|---|---|---|
| **Événements actifs à venir** | count statut actif & date_debut ≥ aujourd'hui | fond de stock |
| **Couverture par territoire** | count actifs groupés par territoire | déséquilibre → pousser un levier sur le territoire creux |
| **% avec photo** | actifs avec image / total actifs | < seuil → problème de sourcing (déjà identifié) |
| **Routage** | count score ≥7 (→ Cultura Sabauda) vs <7 (→ Agenda Sabaudo) | dimensionne les deux flux de publication |
| **Passés non purgés** | count date_fin < aujourd'hui & statut actif | > 0 → relancer la purge |
| **File de publication** | actifs non encore poussés en brouillon | backlog éditorial |

→ Répond à « **où on en est côté CONTENU** » (ton vrai levier). Le « où on en est côté TRAFIC »
vit dans Looker Studio (§3). Deux tableaux, un seul par sujet, aucun doublon.

## 8. Feuille de route priorisée

**Socle (quand le site est live, effort ponctuel)** : GSC (DNS) + RankMath Analytics + schema Event
+ IndexNow ON → puis **Looker Studio** (1-2 h, zéro maintenance) + capture newsletter.
**Dans le mois** : widget embeddable → adoption OT ; formulaire « proposer un événement » modéré ;
10 backlinks locaux de qualité.
**Discipline permanente** : passés en `noindex` + valeur ajoutée top 20 % ; **routine hebdo 15 min**
= 1 page position 11-20 optimisée + report du chiffre newsletter.

## 9. À vérifier soi-même en 5 min (données non récupérables en session)
WHOIS/1er snapshot archive.org de guidatorino.com · Domain Rating/backlinks (Ahrefs Free) ·
abonnés newsletter GuidaTorino · trafic mentelocale.it. (WebFetch bloqué 403 + archive.org
indisponible côté agents ; chiffres §1 = snippets Semrush/Similarweb.)
