# Règle canonical — Cultura Sabauda ↔ Agenda Sabauda

*Décision anti contenu-dupliqué entre les deux sites. À appliquer AVANT de lancer le volume.*

---

## Le problème

Un même événement peut exister sur les **deux** sites :
- **Cultura Sabauda** (média curé) : article rédigé, score ≥ 7.
- **Agenda Sabauda** (site de volume) : fiche factuelle, tous les événements.

Si les deux pages se ressemblent, Google voit du **contenu dupliqué** → il en déclasse une (ou
les deux), et l'autorité se disperse au lieu de se concentrer.

## La décision : Cultura Sabauda est canonique

Quand un événement est publié sur les deux, **Cultura Sabauda fait foi** (page plus riche,
éditoriale, à plus forte autorité). La fiche Agenda Sabauda pointe alors un `rel=canonical` vers
l'URL Cultura Sabauda.

| Où est l'événement | `rel=canonical` de chaque page |
|---|---|
| Seulement sur Cultura Sabauda | CS → elle-même (défaut) |
| Seulement sur Agenda Sabauda | Agenda → elle-même (défaut) — **le cas majoritaire** (score < 7) |
| Sur les DEUX | CS → elle-même ; **Agenda → l'URL CS** |

Ainsi l'autorité se concentre sur la page CS, sans jamais faire disparaître la fiche Agenda
(elle reste accessible et sert le maillage/volume — elle dit juste à Google « la version de
référence est là-bas »).

## Deux garde-fous complémentaires

1. **Différencier les contenus.** L'idéal reste que les deux versions ne soient PAS identiques :
   CS = article éditorial (chapô + corps + regard) ; Agenda = fiche factuelle (dates, lieu,
   infos pratiques, description courte). Deux angles = moins de duplication au départ. Le
   canonical est la ceinture ; contenus distincts sont les bretelles.
2. **Ne jamais republier le même bloc de texte enrichi tel quel sur les deux** sans canonical.

## Mise en œuvre

- **Aujourd'hui (export CS uniquement)** : rien à faire — un post WordPress est canonique à
  lui-même par défaut. La règle n'a d'effet qu'une fois le site Agenda construit.
- **Demain (export Agenda Sabauda, à construire)** : dans le publisher Agenda, si l'événement a
  un `wp_post_id_cs` (donc déjà publié sur CS), récupérer l'URL du post CS (`GET .../posts/{id}`
  → champ `link`) et la poser en `_yoast_wpseo_canonical` sur la fiche Agenda. Sinon, canonical
  = la fiche elle-même (défaut).
- **Suivi** : le champ `wp_post_id_cs` existe déjà en base (rempli à « Publier CS ») — c'est le
  signal « cet événement est aussi sur CS ». Rien à ajouter au schéma.

## À retenir pour le lancement de ce soir

Le site Agenda Sabauda peut se construire sans canonical dans un premier temps (peu
d'événements sont encore sur CS). Mais **avant de pousser du volume qui recoupe CS**, brancher
la règle ci-dessus dans l'export Agenda. Le noter dans le runbook d'installation.
