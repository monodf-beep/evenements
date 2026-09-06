---
name: redaction-agenda-sabauda
description: Rédige un texte éditorial destiné à agendasabauda.eu directement dans la conversation — un article, une "curiosité" (série d'articles évergreens sur des faits insolites d'une ville), une légende de réseau social, un texte de guide, ou tout autre contenu qui ira sur le site. À utiliser DÈS QU'ON DEMANDE D'ÉCRIRE OU DE RÉDIGER quelque chose pour Agenda Sabauda, même si la demande ne mentionne ni Obsidian, ni la charte, ni le vocabulaire, ni le ton — c'est justement le rappel que l'opérateur ne devrait plus avoir à faire lui-même. Ne s'applique PAS au pipeline automatique du dépôt (scripts/enrich.py, scripts/translate_events.py…), qui applique déjà sa propre doctrine tout seul, ni à la relecture de code.
---

# Rédiger pour Agenda Sabauda, en session

## Pourquoi ce skill existe

Le pipeline automatique de ce dépôt (`utils/voix.py`, `utils/vocabulaire.py`) lit sa
doctrine éditoriale — ton, vocabulaire interdit — EN DIRECT dans des notes Obsidian sur
le serveur de production, à chaque exécution. Une session Claude Code qui écrit un texte
directement dans la conversation n'a pas ce réflexe par défaut : elle peut écrire un
texte propre en apparence sans jamais avoir consulté cette doctrine, et Franck (l'auteur
du projet) doit alors la réexpliquer à la main, à chaque demande. C'est exactement ce
qu'il a signalé le 06/09/2026 : « c'est pénible quand je demande de la rédaction ici sur
Claude, je dois systématiquement expliquer que c'est via Obsidian, le ton, la doctrine,
le vocabulaire etc. »

Ce skill porte la PROCÉDURE et la CHECKLIST — pas une nouvelle copie de la doctrine.
Le dépôt vient justement d'éliminer les copies divergentes du vocabulaire interdit
(`config/vocabulaire_interdit.json` a été supprimé le 05/09/2026 au profit d'une lecture
directe d'Obsidian, voir `docs/VOCABULAIRE_OBSIDIAN.md`) : recopier la doctrine ici
recréerait le même problème une couche plus haut.

## Étape 1 — aller chercher la doctrine avant d'écrire un mot

Cette session (le conteneur Claude Code) n'atteint jamais le VPS de production
directement — vérifié le 05/09/2026, aucune clé SSH, aucune route réseau. Franck est le
seul canal. Ne jamais redemander « où est Obsidian » ou « comment j'y accède » : ce
point est réglé une fois pour toutes. La seule question à poser, si la conversation en
cours ne porte pas déjà ces informations (collées par Franck plus tôt dans l'échange),
est de lui demander de coller la sortie de ces deux commandes :

```
.venv/bin/python -c "from utils import voix; print(voix.load_voix())"
.venv/bin/python -c "from utils import vocabulaire as v; print(v.consigne_prompt())"
```

La première donne la voix éditoriale réelle — le ton, la structure attendue, les
marqueurs de style, tels qu'ils vivent aujourd'hui dans Obsidian (`utils/voix.py` en
explique le mécanisme). La seconde donne la liste des expressions interdites avec leur
remplacement ou leur conseil, telle qu'elle vit dans Obsidian (`utils/vocabulaire.py`,
`docs/VOCABULAIRE_OBSIDIAN.md`).

Lire aussi, toujours, `docs/CHARTE_EDITORIALE.md` — celui-là est dans le dépôt, jamais
besoin de le demander à personne. Il porte la structure d'un article, le temps des
verbes, les règles de casse, le bilinguisme FR/IT (§ 6, § 6 bis), et surtout les dark
patterns proscrits (§ 7) : urgence ou rareté factice, titre-piège façon « vous n'allez
pas croire », confirmshaming, case pré-cochée, publicité déguisée en contenu éditorial.

Si Franck a déjà collé la voix et le vocabulaire plus tôt dans la même conversation
(pour une rédaction précédente, par exemple), ne pas les redemander : les relire dans
l'historique suffit. Le but est de ne jamais faire répéter Franck, pas de créer un
rituel qui l'oblige à recoller la même chose à chaque texte.

## Étape 2 — écrire, avec trois exigences qui priment sur le style

**Les faits d'abord.** Franck : « on se base uniquement sur les infos officielles ».
Un fait dont la source n'est pas solide (musée officiel, institution publique, ministère,
document patrimonial reconnu — jamais un blog de voyage comme source, tout au plus comme
piste à vérifier ailleurs) doit être écarté du texte, pas gardé avec une réserve. Un
texte avec six faits solides vaut mieux qu'un texte à douze qui en compte deux fragiles :
le compte annoncé dans le titre doit être le compte réellement tenu, jamais un chiffre
gonflé pour faire un meilleur titre.

