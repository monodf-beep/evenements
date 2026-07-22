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

⚠️ **Deux systèmes existent chez Meta pour publier sur Instagram** : l'ancien, basé
sur une Page Facebook + Graph API Explorer (compliqué, jetons de Page, permissions
`pages_show_list`/`instagram_basic`…) et le **nouveau**, basé sur une **connexion
Instagram directe** (« API Instagram », permissions `instagram_business_*`). **On
utilise le nouveau** — plus simple, pas besoin de jeton de Page. Ce qui suit est le
chemin **vérifié en conditions réelles** (compte Savoie, juillet 2026).

**Une seule app Meta sert pour les 4 comptes.** Une fois créée (App Meta →
« Ajouter un produit » → **API Instagram**) :

1. **developers.facebook.com** → l'app → **Cas d'utilisation** → **API Instagram**
   → **Autorisations et fonctionnalités**. Vérifier que `instagram_business_basic`
   et `instagram_business_content_publish` sont bien **« Prête pour le test »**
   (elles le sont par défaut dès que le produit API Instagram est ajouté — rien à
   activer). *(Ignorer `instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, `pages_read_engagement` — ce sont les permissions de
   l'ANCIEN système, pas les nôtres.)*

2. **Cas d'utilisation → API Instagram → Rôles dans l'application → Rôles**
   → onglet **« Testeurs Instagram »** → **« Ajouter des personnes »** → coche
   **« Testeur(se) Instagram »** → tape le nom du compte (ex. `agendasabauda.savoie`)
   → Ajouter. Le compte apparaît avec le statut **« En attente »**.

3. **Le propriétaire du compte** (jamais un agent/automate — c'est un vrai mot de
   passe) se connecte lui-même sur **instagram.com/accounts/manage_access/** avec
   ce compte Instagram → onglet **« Invitations à tester »** → accepte l'invitation
   de l'app.

4. Retour sur **Cas d'utilisation → API Instagram → Configuration de l'API avec la
   connexion Instagram**, section **« 2. Générez des tokens d'accès »** : le compte
   apparaît automatiquement dans le tableau, avec son **ID** déjà affiché sous son
   nom (ex. `17841410500624417`) — **c'est l'IG_ACCOUNT_ID**, pas besoin de requête
   API séparée pour l'obtenir.

5. Clique sur **« Générer un token »** à côté du compte. Une fenêtre de connexion
   Instagram s'ouvre. **Si elle refuse la connexion** (« Impossible de se connecter »,
   même avec les bons identifiants) : c'est presque toujours un souci de
   session/contexte navigateur, pas les identifiants. Solutions qui ont marché :
   - se connecter **d'abord** au compte sur instagram.com dans un **onglet
     séparé**, puis refaire « Générer un token » ;
   - si ça persiste, tout refaire **dans une seule fenêtre de navigation privée**,
     du login jusqu'au clic sur « Générer un token », sans rien d'automatisé ;
   - vérifier côté **appli mobile** qu'aucune alerte de sécurité Instagram
     n'attend une confirmation ;
   - en dernier recours, essayer un **autre navigateur** (une extension peut
     interférer avec la fenêtre de connexion).

6. Une fois généré, le champ **« Token »** est rempli. C'est l'**IG_TOKEN** — il
   commence par **`IGAA`** (pas `EAA`, c'est normal, c'est le format du nouveau
   système). **Ne le fais jamais transiter en clair dans un chat** — copie-le
   directement dans le `.env` du VPS.

⚠️ **Piège déjà rencontré (compte Savoie)** : un token `IGAA...` doit être utilisé
contre **`graph.instagram.com`**, PAS `graph.facebook.com` (réservé aux anciens
tokens de Page, préfixe `EAA...`). Si l'erreur *« Invalid OAuth access token —
Cannot parse access token »* apparaît alors que le token est bien copié en entier,
c'est ce piège — déjà corrigé dans `utils/instagram_publish.py` (constante
`GRAPH`), rien à refaire pour les prochains territoires.

*(Étapes 1, 4, 6 : sans risque à déléguer à Claude Cowork. Étapes 2-3-5 impliquent
une vraie connexion au compte : à faire par le propriétaire du compte lui-même.)*

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
