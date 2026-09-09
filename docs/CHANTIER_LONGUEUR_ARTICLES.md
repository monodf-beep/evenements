# Chantier « longueur des articles » — le premier verrou du vert Yoast

Écrit le 2026-09-10, après que Franck a refusé une conclusion tirée de deux fiches :
« là tu fais des cas spécifiques sur 2 événements. Mais c'est sur l'ensemble des
événements qu'on a un mauvais SEO rouge Yoast. » Ce document part donc de la mesure,
pas d'un exemple.

## 1. Ce qui a été mesuré, et sur quoi

**Périmètre : les 146 fiches événement PUBLIÉES et non terminées**, les deux langues
(36 italiennes). Source : l'API REST du site, qui exclut les événements passés — c'est
exactement le périmètre de la règle 5, pour une fois sans effort.

| critère Yoast | fiches en échec | part |
|---|---|---|
| texte sous 300 mots (« texte trop court ») | **109 / 146** | 74 % |
| aucun sous-titre h2/h3 | 45 / 146 | 30 % |
| les deux à la fois | 41 / 146 | 28 % |
| ni l'un ni l'autre (seules candidates au vert) | 33 / 146 | 23 % |

Longueur : **médiane 234 mots**, min 30, max 1108 — 56 fiches sous 200 mots,
53 entre 200 et 299, 37 au-dessus de 300.

Et une quatrième mesure, celle-là **estimée** : Yoast n'expose pas le focus keyphrase en
REST, mais le `<title>` de chaque page EST le titre SEO du pipeline, qui par construction
commence par l'expression clé. Sur les **130 pages qui ont répondu** (16 n'ont pas
répondu dans le délai : NON MESURÉES, pas « bonnes ») :

> **47 fiches sur 130 — 36 % — n'ont pas même DEUX mots du début de leur titre SEO dans
> le corps.** L'expression clé y est presque certainement absente, donc « clé dans
> l'introduction », « densité » et « clé dans un sous-titre » sont rouges d'un bloc.

Sur ces 47, `scripts/recale_cles_seo.py` (gratuit, déterministe) en rattrape **2**. Les
45 autres portent une clé dont les mots ne sont pas dans le texte : elles demandent un
appel LLM. C'est écrit en toutes lettres parce que j'avais annoncé l'inverse — voir
`docs/ERREURS_2026-09-10_SEO.md`, faute 9.

## 2. Ce qui est déjà réglé, sans rien payer

Le `<h2>` posé par `publisher_as.titre_liens` coiffe les deux liens de fin de corps et
**porte l'expression clé**. Il règle les 45 fiches sans sous-titre et donne aux 146 un
sous-titre contenant la clé, à la première republication. Aucun appel LLM.

Le plancher d'`enrich` est passé à 300-380 mots (mode court : 280-320, et
`COURT_MAX_TOKENS` de 1800 à 2600 pour que la réponse ne parte pas tronquée). **Cela ne
vaut que pour les articles écrits ENSUITE** — les 109 fiches déjà en ligne gardent leur
longueur. C'est tout l'objet de ce chantier.

## 3. La file, et la commande qui la donne

Pas de nouveau script : le panier 5 de l'audit existant.

    cd /root/evenements && .venv/bin/python -m scripts.audit_substance_published

Il réutilise `utils/substance.mots_publies`, le MÊME compteur que les paniers 1 à 3 —
trois seuils (40 le refus AdSense, 250 le lecteur, 300 Yoast), un seul détecteur. Deux
détecteurs pour la même chose, un seul juste, c'est la racine des seize fautes du 08/09.

Le panier 5 écarte les traductions et le dit : `enrich` les REFUSE, parce qu'il écrit en
français et écraserait la version italienne. Pour une fiche italienne, le geste est
d'enrichir son ORIGINAL, puis `translate_events --retranslate`. L'audit imprime les deux
listes séparément, avec la commande de chacune.

## 4. L'ordre des trois commandes, et pourquoi il compte

L'audit imprime le lot des 10 plus courtes, prêt à copier :

    .venv/bin/python scripts/backup_db.py
    .venv/bin/python -m scripts.enrich <ids>
    .venv/bin/python -m scripts.seo_batch --redo --ids <ids>
    .venv/bin/python -m scripts.publish_batch_as --ids <ids>

**L'article ré-écrit change le corps, donc l'expression clé doit être choisie APRÈS lui.**
Calculer la clé avant recréerait exactement l'écart clé/texte qui rend 47 fiches rouges à
l'introduction, à la densité et au sous-titre. C'est pour ce chaînon que `seo_batch` a
reçu `--ids` le 10/09 : `--redo --cap 10` reprend la file dans SON ordre, on croit
relancer les 10 qu'on vient d'écrire et on en relance 10 autres.

**Ce qui n'est pas réversible ici** : l'article publié est REMPLACÉ, l'ancien texte n'est
pas conservé en base. D'où la sauvegarde en première ligne — c'est le seul retour arrière.

## 5. Ce qu'il faut LIRE avant d'aller plus loin que 10

Un lot de 10 ne sert à rien si personne ne regarde ce qu'il a produit. Trois contrôles,
dans cet ordre :

1. **la longueur a-t-elle bougé** — relancer l'audit : les 10 doivent avoir quitté le
   panier 5. Si elles y sont encore, le plancher du prompt n'a pas pris, inutile de
   lancer les 99 suivantes ;
2. **le texte tient-il debout** — lire deux ou trois articles en entier. Un prompt qui
   passe de 200 à 300 mots peut délayer au lieu d'ajouter de la matière : c'est
   exactement ce que la doctrine refuse, et ce que Google appelle du contenu faible.
   Si le gain de mots est du remplissage, **arrêter le chantier** et resserrer le prompt
   d'abord ;
3. **la clé est-elle dans le corps** — `scripts/recale_cles_seo.py` (dry-run) compte
   séparément les clés présentes, recalables et introuvables. Sur les 10, la ligne
   « introuvable » doit être à zéro.

Le point 2 est le seul qui demande un jugement humain, et c'est le seul qui puisse
condamner le chantier. Yoast prime sur la doctrine (arbitrage de Franck du 09/09), mais
« 300 mots » n'a jamais voulu dire « 300 mots de n'importe quoi ».

## 6. Ce que ce chantier ne règle PAS

- les 8 fiches créées à la main dans WordPress, hors de `events_raw` : aucun script du
  pipeline ne les atteint ;
- les pages `/lieu/` sans contenu propre (chantier séparé, validé) ;
- l'indexation elle-même : les deux mu-plugins `cs-index-budget.php` et
  `cs-passe-noindex.php` sont écrits et **toujours pas déposés sur WordPress**. Un article
  vert dans un site qui déclare trois fois plus de pages vides que de vraies reste un
  article vert que Google explore tard.
