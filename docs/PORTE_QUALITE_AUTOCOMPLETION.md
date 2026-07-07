# Porte qualité + Agent d'auto-complétion

*But (demande de Franck) : un événement ne part en brouillon sur **Agenda Sabauda**
que s'il est **complet**. S'il lui manque quelque chose, il **reste dans le
dashboard**, où un **agent** le complète (scraping + recherche web), puis émet un
signal **« bon »** (on pousse) ou **« pas bon »** (on informe Franck sur Slack).*

## 1. « Complet », c'est quoi ?

Six champs **obligatoires** (`utils/completeness.py` — source unique de vérité) :

| Champ | Colonne DB | Rempli par |
|---|---|---|
| Date | `date_event_start` | `scripts/dates.py` (page JSON-LD → texte FR/IT LLM) |
| Lieu | `lieu` | `scripts/venues.py` → `scripts/venues_web.py` (recherche web) |
| Ville | `ville` | idem |
| Territoire | `territoire` | source / évaluation |
| Catégorie | `llm_categorie` | `scripts/evaluator.py` |
| Image | `url_image` | `scripts/visuals.py` → `scripts/images_web.py` (web + **vérif vision**) |

> L'**image** a un filet de sécurité : la **bannière territoire** (`visuals.py`,
> étage 4) remplit toujours l'obligation. Mais on **préfère une vraie photo
> vérifiée** — `images_web.py` cherche une photo pertinente et un **second agent
> (vision)** confirme qu'elle correspond au sujet avant de l'accepter.

## 2. L'agent d'auto-complétion — `scripts/autocomplete.py`

Pour chaque événement **retenu, à venir, incomplet** : il complète (date → lieu →
image, du plus sûr au dernier recours), **re-vérifie**, puis :

- **complet** → pousse en **brouillon** Agenda Sabauda (jamais en ligne auto) +
  Slack ✅ ;
- **incomplet** → **reste** dans le dashboard (onglet « À compléter ») + Slack ⚠️
  avec la **liste des manques**.

Anti-spam : on ne re-notifie que si l'état a **changé** (`autocomplete_state`).

```bash
.venv/bin/python3 -m scripts.autocomplete --dry-run          # voir les incomplets + manques
.venv/bin/python3 -m scripts.autocomplete --cap 20           # compléter + pousser + Slack
.venv/bin/python3 -m scripts.autocomplete --no-web           # sans recherche web (moins cher)
.venv/bin/python3 -m scripts.autocomplete --no-publish       # compléter/signaler sans pousser
.venv/bin/python3 -m scripts.autocomplete --no-banner        # ne pas boucher l'image à la bannière
```

Bouton dashboard : **🛠️ Auto-compléter + porte qualité** (ou depuis l'onglet
« À compléter »).

## 3. La porte qualité à la publication en lot

`scripts/publish_batch_as.py` **n'envoie que les événements complets** par défaut.
Les incomplets sont **écartés** (listés avec leurs manques).

```bash
.venv/bin/python3 -m scripts.publish_batch_as --dry-run      # complets à publier / incomplets écartés
.venv/bin/python3 -m scripts.publish_batch_as --cap 50       # publie les complets
.venv/bin/python3 -m scripts.publish_batch_as --allow-incomplete   # contourne la porte (à éviter)
```

## 4. L'onglet « À compléter » (dashboard)

`/a-completer` : la file des retenus incomplets, avec pour chacun **les champs qui
manquent** (badges rouges) et un formulaire **✍️ Compléter à la main**. Un badge de
compteur apparaît dans la barre latérale.

## 5. Slack

### Sortant (signaux « bon » / « pas bon ») — **Incoming Webhook**
1. Slack → *Apps* → **Incoming Webhooks** → *Add to Slack* → choisir le canal.
2. Copier l'URL et l'ajouter au `.env` du VPS :
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
   BACKOFFICE_BASE_URL=https://backoffice.tondomaine.eu   # pour les liens « Compléter »
   ```
Sans `SLACK_WEBHOOK_URL`, les signaux sont simplement ignorés (rien ne casse).

### Entrant (Franck renvoie une info trouvée lui-même) — **Slash Command**
1. Slack app → **Slash Commands** → *Create* : commande `/agenda`,
   *Request URL* = `https://backoffice.tondomaine.eu/slack/complete`.
2. *Basic Information* → copier le **Signing Secret** dans le `.env` :
   ```
   SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxx
   ```
3. Usage depuis Slack :
   ```
   /agenda complete 42 lieu=Parco del Valentino ville=Torino url_image=https://…/photo.jpg
   ```
   Champs reconnus : `lieu`, `ville`, `territoire`, `categorie`, `image`/`url_image`,
   `date`/`date_start`, `date_end`. L'endpoint **vérifie la signature Slack** (HMAC) ;
   sans `SLACK_SIGNING_SECRET`, il refuse tout (pas d'accès ouvert).

## 6. Colonnes ajoutées

`autocomplete_at` (dernier passage), `autocomplete_state` (`ready` /
`missing:Lieu,Image` — pour l'anti-spam Slack). Migrées automatiquement par
`init_db` au prochain démarrage.

## 7. Sécurité (rappel)

Publication **toujours** en `draft`. Aucun secret dans le dépôt (tout en `.env`).
Le webhook Slack et le signing secret sont **révocables**. La recherche web d'image
respecte la charte §8 (source licenciable/institutionnelle, jamais le radar crédité).
