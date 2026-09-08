# Incidents réseau VPS ↔ WordPress (OVH) — journal

Ce fichier consigne chaque épisode où le VPS n'arrive pas à joindre `agendasabauda.eu`
(ou l'API REST WordPress), pour distinguer un incident ponctuel d'un motif récurrent
avant d'écrire à OVH. Voir `docs/ERREURS_2026-08-18.md` §1-4 pour l'incident qui a motivé
la création de `scripts/publier_sante.diagnostic()` — la référence sur COMMENT diagnostiquer
ce genre de coupure (DNS → IPv4 vs IPv6 → port 443 → route WordPress), pas seulement le
constater.

**Règle d'écriture ici** : ne consigner que ce qui a été MESURÉ. Un "site injoignable" sans
ping/port/DNS n'est pas un diagnostic — c'est un symptôme. S'il n'y a pas eu de mesure,
l'écrire explicitement plutôt que de deviner la cause.

---

## 2026-08-19 00:xx — `verifier_doublons_publies --en-ligne` : 14/14 interrogations sans réponse

**Constat** : lors du déploiement de e7ace83 (ajouts de sources), la commande suivante a
été lancée juste après un redémarrage du service `agenda-admin` :

```
.venv/bin/python -m scripts.verifier_doublons_publies --en-ligne
```

Sortie :
```
Interrogation de WordPress pour 14 post(s)…
⚠️  AUCUNE VÉRIFICATION N'A EU LIEU. WordPress n'a répondu à aucune
    interrogation — site injoignable depuis ce serveur. Le nombre de
    suspects ci-dessus ne vaut RIEN...
SONDAGE IMPOSSIBLE       : 14/14 interrogations sans réponse
```

**Ce qui N'A PAS été mesuré** (donc pas su, à ne pas supposer) :
- DNS résolu ou non depuis le VPS ;
- IPv4 vs IPv6 (le piège exact de `ERREURS_2026-08-18.md` §3) ;
- port 443 ouvert ou fermé/expiré ;
- si la route REST répond sans authentification (401 = WordPress vivant, juste
  l'identifiant qui manque — pas un problème réseau).

**Cause non tranchée.** Ce script (`verifier_doublons_publies.py`) ne fait qu'un `try/except`
générique sur l'appel WordPress ; il n'appelle pas `scripts/publier_sante.diagnostic()`, qui
existe précisément pour répondre aux quatre questions ci-dessus en une dizaine de secondes.
**À faire la prochaine fois que ça se reproduit**, depuis le VPS :

```
.venv/bin/python -c "from scripts.publier_sante import diagnostic; print(diagnostic('https://agendasabauda.eu'))"
```

Ça dira si c'est DNS, IPv4/IPv6, un port bloqué (→ demander à OVH de débloquer l'IP
publique du VPS, que la fonction affiche), ou WordPress lui-même (mu-plugin absent,
identifiants). Sans cette mesure, impossible de dire ici si c'est OVH, WordPress, ou une
panne temporaire du VPS.

**Suivi** : si cet épisode se reproduit sans cause identifiée après plusieurs occurrences,
ce sera le signal pour écrire à OVH — avec l'IP publique et les résultats de `diagnostic()`
en pièce jointe, pas une hypothèse.

---

<!-- Ajouter chaque nouvel épisode au-dessus de cette ligne, le plus récent en premier. -->
