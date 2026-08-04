# Conformité — IA, consentement, droits d'image

> **Portée** : Agenda Sabauda, et par extension les projets de l'écosystème Cultura
> Sabauda qui publient du contenu assisté par IA ou affichent de la publicité.
> Créé le 2026-08-04 après un audit qui a trouvé trois trous en une session.
> **À lire avant** de toucher au pipeline image, aux mentions légales, ou à la régie.

---

## 1. AI Act — ce qu'on doit faire, et ce qu'on ne doit pas faire

**L'article 50 du règlement européen sur l'IA est applicable depuis le 2 août 2026.**
Il n'a pas été repoussé par le digital omnibus, contrairement aux obligations
« haut risque » qui basculent en décembre 2027. Sanction : jusqu'à 15 M€ ou 3 % du
chiffre d'affaires mondial.

**Notre situation.** Nous sommes **déployeur**, pas fournisseur : le marquage
technique invisible des contenus incombe aux éditeurs de modèles. Nous ne sommes pas
un système à haut risque (pas de biométrie, pas de reconnaissance d'émotions, pas de
notation de personnes). Nous n'avons pas de chatbot. Deux obligations nous concernent.

**Texte généré.** L'article 50(4) impose de divulguer les textes générés par IA
destinés à informer le public. Une exemption existe si le contenu est relu par un
humain et qu'une personne assume la responsabilité éditoriale.

> **Règle : on déclare, on ne joue pas l'exemption.** Déclarer est toujours conforme
> et ne coûte rien. L'exemption ne sert qu'à s'éviter la mention, et elle suppose une
> relecture réelle que nous n'avons pas sur l'ensemble du catalogue. La déclaration
> est dans `docs/legal/mentions_legales.md` §4 (FR et IT).

**Images générées.** L'article 50(4) impose de signaler visiblement toute image
artificiellement générée ou manipulée, dès l'exposition au contenu, pas dans les
mentions légales.

> **Règle : aucune image publiée sur Agenda Sabauda n'est générée par IA.** C'est ce
> que nos mentions légales affirment. Vérifié le 2026-08-04 : les visuels maison sont
> des compositions programmatiques (1200×675, sans EXIF logiciel ni marqueur C2PA).
> **Si un jour on introduit une image générée, il faut d'abord corriger les mentions
> légales, puis étiqueter l'image à l'affichage.** Pas l'inverse.

---

## 2. Consentement et publicité (RGPD + exigences Google)

Le site utilise **Complianz GDPR**, région UE, bandeau et blocage de scripts actifs.

**Deux manques connus au 2026-08-04**, tous deux liés à la version gratuite :

- **Pas de module TCF.** Google exige une CMP certifiée intégrant le TCF pour servir
  des annonces aux visiteurs de l'EEE et du Royaume-Uni. Sans lui, aucune chaîne de
  consentement n'est émise et les emplacements européens ne se remplissent pas. Notre
  audience étant européenne à 100 %, une validation AdSense sans TCF ne rapporte rien.
- **Pas d'enregistrement des preuves de consentement.** Le RGPD (art. 7.1) demande de
  pouvoir démontrer le consentement obtenu.

> **Règle : ne jamais conclure qu'un site est conforme parce qu'un plugin de
> consentement est actif.** Vérifier le niveau de licence et la présence effective du
> module TCF, pas seulement la présence du bandeau. La présence de `__tcfapi` dans le
> HTML ne prouve rien : le script Google lui-même appelle cette API pour la chercher.

---

## 2 bis. Fiches de démonstration : ne jamais en laisser en ligne

Le 2026-08-04, dix fiches publiées se sont révélées fabriquées. Créées le 17 juillet
à 17:58, **en deux secondes**, par `agenda-bot`. Signature :

- `as_verifie_le = 2026-07-17`, la date de création elle-même : la fiche **affirmait**
  avoir été vérifiée ;
- `as_source_officielle_url` vide : il n'y avait rien à vérifier ;
- aucune correspondance dans `events_raw` : jamais collectées ;
- dates de début en **escalier régulier** (19, 21, 23, 25, 30 juillet, puis 1, 3, 5, 7,
  10 août), en alternant les quatre territoires.

