# Donner les droits Gmail (lecture seule) — guide pas-à-pas

Ce guide explique comment générer le fichier **`credentials.json`** qui autorise
l'agenda à **lire** les newsletters culturelles reçues sur Gmail (label `Agenda`).
**Aucune compétence technique requise** : il suffit de suivre les écrans dans
l'ordre. Compte à utiliser : **franck.monod@culturasabauda.eu**.

> ⏱️ Durée : ~15 minutes, une seule fois.
> 🔒 Le fichier obtenu est un **secret** : ne jamais l'envoyer par email ni le
> mettre sur GitHub (il est déjà exclu automatiquement par `.gitignore`).

---

## Étape 1 — Ouvrir la console Google Cloud

1. Va sur **https://console.cloud.google.com/** et connecte-toi avec
   `franck.monod@culturasabauda.eu`.
2. En haut, clique sur le sélecteur de projet → **« Nouveau projet »**.
3. Nom du projet : `Agenda Cultura Sabauda` → **Créer**.
4. Attends quelques secondes, puis sélectionne ce projet (sélecteur en haut).

## Étape 2 — Activer l'API Gmail

1. Menu ☰ (en haut à gauche) → **« API et services » → « Bibliothèque »**.
2. Cherche **« Gmail API »** → clique dessus → bouton **« Activer »**.

> L'agenda n'a besoin **que** de Gmail (pas de Drive) : une seule API à activer.

## Étape 3 — Configurer l'écran de consentement

1. Menu ☰ → **« API et services » → « Écran de consentement OAuth »**.
2. Type d'utilisateur : **Externe** → **Créer**.
3. Remplis le minimum demandé :
   - Nom de l'application : `Agenda Cultura Sabauda`
   - E-mail d'assistance : `franck.monod@culturasabauda.eu`
   - Coordonnées du développeur : `franck.monod@culturasabauda.eu`
   - **Enregistrer et continuer**.
4. Écran « Niveaux d'accès / Scopes » : tu peux **passer** (Enregistrer et continuer)
   — le scope sera demandé automatiquement au premier lancement.
5. Écran « Utilisateurs test » → **« + Add users »** → ajoute
   `franck.monod@culturasabauda.eu` → **Enregistrer et continuer**.

> ℹ️ Tant que l'application reste en mode « test », c'est parfait : seuls les
> comptes ajoutés ici peuvent l'utiliser. Pas besoin de publication.

## Étape 4 — Créer les identifiants (le fameux credentials.json)

1. Menu ☰ → **« API et services » → « Identifiants »**.
2. Bouton **« + Créer des identifiants » → « ID client OAuth »**.
3. Type d'application : **« Application de bureau »**.
4. Nom : `Agenda poste local` → **Créer**.
5. Une fenêtre s'affiche → bouton **« Télécharger le JSON »**.
6. **Renomme le fichier téléchargé en `credentials.json`.**

## Étape 5 — Déposer le fichier dans l'outil

Place `credentials.json` dans le dossier **`config/`** de l'agenda
(sur la machine/VPS où l'outil tournera).

## Étape 6 — Première autorisation (une seule fois)

Lance le script d'autorisation :

```bash
# Poste de bureau (avec navigateur) :
python scripts/authorize.py

# Serveur / VPS sans navigateur :
python scripts/authorize.py --manual
```

En mode `--manual`, le script affiche une URL :

1. Ouvre-la dans ton navigateur, choisis `franck.monod@culturasabauda.eu`.
2. Google affiche **« Google n'a pas validé cette application »** (normal en mode test) :
   clique sur **« Paramètres avancés » → « Accéder à Agenda Cultura Sabauda (non sécurisé) »**.
3. Coche l'autorisation de **lecture Gmail** → **Continuer**.
4. Le navigateur affichera « localhost a refusé la connexion » : c'est **normal**.
   Copie l'URL COMPLÈTE de la barre d'adresse (elle contient `?code=...`) et
   recolle-la dans le terminal.

Un fichier `config/token.json` est alors créé automatiquement. **Les lancements
suivants ne demanderont plus rien** — c'est ce qui permet au cron de tourner seul.

---

## Ce que ce droit permet (et ne permet pas)

| Autorisation demandée | Ce que ça permet | Limite |
|-----------------------|------------------|--------|
| `gmail.readonly`      | **Lire** les mails portant le label `Agenda` | Aucune modification/suppression possible |

C'est volontairement le strict minimum : l'outil ne peut ni envoyer, ni modifier,
ni supprimer tes emails — uniquement les lire pour en extraire les événements.

---

## Dépannage

| Message | Solution |
|---------|----------|
| « Accès bloqué : Agenda Cultura Sabauda n'a pas terminé la procédure de validation » | Vérifie que ton compte est bien dans **Utilisateurs test** (Étape 3.5). |
| « redirect_uri_mismatch » | Le type d'application n'est pas « Application de bureau » — refais l'Étape 4 avec le bon type. |
| « invalid_grant » au lancement suivant | Le `token.json` a expiré/été révoqué : supprime `config/token.json` et relance pour réautoriser. |
| « insufficient authentication scopes » | Supprime `config/token.json` et relance : le scope sera redemandé. |

> Rappel : le **label Gmail `Agenda`** (variable `GMAIL_LABEL` dans `.env`) est le
> sélecteur des mails à collecter. Applique-le aux newsletters auxquelles tu t'abonnes.
