# Le VPS ne joint plus le site — ce qui est à l'arrêt, et dans quel ordre le reprendre

Ouvert le **2026-08-18**. À tenir à jour tant que ce n'est pas résolu, et à archiver
ensuite plutôt qu'à supprimer : la prochaine coupure ressemblera à celle-ci.

---

## LES FAITS, MESURÉS

Depuis le **18/08 entre 13h01 et 13h08**, le VPS `152.239.112.112` ne joint plus
`agendasabauda.eu` (`5.135.23.164`).

| Mesure | Résultat |
|---|---|
| `ip -4 route` | route par défaut présente, `via 152.239.112.254 dev eth0` |
| `curl -4 https://ifconfig.me` | **152.239.112.112** — la sortie IPv4 fonctionne |
| `getent ahostsv4 agendasabauda.eu` | **5.135.23.164** — le DNS résout correctement |
| `ping -4 agendasabauda.eu` | **100 % de perte** |
| `curl` port 80 | timeout |
| `curl` port 443 | timeout |
| Le site depuis un autre réseau | **répond normalement** (Novamira, navigateur) |

Trois protocoles, tous jetés en silence, vers **cette seule adresse**, alors que la même
IPv4 joint le reste d'internet. Ce n'est ni une route perdue, ni le DNS, ni le port 443 :
**les paquets sont bloqués à destination**.

⚠️ **UN DIAGNOSTIC A ÉTÉ ANNONCÉ PUIS INFIRMÉ.** Une première conclusion — « le VPS n'a
plus d'IPv4 » — a été tirée de `ifconfig.me` répondant une adresse IPv6. Ça prouve
seulement que le serveur PRÉFÈRE l'IPv6 quand les deux existent. `ip -4 route` l'a
démentie. Ne pas repartir de cette hypothèse.

Cause probable, **non établie** : une protection anti-flood de l'hébergement déclenchée
par une salve de publication. La coupure suit une publication, mais le lot de 156 fiches
de la veille est passé entier sans rien déclencher — le volume seul n'explique donc pas.

### La phrase pour le ticket

> Mon serveur `152.239.112.112` ne joint plus l'IP `5.135.23.164` (agendasabauda.eu).
> Ping, port 80 et port 443 sont tous en timeout depuis le 18 août vers 13h, alors que ce
> même serveur joint sans problème tout le reste d'internet en IPv4, et que le site répond
> normalement depuis d'autres réseaux. La route IPv4 et le DNS sont corrects de mon côté.
> Merci de vérifier si l'IP `152.239.112.112` est bloquée par la protection de
> l'hébergement.

Ne PAS écrire « débloquez mon IP » sans ces mesures : ça envoie le support chercher au
mauvais endroit.

---

## CE QUI EST À L'ARRÊT

Classement obtenu en cherchant, dans chaque script du crontab, un appel RÉEL à WordPress
(`WP_AS_URL`, `publish_to_as`, `publish_main`, route `wp-json`) — pas une simple mention.
Deux faux positifs ont été écartés à la relecture : `scraper_events` et `verifier_lieux`
ne citent le site que dans des commentaires.

| Heure | Cron | Ce qui ne se fait plus |
|---|---|---|
| 08h45 | `dates.py` | les fiches dont la date a changé ne sont plus repoussées en ligne |
| 09h30 | **`daily_batch`** | **le lot du jour ne part pas — aucune fiche nouvelle en ligne** |
| 09h50 | `verifier_doublons_publies --en-ligne` | ne peut plus sonder ; il le DIT et refuse de conclure |
| 10h30 | `seo_batch` | le SEO se calcule, mais n'atteint pas Yoast (poussé à la republication) |
| 10h45 | `translate_events --apply` | les traductions se rédigent mais ne se publient pas |
| 10h45 | `refresh_deplacement --apply` | les notes datées ne sont plus rafraîchies EN LIGNE |
| 12h05 | `publier_sante --publier` | le relevé de santé n'est plus publié |
| 13h00 | `homepage_health` | plus de contrôle de la page d'accueil |
| 14h00 | `site_audit` | plus d'audit du site |
| 14h15 | `gabarit_health` | plus de contrôle des gabarits |
| hebdo | `site_health_check`, `gsc_report`, `weekly_audits` | à l'arrêt |

**La conséquence à retenir, en une phrase : le catalogue a cessé de grandir.** Le site
reste en ligne et complet, mais plus rien n'y entre. Chaque journée de blocage, c'est un
lot quotidien qui ne part pas.

### Ce qui continue normalement

Scraping, collecte des newsletters, dédoublonnage, évaluation, datation (la partie
calcul), recherche de lieux, enrichissement, traduction (la rédaction), et le digest Slack
— sa boîte est un fichier local. Tout ce travail s'accumule proprement en base et partira
d'un coup au déblocage. **Rien n'est perdu, tout est différé.**

---

## LE CONTOURNEMENT EN PLACE

`scripts/export_une_now.py` sépare le CALCUL (local, intact) du TRANSPORT (bloqué) : le
VPS rend un JSON `post_id → valeur`, un autre canal (Novamira, qui joint le site depuis un
autre réseau) l'écrit. 265 métas `as_une_now` ont été posées comme ça le 18/08.

Il porte une empreinte sha256 de sa charge, à vérifier avant écriture — le JSON traverse
une conversation, donc il est retapé, collé, éventuellement tronqué.

Ce contournement ne vaut que pour des MÉTAS. Il ne remplace pas une publication : ni
texte, ni images, ni création de page.

---

## AU DÉBLOCAGE — DANS CET ORDRE

1. **Vérifier que ça passe vraiment**, avant tout le reste :
   `curl -4 -sS -m 10 -o /dev/null -w "%{http_code}\n" https://agendasabauda.eu/wp-json/cs/v1/`
2. **Le lot en retard**, détaché pour qu'une déconnexion ne le tue pas :
   `cd ~/evenements && nohup .venv/bin/python -m scripts.publish_batch_as --update --skip-media --cap 200 > /tmp/lot.log 2>&1 &`
3. **Les doublons**, que le blocage empêchait de sonder :
   `.venv/bin/python -m scripts.verifier_doublons_publies --en-ligne`
4. **Terra Madre** (post 2190) : la version italienne n'existe plus nulle part, le post
   italien 1931 ayant été écrasé par le texte français puis corbeillé le 03/08. L'article
   italien est toujours en base (fiche 2507) : le republier sur une page neuve, relier la
   paire.
5. **Les deux traductions du mauvais côté** (fiches 3495 et 3509) :
   `.venv/bin/python -m scripts.audit_langue_polylang`
6. **Si la piste anti-flood se confirme**, ralentir les lots : `publish_batch_as --delay`
   existe (défaut 1,5 s) et n'a jamais été augmenté.

---

## CE QUE CET INCIDENT A APPRIS

**Un timeout n'est pas un refus.** « Connection timed out » sur ping + 80 + 443 vers une
seule adresse désigne un filtrage silencieux ; « connection refused » ou « no route to
host » diraient autre chose. Cette distinction a tranché le diagnostic.

**Quatre commandes suffisaient, et il fallait les taper à la première minute** : sortie
IPv4 vers un hôte témoin, résolution DNS, port 80, ping. Elles séparent « le VPS est
cassé » de « cette destination nous bloque ». Deux hypothèses fausses ont été annoncées
avant de les lancer.

**Un script bloqué doit le dire, pas rendre zéro.** `verifier_doublons_publies` a annoncé
« SONDAGE IMPOSSIBLE : 14/14 » et déclaré son zéro non fiable, au lieu de laisser croire
que le site était sain. C'est le comportement à copier partout ailleurs.
