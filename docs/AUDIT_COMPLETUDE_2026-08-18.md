# Audit : comment une fiche devient complète, et ce qui peut tourner sans Franck

Demandé le 2026-08-18 : « un audit complet de ce qui se fait pour que les fiches des
événements soient complètes, et un audit pour savoir si on peut rendre les choses
autonomes via un cadre de décision — mais le cadre de décision, on l'a déjà bien établi. »

Le cadre est en effet établi (`CLAUDE.md`, « Autonomie : réversible = seul, irréversible =
jamais »). Cet audit ne le rediscute pas : il l'APPLIQUE, étape par étape, et dit ce qui
peut être allumé aujourd'hui.

**Méthode** : lecture du code et du `crontab.txt` réel, pas de la documentation. Les
chiffres de files manquent volontairement — ils arriveront par le relevé de santé de 12h05
(`scripts/publier_sante`), et un audit qui les inventerait vaudrait moins que rien.

---

## 1. Ce qu'est une fiche complète

Six champs, définis en un seul endroit (`scripts/lister_a_completer._OBLIGATOIRES`), avec
le même périmètre que la pastille du back-office — c'est ce qui garantit que le nombre
affiché ici et celui de l'écran ne divergent pas (règle 6) :

| Champ | Exception |
|---|---|
| `date_event_start` | sauf récurrents |
| `lieu` | sauf multi-lieux |
| `ville` | sauf multi-lieux |
| `territoire` | — |
| `llm_categorie` | — |
| `url_image` | — |

---

## 2. La chaîne réellement planifiée

Ce que le crontab exécute, dans l'ordre de la matinée :

| Heure | Script | Ce qu'il remplit | Coût |
|---|---|---|---|
| 8h00 | `scraper_events` | crée la fiche (titre, url, description) | nul |
| 8h15 | `gmail_collect` | idem, depuis les newsletters | nul |
| 8h25 | `dates --no-fetch --no-llm` | `date_event_*` par le texte seul | nul |
| 8h45 | `dates` | `date_event_*` (JSON-LD, puis LLM) | API |
| 8h47 | `dates_depuis_mail` | `date_event_*` depuis le corps du mail | nul |
| 8h50 | `venues` | `lieu`, `ville` (JSON-LD, puis LLM) | API |
| 8h52 | `moisson_officielle` | **tous** les champs d'une page officielle lue une fois | nul |
| 9h00 | `evaluator` | `territoire`, `llm_categorie`, score | API |
| 9h15 | `agent_quotidien` | tout, par lecture humaine des pages | API |
| 9h30 | `daily_batch` → `enrich` | article, et `url_image` par `og:image` | API |

**Le seul chemin qui traite un champ manquant après coup est l'agent de 9h15.** Tous les
autres sont des passes qui regardent la fiche une fois, à leur heure, et passent.

---

## 3. Ce qui existe et NE TOURNE PAS — le vrai trou

Trois outils écrits, testés, documentés… et jamais appelés :

| Script | Ce qu'il sait faire | Pourquoi il ne tourne pas |
|---|---|---|
| `autocomplete` | **l'orchestrateur** : date → lieu → image, chacun avec repli web, puis porte qualité et poussée en brouillon | appelé uniquement par `deploy/cron_pipeline.sh`, **qui n'est pas planifié** |
| `visuals` | image par Wikimedia Commons puis recherche web + vision | idem, et `complete_period` (manuel) |
| `images_web` | recherche d'image par le web | jamais appelé par un cron |

Son propre en-tête décrit `autocomplete` comme « le cœur de la demande de Franck ». Il ne
s'exécute pas depuis des semaines.

**MESURÉ APRÈS COUP, et c'est pire que ce que cette section annonçait.** Le détecteur écrit
dans la foulée (`scripts/audit_orphelins`) trouve **quatorze** étapes déclarées dans
`deploy/cron_pipeline.sh` que le crontab n'atteint jamais :

    autocomplete · visuals · images_web · images_wide · dates_web · venues_web
    refill_images_as · organizer_handles · press_kits · newsletter · ig_scheduler
    semaine_reminder · gmail_relink · cleanup_cinema

Les six premières sont exactement la **couche « dernier recours » de la complétude** : ce
qu'on lance quand la source se tait. Elles n'ont jamais tourné. C'est la réponse la plus
directe à « toutes les informations, on les trouve, c'est juste que des fois c'est mal
cherché » — ce n'est pas mal cherché, c'est que la recherche de secours n'est pas branchée.

**Et ce n'est pas un accident isolé : c'est un MOTIF de ce dépôt.** Quatre cas identiques
en trois semaines :

- `venues.py` — sa docstring disait « cron : après la datation » depuis toujours ; jamais
  planifié. Conséquence mesurée le 02/08 : 19 fiches sur 20 bloquées sur « manque Lieu » ;
- `dates_depuis_mail` — ajouté à `cron_pipeline.sh` seulement, donc inerte (11/08) ;
- `site_health_check` — « tourne chaque semaine en cron », faux ; 34 points périmés
  affichés (12/08) ;
- `auto_deploiement` — écrit hier soir, committé et inerte jusqu'à ce qu'on installe le
  crontab ce matin.