Deux portaient des noms d'événements réels (Bataille des Reines, Sagra della Toma) avec
des dates inventées, ce qui est plus trompeur qu'un titre entièrement fictif. Cinq
avaient une date encore à venir au moment de la découverte. Mises à la corbeille, pas
supprimées (sauvegarde `cs_bk_fiches_demo_20260804`), plus la traduction FR liée.

> **Règle : une fiche qui affirme `as_verifie_le` sans porter de source est un mensonge
> publié.** Nos mentions légales promettent que les données pratiques sont « vérifiées à
> la source officielle indiquée sur chaque fiche ». Une fiche sans source ne peut pas
> porter de date de vérification.

> **Règle : ne jamais publier de contenu de démonstration sur le site live.** Pour
> éprouver un gabarit, utiliser un brouillon ou un statut non public. Un jeu de test qui
> passe en production devient indiscernable du vrai au bout de quelques semaines.

**Détection.** Chercher les fiches publiées qui ont `as_verifie_le` non vide et
`as_source_officielle_url` vide. **Attention au faux positif** : au 2026-08-04, 43 fiches
répondent à ce critère sans être fabriquées. Ce sont de vrais événements collectés dont
le pipeline n'a pas recopié la source vers WordPress. Le signe distinctif de la
fabrication n'est pas la source manquante seule, c'est **la création en lot en quelques
secondes, l'absence de ligne dans `events_raw`, et l'escalier des dates**.

> **Question ouverte (2026-08-04)** : pourquoi 43 fiches publiées n'ont-elles pas de
> source dans WordPress alors qu'elles en ont une côté pipeline ? Tant que ce n'est pas
> résolu, la phrase des mentions légales est partiellement fausse.

---

## 3. Droits d'image

La doctrine est dans `docs/IMAGES.md` §1. Elle était juste, mais elle s'appuyait sur
une liste de domaines proscrits **fausse**, héritée d'un autre projet et limitée à la
presse nationale française. Conséquence : 41 fiches illustrées par une photo du
Dauphiné Libéré, de Nice-Matin, d'Aosta Oggi, ou reprise chez l'agenda concurrent
agendaculturel.fr.

> **Règle : la liste des domaines proscrits doit couvrir la presse RÉGIONALE des
> quatre territoires**, c'est-à-dire précisément celle qui couvre nos événements.
> Voir `config/blocked_image_domains.txt`, section ajoutée le 2026-08-04.

> **Règle : un crédit ne régularise pas une image de presse.** Quand une photo n'est
> pas licenciable, la seule issue est le remplacement ou le repli. On ne crédite que
> ce qu'on a le droit d'afficher.

> **Règle : détacher ne suffit pas, héberger est déjà l'infraction.** Une copie de
> photo de presse dans `wp-content/uploads` doit être supprimée, pas seulement retirée
> de l'affichage.

---

## 4. Méthode — trois pièges rencontrés le même jour

Ces règles ne sont pas juridiques, elles sont opératoires. Les trois erreurs ci-dessous
ont été commises et rattrapées dans la même session, et elles se ressemblent.

**Une règle adossée à une liste doit être auditée sur les données réelles.** La règle
« on évite les photos de presse » existait depuis juillet et était respectée par le
code. Elle a laissé passer 41 fiches parce que personne n'avait comparé la liste aux
domaines réellement présents en base. Énoncer une règle n'est pas la vérifier.

**Vérifier ce qu'on risque d'emporter, pas seulement ce qu'on ajoute.** Un contrôle
« ce fichier est-il utilisé ailleurs ? » fondé sur `_thumbnail_id` renvoie zéro pour
les 48 visuels de repli, puisque le repli du site (snippet 87) est un mécanisme
d'affichage qui n'utilise aucune miniature. Une suppression en masse aurait effacé le
système de repli entier. **Avant toute suppression, lister les cibles et les lire.**

**Un motif de recherche large produit des faux positifs qui ressemblent à des
résultats.** `LIKE '%IA%'` attrape Wikimedia, Italia, Giulia. `\bAI\b` attrape une
déclaration de police CSS. Un détecteur qui renvoie 80 correspondances doit être
échantillonné avant d'être cru, surtout quand il sert à décider d'une suppression.

