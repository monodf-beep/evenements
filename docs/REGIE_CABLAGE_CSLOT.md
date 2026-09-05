# Câblage régie — activer l'override par bloc (`[cs_slot]`)

*But : rendre réel le modèle « AdSense par défaut, remplacé par le backoffice quand un
annonceur est vendu ». La plomberie est prête (`/api/active-ads` répond HTTP 200 ; le
mu-plugin `cs-regie-serve.php` v0.2 expose le shortcode `[cs_slot]`). Il reste à**déployer
le mu-plugin** et à **envelopper le code AdSense de chaque bloc**. À faire dans une session
connectée à Novamira, verify-first, réversible.*

---

## Rappel du mécanisme

`cs-regie-serve.php` fournit :
- Shortcode **`[cs_slot bloc="N"]…code AdSense du bloc N…[/cs_slot]`** → si le backoffice a
  une campagne active pour le bloc N (`/api/active-ads`), affiche la **créative backoffice** ;
  sinon affiche le **code AdSense enveloppé**. Gating consentement marketing (Complianz) inclus.
- Helper PHP pour les gabarits : **`echo cs_regie_slot('N', $code_adsense_html);`** (même logique).

Sécurité : image autorisée uniquement depuis `agendasabauda.eu`, lien uniquement vers
`backoffice.agendasabauda.eu` (le `/go/<id>` de comptage), https exigé. Sinon → repli AdSense.

---

## Prérequis (déjà fait côté git)

Le fichier `deploy/wordpress/cs-regie-serve.php` (v0.2) est prêt. Le déblocage `.env`
(guillemets ligne 40) doit être fait pour que `push-wordpress.sh` fonctionne.

Déployer le mu-plugin — deux voies (inoffensif : il ne produit RIEN tant qu'aucun
`[cs_slot]` ne l'appelle) :

- **Voie A (SFTP depuis le VPS)** — nécessite `WP_DEPLOY_SSH` / `WP_DEPLOY_MU_DIR` dans
  `.env` (identifiants FTP-SSH OVH ; SSH activé côté offre) :
  ```bash
  cd /root/evenements && git pull
  bash deploy/push-wordpress.sh cs-regie-serve.php
  ```
- **Voie B (Novamira)** — si le SFTP n'est pas configuré : la session Novamira écrit le
  fichier directement dans `wp-content/mu-plugins/cs-regie-serve.php` (contenu =
  `deploy/wordpress/cs-regie-serve.php` du dépôt) via `file_put_contents`. C'est la
  première étape du prompt ci-dessous.

---

## Prompt à coller dans la session Novamira

```
On CÂBLE l'override de régie sur agendasabauda.eu. Le mu-plugin cs-regie-serve.php (v0.2)
est déployé : il expose le shortcode [cs_slot bloc="N"]…AdSense…[/cs_slot] et le helper
PHP cs_regie_slot('N', $adsense_html). Objectif : chaque emplacement pub = AdSense par
défaut, remplacé par la créative backoffice si une campagne est active pour ce bloc.
Verify-first, réversible, confirmation avant chaque écriture. Sauvegarde chaque valeur
avant modif.

ÉTAPE 0-bis — DÉPLOYER LE MU-PLUGIN (si pas déjà fait)
Si wp-content/mu-plugins/cs-regie-serve.php est absent ou plus ancien que la v0.2, écris-le
avec le contenu exact de deploy/wordpress/cs-regie-serve.php du dépôt (via file_put_contents).
Vérifie ensuite qu'il est chargé (le shortcode [cs_slot] doit exister).

ÉTAPE 0 — CARTOGRAPHIE (ne rien modifier)
Pour CHAQUE bloc pub réellement rendu aujourd'hui (au moins les blocs 1 et 2 AdSense
actifs), dis-moi OÙ vit son code AdSense :
  (a) dans un bloc Ad Inserter (lequel, numéro), ou
  (b) en dur dans un gabarit du thème (homepage-template.php, etc. — lequel, quelle ligne).
Donne-moi ce mapping bloc → emplacement du code AVANT de câbler.

ÉTAPE 1 — VÉRIFIER QUE LE SHORTCODE TOURNE
Confirme que le shortcode [cs_slot] est bien enregistré (le mu-plugin est chargé).
Teste : place [cs_slot bloc="99"]TEST-ADSENSE[/cs_slot] dans un endroit visible de test ;
sans campagne pour le bloc 99, il doit afficher « TEST-ADSENSE ». Retire-le après.

ÉTAPE 2 — ENVELOPPER, BLOC PAR BLOC
Pour chaque bloc du mapping :
  - Cas (a) Ad Inserter : active « Process shortcodes » sur le bloc, puis entoure le code
    AdSense par [cs_slot bloc="N"] … [/cs_slot] (N = le VRAI numéro de plan du bloc).
  - Cas (b) thème : remplace `echo $code_adsense;` par
    `echo function_exists('cs_regie_slot') ? cs_regie_slot('N', $code_adsense) : $code_adsense;`
    (le function_exists garantit un repli propre si le mu-plugin est retiré).
Commence par le bloc 1 seul, montre-moi le rendu, puis on continue.

ÉTAPE 3 — TEST D'OVERRIDE DE BOUT EN BOUT
Dans le backoffice (onglet Régie), il existe une campagne test « Printemps des arts »
sur le bloc 3. Réaffecte-la (ou crée une campagne test) sur un bloc RÉELLEMENT rendu et
enveloppé (ex. bloc 1), image hébergée sur agendasabauda.eu, statut actif.
Puis visite la home avec consentement marketing accepté + purge cache :
  https://agendasabauda.eu/?cs_regie_refresh=1
Attendu : la créative backoffice s'affiche À LA PLACE de l'AdSense du bloc 1. Termine la
campagne test → l'AdSense revient. Confirme les deux sens.

ÉTAPE 4 — NUMÉROTATION (conflit #1 du socle)
Vérifie que le numéro passé dans [cs_slot bloc="N"] correspond au VRAI bloc du plan 12
(pas au numéro Ad Inserter s'ils divergent). Si Ad Inserter blocs 1-4 ont été configurés
pour autre chose que le plan, réaligne (renumérote vers 13-16 ou corrige le mapping) et
dis-moi la table finale bloc-plan ↔ bloc-Ad-Inserter ↔ [cs_slot].

RÈGLES : par étapes, confirmation avant chaque modif, rollback documenté. Commence par
l'ÉTAPE 0 (cartographie) et donne-la-moi.
```

---

## Rappels

- **AdSense est en « Examen requis » chez Google** : tant que ce n'est pas approuvé, le
  « défaut AdSense » est vide. L'override backoffice, lui, marche indépendamment — c'est
  le seul moyen d'afficher une vraie pub aujourd'hui.
- **Rollback global** : supprimer `cs-regie-serve.php` fait retomber tous les `[cs_slot]`
  sur leur AdSense enveloppé (le `function_exists` protège les gabarits).
- Après toute modif backoffice, la diffusion se met à jour en ~5 min (cache transient) ou
  immédiatement via `?cs_regie_refresh=1`.
