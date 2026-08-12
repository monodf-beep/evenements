# Quels articles écrire — audit par intention de recherche, 4 territoires

*13 août 2026. Complète `INTENTIONS_RECHERCHE_SEO.md` (qui traite les **pages hub**) et
`CATALOGUE_GEO_SEO.md` (qui liste les **entités géographiques**). Ni l'un ni l'autre ne dit
rien des **articles** : c'est le trou que ce document remplit.*

---

## La limite à connaître avant de lire le reste

**Je n'ai aucune donnée de volume de recherche.** Ni Search Console, ni Keyword Planner, ni
Ahrefs, ni DataForSEO. Aucun chiffre de ce document ne dit « tant de recherches par mois », et
je n'en invente pas.

Ce que je classe, je le classe donc sur trois critères **mesurés ou écrits**, pas devinés :

1. **la matière** — combien de fiches de l'Agenda alimentent réellement le sujet (compté) ;
2. **les gabarits d'intention** que `CATALOGUE_GEO_SEO.md` a déjà établis à partir de la
   structure réelle des SERP (écrit, et je ne le refais pas) ;
3. **l'équilibre entre les quatre territoires** et la saisonnalité (compté).

`INTENTIONS_RECHERCHE_SEO.md` §7 dit déjà ce qu'il manque : « un passage Google Keyword Planner
/ Ahrefs France affinera l'ordre exact ». C'est toujours vrai, et ça reste le seul moyen de
transformer cet ordre-ci en ordre définitif.

---

## 1. Ce qui existe : six articles, et ils sont bons

Le sitemap `post` contient 12 URL, soit **six articles déclinés en FR et IT** :

| Article | Territoire | Mots FR / IT |
|---|---|---|
| `concerts-nice-2026` | Comté de Nice | 1018 / 994 |
| `cuisine-nissarde-tables-labellisees` | Comté de Nice | 1525 / 1501 |
| `expositions-turin-2026` | Piémont | 923 / 921 |
| `sagre-piemont-2026` | Piémont | 1001 / 1005 |
| `fetes-vallee-aoste` | Vallée d'Aoste | 1068 / 1048 |
| `festivals-savoie-2026` | Savoie | 974 / 962 |

Le gabarit est solide et il faut le dire : **921 à 1525 mots**, schéma `Article` sur les 12,
`hreflang` FR/IT réciproque sur les 12, meta descriptions de 122 à 171 caractères, titres de 44
à 85. Rien à voir avec les pages « lieu » ou « organisateur » de l'audit d'hier.

**Le déséquilibre, lui, est net.** La Savoie et la Haute-Savoie — que
`INTENTIONS_RECHERCHE_SEO.md` désigne comme le **cœur à consolider en premier**, le
transfrontalier étant « phase 2 » — n'ont **qu'un seul article**, quand le Comté de Nice en a
deux. La phase 2 a démarré avant la phase 1.

---

## 2. Deux défauts de gabarit à corriger AVANT d'écrire le septième

Même logique qu'hier : un correctif de gabarit vaut pour tous les articles à venir, un
correctif d'article ne vaut que pour lui.

### 2.1 L'année est dans l'URL de quatre articles sur six

```
/concerts-nice-2026/        /expositions-turin-2026/
/festivals-savoie-2026/     /sagre-piemont-2026/
```

`CATALOGUE_GEO_SEO.md` écrit noir sur blanc : « **Règle URL : jamais l'année dans l'URL**
(`/annecy/ce-week-end/`, pas `/2026/`) → la page cumule son autorité. » Ces quatre-là violent une
règle que le dépôt a lui-même posée.

Conséquence concrète : en janvier 2027, soit l'article reste avec un titre périmé, soit il faut
créer `/concerts-nice-2027/` — une URL neuve, sans backlink, sans historique, qui repart de zéro
pendant que l'ancienne agonise. **Quatre fois par an, indéfiniment.**

Les deux articles qui ne portent pas d'année — `cuisine-nissarde-tables-labellisees` et
`fetes-vallee-aoste` — sont les seuls construits pour durer. Ce sont les bons.