---

## 5. Sources officielles — ce qu'une URL de source n'a pas le droit d'être

Trouvé le 2026-08-04, après la première publication en lot. Neuf fiches portaient comme
`as_source_officielle_url` un **lien de redirection de newsletter** au lieu de la page
de l'organisateur : `us.list-manage.com` (Mailchimp), `turismovda.musvc2.net` et
`customer86768.musvc3.net` (MailUp). Le collecteur ingère une lettre d'information et
conserve le lien cliqué, qui est une redirection de traçage, pas une source.

Cinq d'entre elles contenaient un paramètre `e=`, c'est-à-dire **notre propre
identifiant d'abonné**, republié sur des pages publiques. `e=06a93eea46` revenait sur
quatre fiches. Un tiers pouvait en déduire à quelles lettres la rédaction est abonnée.

> **Règle : une source officielle est une page, pas une redirection.** Sont interdits
> comme `as_source_officielle_url` : `*.list-manage.com`, `mailchi.mp`, `*.musvc*.net`,
> `*.sendinblue.com`, `*.mailerlite.com`, et plus généralement toute URL contenant
> `/e/tr?`, ou un paramètre `e=`, `eid=`, `subscriber=`. Ces liens **expirent**, ils
> **tracent**, et certains **exposent un identifiant d'abonné**.

> **Règle : ce qui vient d'une newsletter doit être résolu avant d'être publié.** La
> lettre d'information est un canal de détection, comme la presse (§4 des mentions
> légales). La source à publier est la page de l'organisateur, du lieu, de l'office de
> tourisme ou de la billetterie officielle, trouvée et vérifiée séparément.

**Corollaire découvert en réparant.** En allant chercher les vraies pages, deux fiches
se sont révélées annoncer un événement **déjà passé** : une séance unique avait reçu
comme date de fin celle de la saison de la salle (concert du 10 juillet étiré au
16 octobre, afterwork du 16 juillet étiré au 11 août). La fiche restait donc dans les
actifs des mois après sa tenue.

> **Règle : la date de fin est celle de l'événement, jamais celle de la saison.** Pour
> une séance unique, fin = début. Contrôle : une fiche dont le titre nomme une séance
> unique (« concert de », « soirée », « afterwork », « séance », « vernissage ») et
> dont la durée dépasse trente jours est suspecte.

**Le piège inverse : un filtre juste appliqué au mauvais objet.** Le même jour, on a
trouvé 43 fiches publiées affichant « vérifié le … » sans aucune source. Explication :
le publisher renvoyait `""` pour **tout** le radar. Or la charte §8 interdit de lier
l'**article de presse** qui a servi à détecter l'événement, pas la **page de
l'organisateur** que le pipeline remonte ensuite depuis cet article — laquelle est
exactement ce que `docs/SOURCE_OFFICIELLE.md` appelle la source officielle, mémorisée
dans `url_officiel` seulement après avoir été lue et jugée pertinente. Dix-sept fiches
avaient donc une page officielle vérifiée que le publisher jetait.

> **Règle : le radar publie `url_officiel`, jamais `url_source`.** Détecter par la
> presse puis remonter à l'officiel est le trajet normal, pas une exception. Un filtre
> qui protège d'un risque réel doit être vérifié sur ce qu'il écarte, pas seulement sur
> ce qu'il laisse passer.

> **Règle : pas de source publiée, pas de date de vérification.** `as_verifie_le` était
> estampillé sans condition. Une fiche affirmait donc une vérification que le lecteur
> ne peut pas contrôler, alors que les mentions légales §4 promettent une vérification
> « à la source officielle **indiquée sur chaque fiche** ».

---

## 6. Divergences connues à surveiller

- `config/blocked_image_domains.txt` porte l'en-tête « SYNCED FROM
  observatoire-business-sabaudo, ne pas diverger ». L'ajout du 2026-08-04 **doit être
  porté** dans l'autre dépôt.
- Le texte des pages légales a **deux emplacements** : la source
  `docs/legal/mentions_legales.md` et le snippet WordPress 50 qui la rend. Toute
  modification faite directement dans le snippet est écrasée à la régénération.
  **Modifier la source d'abord.**