La règle 1 (« un identifiant en base ne prouve rien sur le site ») a donc un frère qu'il
faut écrire noir sur blanc : **un script dans le dépôt ne prouve pas qu'il s'exécute.**
`scripts/watchdog_crons` surveille les passages des scripts qu'il CONNAÎT ; il ne peut pas
signaler l'absence de ce qui n'a jamais été inscrit.

---

## 4. Par champ : qui remplit, et que se passe-t-il en cas d'échec

C'est la question qui décide de l'autonomie. Un champ dont l'échec n'a pas de recours est
un champ que seul un humain finira par remplir.

| Champ | Remplit | Recours si échec | Rouvreur | Verdict |
|---|---|---|---|---|
| date | `dates` (JSON-LD → LLM), `dates_depuis_mail`, moisson | `dates_web` (recherche) **non planifié** | compteur + empreinte de matière (`_rearme_matiere_changee`) | ✅ fermé |
| lieu / ville | `venues` (JSON-LD → LLM), moisson | `venues_web` **non planifié** | cooldown `VENUE_COOLDOWN_DAYS` | 🟡 recours non branché |
| territoire | `evaluator` | aucun | ré-évaluation | ✅ suffisant |
| catégorie | `evaluator` | aucun | ré-évaluation | ✅ suffisant |
| image | `enrich` (`og:image`) | `visuals`, `images_web` **non planifiés** | aucun | 🔴 **trou** |
| tous | `agent_quotidien` (lecture) | — | **mémoire des tentatives** (posée le 18/08) | ✅ depuis aujourd'hui |

**L'image est le seul trou franc.** Si `og:image` ne donne rien, plus personne ne cherche :
ni Wikimedia, ni la recherche web, ni la vision. La fiche reste « manque Image »
indéfiniment — c'est le cas de [4785] Oktoberfest, signalé ce matin, et la raison pour
laquelle des fiches complètes par ailleurs n'arrivent jamais au lot de publication.

---

## 5. Ce que le cadre de décision autorise, aujourd'hui, sans nouvelle règle

Rappel du cadre : **réversible = seul ; irréversible = jamais ; le jugement éditorial reste
humain.** Aucune des propositions ci-dessous n'est irréversible — elles écrivent des champs
en base (re-modifiables) et poussent des BROUILLONS (jamais en ligne).

| Proposition | Réversible ? | Coût | Décision |
|---|---|---|---|
| Planifier `autocomplete --cap N` après la moisson | oui | API par fiche | **arbitrage de coût**, pas de risque |
| Planifier `visuals` sur les fiches sans image | oui | API vision | idem |
| Brancher `dates_web` / `venues_web` en dernier recours | oui | API recherche | idem |
| Faire écrire à l'agent la mémoire des tentatives | oui | nul | ✅ **fait le 18/08** |
| Sortie de file après six angles épuisés | oui | nul | ✅ **fait le 18/08** |

**Ce qui bloque n'est donc pas le risque, c'est l'argent.** Trois jours d'arrêt complet du
14 au 17/08 pour crédit épuisé l'ont montré : la ressource rare de ce dispositif n'est ni
le code ni la confiance, c'est le quota API. Toute mise en autonomie supplémentaire doit
donc dire ce qu'elle coûte par jour — et c'est la seule question qui revient à Franck.

**La mémoire des tentatives change ce calcul**, et c'est pour ça qu'elle vient en premier :
sans elle, planifier `autocomplete` revenait à repayer chaque nuit les mêmes échecs (le
défaut mesuré sur la traduction : cinq refus identiques en une nuit). Avec elle, une
relance essaie un angle qui n'a jamais été essayé, ou n'a pas lieu.

---

## 6. Ce qui doit rester humain, et pourquoi

- **trancher un doublon en ligne** — deux fiches valides, une seule doit rester : c'est un
  choix éditorial, pas un fait ;
- **recharger le crédit API** — de l'argent ;
- **accepter une information que la source ne publie pas** — personne ne peut vérifier la
  capacité d'accueil d'une sortie au lac. Ce n'est pas une tâche, c'est un silence de la
  source, et la file ne doit pas le présenter comme un travail (leçon des 315 « tarifs non
  publiés » du 11/08) ;
- **fusionner deux branches divergentes**, déployer du CSS, dé-fusionner une fiche.

---

## 7. L'ordre que je propose

1. **Brancher l'image** — c'est le seul trou franc, et il bloque des fiches complètes par
   ailleurs. `visuals` sur les fiches sans image, cap serré, après la moisson ;
2. **Planifier `autocomplete`** avec un cap explicite, une fois (1) mesuré : il devient
   alors le recours général, et la mémoire des tentatives l'empêche de tourner en rond ;
3. **Brancher `dates_web` / `venues_web`** en dernier recours, dans l'échelle des angles ;
4. **Un contrôle « script écrit mais jamais planifié »** — comparer les scripts du dépôt
   aux lignes du crontab, et signaler les orphelins. C'est ce contrôle qui aurait trouvé
   les cinq cas de ce document, dont le mien d'hier soir.

Le point 4 est le plus important des quatre : les trois autres sont des correctifs, celui-là
empêche la faute de revenir.
