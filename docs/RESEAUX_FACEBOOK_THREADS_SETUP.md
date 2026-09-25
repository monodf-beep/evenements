# Publication automatique Facebook + Threads — configuration (une fois par territoire)

*Complète `docs/RESEAUX_INSTAGRAM_SETUP.md`. Une fois les variables ci-dessous
renseignées pour un territoire, `/reseaux/publish` republie automatiquement (best
-effort) le même visuel + légende que le post Instagram sur la Page Facebook et
Threads du territoire — cf. `utils/facebook_publish.py` / `utils/threads_publish.py`.
Un échec Facebook/Threads ne bloque jamais la publication Instagram.*

⚠️ **Contrairement au guide Instagram, celui-ci n'a pas encore été vérifié en
conditions réelles** (Meta change régulièrement ses interfaces — le guide
Instagram a dû être corrigé après coup pour la même raison). À ajuster au fur et
à mesure, comme on l'a fait pour Instagram.

## 1. Variables à ajouter dans `.env` (VPS)

```
FB_PAGE_ID_SAVOIE_HAUTE_SAVOIE=xxxxxxxxxxxxxxx
FB_PAGE_TOKEN_SAVOIE_HAUTE_SAVOIE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

THREADS_USER_ID_SAVOIE_HAUTE_SAVOIE=xxxxxxxxxxxxxxx
THREADS_TOKEN_SAVOIE_HAUTE_SAVOIE=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
*(même paire pour PIEMONT, VALLEE_D_AOSTE, NICE_ALPES_MARITIMES — mêmes slugs
que pour Instagram et Brevo.)*

### Pages Facebook par territoire (URL publiques)

Adresses canoniques des Pages (à créer/activer côté Meta ; certaines ne sont pas
encore en ligne). C'est la référence pour renseigner `FB_PAGE_ID_<SLUG>` (§2 point 4)
et pour les liens sortants (pied de newsletter, site).

| Territoire | Slug | URL de la Page | Statut |
|---|---|---|---|
| Savoie / Haute-Savoie | `SAVOIE_HAUTE_SAVOIE` | https://www.facebook.com/agendasabauda-savoie/ | ⏳ pas encore active (prévue) |
| Piémont | `PIEMONT` | *(à définir)* | — |
| Vallée d'Aoste | `VALLEE_D_AOSTE` | *(à définir)* | — |
| Nice / Alpes-Maritimes | `NICE_ALPES_MARITIMES` | *(à définir)* | — |

## 2. Facebook — Page Access Token via UTILISATEUR SYSTÈME (recommandé)

Contrairement au token Instagram (60 jours, à renouveler), un token de Page généré
via un **utilisateur système** peut être **sans expiration** — plus adapté à un
serveur qui publie tout seul, pas besoin de repasser dessus tous les 2 mois.

1. **business.facebook.com → Paramètres de l'entreprise → Utilisateurs → Utilisateurs
   système → Ajouter**. Nom : « Agenda Sabauda — publication automatique ». Rôle :
   Admin (ou Employé, avec les bons droits sur la Page ci-dessous).
2. **Assigner des actifs** à cet utilisateur système : la **Page Facebook**
   « Agenda Sabauda » (ou la Page dédiée au territoire), droit **« Gérer le
   contenu »**.
3. Sur cet utilisateur système, clique **« Générer un nouveau token »** :
   sélectionne l'app « Agenda Sabauda App », coche `pages_manage_posts` +
   `pages_read_engagement`, **expiration : jamais** si l'option existe. Copie le
   token → c'est le **FB_PAGE_TOKEN**.
4. **FB_PAGE_ID** : visible dans les paramètres de la Page (Paramètres → À
   propos), ou via `GET /me/accounts?access_token=CE_TOKEN` (le champ `id`).

## 3. Threads — probablement le même schéma que l'Instagram « nouvelle API »

Threads a sa propre app produit chez Meta (distincte de l'API Instagram) :

1. **developers.facebook.com** → l'app → **Ajouter un produit** → cherche
   **« Threads API »** (ou « API Threads »).
2. Une fois ajouté, va dans **Cas d'utilisation → Threads API → Autorisations et
   fonctionnalités** : vérifie que `threads_basic` et `threads_content_publish`
   sont **« Prête pour le test »**.
3. **Rôles → Rôles dans l'application → Rôles** : ajoute le compte Threads du
   territoire comme testeur (probablement un onglet « Testeurs Threads », sur le
   même principe que « Testeurs Instagram »).
4. Le propriétaire du compte accepte l'invitation **côté Threads/Instagram**
   (comptes liés).
5. Retour sur la page de config Threads de l'app → génère le token directement
   pour ce compte (même mésaventure possible qu'avec Instagram si la fenêtre de
   connexion refuse : se connecter au compte D'ABORD dans un onglet séparé,
   ou tout faire dans une fenêtre de navigation privée, à la main, jamais via un
   agent automatisé — cf. `RESEAUX_INSTAGRAM_SETUP.md` §2 point 5).
6. **THREADS_USER_ID** : affiché à côté du compte sur cette même page (comme
   l'IG_ACCOUNT_ID pour Instagram).

## 4. Une fois configuré

- `/reseaux/publish` (post simple uniquement, pas carrousel/story) republie
  automatiquement sur Facebook + Threads dès qu'Instagram a réussi, pour les
  territoires configurés.
- Le message de confirmation liste les canaux touchés :
  « publié sur Instagram (…) + Facebook, Threads ».
- Chaque tentative est journalisée (`social_posts`, colonne `platform`).

## 5. Sécurité — même règle que pour Instagram

**Aucun token, mot de passe ou clé secrète ne doit transiter dans un chat** (avec
moi ou avec Claude Cowork). Ajoute-les directement dans le `.env` du VPS
toi-même, puis confirme juste « c'est fait ».
