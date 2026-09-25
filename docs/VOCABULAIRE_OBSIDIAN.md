# Vocabulaire — la règle vit dans Obsidian, plus dans ce dépôt

**Changement du 05/09/2026.** Ce fichier documentait un miroir : le vocabulaire interdit
vivait dans `config/vocabulaire_interdit.json` (la référence exécutable) ET dans une note
Obsidian (à recopier à la main). Franck, le 05/09, en reconstituant la voix éditoriale :
« tout doit être dans Obsidian, les règles ne doivent pas vivre dans GitHub. »

**Ce que ça a montré, avant d'être corrigé.** Le miroir avait déjà divergé dans les deux
sens — la preuve qu'un miroir recopié à la main ne tient pas, exactement le défaut que
`config/vocabulaire_interdit.json` avait été créé pour éviter (quatre prompts + la charte,
cinq copies, aucune ne faisant foi), simplement déplacé d'un cran :

- **dans Obsidian, absent du JSON** : « frontière », « langues régionales »,
  « francoprovençal », « patois » — quatre règles qu'aucun audit du dépôt ne vérifiait ;
- **dans le JSON, jamais recopié dans Obsidian** : « royaume de Sardaigne », « Venise des
  Alpes » — alors que ce document disait lui-même de recopier des deux côtés.

**La correction.** `config/vocabulaire_interdit.json` **n'existe plus**. `utils/vocabulaire.py`
lit la note Obsidian **en direct sur le VPS**, comme `utils/voix.py` lit la voix éditoriale
— même principe, appliqué au vocabulaire :

```
OBSIDIAN_VOCAB_PATH=/opt/obsidian/config/main/01-Commun/Vocabulaire interdit.md
```

Tu édites la note dans Obsidian, le prochain enrichissement/traduction en tient compte.
Aucune synchronisation, aucun fichier à maintenir à jour dans ce dépôt.

**Une différence assumée avec la voix.** `utils/voix.py` garde un filet versionné dans le
dépôt (« la voix est toujours vivante, même sans Obsidian »). Ici, non : Franck a choisi
explicitement, le 05/09, qu'une panne Obsidian (VPS éteint, chemin cassé) laisse le
pipeline tourner **sans aucun filtre plutôt que de bloquer** — « continuer sans filtre,
silencieusement ». `utils/vocabulaire.interdits()` renvoie alors un tuple vide, comme si
aucune règle n'existait. C'est un choix assumé, pas un oubli.

---

## Le format que le code attend

Un tableau Markdown à 3 colonnes, celui déjà en place dans la note au 05/09 :

```markdown
| Terme interdit | Pourquoi | Alternative |
| --- | --- | --- |
| **« terme »**, « variante » | motif | **remplacement** *(IT : remplacement_it)* |
```

- **Terme interdit** : une ou plusieurs formes entre guillemets français. La première est
  la clé, les suivantes des variantes (accents et casse ignorés à la détection). Un texte
  hors guillemets dans la même cellule (« pour Savoie + Piémont », « en H1 ») est un
  qualificatif informatif, ajouté au motif — **pas appliqué structurellement** : la portée
  fine (seulement en titre, seulement en tel contexte) reste à l'œil humain.
- **Alternative** entièrement en gras, avec ou sans `*(IT : ...)*` à la suite → un
  remplacement DIRECT, celui que `consigne_prompt()` propose mot à mot.
- **Alternative** en prose (« Reformuler (…) », « Nommer la langue ») → un CONSEIL, pas un
  remplacement mot à mot. `remplacement()` renvoie `""` dans ce cas ; `consigne_prompt()`
  rend le conseil tel quel, jamais une interdiction nue.

## Comment ça vit maintenant

| Où | Quoi |
|---|---|
| Obsidian, `01-Commun/Vocabulaire interdit.md` | la **source unique**, la seule à éditer |
| `utils/vocabulaire.py` | la lit EN DIRECT (pas de cache) ; `consigne_prompt()` la rend aux rédacteurs, `trouver()` la cherche dans un texte déjà publié |
| `scripts/audit_vocabulaire.py` | trouve ce qui est **déjà publié**, avec la phrase — inchangé |
| les quatre prompts | `enrich`, `translate_events`, `conform_articles`, `utils/social` — appellent `consigne_prompt()`, ne recopient rien |
| `tests/test_vocabulaire.py` | fabrique une note temporaire pour tester le format réel, et vérifie explicitement le cas « Obsidian injoignable → silence, pas de blocage » |

**Pourquoi aucun remplacement automatique** (inchangé). Une expression interdite peut être
un titre officiel ou une citation : « Il Regno di Sardegna » sur l'affiche d'un musée n'est
pas notre prose. Seul un œil tranche, la phrase sous les yeux.

## Pour ajouter une expression

1. l'écrire **dans la note Obsidian**, dans le tableau, avec ses variantes et son
   remplacement (ou son conseil) dans les deux langues ;
2. lancer `.venv/bin/python -m scripts.audit_vocabulaire` (sur le VPS, où la base et la
   note sont accessibles) pour voir ce qui est déjà en ligne.

Rien d'autre : aucun fichier du dépôt à toucher, aucune copie à tenir à jour.
