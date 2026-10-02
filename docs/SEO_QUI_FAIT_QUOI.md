# Qui écrit quoi sur une fiche — et dans quel ordre

**Arbitrage de Franck, 2026-09-21** : « si cowork a travaillé le seo, on ne doit pas
pouvoir revenir dessus avec le cron. Le processus : création de l'article en fr et it →
cron seo → cowork seo. Uniquement dans ce sens. »

Et, le même jour, le rapport de fin de session de Cowork : « la réapparition de 9378 en
rouge confirme que le risque d'écrasement par le cron reste actif et concerne
potentiellement tous les articles retravaillés aujourd'hui ».

---

## Le sens de marche

```
   scraping → évaluation → rédaction (enrich) → publication FR
                                              → traduction IT
                                                     ↓
                                         cron SEO  (seo_batch, 10h30)
                                                     ↓
                                     reprise à la main / Cowork
                                                     ↓
                                              ── et on s'arrête là ──
```

**Chaque étage peut écraser ce que le précédent a posé, jamais l'inverse.** Le dernier
mot revient à l'humain (ou à la session qui travaille pour lui), et il ne se reprend pas.

## Ce qui écrasait, exactement

Ce n'est pas une hypothèse, c'est le chemin du code. `publish_batch_as` → `publisher_as.
_build_payload()` reconstruit le **titre** et le **corps** depuis `enrich_data` de la base
SQLite (`scripts/publisher.build_post`), y ajoute les trois métas Yoast depuis les
colonnes `seo_*`, et poste le tout sur `cs/v1/event`. Côté WordPress, `cs-publish.php`
écrit `post_title` et `post_content` (l. 122-123) puis `_yoast_wpseo_title`,
`_yoast_wpseo_metadesc`, `_yoast_wpseo_focuskw` (l. 428-430).

Une republication suffisait donc à défaire une reprise à la main — et il y en a plusieurs
par jour : le lot quotidien de 9h30, la passe SEO de 10h30, une correction d'image, une
annulation, un changement de score home.

## Le mécanisme : le gel du texte

`deploy/wordpress/cs-gel-texte.php` (mu-plugin) intercepte la route `cs/v1/event` avant
et après `cs-publish.php`.

**Comment il sait qu'une fiche a été reprise** — par **empreinte**, pas par la date de
modification. À chaque passage du pipeline, il range un md5 des six champs éditoriaux
(titre, corps, extrait, les trois métas Yoast). Au passage suivant, si l'empreinte a
changé, c'est que quelqu'un d'autre a écrit : la fiche est gelée, et le journal le dit.

> **Pourquoi pas `post_modified`**, qui aurait été plus simple : trois choses le font
> bouger sans qu'aucune main n'ait touché au texte — `cs-completude.php` repasse une
> fiche incomplète en brouillon, le rouvreur `137-cs-completude-rouvreur.php` la
> republie, `cs-polylang.php` aligne le slug d'une paire FR/IT. On aurait gelé le
> catalogue entier en trois jours, sans que personne comprenne pourquoi le pipeline
> s'était arrêté.

**Ce qui ne descend plus sur une fiche gelée** : titre, corps, extrait, titre Yoast, méta
description, expression clé, slug.

**Ce qui continue de descendre, et c'est voulu** : dates, heure de début, lieu, ville,
catégorie, territoire, langue Polylang, prix, source officielle, toutes les métas `as_*`
(score home, à la une, ça vaut le déplacement, panel), l'image à la une. Le gel protège
un TEXTE, il ne met pas la fiche à la retraite — sinon ce serait un cul-de-sac au sens de
la règle 3, et une date corrigée ne serait plus jamais publiée.

**La seule exception** : une **annulation** force le titre (`forcer_texte=["title"]`,
`app/app.py`, `_appliquer_annulation`). Le préfixe « ANNULÉ — » est la seule information
qu'un lecteur doit voir coûte que coûte ; le corps retravaillé, lui, reste en place.

**Et une contre-épreuve.** L'interception réécrit le corps de la requête ; si jamais elle
ne tenait pas, le mu-plugin compare le texte APRÈS l'appel et le **remet** — le journal
porte alors une ligne `⚠️`, et `publish_batch_as` l'affiche en rouge. Un garde-fou qui
n'a qu'une jambe ne prouve rien tant qu'on ne l'a pas vu échouer.

## Qui rouvre, et où se voit le compte

Trois chemins, conformément à `docs/ETATS_TERMINAUX.md` :

1. **la case « Texte retravaillé à la main »** de l'encadré *Journal Agenda Sabauda*,
   dans l'éditeur WordPress de la fiche — décocher rend la main au pipeline ;
2. `.venv/bin/python -m scripts.gel_texte --degel <id> --apply` ;
3. `forcer_texte` dans le payload, pour un cas nommé (aujourd'hui : l'annulation, et
   elle seule).

Le compte des fiches garées se voit **à trois endroits**, jamais nulle part :

- le message Slack de `seo_batch`, tous les jours : « 🔒 N fiche(s) au texte gelé » avec
  son périmètre (en ligne, devant nous) ;
- le journal de `publish_batch_as`, lot par lot ;
- `.venv/bin/python -m scripts.gel_texte --liste`, qui interroge le SITE — c'est la seule
  source de vérité, les colonnes `wp_gel_*` de la base n'en sont qu'une copie (règle 1).

