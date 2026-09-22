# TypeSafe / Jev — ce que c'est, et où ça sert ICI

Rapport demandé par Franck le 2026-09-22 : « comprendre la documentation de cet outil,
chercher les cas d'usage, dire sur quoi on peut le mettre pour être plus performant et
moins cher ».

**Statut des chiffres de ce document.** Tout ce qui vient de `typesafe.ai` est **annoncé
par l'éditeur**, pas mesuré par nous. Tout ce qui décrit le dépôt est **lu dans le code**.
Les coûts comparés sont des **estimations avec hypothèses écrites** — le conteneur de
session n'a ni `data/events.db` ni `logs/api_usage.jsonl`, donc **aucun coût réel n'a été
mesuré pour ce rapport** (règle 6 : le périmètre à côté du nombre).

---

## 1. Ce que c'est, en une phrase

Jev n'est pas un LLM. C'est un modèle qui **ne sait pas écrire** : on lui donne un état
(du texte, ou du JSON) et des **questions typées**, il rend des **valeurs** — jamais une
phrase.

Trois primitives, et trois seulement :

| Primitive  | La question                          | Ce qu'on récupère                     |
|------------|--------------------------------------|---------------------------------------|
| **Noul**   | « est-ce vrai ? »                    | une probabilité entre 0 et 1          |
| **Choice** | « laquelle de ces options ? »        | l'option + la distribution + confiance |
| **Score**  | « à quel niveau, sur cette grille ? » | le niveau + la distribution + confiance |

