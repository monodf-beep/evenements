# À reprendre — session du 24-25/09/2026

Liste laissée à la fermeture de la session (Franck, 28/09). Ce qui suit n'est PAS fait.
Rayer une ligne quand elle l'est, avec la date et la mesure qui le prouve.

## Déploiement

- [x] **Fait le 29/09** : déployé en 30f7877 (« ✅ Déploiement terminé »), fusion comprise.
  Au passage, le VPS portait `18f6c51` (redirections Terra Madre / EVO, branche
  `focused-edison`), fusionné là-bas sans avoir été poussé : désormais sur GitHub. **Reste à
  vérifier que ces redirections sont EN LIGNE** — le dépôt ne prouve pas le déploiement WordPress.
  Ancienne consigne : fusionner `claude/affectionate-turing-nj6m0w` dans `claude/quirky-davinci-jvqrnw`, puis
  `bash deploy/update.sh`. Six commits, uniquement des miroirs `deploy/wordpress/` et des
  docs : **tout est déjà en ligne sur WordPress** (déposé par Novamira, md5 vérifiés). La
  fusion ne sert qu'à ce que le dépôt du VPS ne diverge pas du site.
  `cd /root/evenements ; git fetch origin ; git merge origin/claude/affectionate-turing-nj6m0w && git push origin claude/quirky-davinci-jvqrnw && bash deploy/update.sh`
  (`CONFLICT` → `git merge --abort`, jamais de résolution sur le VPS.)

## Cowork (Search Console)

- [ ] Demander l'indexation de `https://agendasabauda.eu/it/` (nouvelle adresse de l'accueil
  IT depuis le 25/09, `/it/home-it/` y redirige en 301), de `https://agendasabauda.eu/`
  (nouveau titre) et de `https://agendasabauda.eu/plaisirs-de-culture-vallee-d-aoste/`
  (quota dépassé le 25/09).
- [ ] Obtenir la liste des 31 pages en erreur 5xx et des 19 en 404 (rapport Indexation), puis
  les corriger — redirection 301 pour les doublons, voir CLAUDE.md.

## En attente d'une décision de Franck

- [ ] Kento, fiche 8921 : la méta-description dit « 13-25 ans », l'article « moins de 25 ans ».
  Fiche GELÉE : ne pas corriger sans son accord.
- [ ] Yoast → Représentation du site : nom, logo, profils sociaux tous vides (relevé le 25/09).
  Il faut les adresses des profils et le nom à déclarer (Agenda Sabauda ou Cultura Sabauda).
  Enjeu : la requête « agenda sabauda » renvoie la Galleria Sabauda (« termes manquants : agenda »).
- [ ] Google Ad Grants : Cultura Sabauda est-elle une association éligible ? (Pas de publicité
  payante : décision de Franck du 25/09.)
- [ ] Slugs des traductions IT : 173/192 pages IT à venir finissent en « -2 » (Polylang gratuit,
  slug partagé impossible). Garder, ou donner leur slug italien aux futures traductions —
  ce serait revenir sur le choix d'août.

## Chantiers ouverts

- [ ] Accès Search Console du VPS (OAuth, « chemin A ») : `gsc_report --tendance` et le cron
  d'archivage hebdomadaire échouent faute d'identifiants.
- [ ] Journées du patrimoine : diffusion (partenaires, groupes), puis préparation des
  éditions 2027 (`docs/EDITIONS_ANNUELLES.md` : même adresse d'une année sur l'autre).
- [ ] Dictionnaire FR→IT de l'accueil (Code Snippets n° 71) : ~14 clés orphelines relevées
  dans son en-tête, qui dérivent en silence à chaque édition de la page 928.

## À mesurer

- [ ] Mi-octobre : taux de clic Search Console (5,8 % mi-août → 3,5 % fin septembre), pour
  voir l'effet des titres et descriptions posés du 24 au 25/09.

## Vérifié à la fermeture (28/09)

- La strate « moment fort » des Journées du patrimoine s'est retirée seule après le 27/09 :
  0 bloc sur l'accueil, le hub Piémont FR et le hub Vallée d'Aoste IT.
