# MCP Novamira : exécuter du PHP sur la production d'agendasabauda.eu

Écrit le 2026-08-11, après une session qui a mis le site hors ligne vingt minutes. Ce document
existe pour que la panne ne se reproduise pas et pour éviter de redécouvrir les mêmes limites.

Ne pas confondre avec `MCP_WORDPRESS.md`, qui décrit un autre montage (le proxy d'Automattic
sur culturasabauda.eu) et qui n'est pas ce qui est utilisé ici.

## Ce que c'est

Un connecteur MCP qui exécute **du PHP arbitraire dans le contexte WordPress d'agendasabauda.eu,
en production directe**. Il n'y a pas de préproduction. Chaque appel s'exécute sur le site que
voient les lecteurs.

Appel type :

```
ability_name : novamira/execute-php
parameters   : { "code": "return current_time('mysql');" }
```

La valeur de `return` revient dans `data.return_value`. Les avertissements PHP arrivent
séparément dans `data.errors[]`, et `data.execution_time_ms` est parfois aberrant : ne pas s'en
servir pour mesurer quoi que ce soit.

Abilités connues et utilisées : `novamira/execute-php`, `novamira/read-file`,
`novamira/create-upload-link`. `mcp-adapter-discover-abilities` donne la liste complète.

---

## Les cinq règles apprises à la dure

### 1. Ne jamais écrire du PHP non validé dans `mu-plugins/`

**C'est la règle qui a coûté vingt minutes de panne.** Le 2026-08-11, un mu-plugin généré par
concaténation contenait une ligne en doubles quotes avec `$hote` dedans. PHP a interpolé la
variable à la génération, et le fichier écrit contenait `if ( === '')`.

Les mu-plugins se chargent avant tout le reste : chaque requête a fatalé. Le site, l'admin,
l'API REST et **le connecteur Novamira lui-même** sont tombés ensemble. Plus aucun moyen de se
corriger : il a fallu un accès SFTP humain pour renommer le fichier.

Conséquences pratiques :

- **Générer le PHP en simples quotes uniquement.** Jamais de doubles quotes contenant un `$`.
- **Valider avant de déposer** : écrire dans `sys_get_temp_dir()`, tenter un `include` sous
  `try { } catch (ParseError $e) { }`, ne déplacer qu'en cas de succès. `php -l` n'existe pas en
  CLI sur cet hébergement (`sh: php: command not found`).
- **Préférer un snippet Code Snippets à un mu-plugin** pour tout nouveau garde-fou. Un snippet
  se désactive depuis l'admin ; un mu-plugin emporte l'admin avec lui.
- Se demander avant d'écrire : **si ce fichier est fautif, par où puis-je le retirer ?** Si la
  réponse est « par le site que je suis en train de modifier », la prudence doit monter d'un cran.

### 2. Lire les avertissements du retour

Au moment exact où le mu-plugin fautif a été écrit, l'outil a renvoyé dans `errors[]` :

```
Warning: Undefined variable $hote
```

L'outil avait signalé le bug. Je ne l'ai pas lu, j'ai regardé `return_value` qui disait
« ecrit : ... (1922 octets) » et je suis passé à la suite. **`data.errors[]` fait partie du
résultat, pas du décor.**

### 3. Le transport plafonne autour d'un kilooctet

Les appels `execute-php` portant plus de ~1 Ko de charge utile échouent de façon répétée, quel
que soit l'encodage, base64 comme hexadécimal. Les petits appels passent. Des `curl` directs
vers le site montrent aussi des connexions perdues par intermittence : le lien réseau est en
cause, pas WordPress.

**Contournement qui marche** pour transporter du volume : `novamira/create-upload-link`, puis un
`curl -X PUT` du fichier, puis un petit appel PHP qui lit le fichier déposé.

### 4. Les paramètres sont du JSON, avec ce que ça implique

Un chemin Windows non échappé, un caractère de contrôle ou une chaîne tronquée produisent une
`InputValidationError` avant même d'atteindre le site. Utiliser des barres obliques, doubler les
antislashs, et se méfier des heredocs PHP dans le champ `code`.

`novamira/read-file` renvoie parfois le contenu **en base64** : vérifier le champ `encoding`
avant d'interpréter le résultat, sinon on conclut à tort qu'un fichier est vide.

### 5. Distinguer « le site est mort » de « le connecteur est mort »

Les trois messages d'erreur n'ont pas le même sens :

| Message | Interprétation |
|---|---|
| `The connector's server isn't responding` | le site ou le connecteur est injoignable |
| `The connector's server returned an error` | le connecteur répond, l'appel échoue |
| `Connection closed` | coupure en cours d'appel, souvent charge utile trop grosse |

Le test qui tranche, en une commande et sans le MCP :

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://agendasabauda.eu/wp-json/
curl -s -o /dev/null -w "%{http_code}\n" https://agendasabauda.eu/wp-json/novamira/v1
```

Si les deux répondent 200, WordPress et le plugin vont bien : la panne est dans le connecteur, il
n'y a **rien à réparer sur l'hébergement**, il faut relancer la connexion côté Claude.

Autres diagnostics utiles sans MCP : `curl` de la page et lecture de l'en-tête `Date` pour
connaître l'heure du serveur, et téléchargement du HTML pour vérifier ce qui est réellement servi.
Une capture d'écran d'un navigateur peut être un cache périmé ; le HTML téléchargé, non.

---

## Méthode de travail

**Avant toute écriture visible d'un lecteur ou d'un moteur**, relire les quatre fichiers de
doctrine du vault Obsidian. Le test n'est pas « est-ce que je rédige ? » mais « est-ce qu'un
lecteur ou un moteur verra le résultat ? ». Remplir une méta, choisir une URL de source, écrire
un slug ou un titre SEO en fait partie.

**Sauvegarder avant de modifier.** Convention en place : une option WordPress
`cs_bk_<sujet>_<date>` contenant l'état antérieur, écrite dans le même appel que la modification.
Exemples existants : `cs_bk_sources_20260809`, `cs_bk_6352_avant_20260809`,
`cs_bk_titres_flux_20260809`.

**Compter, corriger, recompter.** Ne jamais annoncer un résultat sans l'avoir revérifié par une
seconde requête, et de préférence sur le HTML servi plutôt que sur la base.

**`WP_Query` masque les événements passés** sur `tribe_events`. Tout audit de contenu doit passer
par du SQL direct, sinon il rate silencieusement une partie du corpus.

**Vérifier l'instrument avant de croire la mesure.** Trois faux diagnostics dans une seule
session venaient de mes propres outils : un détecteur de langue qui comptait « la » comme
français alors que le mot existe en italien, une requête qui cherchait une clé `bloquants` alors
que le champ s'appelle `bloquant`, et une extraction du JSON-LD qui cherchait
`<script type="application/ld+json">` exactement, sans tenir compte de l'attribut de classe que
Yoast ajoute. Chaque fois, le résultat était plausible et faux.

---

## Ce que le connecteur ne protège pas

Il exécute ce qu'on lui donne, sans garde-fou, sur la production. Il n'y a ni validation
syntaxique, ni sauvegarde automatique, ni retour arrière. La totalité de la prudence est du côté
de l'appelant. C'est un outil de chirurgie, pas un environnement de développement.
