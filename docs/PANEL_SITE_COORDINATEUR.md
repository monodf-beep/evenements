# Panel des personas sur le SITE, et le coordinateur qui les filtre

**Proposition du 2026-08-05.** Demande de Franck (en balade, répondant à ma question
« pourquoi tu ne fais pas en sorte que ça corrige tout seul ? ») : faire lire le SITE par
le panel de personas, pas seulement chaque article — avec un coordinateur qui filtre
leurs retours avant de les transmettre, pour qu'une critique qui contredit un choix
DÉLIBÉRÉ ne remonte pas comme un bug.

**Construit le même jour, une fois « home + 4 pages territoire » validé.** Voir
`config/doctrine_affichage.md`, `utils/doctrine.py`, `scripts/panel_site.py`. Tout ce qui
NE dépend PAS d'un appel LLM est testé (`tests/test_panel_site.py`, 13/13) : le
chargement/matching de la doctrine, la récupération des VRAIES pages du site (aucune clé
API nécessaire — juste HTTP), la construction du prompt, et le coordinateur au complet
sur des trouvailles reconstruites à la main. **Ce qui manque encore : un vrai passage,
crédit API rétabli** — la lecture par les personas eux-mêmes est un appel LLM, rien ne
prouve encore que le panel juge bien un VRAI persona sur une VRAIE page tant que la
chaîne n'a pas tourné une fois pour de vrai.

⚠️ **Précision honnête** : seul le périmètre des pages (« home + 4 territoires ») a été
explicitement validé par Franck le 2026-08-05. Le SEUIL d'accord codé dans
`coordonner()` (2 personas indépendants minimum, même page × même type) est ma
proposition initiale appliquée par défaut, PAS une décision confirmée — l'exception
« un persona LOCAL compte seul sur sa propre aire » n'est pas codée. ⚖️ Toujours ouvert :
valider ou ajuster ce seuil, l'exception locale, le contenu de la doctrine au-delà du
prix, et la destination du rapport (Slack séparé ou section de `weekly_audits` —
actuellement le script n'est branché NULLE PART en cron, volontairement : il coûte du
LLM, à activer seulement une fois le crédit revenu et le seuil validé).

## Ce qui existe déjà, et ce qui manque

Le panel de personas (`docs/personas/`, `utils/personas.py`) existe et tourne — mais il
relit un **article après rédaction**, jamais le **site tel qu'il se présente**. Il juge
« cet article me parle-t-il, à moi ? », jamais « cette page d'accueil, cette section,
raconte-t-elle quelque chose qui tient debout ? ». C'est un usage différent du même
panel, pas un nouveau panel — les 8 personas, leurs aires, leur mémoire éditoriale
restent les mêmes.

## L'exemple de Franck, et pourquoi il est le bon exemple

« Il ne faut pas qu'un persona dise "il n'y a pas le prix" — c'est décidé qu'il n'y en
ait pas, juste gratuit/payant. » C'est exactement le bon cas d'école, parce que la
raison pour laquelle ce risque existe est visible dans le dépôt : **cette décision n'est
écrite nulle part.** `docs/CHARTE_EDITORIALE.md` documente ce qu'un article doit
CONTENIR (tarif inclus, §5) ; aucun fichier ne documente ce qu'une CARTE ou une page
d'accueil doit délibérément TAIRE. Un persona qui compare ce qu'il voit à rien ne peut
que comparer à son intuition — et son intuition dit « un prix manque ».

## Le principe : GROUNDING, comme pour toutes les gardes de ce dépôt

Chaque garde-fou qui a tenu, cette session, tient parce qu'il compare à un **fichier
écrit** : `config/excluded_event_keywords.txt` pour les exclusions éditoriales,
`config/communes_comte_de_nice.json` pour le périmètre, `docs/ETATS_TERMINAUX.md` pour
les questions à se poser avant un état terminal. Rien ne dit qu'un panel de lecture
échapperait à la règle — la documentation de recherche récente sur les architectures
critique/coordinateur dit la même chose sous un autre nom : un « juge » ancré sur une
référence écrite fait moins de faux positifs qu'un jugement à l'intuition seule
(*« grounding the critic […] eliminates false positives »* — voir sources en bas de
page). Le manque n'est donc pas un manque de coordinateur, c'est d'abord un manque de
**doctrine écrite** — le coordinateur vient ensuite, pour ce qu'une doctrine ne peut pas
couvrir à l'avance.