- **Correctif** : slug sans millésime (`/concerts-a-nice/`), millésime dans le `<title>` et le
  `<h1>` seulement, mis à jour chaque année sur la même URL. Avec une **redirection 301** de
  l'ancienne vers la nouvelle — quatre redirections, pas une de plus, et `site_health_check` les
  verra si l'une casse.
- **Comment savoir si c'est fait** : les quatre anciennes URL répondent 301 vers les nouvelles,
  et le sitemap ne liste plus que les nouvelles.

### 2.2 Aucun article ne porte de schéma `ItemList` (0 sur 12)

Ces articles sont des listes — « les festivals de Savoie », « les sagre du Piémont ». `ItemList`
est le balisage fait pour ça : il décrit chaque entrée, son rang, son lien. C'est aussi ce qu'un
modèle de langage lit le plus volontiers quand il cite une liste.

Les 12 ont bien `Article` ; il leur manque la structure de ce qu'ils contiennent. Un seul
correctif de gabarit, valable pour tous les articles futurs.

---

## 3. La matière réellement disponible

Compté sur les fiches datées de l'Agenda, croisées avec leurs taxonomies via l'API REST.

**Périmètre de ce tableau, et il compte** : 92 fiches sur les 129 datées ont pu être appariées à
leur enregistrement REST (71 %). Les chiffres sont donc un **plancher**, pas un inventaire
complet. Et contrairement à l'audit d'hier, **le passé est inclus ici, volontairement** : un
article « les festivals du Piémont en 2026 » se nourrit légitimement des éditions déjà passées de
l'année — la règle 5 borne les files de travail, pas la matière éditoriale.

| Catégorie | Savoie | Piémont | V. d'Aoste | Comté de Nice | Total |
|---|---:|---:|---:|---:|---:|
| Expositions & Patrimoine | 5 | **8** | 1 | 5 | 19 |
| Concerts & Musique | **6** | 4 | 3 | 3 | 16 |
| Festivals | 1 | **7** | 0 | 2 | 10 |
| Sport | 1 | 4 | 3 | 1 | 9 |
| Conférences & Rencontres | 1 | 2 | 4 | 1 | 8 |
| Spectacle vivant | 2 | 1 | 2 | 3 | 8 |
| Gastronomie & Sagre | 0 | 5 | 1 | 0 | 6 |
| Fêtes & Traditions | 0 | 1 | 2 | 3 | 6 |
| Jeune public & Famille | 1 | 1 | 2 | 0 | 4 |
| Marchés & Foires | 2 | 1 | 0 | 0 | 3 |
| Cinéma | 1 | 2 | 0 | 0 | 3 |
| **Total fiches datées** | **20** | **36** | **18** | **18** | 92 |

Deux constats qui orientent tout le reste :

**`festivals-savoie-2026` existe et repose sur UNE fiche.** L'article a donc été écrit sans
l'inventaire du site derrière lui — ce n'est pas illégitime, mais il ne peut pas faire ce qu'un
article de ce type fait de mieux : mailler vers ses propres fiches et prouver que l'Agenda est la
source la mieux informée.

**`Festivals × Piémont` a sept fiches et aucun article.** C'est l'écart le plus criant du
tableau : la matière est là, l'article n'existe pas.

---

## 4. Les articles à écrire, dans l'ordre

Les gabarits de titre viennent de `INTENTIONS_RECHERCHE_SEO.md` §4 — je ne réinvente pas de
patron. Chaque ligne indique la matière mesurée, pour que tu voies sur quoi elle s'appuie.

### Vague 1 — la matière existe déjà, il n'y a qu'à écrire

| # | Article (FR + IT) | Matière | Pourquoi celui-là |
|---|---|---|---|
| 1 | **Les festivals du Piémont** | 7 fiches | Plus gros écart matière/absence du tableau. Le Piémont est le territoire le mieux fourni (36 fiches) |
| 2 | **Les concerts en Savoie et Haute-Savoie** | 6 fiches | Nice a son article concerts, la Savoie non — alors qu'elle a *plus* de matière, et qu'elle est le cœur du plan |
| 3 | **Les expositions en Savoie et Haute-Savoie** | 5 fiches | Rééquilibre le territoire prioritaire ; deuxième catégorie la mieux fournie du site |
| 4 | **Les expositions dans le Comté de Nice** | 5 fiches | Complète Nice, dont l'article existant ne couvre que les concerts |

