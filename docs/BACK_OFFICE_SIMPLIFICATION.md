# Le back-office : inventaire, et ce qu'on en fait

Franck, 2026-08-11 au soir : « il y a trop trop trop de pages… il faut que tu fasses le
listing de tout ce qu'il y a sur le back-office et puis de simplifier. Il faut que ce soit
super simple pour moi, **parce que moi je ne vais pas l'utiliser. Normalement c'est tout
automatique.** Je veux juste que le tableau de bord soit le plus minimal possible, avec les
informations les plus importantes, afin que je sache **s'il faut que j'intervienne ou
pas**. »

Cette phrase est le cahier des charges, et elle renverse la conception d'origine. Le
back-office avait été pensé comme un poste de pilotage — quelqu'un s'y installe et
travaille. Ce n'est pas le cas : la chaîne tourne seule, et Franck vient **vérifier qu'elle
tourne**. La bonne mesure d'un tableau de bord n'est donc pas ce qu'il montre, c'est ce
qu'il permet de ne PAS regarder.

---

## 1. Ce qu'il y avait, page par page

Vingt-quatre entrées de menu, trente gabarits.

| Page | À quoi elle répond | Verdict |
|---|---|---|
| **Aujourd'hui** | dois-je intervenir ? | **Garder** — c'est LA page |
| Pilotage | santé éditoriale, couverture par territoire | garder, second rang |
| Newsletter | rédiger l'envoi hebdomadaire | garder, geste réel |
| Réseaux | publier sur Instagram | garder, geste réel |
| Cette semaine | ce qui sort dans les 7 jours | garder |
| À valider (CS) | choisir ce qui passe sur Cultura Sabauda | garder, file humaine |
| À compléter (AS) | trous à boucher avant publication | garder, file humaine |
| Triage / débloquer | fiches coincées | garder, file humaine |
| À vérifier | doutes sur les faits | garder, file humaine |
| Audit visuel | images à recadrer | garder, file humaine |
| Tous les événements | la base, filtrable | garder, outil de recherche |
| État du système | où en est la chaîne, ce qu'elle coûte | **créé le 11/08**, deux onglets |
| ~~Coûts par date~~ | comparer les dépenses | **fusionné** en onglet le soir même |
| Couverture | trous de programmation | à fusionner avec Pilotage |
| Couverture géo | trous par commune | à fusionner avec Pilotage |
| SEO | trouvailles des audits | à fusionner avec État du système |
| Régie pub | campagnes annonceurs | garder, métier à part |
| Partenariat / widget | code d'intégration | rare → Réglages |
| Wireframe home | maquette de la home | rare → Réglages |
| Voix éditoriale | le ton appliqué | rare → Réglages |
| Personas | les lecteurs visés | rare → Réglages |
| Pipeline auto | ce que font les crons | rare → Réglages |
| Fonctionnement | la doc du système | rare → Réglages |
| Réglages | les interrupteurs | garder |

**Cinq intentions, pas vingt-quatre :** intervenir · traiter · diffuser · comprendre ·
régler. Le regroupement en cinq entrées de menu avec onglets à l'intérieur reste à faire —
il touche vingt fichiers et ce n'est pas une décision technique, c'est la sienne.

---

## 2. Ce qu'il y avait SUR le tableau de bord

Douze blocs, 346 lignes, trois écrans de défilement.

| Bloc | Répond à « dois-je intervenir ? » | Décision |
|---|---|---|
| Alerte API | **oui** | garder, jamais repliable |
| Ta prochaine action | **oui** | garder, en tête |
| À traiter (les files) | **oui** | garder |
| Ton quotidien (3 liens) | non — ils sont dans le menu | **retiré** |
| Coûts API + détail par étape + par modèle | non | **une ligne et un lien** |
| Derniers lancements | rarement | **déplacé dans la cloche** |
| Le stock | non | replié |
| Statistiques | non | replié |
| Comment est calculé le score | non | replié |
| SEO | non | replié |
| Sources RSS | non | replié |
| Newsletters | non | replié |
| Piloter le pipeline à la main | quand ça casse | replié, tel quel |

**Et les six « replié » tiennent sous UNE barre, pas six.** Dix sections repliées ne valent
guère mieux que dix sections ouvertes : on scrolle encore pour trouver la bonne. Le
tableau de bord affiche désormais deux barres grises en tout, sous la partie utile.

---

## 3. Les trois règles qui ont servi à trancher

**① Un raccourci vers ce qui est déjà à un clic n'est pas un raccourci, c'est du bruit.**
« Ton quotidien » proposait Pilotage, Newsletter, Réseaux — les trois premières entrées du
menu de gauche, visibles en permanence.

**② Une information dupliquée finit par diverger.** Le détail des coûts existait sur le
tableau de bord ET sur sa propre page. Deux endroits pour le même chiffre, c'est deux
endroits à maintenir et un jour deux chiffres différents. Le tableau de bord garde le
montant, la page garde l'analyse.

**③ Ce qui alerte ne se replie pas.** Les avertissements et la prochaine action restent
toujours ouverts. Un avertissement qu'on peut ranger d'un clic finit toujours rangé — et
c'est le jour où il dit vrai qu'on le rate. C'est la même raison qui fait que la cloche ne
sonne que pour un échec de moins de 48 heures.

---

## 4. Ce qui reste à faire, et pourquoi pas ce soir

Le regroupement du menu en cinq entrées touche une vingtaine de fichiers sur un dépôt en
production, à minuit. La mécanique est posée — les onglets (`/systeme`), le repli avec
mémoire (`data-pli`) — et le découpage se décide à tête reposée, parce que ce n'est pas une
question technique : « Cette semaine » relève-t-il de traiter ou de diffuser ? « Couverture
géo » sert-il à comprendre ou à décider quoi sourcer ? C'est l'usage qui tranche, et
l'usage, c'est Franck.
