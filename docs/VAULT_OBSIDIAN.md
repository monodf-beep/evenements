# Accès au vault Obsidian (base de connaissance Cultura Sabauda)

Le projet Agenda Sabauda s'appuie sur une **base de connaissance partagée**, tenue
dans un vault Obsidian versionné sur GitHub. C'est la **source de vérité éditoriale**
(charte, voix, non-négociables, contributeurs, décisions). À consulter avant toute
rédaction ou décision éditoriale.

- **Repo (privé)** : `monodf-beep/obsidian-vault`
- **Clone local** : `../obsidian-vault` (dossier **frère** de `evenements`, soit
  `C:\Users\monod\projects\obsidian-vault`). Ne PAS le cloner *dans* ce repo (éviter
  un dépôt git imbriqué et tout commit accidentel de contenu du vault ici).
- Le dossier `.obsidian/` est exclu du dépôt (secrets) : on n'a que les notes `.md`
  (+ quelques PDF/DOCX).

## Mise en place (une seule fois)

1. Créer un token GitHub **fine-grained** limité au repo `obsidian-vault`, permission
   **Contents: Read** (Read and Write seulement si on doit écrire dans le vault).
2. Cloner à côté de ce repo :
   ```bash
   cd C:/Users/monod/projects
   git clone https://github.com/monodf-beep/obsidian-vault.git
   ```
   À la demande d'identifiants : user `monodf-beep`, password = **le token**.
   Laisser le **gestionnaire d'identifiants Windows** le stocker.
3. ⚠️ Ne JAMAIS mettre le token dans l'URL du remote, dans `.git/config`, ni le
   committer où que ce soit.

## À chaque session de travail

Rafraîchir le vault avant de s'appuyer dessus :
```bash
git -C ../obsidian-vault pull
```

## Carte du vault (points d'entrée)

- `00-INDEX.md` — index général, commencer par là.
- `01-Commun/` — la racine : **Charte commune**, **Ligne éditoriale (source)**,
  **Non-négociables**, **Vocabulaire interdit**, **Principe de l'escalier**, et
  `Voix commune/` (ADN Enrico, guide de clonage).
- `02-Projets/` — **Agenda Sabauda** + **Charte Agenda Sabauda (surcharges)**,
  Cultura Sabauda, Nos Alpes, Mordus, L'Observatoire.
- `03-Voix personnelles/Franck/` — voix de Franck + personal branding.
- `04-Studio/` — Vision, Roadmap, Décisions, Architecture technique, Contributeurs.

## Conventions

- **Lecture seule par défaut.** Si on modifie une note : commit + push côté vault,
  puis Obsidian récupère via `git pull`.
- Liens internes au format Obsidian `[[Nom de note]]`.
- Repo privé : ne jamais committer de secrets.

## Règles éditoriales clés (résumé, la source fait foi)

À appliquer pour toute rédaction Agenda Sabauda (détail dans le vault + dans
`CHARTE_EDITORIALE.md` de ce repo) :

- **Vocabulaire interdit** (dur) : « frontière », « langues régionales »,
  « francoprovençal », « patois », « espace alpin » (pour Savoie+Piémont),
  « transfrontalier » en titre. Privilégier **espace sabaudo**, **savoyard**,
  **Aoste** visible. **Nice est cœur, jamais périphérie.**
- **Principe de l'escalier** (gate dure sur le long-form) : ancrage local →
  question universelle.
- **Deux longueurs selon le score** (`Charte Agenda Sabauda (surcharges)`) :
  ≥ 7 → article long ; < 7 → catalogue court (1-3 paragraphes rédigés, jamais la
  description brute recopiée) + faits structurés en listes (programmation,
  horaires, tarifs). Listes **autorisées** sur l'Agenda.
- Pas d'émojis, pas de gras décoratif, pas de tiret cadratin. Aucune publication
  sans validation humaine.

> Note : la fiche `02-Projets/Agenda Sabauda.md` du vault est encore « à compléter
> par Franck » (mission / ton / périmètre non définis). En attendant, la voix
> Agenda = Cultura Sabauda + les surcharges ci-dessus.
