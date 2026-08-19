# Le VPS ne joint plus le site : blocage réseau côté OVH

*Constaté le 2026-08-18. Chaque ligne ci-dessous est une mesure, prise depuis
les deux machines.*

---

## Le fait

**Depuis le 2026-08-18 à 09 h 55 min 36 s, le VPS ne peut plus joindre
agendasabauda.eu.** Le pipeline est à l'arrêt : plus une seule fiche publiée,
plus un relevé de santé déposé, et le récapitulatif Slack part sans les
rapports WordPress.

La coupure est tombée en plein lot : à 09 h 52 le sélecteur retenait huit
événements complets à publier. Aucun n'est parti.

---

## Ce que la mesure montre

| Depuis | Vers `5.135.23.164` | Résultat |
|---|---|---|
| VPS `152.239.112.112` | ICMP | **100 % de perte** |
| VPS | TCP 80 et 443 | **expiration** |
| Poste de travail | ICMP | 0 % de perte |
| Poste de travail | HTTPS | **200** en 2,9 s |

**Le site est en ligne.** C'est le VPS, et lui seul, qui est écarté.

### Ce n'est ni une panne de route, ni le VPS

Depuis le VPS, l'internet général répond en moins de 100 ms (example.com,
google.com, api.github.com, tous en 200). Et surtout, **tous les autres serveurs
OVH répondent** :

| Hôte | IP | Port 443 |
|---|---|---|
| cluster021 | 188.165.53.185 | ouvert |
| cluster025 | 188.165.59.25 | ouvert |
| cluster027 | 54.36.91.62 | ouvert |
| cluster030 | 145.239.37.162 | ouvert |
| ovh.com | | ouvert |
| **cluster100** | **5.135.23.164** | **bloqué** |

Le VPS n'a aucun pare-feu local : `iptables` en politique ACCEPT, `ufw` inactif.
La résolution DNS y est correcte.

**Conclusion : le serveur mutualisé OVH cluster100, qui héberge le site, rejette
les paquets venant de `152.239.112.112`.** Un rejet silencieux, pas un refus,
donc filtré en amont d'Apache.

---

## Ce que ça n'est pas

**Pas une cadence abusive de notre côté.** Sur la demi-heure qui précède la
coupure, les journaux montrent 10 à 15 lignes par minute, et toutes ne sont pas
des requêtes HTTP. Rien qui ressemble à un martèlement.

**Pas un blocage applicatif.** L'ICMP tombe aussi, or aucun greffon de sécurité
ne filtre l'ICMP. Le rejet est réseau.

---

## Ce qu'il faut demander à OVH

> Depuis le 18/08/2026 vers 09 h 55 CEST, l'adresse `152.239.112.112` ne peut
> plus joindre `5.135.23.164` (cluster100), ni en ICMP ni en TCP 80 et 443,
> alors que les autres clusters OVH répondent normalement depuis cette même
> adresse. Merci de vérifier un éventuel blocage anti-abus et de le lever.

Sur un hébergement mutualisé, ce type de blocage n'a pas de levée en libre
service : il passe par un ticket.

---

## Ce qui continue de tourner

Les cinq contrôles quotidiens s'exécutent **sur le serveur du site lui-même**,
pas depuis le VPS. Ils ne sont pas affectés. Le site, la publication manuelle et
l'accès Novamira non plus.

**Seul le pipeline du VPS est coupé.** Ce qui veut dire : aucune nouvelle source
moissonnée n'arrivera en ligne tant que le blocage tient.

---

## Registre de ce qui est bloqué

*Relevé le 2026-08-19 à 14 h. Blocage toujours actif : 100 % de perte ICMP,
HTTPS à 000 depuis le VPS. Six scripts ont échoué dans la journée.*

### Bloqué : tout ce qui parle au site depuis le VPS

| Fonction | Script | Effet |
|---|---|---|
| **Publication des événements** | `publisher_as`, `publish_batch_as` | **Plus une seule fiche mise en ligne depuis le 18/08 à 09 h 55** |
| Téléversement des médias | `utils/wp_media.py` | aucune image ne monte |
| Relevé de santé | `publier_sante` | 4 échecs le 19/08 |
| Rapports dans le récapitulatif Slack | `rapports_wordpress` | le digest part amputé |
| Santé des gabarits | `gabarit_health` | 3 échecs |
| Santé de l'accueil | `homepage_health` | non mesurée |
| Audit du site | `site_audit`, `site_health_check` | non mesuré |
| **Panel de personas sur les pages** | `panel_site.py` | relecture éditoriale à l'arrêt |
| Vérification des doublons publiés | `verifier_doublons_publies` | plus de garde-fou |
| Audit de langue Polylang | `audit_langue_polylang` | plus de garde-fou |
| Réconciliation du catalogue | `reconcile_catalogue`, `reconcile_wp_deleted`, `reconcile_hors_ligne` | la base VPS et le site divergent en silence |
| Audit des fiches fantômes | `audit_wp_ghosts` | |
| Vérification des liens | `verifier_liens` | |
| Bandeaux de catégorie | `upgrade_category_banners_as` | |
| Export « à la une » | `export_une_now` | |

**Conséquence de fond : la base du VPS et le site divergent chaque jour un peu
plus, sans que rien ne le mesure.** La moisson continue de tourner et de
collecter, mais rien n'arrive en ligne.

### Bloqué aussi : les correctifs identifiés mais non déployables

1. La **création de doublons** du 17/08, qui a produit les quatre fiches passées
   en brouillon le 19/08.
2. Le **re-téléversement des médias** à chaque republication, 235 fichiers de nom
   déjà présent, et les trois variantes téléversées pour une seule employée.
3. Les fiches italiennes à **slug français**, et l'étiquetage de langue fautif
   qui a produit 23 fiches françaises déclarées italiennes.
4. Le rattachement des **événements satellites**.

Aucun ne peut être vérifié de bout en bout tant que le VPS ne joint pas le site.

### Ce qui n'est PAS bloqué

- Les **cinq contrôles quotidiens** WordPress : ils tournent sur le serveur du
  site lui-même.
- **Novamira**, donc toute intervention directe sur WordPress.
- La **publication manuelle** par l'administration.
- La **moisson des sources externes** : le VPS joint le reste de l'internet
  normalement, seul `5.135.23.164` le rejette.
- Les notifications **Slack**.

### Ce qui débloque

Un ticket OVH. Le texte à envoyer est au début de ce document. Sur un
hébergement mutualisé, ce type de blocage n'a pas de levée en libre service.
