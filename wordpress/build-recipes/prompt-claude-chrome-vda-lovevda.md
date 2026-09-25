# Prompt Claude dans Chrome — la gastronomie valdôtaine sur lovevda.it

*Créé le 2026-09-06 pour le rayon 2 du hub `/ou-manger/`, après le rayon Turin.*

## Ce qui a été vérifié depuis la session, et ce qui bloque

`lovevda.it` est le site institutionnel de la Région autonome Vallée d'Aoste. Trois
constats du 06/09 :

| Constat | Conséquence |
|---|---|
| Le site sert ses pages **en français nativement** | la version FR de l'article ne sera pas une traduction, c'est la langue source |
| Les pages sont **compressées** : sans `--compressed`, `curl` rend du binaire | piège à connaître, il m'a coûté un aller-retour |
| Les **vignettes de résultats sont rendues en JavaScript** | même détour Chrome que pour Mangébin |
| La page agritourisme **annonce son total, « 30 Résultats »** | c'est ce qui rendra un relevé tronqué détectable |

Chemins trouvés dans `robots.txt`, pas devinés :
`/fr/gastronomie/ou-manger/{agritourisme,refuges,restaurants,restaurants-pizzerias}`,
`/fr/gastronomie/produits/…`, `/fr/gastronomie/evenements/…`.

**La leçon de Turin, à ne pas reperdre** : ma première extraction donnait 10 établissements
là où il y en avait 28, parce qu'un bouton « Télécharger plus » ne peut pas être cliqué par
un téléchargement de page. Le prompt ci-dessous exige donc le TOTAL, et sa comparaison avec
le chiffre que la page affiche elle-même.

---

## À coller dans Claude, dans Chrome

> Ouvre ces deux pages, l'une après l'autre, et attends que la liste des résultats soit
> complètement chargée (elle arrive en JavaScript, quelques secondes après le reste) :
>
> 1. **https://www.lovevda.it/fr/gastronomie/ou-manger/agritourisme**
> 2. **https://www.lovevda.it/fr/gastronomie/ou-manger/refuges**
>
> Pour chaque page, relève **tous** les établissements. Une ligne par établissement, dans
> cet ordre :
>
> `Nom | commune | adresse si affichée | altitude si affichée | l'URL de sa fiche`
>
> Consignes :
> - **La commune est le champ le plus important pour moi**, plus encore que l'adresse.
>   Si elle n'est pas affichée telle quelle mais lisible dans l'adresse, prends-la dans
>   l'adresse et signale-le.
> - **N'invente rien.** Champ non affiché, écris `—`. Un champ vide est une information ;
>   une adresse devinée est une faute.
> - **Ne complète pas depuis tes connaissances** ni depuis une autre source : je veux
>   exactement ce que cette page affiche aujourd'hui.
> - S'il y a une **pagination** ou un bouton « voir plus / charger plus », clique jusqu'au
>   bout.
> - Dis-moi **combien** tu as relevé sur chaque page, ET le chiffre que la page annonce
>   elle-même (elle affiche « N Résultats » en haut). **Si les deux ne coïncident pas,
>   signale l'écart au lieu de le lisser.** Pour la page agritourisme, le chiffre annoncé
>   était 30 le 6 septembre 2026.
> - Si une page ne charge pas, ou si la liste reste vide, **dis-le** plutôt que de me
>   donner une liste plausible.
>
> Ensuite, deux questions courtes, en cherchant sur le site :
>
> **a)** Est-ce qu'un label régional de restauration existe, du type « Saveurs du Val
> d'Aoste » ou « Saveurs de la Vallée d'Aoste » ? Si oui, donne-moi l'URL de la page qui
> le décrit et, s'ils sont publiés, ses **critères d'adhésion**. Si tu ne trouves pas de
> page officielle qui le décrive, dis-le : « pas trouvé » est une réponse utile, une page
> inventée ne l'est pas.
>
> **b)** Sur **https://www.lovevda.it/fr/gastronomie/evenements**, relève la liste des
> fêtes gastronomiques avec, pour chacune, son nom, sa commune et ses dates si affichées.

---

## Ce qu'on en fera

**L'article**, rayon 2 du hub : quatre chapitres, sélection de six à huit adresses sur le
critère déjà éprouvé à Turin, c'est-à-dire les communes où l'agenda porte déjà un
événement. Pas de liste exhaustive : arbitrage de Franck du 06/09, la liste complète reste
chez la source, qui la tient à jour.

**Le point (a)** décide de l'angle. Si un label existe avec des critères publiés, l'article
se construit comme celui de Turin, sur ce que le label garantit et ce qu'il ne garantit
pas. S'il n'existe pas, l'angle bascule sur ce que la Vallée d'Aoste a de propre et que ni
Turin ni Nice n'ont : les **refuges** et les **agritourismes**, où l'on mange à l'endroit
où l'on produit.

**Le point (b) ne sert pas l'article, il sert le pipeline.** Marché au Fort, Fête du lard
d'Arnad, Fête du jambon cru de Bosses, Fête du miel à Châtillon, Fête des pommes d'Antey
et de Gressan : ce sont des ÉVÉNEMENTS, donc de la matière pour l'agenda lui-même, pas
pour un article. `lovevda.it/fr/gastronomie/evenements` est une source à instruire.

---

## Politesse envers la source

`robots.txt` de lovevda.it demande un `Crawl-delay: 10`. Toute reprise automatisée devra le
respecter. Les seuls chemins interdits sont les variantes paramétrées `?url=`, pas les
pages elles-mêmes.
