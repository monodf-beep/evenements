# Accueil : ce qu'on prend à Guidatorino, et ce qu'on ne prend pas

Écrit le 02/10/2026, à la demande de Franck : « rester sur le modèle de Guidatorino, avec
nos contraintes ; beaucoup d'infos mais ça ne submerge pas ; un côté presque amateur,
attachant, qui fait dire : ce sont des passionnés ». Pages de test : `/test-accueil/` (A,
ma première proposition) et `/test-accueil-b/` (B, modèle Guidatorino), toutes deux en
noindex, listées dans le menu « Pages de test » de WordPress.

## 1. Mesuré le 02/10 (navigateur, ordinateur 1400 px)

| | Guidatorino | Accueil actuel | Test A | Test B |
|---|---|---|---|---|
| Hauteur ordinateur | 4 592 px | 7 649 px | 4 724 px | 4 758 px |
| Hauteur téléphone | 14 341 px | 11 436 px | 7 616 px | 6 879 px |
| Articles distincts | 24 | 34 | 44 | 22 |
| Mots visibles | 1 070 | 994 | 1 031 | 1 060 |
| Images | ≈ 48 (60 avec le carrousel) | 42 | 22 | 29 + 13 dessins |

Deux conclusions contre-intuitives, mesurées :

- **L'impression de « beaucoup d'infos » ne vient ni du nombre d'articles ni du texte.**
  Même volume de mots partout ; Guidatorino montre deux fois MOINS d'articles que le
  test A. Elle vient de la **variété des blocs** (une quinzaine de types : carrousel,
  pavés, lettre, « en primo piano », « di oggi », nouveautés avec extraits, pavés
  secondaires, « in evidenza », réseaux sociaux, publicité, liste d'événements…) et du
  **nombre d'images et de dessins**.
- **Le fait main est un système d'IMAGES, pas de code.** Pavés en GIF, encadrés
  (lettre, Instagram, Facebook, publicité) en JPG au trait décalé, titres du carrousel
  incrustés dans les photos. Le site ne charge aucune police : tout est en Georgia.
  Thème maison (`themes/guidatorino/style.css?v=3`), mise en page de blog WordPress
  classique (trois colonnes, extraits avec 2 ou 3 passages en gras, « » », pagination,
  pied de page sur une ligne avec numéro de TVA et e-mail). **Aucune signature.**

Sur téléphone, sa longueur vient en bonne partie des blocs publicitaires « Scopri di
più » intercalés.

## 2. Ce que dit la recherche (sources ouvertes le 02/10)

- **Le désordre coûte au premier regard.** La complexité visuelle se juge en 17 à 50 ms ;
  une forte complexité fait chuter l'attrait, et un site qui RESSEMBLE à son genre est
  mieux jugé (Google Research, Reinecke 2013). Guidatorino passe parce qu'il a la tête
  d'un guide : densité régulière, motifs répétés.
- **L'imperfection n'est sympathique que sur fond de compétence** (effet pratfall,
  Aronson 1966). Les coquilles et liens cassés nuisent (Stanford, Fogg) ; seule une
  erreur corrigée humanise (Bluvstein 2024). Donc : copier la chaleur, jamais les défauts.
  Guidatorino en a (deux coquilles dans « Chi siamo », « Eventi Torino 2025 » encore en
  avant, dates dans les adresses).
- **Chaleur et compétence ensemble produisent l'admiration** (Aaker, Vohs & Mogilner
  2010). Le fait main donne la chaleur ; il faut à côté des preuves de sérieux.
- **Montrer le travail réel augmente la valeur perçue** (Buell & Norton 2011 ; Buell,
  Kim & Tsay 2017, +22 % de qualité perçue), mais le fabriquer « frôle une limite
  éthique » et se retourne s'il est soupçonné.
- **L'écriture manuscrite** humanise, mais l'effet s'inverse sur l'utilitaire : jamais sur
  la date, le lieu ou le prix.
- **Carrousel automatique** : l'offre n'est vue que 20 % du temps (NN/g). On n'en met pas.
- **Fausse présence humaine** : Google qualifie de tromperie les auteurs inventés.
  L'article 50(4) de l'AI Act (en vigueur depuis le 2 août 2026) demande de déclarer un
  texte généré qui informe le public, sauf relecture humaine sous responsabilité
  éditoriale. **Savoir s'il vise un agenda culturel reste une question juridique ouverte,
  à trancher par Franck** : le pipeline enrichit les fiches par LLM.

## 3. Nos contraintes, et le point de tension

**La charte (§ 1) se définit comme « anti-GuidaTorino ».** Je ne crois pas que la demande
la contredise : ce que Franck aime chez eux, c'est la FORME (chaleur, fait main, variété),
pas le REGISTRE, que la charte rejette à raison (§ 6 : pas de « à ne pas manquer », pas
de superlatifs, pas de titres en capitales, pas de surnoms touristiques). Le test B prend
l'une et garde l'autre. Si Franck veut faire bouger la charte, c'est son arbitrage.

Autres contraintes tenues dans B :
- rien de passé (règle 5) : guides des Journées du patrimoine, de Plaisirs de Culture et
  des festivals d'été écartés. **Le test A mettait Plaisirs de Culture en vedette :
  c'était une faute, corrigée** ;
- aucun « coup de cœur » ni « notre sélection » : la sélection est CALCULÉE
  (`cs_home_build_allocation`), le dire humain serait faux ;
- seuls des signaux de travail VRAIS : heure du dernier ajout, date « vérifié auprès de la
  source » de chaque fiche. Mesuré : sur 123 fiches françaises à venir, 71 revérifiées
  dans les 7 jours, 50 depuis plus longtemps. « Vérifié chaque matin » aurait été faux ;
- pas d'encadrés « suivez-nous » : aucun compte social n'est lié depuis l'accueil ;
- images du premier écran chargées tout de suite (le chargement différé retarde le LCP).

## 4. Ce que fait B

Accroche + recherche ; six pavés dont l'icône déborde, à côté de la lettre au trait
décalé ; « À la une » et « Aujourd'hui » en rangées de quatre ; trois colonnes :
nouveautés avec extraits et faits en gras (dates, lieu, gratuité, trois au plus, aucun
mot ajouté), pavés de territoires avec les monuments de la frise de l'en-tête, « À garder
sous le coude », publicité, « Proposer un événement », « Faire connaître votre lieu »,
« Ce week-end ». Deux interrupteurs de comparaison : texte en Georgia, encadrés sobres.

Construction : `deploy/wordpress/tests-lecture/accueil_b_construire.py` et `accueil_b.css`
(instantané de la base, régénérable).

## 5. Questions ouvertes pour Franck

1. La charte § 1 « anti-GuidaTorino » : on la garde telle quelle (forme oui, registre non) ?
2. Présence humaine réelle : Guidatorino n'en a pas ; Time Out et The Infatuation signent
   et montrent des visages. Montrer qui fait l'agenda est le seul « humain » qui serait
   vrai ; c'est un choix personnel.
3. AI Act art. 50(4) : faut-il une mention sur les fiches enrichies ?
