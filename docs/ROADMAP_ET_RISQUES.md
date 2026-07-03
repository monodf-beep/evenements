# Agenda Sabaudo — Reste à faire, risques & challenge

*État au 02/07/2026. Document critique : ce qui reste, ce qui cloche, ce qui manque, et la
question de priorité à trancher.*

---

## 0. Le challenge principal (à lire en premier)

**On polit le SEO du petit site pendant que le gros n'existe pas.**
Tout l'effort SEO récent (expression clé, méta, Open Graph, catégories…) s'applique à **Cultura
Sabauda** — le média curé, **faible volume** (score ≥ 7). Or le vrai gisement SEO/GEO, c'est
**Agenda Sabaudo**, le site de **volume** — et il **n'existe pas encore** (ni domaine, ni
WordPress, ni pages). On a des dizaines de pages de specs excellentes, **zéro ligne de site**.

→ **Décision à prendre** : est-ce qu'on continue à peaufiner l'export Cultura Sabauda, ou on
**démarre la construction d'Agenda Sabaudo** (le vrai chantier) ? Ma reco : figer l'export CS
« assez bon », et **attaquer le site de volume**.

**Risque SEO majeur, sous-estimé : le contenu dupliqué.** Si un même événement part à la fois
sur Cultura Sabauda ET sur Agenda Sabaudo, Google voit **deux pages quasi identiques** → pénalité
possible. Il FAUT une règle de canonical / de séparation éditoriale entre les deux sites **avant**
de lancer le volume. Ce n'est écrit nulle part pour l'instant.

---

## 1. Ce qui est FAIT (rappel)

- **Filtres de qualité des données** : périmètre (2 gardes), hors-zone déterministe, rejet des
  événements passés, filtre par type de source, tri qualité, onglet Actifs, vocabulaire unifié.
- **SEO backoffice** : JSON-LD Event (gratuit) + agent « ✨ Optimiser SEO » (titre, méta,
  expression clé, slug, étiquettes, réponse directe, FAQ), visible au dashboard.
- **Export WordPress (Cultura Sabauda)** : catégorie, étiquettes, méta Yoast, aperçu Open
  Graph/Twitter, extrait, slug, alt+crédit image ; mu-plugin `cs-seo-meta.php` ; correctif de
  sécurité (pas d'exposition du scoring interne ni de la source radar).
- **Lisibilité article** : `enrich.py` produit des sous-titres H2 + phrases courtes.
- **Dossier « site public »** (specs, vérifiées sur GuidaTorino) : brief design, plan du site,
  textes FR/IT, règles SEO/GEO/AEO, guide d'indexation, spec agent SEO, taxonomie WordPress.

---

## 2. Ce qui CLOCHE (bugs / gaps à corriger)

| # | Problème | Impact | Priorité |
|---|---|---|---|
| 1 | **« Publier CS » crée un NOUVEAU brouillon à chaque clic** (pas de mise à jour du `wp_post_id_cs` existant) | Doublons de brouillons WordPress | Haute |
| 2 | **L'expression clé n'est pas dans le corps de l'article** : l'article est rédigé AVANT que le SEO génère l'expression clé → Yoast « clé dans l'intro / densité » reste rouge | SEO on-page incomplet | Haute |
| 3 | **Aucun lien interne injecté dans le corps** (Yoast « aucun lien interne ») : pour CS on ne connaît pas ses URLs de catégorie/archives | Maillage nul | Moyenne (dépend recon CS) |
| 4 | **Catégories créées sur CS** : l'export crée « Concerts & Musique »… mais CS a peut-être sa propre taxonomie éditoriale → risque de **doublons/pollution** | Taxonomie CS salie | Haute (avant d'exporter en masse) |
| 5 | **Pas de sauvegarde de `data/events.db`** (gitignorée, sur le VPS) : si le VPS meurt, **toute la base est perdue** | Perte de données | Haute |
| 6 | **JSON-LD Event sur des articles CS** : CS est un média éditorial, pas un agenda — le schema Event y est un peu hors-sujet (acceptable mais à assumer) | Cohérence | Basse |

---

## 3. Ce qui MANQUE (jamais commencé)

