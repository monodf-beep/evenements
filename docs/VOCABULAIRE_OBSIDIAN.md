# Vocabulaire — le bloc à coller dans Obsidian

Franck tient son vocabulaire dans Obsidian ; ce dépôt n'y a pas accès. Ce fichier est
donc le **miroir versionné** de ce qui doit s'y trouver : à recopier tel quel dans la note
de vocabulaire, et à tenir à jour des deux côtés.

La référence exécutable, elle, est `config/vocabulaire_interdit.json` — c'est elle que les
prompts et l'audit lisent. Ce document-ci ne sert qu'à l'humain.

---

## À coller dans Obsidian

```markdown
## Vocabulaire — Agenda Sabauda

### ❌ « royaume de Sardaigne » → ✅ « les États de Savoie »
*IT : « Regno di Sardegna » → « gli Stati Sabaudi »*

Ne jamais écrire « royaume de Sardaigne ». Le sujet de l'agenda est l'espace savoyard,
pas l'appellation diplomatique adoptée en 1720.

> Vu en ligne le 21/08/2026 sur `/expositions-turin-2026/` :
> « …de l'ancienne capitale du royaume de Sardaigne. Le bâtiment lui-même… »

**Exception** : si c'est le titre officiel d'une exposition ou une citation, on garde —
« Il Regno di Sardegna » sur l'affiche d'un musée n'est pas notre prose.

### ❌ « Venise des Alpes », « Venise du Nord » → ✅ nommer la ville

Aucun surnom de guide touristique. Pas de remplacement : on écrit « Annecy ».

*Trouvé EN LIGNE le 18/08/2026 alors que la consigne figurait déjà dans quatre prompts
de rédaction — un prompt empêche d'écrire demain, il ne corrige pas ce qui est publié.*

### Sigles — développer à la première mention

« Théâtre national de Nice (TNN) », puis « le TNN » ensuite. Le développement d'abord,
le sigle entre parenthèses, **une seule fois**.

Confirmés : **TNN** = Théâtre national de Nice · **MAUTO** = Musée national de
l'automobile.

À vérifier avant usage (jamais deviner) : TFF, TJF, GAM, MAO, OGR, C2C, MITO, ARCA.
```

---

## Comment ça vit dans le dépôt

| Où | Quoi |
|---|---|
| `config/vocabulaire_interdit.json` | la **source unique** : expression, variantes, remplacement, motif |
| `utils/vocabulaire.py` | la lit ; `consigne_prompt()` la rend aux rédacteurs, `trouver()` la cherche dans un texte |
| `scripts/audit_vocabulaire.py` | trouve ce qui est **déjà publié**, avec la phrase |
| `config/acronymes.json` + `utils/acronymes.py` | les sigles, même principe |
| les quatre prompts | `enrich`, `translate_events`, `conform_articles`, `utils/social` |

**Pourquoi une source unique.** La consigne « Venise des Alpes » était recopiée dans les
quatre prompts ET dans la charte — cinq copies, aucune ne disant laquelle fait foi. Elles
divergent, et c'est la plus permissive qui gagne. Une expression s'ajoute désormais dans
le JSON ; les prompts y renvoient.

**Pourquoi un audit en plus des prompts.** Un prompt agit sur ce qu'on écrira demain. Il
ne dit rien de ce qui est en ligne — et « Venise des Alpes » y était, malgré les quatre
consignes.

**Pourquoi aucun remplacement automatique.** Une expression interdite peut être un titre
officiel ou une citation. L'audit montre LA PHRASE ; c'est un œil qui tranche.

---

## Pour ajouter une expression

1. l'écrire dans `config/vocabulaire_interdit.json`, avec ses variantes, son remplacement
   dans les deux langues, et **le motif** — c'est lui qu'on relira dans six mois ;
2. recopier la règle dans la note Obsidian et ici ;
3. lancer `.venv/bin/python -m scripts.audit_vocabulaire` pour voir ce qui est déjà en
   ligne.

Rien d'autre : les prompts renvoient à la liste, ils n'ont pas à être modifiés.
