# Prompts Claude-in-Chrome — configuration WordPress d'Agenda Sabauda

*À coller un par un dans Claude-in-Chrome, connecté à `https://agendasabauda.eu/wp-admin`.
Chaque prompt = une étape vérifiable. Règle de sécurité valable pour TOUS : « **ne saisis jamais
mot de passe / 2FA / paiement — arrête-toi et demande-moi. Ne supprime rien. Si un écran diffère,
montre-le-moi avant d'agir.** »*

> **Si tu as lancé `bootstrap.sh` (SSH)** : les étapes **1, 2, 6** sont déjà faites → passe-les.
> Sinon, fais tout dans l'ordre.

---

## 1. Permaliens
> Va dans **Réglages → Permaliens**. Choisis la structure **« Titre de la publication »**
> (`/%postname%/`). Clique **Enregistrer les modifications**. Confirme-moi la structure active.

## 2. Slugs de The Events Calendar
> Va dans **Évènements → Réglages** (onglet **Affichage** ou **URL**). Règle :
> - slug d'un événement (singulier) : **`evenement`**
> - base d'archive des événements : **`evenements`**
> Enregistre. Puis retourne dans **Réglages → Permaliens → Enregistrer** (pour purger les règles).
> Confirme-moi les valeurs enregistrées.

## 3. Assistant Rank Math + schéma unique + IndexNow
> **3a.** Ouvre l'assistant de configuration de **Rank Math**. Choisis **« Ignorer »** la connexion
> de compte (optionnelle), **Mode Avancé**, type de site **« Autre »**, **Sitemap : ON**. Termine
> l'assistant. Ne modifie rien d'autre pour l'instant.
>
> **3b. Schéma unique** (important) : va dans **Rank Math → Réglages du titre → Types de
> publication → Évènements**. Mets **« Type de schéma par défaut » = Aucun (None)**. Enregistre.
> *(Le schema Event doit venir uniquement de The Events Calendar — pas de double markup.)*
>
> **3c. IndexNow ON / Google OFF** : va dans **Rank Math → Tableau de bord → Modules**. Active
> **« Instant Indexing »**. Dans ses réglages, **IndexNow** doit être actif (Bing/Yandex).
> **Ne connecte PAS l'API Google** (ne téléverse aucune clé de service Google Indexing).
> Confirme-moi : schéma Évènements = Aucun, module Instant Indexing activé, pas d'API Google.

## 4. Polylang — langues FR / IT + hreflang
> **4a.** Va dans **Langues → Langues**. Ajoute **Français** (langue par défaut) puis **Italien**.
>
> **4b.** Va dans **Langues → Réglages → Modifications des URL** : « la langue est définie par le
> **répertoire dans le permalien** » (pour obtenir `/fr/`, `/it/`) ; **« Masquer l'information de
> langue pour la langue par défaut » = NON** (on veut `/fr/` explicite). Enregistre.
>
> **4c.** Va dans **Langues → Réglages → Types de publication et taxonomies personnalisés** :
> **coche** `tribe_events` (Évènements), `tribe_events_cat` (catégories), **`territoire`**, ainsi que
> les lieux/organisateurs si listés. Enregistre.
> Confirme-moi : 2 langues (FR défaut, IT), URL en répertoire, `/fr/` explicite, tribe_events +
> catégories + territoire cochés.

## 5. Polylang — traduire les termes en italien
> Il faut donner le libellé **italien** aux 11 catégories et aux 4 territoires (Polylang gère la
> paire FR↔IT par terme). Va dans **Évènements → Catégories** ; pour chaque catégorie FR, crée/renseigne
> sa **traduction italienne** avec le libellé ci-dessous (garde le même ordre, slugs libres côté IT) :
>
> | FR | IT |
> |---|---|
> | Expositions & Patrimoine | Mostre & Patrimonio |
> | Concerts & Musique | Concerti & Musica |
> | Spectacle vivant | Spettacolo dal vivo |
> | Festivals | Festival |
> | Gastronomie & Sagre | Gastronomia & Sagre |
> | Marchés & Foires | Mercati & Fiere |
> | Sport | Sport |
> | Cinéma | Cinema |
> | Jeune public & Famille | Per bambini & Famiglia |
> | Conférences & Rencontres | Conferenze & Incontri |
> | Fêtes & Traditions populaires | Feste & Tradizioni popolari |
>
> Puis va dans **Évènements → Territoires** et traduis les 4 territoires :
>
> | FR | IT |
> |---|---|
> | Savoie / Haute-Savoie | Savoia / Alta Savoia |
> | Piémont | Piemonte |
> | Vallée d'Aoste | Valle d'Aosta |
> | Nice / Alpes-Maritimes | Nizza / Alpi Marittime |
>
> *(Les villes-termes : on les traduira plus tard, elles ne sont pas urgentes.)*
> Fais-le méthodiquement, un terme à la fois, et dis-moi si un terme n'a pas d'option de traduction.

## 6. robots.txt
> Va dans **Rank Math → Réglages généraux → Modifier robots.txt** (Rank Math sert un robots.txt
> virtuel). Colle le contenu que je te donnerai (fichier `deploy/agenda-sabaudo/robots.txt`).
> Enregistre. Vérifie ensuite `https://agendasabauda.eu/robots.txt` : le **Sitemap** doit être
> référencé, les crawlers IA (GPTBot, PerplexityBot, Google-Extended) **autorisés**, et les vues
> techniques TEC **Disallow**. *(Demande-moi le contenu exact avant de coller.)*

## 7. Google Search Console + sitemap
> **7a.** Ouvre **search.google.com/search-console**. Ajoute une propriété **« Domaine »** =
> `agendasabauda.eu` (couvre `/fr/` et `/it/` d'un coup). La vérification demande un
> **enregistrement TXT DNS** → arrête-toi et donne-moi le TXT : je te dirai où le poser chez Gandi.
> **7b.** Une fois vérifié, **Sitemaps → ajouter** `sitemap_index.xml`.
> **7c.** Vérifie le rapport **Indexation** (pas d'erreur bloquante).

---

## Ce qui N'EST PAS dans Chrome (je m'en occupe en code)
- **Slug `luoghi`** des lieux (Venues TEC) : nécessite un petit filtre PHP → mu-plugin que je fournis.
- **Thème enfant + templates** (home, fiche, hubs…) : code Git, déployé par WP-CLI/SFTP.
- **Pont backoffice → WordPress** (`cs-rest-auth`, `cs-seo-meta` + `publisher.py`) : phase suivante,
  avec Application Password sur un compte dédié.

## Ordre conseillé
Si SSH : **`bootstrap.sh`** (fait 1-2-5-catégories/territoires) → puis Chrome pour **3, 4, 6, 7**.
Sinon : Chrome dans l'ordre **1 → 7**.