## Le journal de fiche

Chaque événement porte un journal horodaté (méta WordPress `as_journal`, 40 entrées) :

| Qui | Écrit quand |
|---|---|
| `pipeline` | à chaque passage de `cs/v1/event` — ce qui a été écrit, ou ce qui a été gelé |
| `gel` | quand une retouche est détectée, et quand la contre-épreuve a dû restaurer |
| le compte WordPress | à chaque enregistrement depuis l'éditeur |
| `cowork` | ce qu'une session déclare avoir fait (`POST cs/v1/journal`) |

Où le lire : l'encadré **Journal Agenda Sabauda** dans l'éditeur (colonne de droite,
événements, articles et pages), ou
`.venv/bin/python -m scripts.gel_texte --wp --journal 9378`.

> Le journal **commence à l'installation du mu-plugin**. Il ne reconstitue pas le passé,
> et il ne faut pas lui faire dire ce qu'il ne sait pas.

## Ce que Cowork doit faire, en plus de son travail

À la fin d'une fiche, déclarer le passage — une ligne, qui rend le reste lisible :

```
POST /wp-json/cs/v1/journal
{"post_id": 9378, "qui": "cowork", "quoi": "SEO repris : expression clé « foire de … », chapô réécrit, H2 ajouté"}
```

Le gel, lui, n'a **pas** besoin d'être demandé : modifier le texte suffit, l'empreinte
s'en charge. `"gel": true` n'est utile que pour protéger une fiche qu'on a jugée bonne
**sans y toucher**.

## Rattrapage — les fiches déjà retravaillées

Une fiche reprise **avant** l'installation du mu-plugin n'a pas d'empreinte de référence :
rien ne peut deviner qu'on y a touché, et le premier passage du cron l'écraserait. Leur
liste d'ids est la seule façon honnête de les protéger. C'est le cas du lot Cowork du
21/09 (9378 et les autres articles de la liste « à améliorer ») :

**Où trouver les ids** : dans le rapport de fin de session de Cowork (il nomme les
articles traités), ou dans wp-admin → Événements, colonne triée sur « Modifié ». Ne pas
essayer de les deviner depuis `post_modified` en base : trois mu-plugins le font bouger
sans qu'aucune main n'ait touché au texte (voir plus haut).

```bash
.venv/bin/python scripts/backup_db.py
.venv/bin/python -m scripts.gel_texte --wp --gel 9378 <autres ids> \
    --motif "SEO Cowork 21/09" --qui cowork            # dry-run : on LIT la sortie
.venv/bin/python -m scripts.gel_texte --wp --gel 9378 <autres ids> \
    --motif "SEO Cowork 21/09" --qui cowork --apply
.venv/bin/python -m scripts.gel_texte --liste          # contrôle : le site confirme
```

## Déploiement

1. **le mu-plugin** — ✅ **en ligne depuis le 21/09 à 17 h**, déposé par le canal Novamira
   (`docs/DEPLOIEMENT_WORDPRESS.md` § 3 et la section du 21/09). `deploy/push-wordpress.sh`
   ne marche PAS sur cet hébergement : SFTP, SSH et FTPS refusent les trois. Contrôle que
   la version EN LIGNE est la bonne, parce qu'un fichier poussé ne prouve rien (règle 1) :
   `curl -s https://agendasabauda.eu/wp-json/cs/v1/gel/version`
   → `{"cs_gel":"2026-09-21b — mémoire liée à LA requête (v1.1)"}`.
   **Éprouvé en production sur une fiche jetable, trois cas** (non gelée → écrasée ;
   retouchée → intacte ; annulation → titre forcé, corps conservé, date mise à jour).
   La v1.0 était fausse et c'est cet essai qui l'a dit — détail dans l'autre document.
2. **le Python** — `bash deploy/update.sh` sur le VPS. Tant que le mu-plugin n'est pas en
   ligne, la réponse de `cs/v1/event` ne porte pas de clé `gel` : la base ne marque rien
   et **ne dégèle rien non plus** (« pas de gel » et « on ne sait pas » ne rendent pas le
   même résultat). Le Python seul ne protège donc rien — c'est le site qui décide.

## Ce que ce dispositif ne fait PAS — à savoir avant de s'y fier

- **il ne fait pas remonter le texte retouché dans la base.** SQLite garde la version
  du pipeline ; le site porte la version retravaillée. Conséquence pratique : la
  prévisualisation du back-office, la file « Cette semaine » et les audits qui jugent le
  texte PUBLIÉ en le lisant en base (`audit_substance_published`,
  `audit_article_quality`…) raisonnent sur l'ancienne version pour ces fiches-là. C'est
  le prochain chantier ; en attendant, le nombre de fiches concernées est affiché tous
  les jours, il ne se découvrira pas dans six semaines ;
- **il ne protège pas les images.** Une photo posée à la main se protège autrement
  (`--skip-media`, l'éditeur de cadrage) — c'est une autre question, avec ses propres
  incidents (10/09) ;
- **il ne remplace pas le cron SEO.** Une fiche jamais reprise à la main continue d'être
  optimisée automatiquement, et c'est très bien : Cowork ne traite que le haut du panier.
