# Conventions du dépôt

Deux sites, deux modes d'accès. **agendasabauda.eu** se pilote depuis WordPress via le connecteur
MCP Novamira. Le **pipeline** qui l'alimente vit sur le VPS et se déploie depuis ce dépôt.
Une correction faite dans WordPress est **réécrite à la republication suivante** tant que le
défaut n'est pas corrigé en amont : toujours se demander de quel côté est la vraie cause.

## Avant d'écrire quoi que ce soit qu'un lecteur ou un moteur verra

Relire les quatre fichiers de doctrine du vault Obsidian (`~/projects/obsidian-vault`) :
`01-Commun/Lexique sabaud.md`, `01-Commun/Vocabulaire interdit.md`,
`01-Commun/Non-négociables.md`, `04-Studio/Humanizer.md`. **Les quatre, pas celui dont le titre
colle au sujet.**

Le test n'est pas « est-ce que je rédige ? » mais **« est-ce qu'un lecteur ou un moteur verra le
résultat ? »**. Remplir une méta, choisir une URL de source, écrire un slug, un titre SEO, une
balise alt ou un libellé d'interface en fait partie.

Trois règles s'oublient particulièrement souvent :

- **Jamais de tiret cadratin ni demi-cadratin**, nulle part, ni dans les contenus ni dans les
  réponses.
- **Le gentilé du territoire, jamais la nationalité.** Et les termes proscrits valent à
  l'identique en italien : la règle porte sur le concept, pas sur le mot.
- **Une source ne désigne qu'un organisme public ou l'organisateur réel.** Jamais un agrégateur,
  un guide, un magazine privé, un domaine nu ou un email. Vérifier l'éditeur sur la page avant
  d'écrire l'URL. Mieux vaut aucune source qu'une source douteuse.

## Toucher à agendasabauda.eu

Lire **`docs/MCP_NOVAMIRA.md`** avant le premier appel. Il contient le plafond de transport, la
sémantique des messages d'erreur, et le moyen de distinguer une panne du site d'une panne du
connecteur.

Trois règles non négociables, chacune payée cher :

1. **Aucun PHP non validé sur la production.** Générer en simples quotes uniquement, valider hors
   production, et préférer un snippet Code Snippets à un mu-plugin : un snippet se désactive
   depuis l'admin, un mu-plugin emporte l'admin avec lui. Voir
   `docs/POSTMORTEM_2026-08-11_MU_PLUGIN.md`.
2. **Lire `data.errors[]` du retour**, pas seulement `return_value`. C'est là qu'était
   l'avertissement qui annonçait la panne du 11 août.
3. **Sauvegarder avant de modifier**, dans une option `cs_bk_<sujet>_<date>` écrite dans le même
   appel que la modification.

Et deux pièges de mesure : **`WP_Query` masque les événements passés** sur `tribe_events`, donc
tout audit passe par du SQL direct ; et une capture d'écran de navigateur peut être un cache
périmé, alors que le HTML téléchargé par `curl` ne ment pas.

## Déployer le pipeline

`deploy/update.sh` fait tout : récupération, remise à niveau, dépendances, redémarrage. Ne pas
dicter de `git pull` à la main.

## Vérifier son propre outillage

Plusieurs faux diagnostics dans ce projet venaient d'outils de mesure, pas des données : un
détecteur de langue comptant « la » comme français alors que le mot existe en italien, une
requête cherchant une clé au pluriel quand le champ est au singulier, une extraction du JSON-LD
ignorant l'attribut de classe ajouté par Yoast. Le résultat était à chaque fois plausible et
faux. **Compter, corriger, recompter**, et douter de l'instrument avant de douter des données.

Avec l'outil Workflow, `args` doit être un **vrai tableau JSON**, jamais une chaîne, et le
fan-out doit être borné par un garde-fou dur. Une chaîne passée en argument a produit 768 agents
et 15,5 millions de tokens pour zéro résultat.

## Où trouver quoi

| Sujet | Fichier |
|---|---|
| Connecteur MCP d'agendasabauda | `docs/MCP_NOVAMIRA.md` |
| Panne du 11/08 et inventaire des erreurs | `docs/POSTMORTEM_2026-08-11_MU_PLUGIN.md` |
| État courant, journaux de session, dette | `docs/BACKLOG.md` |
| Doctrine éditoriale appliquée | `docs/CHARTE_EDITORIALE.md` et le vault Obsidian |
| Contrat des métas d'événement | `docs/CONTRAT_META_AS.md` |
| Taxonomie | `docs/CONTRAT_TAXONOMIE_AGENDA_SABAUDA.md` |
