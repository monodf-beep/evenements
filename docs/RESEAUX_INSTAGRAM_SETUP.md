# Publication automatique Instagram — configuration (une fois par compte)

*Une fois ces variables renseignées pour un territoire, le bouton « 🚀 Publier » dans
`/reseaux` publie réellement (génère le visuel, l'héberge sur agendasabauda.eu, poste
sur le bon compte Instagram). Tant qu'elles manquent, le back-office l'indique
clairement et propose le copier-coller manuel — rien ne casse.*

## 1. Variables à ajouter dans `.env` (VPS), une paire par territoire

Même convention que les listes Brevo (`BREVO_LIST_<SLUG>`) :

```
IG_ACCOUNT_ID_SAVOIE_HAUTE_SAVOIE=xxxxxxxxxxxxxxx
IG_TOKEN_SAVOIE_HAUTE_SAVOIE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

IG_ACCOUNT_ID_PIEMONT=xxxxxxxxxxxxxxx
IG_TOKEN_PIEMONT=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

IG_ACCOUNT_ID_VALLEE_D_AOSTE=xxxxxxxxxxxxxxx
IG_TOKEN_VALLEE_D_AOSTE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

IG_ACCOUNT_ID_NICE_ALPES_MARITIMES=xxxxxxxxxxxxxxx
IG_TOKEN_NICE_ALPES_MARITIMES=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

`IG_ACCOUNT_ID_*` = l'**Instagram Business Account ID** (pas le nom @, un nombre).
`IG_TOKEN_*` = un **jeton d'accès longue durée** avec la permission de publication.

## 2. Comment obtenir ces deux valeurs, par compte

Prérequis (une fois par compte, dans l'app Instagram) :
1. Le compte Instagram est en **Professionnel** (Business ou Creator).
2. Il est **relié à une Page Facebook** (une Page dédiée par territoire, ou une Page
   « Agenda Sabauda » avec cet onglet — au choix).

Puis, dans **Meta for Developers** (developers.facebook.com) :
1. Créer **une seule app Meta** pour les 4 comptes (type « Entreprise »).
2. Demander les permissions `instagram_basic` + `instagram_content_publish` +
   `pages_show_list` + `pages_read_engagement` → passage en **App Review** (Meta
   valide sous quelques jours ; jusque-là, l'app ne fonctionne qu'en mode test avec
   les comptes que tu déclares explicitement testeurs).
3. Avec l'outil **Graph API Explorer** (ou un échange de jeton), générer un **jeton
   longue durée** (60 jours, renouvelable) pour la Page liée à CE territoire.
4. Récupérer l'**Instagram Business Account ID** :
   `GET /{page-id}?fields=instagram_business_account&access_token=...`
   → le champ `instagram_business_account.id` est la valeur à mettre dans
   `IG_ACCOUNT_ID_<SLUG>`.

*(Cette étape peut être déléguée à Claude Cowork ou faite à la main dans l'interface
Meta — le back-office n'a besoin que du résultat : les deux valeurs ci-dessus.)*

## 3. Une fois configuré

- `/reseaux` affiche **🟢 publication auto connectée** en tête de la section du
  territoire, et le bouton **🚀 Publier** apparaît sur chaque événement.
- Publier génère le visuel (post simple pour l'instant ; carrousel prêt côté code,
  pas encore branché dans l'interface), l'héberge dans la médiathèque
  agendasabauda.eu, puis le poste sur le compte Instagram du territoire.
- Chaque tentative est journalisée (table `social_posts`) : republier un événement
  déjà publié demande une confirmation explicite (pas de doublon accidentel).

## 4. Ce qui reste manuel (limitation Meta, pas du back-office)

- **Reels à musique tendance/sous licence** : à publier depuis l'app (cf.
  `docs/RESEAUX_SOCIAUX_PLAN.md` §5).
- **Géolocalisation** du post : à ajouter à la main si voulu.
- **Collab / miniature de Reel** : à faire dans l'app.
