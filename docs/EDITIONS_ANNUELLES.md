# Événements annuels : une URL, mise à jour d'édition en édition

**Décision de Franck** (08-09/09, rappelée le 15/09) : « les événements annuels, il serait
bien de les garder d'une année sur l'autre et de les mettre à jour, pour capitaliser sur
les backlinks et le SEO ». Le 09/09 il a précisé : pas besoin de mesurer combien de fiches
sont concernées, « ce sera l'ensemble des événements presque ».

État au 15/09 : **décidé, audité, pas construit** — et le 10/09 j'ai déployé quelque
chose qui va CONTRE (§3). Ce document dit ce qui existe, ce qui manque, et l'ordre.

## 1. Pourquoi ça compte

Chaque édition crée aujourd'hui une NOUVELLE fiche → un nouveau post → une nouvelle URL.
Mesuré : la foire de Vicoforte a eu quatre adresses en un an (docs/ERREURS_2026-09-10_SEO.md,
faute 12) ; les requêtes qui portent dans la Search Console sont des éditions annuelles
(« la farandole nice 2026 », docs/AUDIT_SEO_2026-09-08.md). Chaque nouvelle URL repart de
zéro : positions, liens entrants, historique — tout ce que l'édition précédente avait gagné
reste sur une page que plus personne ne met à jour.

Les sites d'événements qui se classent gardent UNE adresse par événement et la remettent
à jour : nouvelles dates, nouveau programme, même URL. C'est ce qu'on fait maintenant.

## 2. Ce qui existe, ce qui vient d'être écrit

| pièce | état | fichier |
|---|---|---|
| détecter les paires d'éditions (titre sans l'année, même lieu, 10-14 mois) | audit lecture seule, **09/09** | `scripts/appariement_editions.py` |
| **adopter** : la nouvelle fiche reprend le post de l'ancienne | **écrit le 15/09**, dry-run, fixture 13 contrôles | `scripts/adopter_edition.py`, `tests/test_adopter_edition.py` |
| colonnes `edition_precedente` / `edition_suivante` / `edition_adoptee_le` | déclarées dans `init_db` | `scripts/scraper_events.py` |
| republier = mettre à jour le post existant | **existe déjà** : `publish_batch_as --ids` met à jour dès que `wp_post_id_as` est posé | `scripts/publish_batch_as.py` |
| slug sans année pour les récurrents | consigne dans le prompt SEO | `utils/seo.py` |

L'adoption ne touche que la BASE (réversible par `--defaire`) ; c'est la republication qui
change le post. Deux gestes, dans cet ordre :

    .venv/bin/python scripts/backup_db.py
    .venv/bin/python -m scripts.adopter_edition --depuis-audit          # dry-run, LIRE
    .venv/bin/python -m scripts.adopter_edition --depuis-audit --apply
    .venv/bin/python -m scripts.publish_batch_as --ids <les nouvelles>  # imprimé par --apply