Limites de forme : **255 options** par Choice, **10 niveaux** par Score, **64k jetons** de
contexte par requête (dont 32k pour l'état + la plus longue question). Plusieurs questions
partent dans **un seul appel** et sont évaluées **en parallèle** sur le même état — c'est
le motif « fan-out », et c'est là qu'est le gain.

Un seul modèle existe aujourd'hui : `jev-1.13.0` (alias `jev-latest`). Endpoint
`POST https://api.typesafe.ai/v1/systemone`, SDK Python `typesafe-sdk`.

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()
response = client.system_one(
    state=texte_de_la_fiche,
    questions={
        "categorie": Choice(instructions="…", criteria={"Concerts & Musique": "…", …}),
        "interet":   Score(instructions="…", criteria=["…", "…", "…"]),
        "hors_perimetre": Noul(instructions="L'événement se déroule hors de nos 4 territoires"),
    },
)
response.answers["categorie"].choice        # la valeur
response.answers["categorie"].confidence    # la confiance, calibrée
response.answers["hors_perimetre"].noul     # 0.0 – 1.0
```

**Tarif annoncé : 42 $ le MILLIARD de jetons d'entrée, sortie gratuite** — soit
0,042 $ / million. Sonnet est à 3 $ / million en entrée et 15 $ en sortie
(`utils/usage.py`). Le rapport de prix brut est donc de l'ordre de **70× en entrée, et
l'infini en sortie**.

Débit annoncé : 250 000 jetons/seconde, 1 200 requêtes/minute, 70 à 500 ms par appel.

---

## 2. Ce qu'il ne sait PAS faire — à lire en premier

C'est la moitié utile du sujet, parce qu'elle élimine d'un coup **le gros de notre
facture**.

- **Il ne génère aucun texte.** Donc : `enrich.py` (rédaction), `translate_events.py`
  (traduction FR↔IT), `seo_batch.py` (titre, méta, FAQ), `social_caption`,
  `textes_hubs.py`, `conform_articles.py` — **aucun n'est remplaçable**. Or ce sont très
  probablement nos postes les plus chers (`scripts/audit_couts.py` le dira).
- **Il n'est pas multimodal.** Aucune mention d'image dans la référence API. Donc
  `utils/image_verify.py`, `scripts/image_audit.py`, `images_web.py` — **hors sujet**.
- **Il ne cherche pas sur le web.** Donc `site_officiel_recherche`, `dates_web.py`,
  `venues_web.py`, `image_web_search` — **hors sujet**.
- **Il n'est pas une calculatrice**, et la page des limites connues de Jev 1.13 range
  explicitement les **comparaisons de dates et d'heures** parmi ses neuf points faibles.
  C'est gênant : il existe un cookbook « date extraction », mais l'éditeur lui-même
  prévient sur le raisonnement temporel. `scripts/dates.py` n'est donc **pas** un candidat
  de confiance, malgré les apparences.
- Autres faiblesses annoncées : lecture trop littérale des consignes, raisonnement à
  plusieurs niveaux (indirection), **perte d'exactitude quand le contexte est long et
  bruité**, sensibilité aux injections, et confusion quand les instructions contredisent
  les critères.

Ce dernier point vise directement notre évaluateur : `EVAL_PROMPT` fait **9 345
caractères (~2 670 jetons)** et enchaîne les exceptions (« piège presse », « piège
cinéma », « ne juge pas sur le mot du titre »). Tel quel, il ne se recopie pas dans Jev —
il se **découpe**.

---

## 3. Le trou de ce rapport : trois mesures qui manquent

Aucune décision ne devrait être prise avant celles-ci.

1. **Où part vraiment l'argent.** Sur le VPS :
   `.venv/bin/python -m scripts.audit_couts --jours 30`
   Tant qu'on ne l'a pas, « moins cher » est une intention, pas un résultat. Il se peut
   que l'évaluateur pèse 3 % de la facture et que tout ce rapport porte sur du vent.
2. **Est-ce que Jev parle français et italien ?** **La documentation n'en dit RIEN** — ni
   la page des limites, ni le billet de lancement, ni la référence API. Nos fiches sont
   intégralement FR et IT. C'est le risque n°1, et il se teste en une demi-heure sur
   cinquante fiches déjà évaluées.
3. **Est-ce qu'il est d'accord avec nous ?** Le seul test qui compte : rejouer Jev sur des
   fiches dont l'évaluation Claude a été **validée ou corrigée par Franck**, et compter les
   désaccords. Avec, comme l'exige la règle 3 du CLAUDE.md, **des cas qui doivent PASSER,
   choisis près de la frontière** : un salon du livre, un café philo, une conférence de
   musée — ceux que le prompt actuel protège explicitement contre un filtre bête.

---

## 4. Les candidats, du plus solide au plus douteux

### A. `scripts/evaluator.py` — le meilleur candidat, de loin

C'est exactement la forme que Jev attend. L'évaluateur pose aujourd'hui, en un appel LLM
par fiche et en JSON, six questions qui sont **toutes** des primitives :

| Ce qu'il demande aujourd'hui | Primitive Jev | Cardinalité |
|------------------------------|---------------|-------------|
| `hors_perimetre`             | Noul          | —           |
| `est_evenement`              | Noul          | —           |
| `public_vise`                | Choice        | 2           |
| `categorie`                  | Choice        | 11          |
| `territoire`                 | Choice        | 4           |
| `score` éditorial 0–10       | Score         | 10 niveaux (le maximum) |

Tout passe **dans un seul appel**, en parallèle. Et les « pièges » du prompt actuel
deviennent des nouls séparés, ce que la doc appelle la décomposition et que nous avons
appris à nos dépens : `utils/eventness.py` existe précisément parce que « le LLM
d'évaluation s'accroche au gros mot-clé (Tour de France) et les note haut à tort ».
Découpé en nouls atomiques — « c'est un article SUR l'événement », « c'est de la
logistique », « c'est un compte rendu », « c'est une séance de cinéma ordinaire » — chaque
jugement devient inspectable un par un, au lieu d'être noyé dans 2 670 jetons de consignes.

**Le bénéfice n'est pas d'abord le prix, c'est la confiance calibrée.** Aujourd'hui
l'évaluateur rend un score sec et le pipeline le croit. Avec une confiance, on peut router :
haute confiance → automatique, zone grise → Claude en second avis, très incertain → file
humaine. C'est le motif « confidence-gated routing » de la doc, et c'est le seul mécanisme
de ce rapport qui améliore la **qualité** et pas seulement la facture.

### B. Les détecteurs à expressions régulières — le gain le plus sûr

Le dépôt en est plein, et le CLAUDE.md documente noir sur blanc qu'ils se trompent :

- `utils/temps_recit.py` — prenait « est présenté » (présent passif) pour un passé et lisait
  « à ciel ouvert » comme l'auxiliaire *avoir* ;
- `utils/eventness.py` — liste de motifs « volontairement étroits », qui renvoie `None` dès
  qu'il doute, donc qui laisse passer tout ce qui n'est pas dans la liste ;
- `utils/triage.py` — classe une fiche bloquée sur des indices de mots-clés
  (`RECURRING_HINTS` : « toute l'année », « sur réservation »…) ;
- `utils/acronymes.py`, `utils/lisibilite.py`, `utils/coherence.py`, même famille.

Ces modules ont été écrits en déterministe pour une bonne raison : **ils sont gratuits et
ils tournent sur tout**. Un LLM à cet endroit coûterait trop cher pour le service rendu.
Jev change ce calcul : à 0,042 $ le million de jetons d'entrée, poser un noul sur chaque
fiche coûte moins que rien, et un noul comprend « est présenté » là où une regex échoue.

C'est le remplacement le plus tranquille du lot : ces détecteurs **signalent**, ils ne
publient ni ne suppriment. Une erreur y coûte une ligne de rapport, pas une fiche en ligne.

### C. Le tri des files d'audit — la réponse technique à « 548 tâches ! »

Le CLAUDE.md raconte la matinée du 11/08 : trois compteurs gonflés, et sur « 454 points à
contrôler », **315 n'étaient pas des faits douteux mais des informations que la source ne
publie pas**. La règle qui en est sortie : « avant d'ajouter une ligne à une file, se
demander ce que le lecteur en FERA ».

Cette question est un noul, et rien d'autre :

> « Ce point peut-il être vérifié par une personne qui n'a que la page source sous les
> yeux ? »

Posée sur chaque ligne avant affichage, à coût négligeable, elle vide la file de son bruit
et remonte le seul point qui comptait ce jour-là. Même chose pour `utils/site_issues.py`,
les `audit_*.py` qui alimentent Slack, et le panneau du back-office.

### D. `scripts/dedupe.py` — probable, à vérifier

TypeSafe publie un cookbook « entity alignment » (450 paires de produits) qui est
exactement notre problème : deux fiches désignent-elles le même événement ? Un noul par
paire candidate, avec confiance, remplacerait ou doublerait le dédoublonnage actuel. À
tester — mais avec prudence, parce que **une mauvaise fusion corrompt une date** (WP#6798),
donc ce n'est pas un endroit où l'on se trompe gratuitement.

### E. Le panel de relecture — partiel seulement

`panel_lecteur` et `panel_site` coûtent cher (3–4 personas par fiche, ×2 si révision). La
partie **note** se traduit en Score ; la partie **remarque rédigée** ne se traduit pas du
tout. On peut imaginer Jev en pré-filtre — ne convoquer le panel Claude que sur les fiches
dont le Score est bas ou la confiance faible — mais on perd les personas là où ils servent.
À discuter, pas à trancher ici.

### F. Ce qui ne bouge pas

`scripts/perimetre.py` lit `config/communes_comte_de_nice.json` : c'est une liste qui fait
foi, donc du code, et ça doit le rester. La doc de TypeSafe dit la même chose —
« garder le flux de contrôle et les règles déterministes dans le code ».

---

## 5. Le prix, avec les hypothèses écrites

**Hypothèses** (à corriger dès qu'`audit_couts` aura parlé) : fiche ~600 jetons, sortie
JSON ~150 jetons, Sonnet à 3 $/15 $ le million, questions Jev ~500 jetons de critères.
`scripts/evaluator.py:213` **met déjà son prompt système en cache** (relecture à 0,1×) —
la comparaison honnête se fait donc contre le prix *avec* cache, pas contre le plein tarif.

| Pour 1 000 fiches évaluées | Entrée | Sortie | Coût |
|---|---|---|---|
| Sonnet, sans cache | 3 270 k jetons | 150 k | **≈ 12,10 $** |
| Sonnet, avec cache (l'état actuel) | idem, système à 0,1× | 150 k | **≈ 4,90 $** |
| Jev | 1 100 k jetons | gratuite | **≈ 0,05 $** |

Soit **environ 100× moins cher que ce qu'on paie aujourd'hui** sur ce poste précis — pas
les 445× de la page d'accueil, qui se comparent à un LLM non caché et dont le billet de
lancement de TypeSafe reconnaît lui-même qu'ils sont « probably on the higher end of real
world gains ».

**Ce que ça représente en euros par mois : inconnu**, faute de connaître le volume
quotidien de fiches évaluées. `audit_couts` le donne.

---

## 6. Ce que Jev ne règle PAS chez nous

À dire tout de suite, pour qu'on ne le découvre pas dans trois semaines.

- **Il ne rouvre aucun cul-de-sac** (règle 3). Un portillon Jev posé sur la même entrée
  rendra la même réponse demain — c'est même *plus* vrai qu'avec un LLM, puisqu'il est
  conçu pour être reproductible. La bonne nouvelle : la confiance donne enfin un **seuil
  réglable** et un **chiffre à afficher**, là où une regex ne donnait qu'un booléen muet.
  Mais la question « qui sort la fiche de cette file » reste entière.
  → **À nuancer** : le cookbook *self-consistency* décrit une **bande d'incertitude**
  (0,30–0,70) qui constitue une file nommée, bornée et dénombrable, avec un propriétaire
  désigné d'avance. Voir `docs/TYPESAFE_JEV_NOEUDS.md` § 4.
- **Il ne dispense d'aucune fixture.** Un détecteur Jev se valide exactement comme les
  autres : sur des données réelles, en LISANT ce qu'il refuse, avec un cas qui doit passer
  près de la frontière.
- **Il ajoute une dépendance et une clé de plus**, donc un mode de panne de plus. Prévoir
  le repli : si l'appel Jev échoue, on retombe sur le chemin actuel, jamais sur un rejet.
- **Il ne connaît rien à notre périmètre.** Toute la matière — les 62 communes de Grasse,
  les quatre territoires, les onze catégories — doit voyager dans les `criteria` de chaque
  question, et la doc prévient que trop de contexte non pertinent dégrade l'exactitude.

---

## 7. Ce que je propose, dans l'ordre

1. **Mesurer d'abord** : `audit_couts --jours 30` sur le VPS. Si l'évaluation ne pèse
   rien, ce rapport se referme ici et on va voir ailleurs.
2. **Une clé d'essai et un banc de test hors ligne** : rejouer Jev sur 100 à 200 fiches
   déjà évaluées, sans rien écrire en base, et sortir la matrice de désaccord avec
   l'évaluation actuelle — dont les fiches corrigées à la main par Franck. **C'est ce test
   qui répond à la question du français et de l'italien**, et lui seul.
3. **Si le banc est bon**, commencer par la famille B (les détecteurs à regex) : c'est là
   que le risque est le plus faible et le bénéfice de justesse le plus net.
4. **Puis l'évaluateur**, en double lecture pendant deux semaines : Jev décide, Claude
   contrôle un échantillon, on compare, et on ne débranche Claude que sur des chiffres.
5. **La file d'audit (C) à tout moment** — elle ne touche pas au site.

Note utile : TypeSafe publie une page « agent skill » (`docs.typesafe.ai/agent-skill.md`)
prévue pour Claude Code. Si on va au-delà de l'essai, elle évitera de réécrire les
conventions d'appel à la main.

---

**Suite de ce rapport** : `docs/TYPESAFE_JEV_NOEUDS.md` passe la chaîne nœud par nœud et
traite la question de la **complétion** — c'est là qu'est le gain le plus net.

## Sources

- <https://typesafe.ai/> · <https://typesafe.ai/blog/introducing-system-one-models-and-jev>
- <https://docs.typesafe.ai/> · index complet : <https://docs.typesafe.ai/llms.txt>
- Limites connues : <https://docs.typesafe.ai/model-jaggedness/jev-1.13.md>
- Méthode : <https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md>
- Tarifs et quotas : <https://docs.typesafe.ai/models.md> · API : <https://docs.typesafe.ai/api.md>
- Cookbooks cités : `entity_alignment`, `date_extraction_cookbook`, `parallel_questions`,
  `classification_using_confidence`, `llm_guardrails`