**Proposition concrète : `config/doctrine_affichage.md`.** Même mécanique que le fichier
d'exclusions — une liste courte, en langage courant, que Franck édite librement, sans
toucher au code. Premier point : « pas de prix chiffré affiché nulle part sur le site,
seulement un badge gratuit/payant — décision du [date]. » D'autres viendront au fil des
retours du panel (c'est lui-même qui, en se trompant une fois, désigne ce qu'il faut y
ajouter).

## Le mécanisme en trois étages

**1. Les personas lisent le SITE**, pas un brouillon. Nouveau prompt (même personas,
nouvel usage) : « voici la page d'accueil / la section [Territoire] telle qu'elle se
présente aujourd'hui — qu'est-ce qui te manque, qu'est-ce qui te semble en trop,
qu'est-ce qui n'a rien à faire là ? » Chaque persona répond avec SA sensibilité propre
(Kévin, ouvrier de vallée, ne réagit pas comme Chantal, fonctionnaire bilingue) — c'est
la richesse du panel, pas un bruit à uniformiser. Sortie structurée : type de trouvaille
(manque / excès / hors-lieu / hors-saison / info manquante), la section concernée, et
une justification en une phrase. La doctrine (`doctrine_affichage.md`) est injectée dans
LEUR prompt aussi — premier filtre, gratuit, avant même le coordinateur : mieux vaut ne
pas générer une fausse critique que la filtrer après coup.

**2. Le coordinateur reçoit toutes les trouvailles, et fait ce qu'aucun persona seul ne
peut faire :**
- **Revérifie contre la doctrine** — un filet de sécurité, pour le cas où un persona
  l'aurait quand même ignorée (un LLM peut dériver d'un prompt) ;