**La voix reçue, telle quelle.** Si la note collée par Franck décrit des règles dures
(par exemple : premier paragraphe qui répond aux cinq questions et reprend les mots du
titre ; plusieurs chapitres aux longueurs VARIÉES, jamais uniformes ; au moins un lien
externe vers une source officielle ; chaque personne nommée avec sa fonction et son
territoire ; chaque lieu situé ; aucune voix passive ; aucun `---` ; aucun encadré, aucun
emoji ; aucune liste à puces dans une prose narrative — les listes restent admises pour
des faits structurés comme des horaires ou une programmation, seulement si la note le
prévoit explicitement), ce sont des contraintes concrètes à vérifier une par une, pas des
inspirations vagues.

**Le vocabulaire reçu, aucune exception.** Aucune des expressions listées, ni leurs
variantes, quelle que soit la langue du texte.

## Étape 3 — s'auto-évaluer AVANT de livrer, par écrit, sans arrondir

Ne pas se contenter de dire « c'est conforme » : montrer la vérification. Le 06/09/2026,
un premier brouillon a dû être corrigé deux fois de suite parce que cette étape n'avait
pas été faite d'emblée — Franck a demandé « tu as utilisé le ton ? » puis « même les dark
patterns ? » avant qu'elle le soit. Le but de cette étape est qu'il n'ait plus jamais à
poser ces deux questions : la réponse doit déjà être dans la première livraison.

1. **Vérification mécanique du vocabulaire**, pas une relecture à l'œil : faire tourner
   `utils.vocabulaire.trouver(texte)` sur le texte réellement écrit (le lancer en Python,
   avec `OBSIDIAN_VOCAB_PATH` pointé vers un fichier temporaire reconstitué à partir de ce
   que Franck a collé, si la session n'a pas d'accès direct à la vraie note). Rapporter le
   résultat exact : « aucune occurrence » ou la liste trouvée.
2. **Vérifications mécaniques simples** : présence d'un tiret cadratin (—), présence
   littérale de `---`, nombre de mots par chapitre (pour juger si les longueurs sont
   vraiment variées, pas seulement toutes sous la limite).
3. **Les marqueurs de style de la voix**, un par un, si la note en liste — dire
   concrètement lesquels sont présents, avec une courte citation du texte à l'appui, et
   lesquels sont absents. Ne pas arrondir dans le sens qui arrange : un marqueur absent
   se dit comme absent.
4. **Les dark patterns de `docs/CHARTE_EDITORIALE.md` § 7**, un par un : urgence ou
   rareté factice, titre-piège, confirmshaming, case pré-cochée ou opt-in déguisé,
   publicité déguisée en contenu éditorial, collecte de données. Dire pour chacun s'il
   est présent ou absent. Si un point relève d'un jugement plutôt que d'un fait vérifiable
   (un titre « catchy » qui joue sur la curiosité, par exemple), le présenter comme un
   jugement à trancher, jamais comme un fait acquis.

## Étape 4 — livrer un brouillon, jamais publier seul

Présenter le texte dans la conversation, avec l'auto-évaluation de l'étape 3 juste avant
ou juste après. Ne jamais publier automatiquement sur WordPress un texte d'un genre pas
encore rodé dans le pipeline (une nouvelle série d'articles, par exemple — voir
`docs/CURIOSITES.md`). Attendre la relecture de Franck avant toute mise en ligne, comme
pour les guides déjà publiés du site.