### 3.1 Le site Agenda Sabaudo (le gros chantier)
- [ ] **Réserver le domaine** `agendasabaudo.eu` (n'existe pas).
- [ ] **Créer le WordPress** + choisir le plugin (**décision TEC vs Events Manager**).
- [ ] **Enregistrer les taxonomies** : `territoire` (4 > villes), catégorie (11), lieu, étiquettes.
- [ ] **Gabarits** : home (6 tuiles, En évidence, tour des territoires), hubs temporels evergreen,
      territoire, catégorie, **fiche (mode minimal d'abord)**, listicle, recherche, 404.
- [ ] **Bilinguisme FR/IT** (Polylang/WPML + hreflang).
- [ ] **Export backoffice → Agenda Sabaudo** (aujourd'hui on n'exporte QUE vers CS).
- [ ] **Design** (en cours de ton côté, Claude Design).

### 3.2 SEO / indexation (infra du futur site)
- [ ] Sitemaps propres + soumission Search Console (les 2 sites).
- [ ] **IndexNow** (RankMath) activé.
- [ ] hreflang FR/IT.
- [ ] **Règle anti-duplication CS ↔ Agenda Sabaudo** (canonical) — cf. §0.
- [ ] Analytics (GA4 ou Matomo) — **rien n'est mesuré aujourd'hui**.
- [ ] Backlinks locaux (offices de tourisme, presse) — le vrai levier des 6-18 mois.

### 3.3 Pages & conformité
- [ ] **Mentions légales, RGPD/cookies, politique crédits photos** (proposées, jamais rédigées).
- [ ] Page « Proposer un événement » (machine à contenu).

### 3.4 Backoffice — améliorations en attente
- [ ] Corriger le doublon « Publier CS » (mettre à jour si `wp_post_id_cs` existe).
- [ ] **Chaîner expression clé → article** (générer la clé AVANT ou réinjecter dans l'intro).
- [ ] **Injecter les liens internes** dans le corps (une fois les URLs cibles connues).
- [ ] Fiche éditable (corriger lieu/date/catégorie à la main).
- [ ] Écran « doublons » (dédup visible).
- [ ] Recalibrer le **seuil ≥ 7** (tu voulais un brief à la demande).

### 3.5 Données & opérationnel
- [ ] **Lancer le pipeline** avec les nouveaux filtres (purge hors-zone + passés, datation,
      évaluation) — beaucoup de code poussé **pas encore vérifié en prod**.
- [ ] Finir les **~40 newsletters** à inscrire.
- [ ] **Autoriser Brevo** (le connecteur MCP n'est pas authentifié) pour la newsletter.
- [ ] Sauvegarde régulière de `data/events.db`.

---

## 4. Ce qu'il faut VÉRIFIER (incertitudes)

- **Le déploiement a-t-il été fait ?** Beaucoup de commits (SEO, filtres, UX) attendent peut-être
  encore `bash deploy/update.sh`. À confirmer que la prod tourne bien le dernier code.
- **La reconnaissance de Cultura Sabauda** (catégories réelles, articles liés) : nécessaire pour
  régler le mapping de catégories (#4) et le maillage (#3).
- **Le pipeline complet** tourne-t-il sans erreur bout en bout depuis les derniers changements ?

---

## 5. Ordre recommandé (ma proposition)

1. **Trancher le §0** : figer CS, démarrer Agenda Sabaudo. Réserver le domaine.
2. **Sauvegarder la base** (rapide, évite la catastrophe).
3. **Corriger les 2 bugs backoffice** #1 (doublon Publier) et #2 (clé dans l'article).
4. **Recon Cultura Sabauda** → régler #3 et #4.
5. **Lancer le pipeline** en prod (données propres).
6. **Construire Agenda Sabaudo** (le chantier) : plugin → taxonomies → gabarits → export → SEO.
7. Legal + analytics + backlinks en parallèle.

*Le vrai message : on a une base saine et des specs solides. Le risque n'est pas la qualité,
c'est de continuer à polir le petit site au lieu d'attaquer le grand — et de lancer le volume
sans régler la duplication CS/Agenda et sans sauvegarde.*