- **Regroupe les trouvailles qui se recoupent** — si 3 personas indépendamment signalent
  qu'un même événement de Noël traîne en plein été, c'est un signal plus fort qu'un avis
  isolé (même principe que la vérification adversariale utilisée pour les audits de ce
  dépôt : plusieurs voix indépendantes qui convergent pèsent plus qu'une seule) ;
- **Route chaque trouvaille SURVIVANTE vers sa destination**, sans jamais agir
  lui-même :
  - « il manque le lieu / la date » → ce n'est pas un scoop, c'est déjà suivi par
    `scripts/slack_learning.py` (ce document même) — le coordinateur ne fait que
    CORROBORER un signal qui existe déjà, avec un humain en plus qui l'a remarqué ;
  - « un événement de Noël visible en été » → directement la question ouverte de
    `docs/TEMPS_FORTS.md`, pas un bug à corriger au coup par coup ;
  - « trop d'événements du même type » ou « cet événement n'a rien à faire là » →
    aucun mécanisme existant ne les couvre : DÉSIGNATION SEULE, pour un humain ;
  - une critique qui contredit la doctrine → **rejetée**, jamais transmise, mais gardée
    dans un journal (pour repérer si UN MÊME point revient souvent malgré la doctrine —
    ça peut vouloir dire que la doctrine elle-même mérite d'être réexaminée, pas
    seulement rappelée aux personas).

**3. Un rapport, jamais une action.** Comme tous les audits de ce dépôt (règle : détecter
et désigner, jamais corriger tout seul sans jugement — Franck, 2026-08-04). Le
coordinateur alimente un digest lisible, pas une file de tickets à traiter en urgence.

## Ce que ça coûte, et pourquoi ce n'est pas quotidien

Contrairement aux audits déterministes de ce dépôt (gratuits, tournent chaque jour),
faire LIRE le site par un panel de personas est un usage LLM — donc suspendu tant que le
crédit API est vide, et coûteux même une fois rétabli si c'est quotidien. Proposition :
hebdomadaire, le même jour que la revue adversariale (dimanche), pas plus.

## Pourquoi je n'ai pas fait « ça corrige tout seul » — la question posée directement

Deux réponses, pas une esquive :

1. **Pour les manques déjà connus (Lieu, Ville, Image), la correction automatique EXISTE
   déjà et tourne chaque jour** — `scripts/autocomplete.py` retente. En construisant
   `slack_learning.py` aujourd'hui, j'ai vérifié le cas de l'Image précisément pour
   voir s'il restait un geste mécanique à automatiser : non — la bannière de repli est
   déjà retentée automatiquement chaque jour ; ce qui reste, une fois épuisé, est soit
   l'absence d'une image dans un fichier de configuration (un geste éditorial : choisir
   une image), soit une source qui ne publie structurellement pas cette donnée (garder
   la source ainsi, la corriger à la main, ou l'écarter). Aucune des deux n'est un
   geste mécanique — les deux sont des décisions.
2. **Pour les trouvailles du panel de personas, la nature même du signal est un
   jugement.** « Cet événement n'a rien à faire là » ou « il manque un événement de ce
   genre » ne se corrige pas par une commande : la première suppose de RETIRER quelque
   chose de publié (irréversible sans arbitrage), la seconde suppose d'aller EN
   CHERCHER un nouveau (pas une correction, une action éditoriale). La règle du dépôt
   (réversible = seul, irréversible = jamais, et « pas d'automatique sans réfléchir »)
   n'est pas de la prudence par principe : c'est que la commande qui « corrigerait »
   n'existe pas encore, parce que personne n'a encore décidé LAQUELLE.

Le fil conducteur : l'endroit où « corriger tout seul » a un sens, c'est déjà automatisé
(retenter, ressurfacer, republier). Ce qui reste à désigner, c'est précisément ce
qu'aucune commande ne sait faire sans un choix humain d'abord.

## ⚖️ Décisions

- **✅ Quelles pages le panel lit-il ?** Tranché le 2026-08-05 : la page d'accueil + les
  4 pages territoire (`scripts/panel_site.py:PAGES`, URLs vérifiées sur le site réel).
- **Le premier contenu de `config/doctrine_affichage.md`** : le prix (cité par Franck),
  seule entrée pour l'instant. Y a-t-il d'autres choix délibérés à y consigner tout de
  suite plutôt que de les découvrir un par un via de fausses alertes ? Toujours ouvert.
- **Le seuil d'accord** — codé par défaut à 2 personas indépendants minimum (même page ×
  même type), PAS confirmé par Franck. L'exception « un persona LOCAL du territoire
  concerné compte seul » (proposée à l'origine, comme pour la note de déplacement)
  N'EST PAS codée — à trancher, puis à implémenter si retenue.
- **Où atterrit le rapport** — un digest Slack séparé, ou une section de plus dans
  `weekly_audits` ? Toujours ouvert : `scripts/panel_site.py` n'est branché dans AUCUN
  cron pour l'instant (coût LLM, à activer une fois le crédit revenu et ce point tranché).

## Sources (recherche du 2026-08-05, bonnes pratiques multi-agents)

- [LLM-as-Judge in Production: Agent Reasoning Verification, Self-Correction, and
  Hallucination Defense](https://zylos.ai/research/2026-04-10-llm-as-judge-production-agent-verification-2026/)
  — le grounding sur une référence écrite réduit les faux positifs d'un juge LLM.
- [LLM-as-Judge Patterns for Agent Evaluation: Calibration, Bias, and Trajectory
  Assessment](https://zylos.ai/research/2026-05-26-llm-as-judge-agent-evaluation-patterns/)
- [Multi-Agent Orchestration: 5 Patterns That Work in
  2026](https://www.digitalapplied.com/blog/multi-agent-orchestration-5-patterns-that-work)
  — le patron « spécialistes + coordinateur qui agrège » est celui retenu ici.
- [When Helping Hurts and How to Fix It: Multi-Agent Debate for Data
  Cleaning](https://arxiv.org/html/2606.02866) — grounder le critique dans des preuves
  concrètes (pas une impression) diminue les faux signaux ; principe transposé à la
  doctrine écrite ci-dessus.
