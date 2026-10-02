# Offres commerciales — ce qui existe déjà, ce qui manque

Recensement du 02/10/2026, à la demande de Franck (« regarder dans le repo si on n'a pas déjà
parlé de prestations, et chercher ce qui pourrait être des offres commerciales »). Rassemble des
documents épars ; ne remplace aucun d'eux.

Sources lues : `docs/REGIE_ANNONCEURS.md` (régie, grille, kit annonceurs), `docs/PAGE_PUBLICITE.md`
(texte de la page « Annoncer »), `docs/MARKETING_ET_PILOTAGE_AGENDA_SABAUDO.md` (modèle économique
de GuidaTorino, trafic projeté), `docs/PARTENARIAT_WIDGET.md` (widget), `app/app.py` (`AD_BLOCKS`,
mise en avant home forcée), maquettes de `/test-accueil-b/`.

## 1. Déjà construit

| Offre | État mesuré | Où |
|---|---|---|
| **6 emplacements display** (leaderboard, pavé in-article, bandeau bas, habillage, 2 gouttières) | grille de prix posée le 05/08 ; blocs 4-6 câblés en direct, blocs 1-3 « à faire » ; le back-office gère campagnes, dates, et **compte les clics** (`/go/<id>`) | `AD_BLOCKS`, `cs-regie.php`, `cs-regie-serve.php`, page `/regie` du back-office |
| **Forcer une fiche en une** | existe déjà, mais réservé à l'édition : bouton « mise en avant home » du back-office, méta `as_home_override` | `app.py`, `set_home_override` |
| **Widget pour sites partenaires** | en ligne, **gratuit** par choix (levier de liens et de notoriété, pas de revenu) | `PARTENARIAT_WIDGET.md` |
| **Page « Annoncer »** | publiée (page 995, 200) ; son texte est prêt dans `PAGE_PUBLICITE.md`. Le contenu en base est vide : la mise en page vit probablement dans le constructeur (non vérifié) | `/annoncer/` |

Grille actuelle (palier « amorçage », < 3 000 visites/mois) : leaderboard 60 €, pavé 45 €, bandeau
bas 55 €, habillage 150 €, gouttières 70 € chacune. Estimation raisonnée, aucun prix de marché
vérifié (le document le dit).

## 2. Prévu, jamais construit

Le kit annonceurs nomme deux formats « qui ne sont pas de la pub display » :

- **Mise en avant d'un événement partenaire** : champ « sponsorisé » sur la fiche, épinglée en
  position 1 avec un badge « Partenaire ». C'est exactement l'idée de Franck du 02/10 ; la
  maquette existe désormais sur `/test-accueil-b/` (une encadrée, bandeau « Partenaire »).
- **Article partenaire** : vrai article signalé « Contenu partenaire ».

Et deux hors site : **newsletter** (emplacement 560×240) et **réseaux sociaux** (specs seulement).

## 3. Nouvelles pistes (02/10), tirées des maquettes et de GuidaTorino

GuidaTorino vit de : publireportages, mises en avant payantes de lieux et d'organisateurs,
newsletter sponsorisée, AdSense, affiliation billetterie (`MARKETING_ET_PILOTAGE`, § 1).

| Offre | Pour qui | Pourquoi ça se vend | Garde-fou |
|---|---|---|---|
| **Une partenaire** (la grande fiche de « À la une ») | organisateur d'un gros événement | l'emplacement le plus vu après le haut de page | au plus 2 jours par semaine ; bandeau « Partenaire » ; `rel="sponsored"` |
| **Territoire / ville à l'honneur** (bloc de 3 rendez-vous co-signé, une semaine) | office de tourisme | il achète sa destination, pas un concert : c'est son métier | 1 par semaine ; 3 vraies photos fournies |
| **Diapositive du carnet** (haut de page) | office de tourisme, festival | grande photo, notre cartouche | 1 sur 5 au plus |
| **Badge dans les listes** (« Ce week-end », catégories) | petit organisateur | prix d'entrée bas, à l'unité | 1 par liste |
| **Newsletter du vendredi** | tous | arrive chez des abonnés ; souvent le plus rentable | 1 encart par envoi |
| **Pack lancement** (une + newsletter + badge, une semaine) | premiers clients | plus simple à vendre qu'une liste de formats | prix d'appel, borné dans le temps |
| **Affiliation billetterie** | — | revenu sans client à démarcher | à vérifier : programmes d'affiliation des billetteries du périmètre |

## 4. Ce qui manque avant de vendre (dans l'ordre)

1. **Mesurer.** Le back-office compte les clics des campagnes display. Rien ne compte encore
   les **affichages** ni les clics des mises en avant éditoriales : sans ces deux chiffres,
   pas de bilan client ni de prix défendable.
2. **Marquer une fiche « partenaire »** avec des dates de début et de fin. Le bouton de
   mise en avant forcée existe : il faut l'étendre (motif « partenaire », période, mention
   affichée) plutôt que créer un second mécanisme.
3. **La mention « Partenaire »** affichée automatiquement partout où la fiche apparaît, plus
   `rel="sponsored"` (charte § 7 : publicité identifiable).
4. **Une grille pour ces nouveaux formats**, sur la même méthode que celle du 05/08 (trafic
   réel, paliers), et la page « Annoncer » qui la renvoie vers le formulaire.
5. **Arbitrages de Franck** : fréquence maximale des unes payantes ; refuser ou non un
   partenaire dont l'événement sort de la charte (hors périmètre, public B2B) — la réponse
   proposée est non, le paiement n'ouvre pas le périmètre.
