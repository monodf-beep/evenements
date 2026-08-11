# Connecter Claude Code à WordPress via MCP

> **Ce document ne décrit pas le montage réellement utilisé.** Il porte sur le proxy
> d'Automattic envisagé pour culturasabauda.eu, qui n'a pas été mis en service.
> Le pilotage d'agendasabauda.eu passe par le connecteur **Novamira** : voir
> [`MCP_NOVAMIRA.md`](MCP_NOVAMIRA.md), qui documente son usage, ses limites et
> les règles à respecter pour ne pas mettre la production hors ligne.

Objectif : permettre à **Claude Code** (dans les prochaines sessions) de lire/créer/
vérifier les articles WordPress **directement**, en plus de la publication automatique
du back-office (`scripts/publisher.py`, qui, lui, marche déjà via l'API REST).

Le fichier **`.mcp.json`** (racine du dépôt) déclare le serveur MCP WordPress officiel
(`@automattic/mcp-wordpress-remote`). Il **ne contient aucun secret** : les identifiants
sont lus depuis des variables d'environnement (`${WP_MCP_USER}`, `${WP_MCP_APP_PASSWORD}`).

## Ce qu'il reste à faire (3 étapes — côté toi)

### 1. Installer le plugin « WordPress MCP » sur le site
Le proxy `mcp-wordpress-remote` a besoin que le site expose l'endpoint MCP.
- WordPress → Extensions → Ajouter → chercher **« WordPress MCP »** (Automattic) /
  **MCP Adapter** → Installer → Activer.
- Réf. : https://github.com/WordPress/mcp-adapter
- (Sans ce plugin, seule la publication via l'API REST du back-office fonctionne — ce qui
  suffit déjà pour publier ; le MCP n'est qu'un confort de pilotage.)

### 2. Fournir les identifiants comme variables d'environnement
Dans les **réglages de l'environnement Claude Code** (pas dans le dépôt, jamais commité) :
- `WP_MCP_USER` = ton identifiant de connexion WordPress
- `WP_MCP_APP_PASSWORD` = un **mot de passe d'application** WordPress (Utilisateurs →
  Profil → Mots de passe d'application). Tu peux réutiliser celui du back-office ou en
  créer un dédié « Claude Code MCP ».

### 3. Vérifier la politique réseau de l'environnement
L'environnement Claude Code doit pouvoir **joindre `culturasabauda.eu`** en sortie
(le serveur MCP tourne dans l'environnement et appelle ton site). Si la politique réseau
est restrictive, l'autoriser pour ce domaine.

## Bon à savoir / limites
- **Activation à la prochaine session** : les serveurs MCP sont chargés au démarrage.
  Après avoir fait les 3 étapes, ouvre une **nouvelle session** Claude Code.
- **Vérifie les noms exacts** des variables (`WP_API_URL` / `WP_API_USERNAME` /
  `WP_API_PASSWORD`) contre le README du proxy si une version change la convention :
  https://github.com/Automattic/mcp-wordpress-remote
- **Sécurité** : le mot de passe d'application donne un accès en écriture au site — à
  traiter comme un secret. Il est révocable à tout moment depuis ton profil WordPress.
- Ceci est **indépendant** de la publication du back-office : même sans MCP, le bouton
  « ✅ WordPress » publie déjà (une fois `WP_URL`/`WP_USER`/`WP_APP_PASSWORD` dans le `.env`).