### Vague 2 — saisonnier, à écrire maintenant pour être en place à temps

Un article a besoin de plusieurs semaines pour être indexé et remonter. Écrire un article de Noël
en décembre, c'est le publier après la bataille.

| # | Article | Fenêtre d'écriture | Remarque |
|---|---|---|---|
| 5 | **Les marchés de Noël en Vallée d'Aoste et au Piémont** | **septembre** | ⚠️ voir §5 : la base ne contient que 5 fiches en décembre |
| 6 | **La Foire de Saint-Ours d'Aoste** (30-31 janvier) | octobre | Evergreen, URL sans année. C'est LE rendez-vous valdôtain, et le catalogue le classe P1 |
| 7 | **Le Carnaval d'Ivrea** | novembre | Classé P1 dans `CATALOGUE_GEO_SEO.md` (« Ivrea (P2, Carnevale) »), aucune page |

### Vague 3 — transversal, evergreen, aucun équivalent aujourd'hui

`CATALOGUE_GEO_SEO.md` liste `gratuit` et `en famille / avec enfants` parmi les modificateurs
thématiques, et **aucun article ne les traite**. Ce sont des intentions durables, non
saisonnières, où l'Agenda a la donnée que les guides touristiques n'ont pas.

| # | Article | Matière |
|---|---|---|
| 8 | **Sorties gratuites dans les quatre territoires** | à extraire du champ tarif, non mesuré ici |
| 9 | **Sorties en famille** | 4 fiches en catégorie Jeune public — faible, à consolider d'abord |

Le 9 est signalé pour mémoire : **je ne le recommande pas encore**, la matière ne suit pas.

---

## 5. Le constat qui dépasse la question des articles

Répartition des 129 fiches datées, par mois de début :

```
2026-06  ███████████████ 15
2026-07  ██████████████████████████ 26
2026-08  █████████████████████████████████ 33
2026-09  █████████████████████ 21
2026-10  █████████████ 13
2026-11  ████ 4
2026-12  █████ 5
2027-01  ██ 2
```

**Après octobre, la matière s'effondre.** Or novembre à février, c'est la saison des marchés de
Noël, de la Foire de Saint-Ours, du Carnaval d'Ivrea, de la Fête du Citron de Menton — les
rendez-vous les plus recherchés du calendrier alpin, et ceux sur lesquels un agenda local a le
plus à dire.

**Deux lectures possibles, et je ne peux pas trancher d'ici :**

- soit c'est un **délai d'annonce** — les organisateurs publient leurs programmes d'hiver en
  septembre-octobre, et le creux se remplira tout seul ;
- soit c'est un **trou de sourcing** — les sources scrapées couvrent mal l'hiver.

Ça se départage en comparant avec la même période l'an dernier, donnée que je n'ai pas. **Mais
l'ordre des travaux en dépend** : si c'est un trou de sourcing, l'article n°5 (marchés de Noël)
serait écrit sans rien derrière lui, et il vaudrait mieux ouvrir les sources d'abord.

C'est la question à trancher avant d'attaquer la vague 2.

---

## 6. Ce que je n'ai pas fait

- **Aucun volume de recherche.** L'ordre proposé est un ordre par matière et par équilibre
  territorial, pas par demande mesurée. Un passage Keyword Planner France sur les gabarits du §4
  le corrigerait — et pourrait le bousculer.
- **Aucune mesure de performance des six articles existants.** Sans Search Console, je ne sais
  pas s'ils reçoivent des visites. Si l'un d'eux ne prend pas, écrire quatre articles de plus sur
  le même modèle serait répéter une erreur au lieu de la corriger. **C'est la vérification à
  faire en premier, avant même la vague 1.**
- **Le champ tarif n'a pas été inventorié** — l'article n°8 suppose qu'on sait quelles fiches
  sont gratuites, ce que je n'ai pas vérifié.
- **La matrice repose sur 92 fiches sur 129** (71 %). Les chiffres sont des planchers.
