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

## 5. Divergences connues à surveiller

- `config/blocked_image_domains.txt` porte l'en-tête « SYNCED FROM
  observatoire-business-sabaudo, ne pas diverger ». L'ajout du 2026-08-04 **doit être
  porté** dans l'autre dépôt.
- Le texte des pages légales a **deux emplacements** : la source
  `docs/legal/mentions_legales.md` et le snippet WordPress 50 qui la rend. Toute
  modification faite directement dans le snippet est écrasée à la régénération.
  **Modifier la source d'abord.**