Ce que l'adoption REFUSE, et c'est plus long que ce qu'elle accepte : nouvelle déjà en
ligne (c'est un doublon → 301, pas une adoption), ancienne pas publique sur WordPress
(interrogé par l'API, règle 1), nouvelle déjà passée (règle 5), doublon fusionné, paire
hors critères d'appariement sauf `--force` pour l'œil qui a lu les deux fiches.

## 3. La CONTRADICTION avec ce qui a été déployé le 10/09

`cs-passe-noindex.php` sort de l'index toute fiche dont la date de fin est passée. Pour
un événement ponctuel, c'est juste. Pour un événement ANNUEL dont on veut garder l'URL,
c'est **onze mois de noindex** entre deux éditions — et Google désindexe ce qu'on lui dit
de désindexer. Ré-indexée l'année suivante, la page repart avec une partie de ce qu'elle
avait perdu. Le dispositif du 10/09 et la décision du 09/09 se contredisent, et je ne l'ai
pas vu en déployant.

Ce qu'il faut à la place, pour les fiches annuelles SEULEMENT :

- **rester indexée** entre deux éditions ;
- **dire clairement au lecteur** que l'édition est terminée et que la prochaine est
  attendue (« Édition 2026 terminée — prochaine édition : septembre 2027 », avec la
  date de l'édition passée conservée dans le corps) — sans ça, une page indexée qui
  annonce une date passée est exactement ce que Google appelle une page trompeuse ;
- **ne pas sortir du sitemap** non plus.

Ce qui manque pour ça, côté WordPress, et qui touche à DEUX morceaux de code EN BASE :

1. **un marqueur** que le publisher pousse : `as_edition_annuelle = 1` sur toute fiche
   qui a `edition_precedente`, ou `recurring`. Or `cs-publish.php` (snippet 6, Code
   Snippets) a une **liste blanche** `$allowed` des métas `as_*` (l.358) : un méta absent
   de la liste est jeté en silence. Il faut l'y ajouter — c'est le piège « où vit le
   code » (CLAUDE.md), à faire par la procédure du § 9 de `docs/DEPLOIEMENT_WORDPRESS.md` ;
2. **l'exemption dans `cs-passe-noindex.php`** : `if (get_post_meta($id,
   'as_edition_annuelle', true)) return false;` — trois lignes, mu-plugin, procédure § 6 ;
3. **l'affichage « édition terminée »** : un bandeau sur la fiche quand la date de fin est
   passée ET le marqueur posé. C'est du gabarit (Elementor/JetEngine ou snippet) : à
   décider avec Franck, ce n'est pas un correctif.

Ces trois pièces sont **à soumettre avant d'y toucher** : deux d'entre elles sont du PHP
en production, et la troisième est éditoriale.

## 4. Le slug : l'année dedans, ou pas

Le post adopté garde son slug — `la-farandole-nice-2026` restera l'URL de l'édition 2027.
Un slug avec l'année dedans est un défaut mineur (WordPress redirige tout seul un slug
renommé, et la requête « farandole nice 2027 » se classe sur le contenu, pas sur l'URL),
mais il vieillit. Le prompt SEO dit déjà « sans année si récurrent » pour les NOUVEAUX
slugs ; pour les posts adoptés, deux options :

- laisser (rien à faire, URL stable, année fossile) ;
- renommer une fois vers le slug sans année (WordPress pose la 301 ; l'URL change une
  seule fois, puis plus jamais).

**Arbitrage de Franck.** Je penche pour la seconde, une fois et pour toutes, parce que
l'année dans l'URL contredit l'idée même d'une adresse qui dure.

## 5. Ce qui reste à mesurer, sur le VPS

Le dry-run de l'adoption dit combien de paires sont adoptables AUJOURD'HUI. Le chiffre
que je n'ai pas : combien de fiches à venir sont l'édition N+1 d'une fiche publiée. Franck
a dit « presque toutes » ; la commande le dira, et c'est elle qui commande le reste :

    .venv/bin/python -m scripts.adopter_edition --depuis-audit

Si le nombre est petit, on adopte à la main paire par paire. S'il est grand, l'adoption
doit entrer dans la chaîne (après le dédoublonnage, avant la publication) — et là, la
question de la règle 3 se pose : **qui rouvre une paire refusée à tort ?** Réponse à écrire
avant de brancher quoi que ce soit au cron.


---

## 2026-09-21 — RÈGLE : une URL ne porte JAMAIS de date

**Décision de Franck**, en voyant l'adresse d'un événement annuel : « les url doivent-elles
comporter la date alors qu'on veut que le lien et l'événement soit mis à jour d'une année
sur l'autre ? », puis, tranché : « **ne mets jamais les dates**, mets dans la doctrine
qu'il ne faut jamais mettre les dates ».

C'est le corollaire manquant du §1 : on ne peut pas à la fois vouloir UNE adresse qui
traverse les éditions et la millésimer. Une URL qui dit `2026` condamne l'édition 2027 à
en créer une autre, qui repart de zéro.

### Ce qui produisait la date — mesuré, pas deviné

`scripts/publisher_as.py` n'envoyait **aucun slug** pour une fiche originale : seules les
traductions en avaient un, pour rester appariables à l'œil. Sans slug, WordPress dérive le
permalien du **titre** — et un titre dit « Marché au Fort 2026 : … » ou « Du 24 au 27
septembre, Terra Madre … ». Relevé le même jour par l'API WordPress : **27 des 188 fiches
en ligne et non terminées** portaient une année ou un mois dans leur adresse.

### Ce qui change, et ce qui ne change pas

| | |
|---|---|
| **l'ADRESSE** | ne porte plus jamais ni année, ni mois, ni quantième — `utils.seo.slug_sans_date`, posé par `publisher_as` **à la création seulement** |
| **le TITRE** | inchangé. Le lecteur et Yoast ont besoin du millésime ; c'est l'adresse qui doit survivre à l'édition, pas le titre |
| **les fiches DÉJÀ publiées** | gardent leur adresse : `cs-publish.php` ne fixe `post_name` qu'à la création, donc une republication ne renomme rien |
| **la consigne du prompt SEO** | « sans année si récurrent » → « **JAMAIS d'année ni de date** » (`utils/seo.py`) |

`slug_sans_date` retire les années (19xx/20xx), les noms de mois FR et IT, les quantièmes
qui TOUCHENT un mois, et les mots qui introduisaient la date (« du 24 au 27 septembre »
part en entier). Il ne touche pas à ce qui ressemble à une date sans en être une —
« 1 000 places », « 65e Fête de la Châtaigne », « les 24 heures du Mans ».

Fixture : `tests/test_slug_sans_date.py`, verte le 21/09, avec **témoin rouge** (les cinq
slugs réels relevés en ligne portent bien une date) et les cas frontière ci-dessus.

**LIMITE CONNUE** : un titre dont le mois EST le sujet perd son mot (« Mai 68 » → « 68 »).
Rare, et une adresse un peu pauvre coûte moins qu'une adresse périmée.

### Les 27 adresses déjà en ligne

Elles ne se corrigent pas toutes seules, et c'est volontaire : renommer un slug est un
geste par fiche. **Renommer le slug dans WordPress suffit — il pose la 301 tout seul**
(mesuré le 15/09 sur Vicoforte, `CLAUDE.md`). À faire en priorité sur les événements
ANNUELS, qui sont ceux dont l'adresse doit durer ; les autres peuvent attendre.
