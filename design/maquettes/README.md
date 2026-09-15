# Maquettes — Agenda Sabauda

Aperçus HTML autonomes, fidèles au **design system** Cultura Sabauda
(projet Claude Design → `colors_and_type.css`, `implementation/tokens.css`,
`ui_kits/agenda/kit.css`). Ce ne sont pas des templates de prod : ils servent
à **figer la DA** avant de coder le thème enfant WordPress (étape 2c du plan).

| Fichier | Contenu |
|---|---|
| `home.html` | Home « Ce week-end » en **desktop + mobile** (une seule page, deux frames). |
| `carte-evenement.html` | Le composant carte-événement seul, sur fond mobile. |

## Tokens repris (source unique)
- **Typo** : Alumni Sans Pinstripe (masthead, MAJUSCULES) · Saira Condensed =
  substitut réseau de **La Semplicità Pro** (titres éditoriaux) · Nunito Sans (corps).
- **Couleurs** : `--cs-bleu #18365E` · `--cs-beige #F7F1E8` · `--cs-noir #1D1D1B` ·
  `--cs-rouge #DC5D45` (accent rare) · filets `#E3DCCE`.
- **Principe** : monochrome + rouge en accent (catégorie à l'encre, une seule mise
  en avant) · territoire = **puce mono bordée** · statut par la typo · coins carrés.

## Corrections du plan appliquées (home)
pub gardée · **bandeau territoire retiré** des cartes · **bandeau noir repurposé**
« Tout l'agenda du week-end » · **« Gratuit » retiré** · tuiles **Gastronomie** &
**En famille** · **météo retirée**.

## À faire ensuite
Quand la DA est validée → coder le **thème enfant** en s'appuyant sur
`implementation/` du design system (`theme.json`, `tokens.css`,
`README-wordpress.md`, `README-jetengine.md`) — **JetEngine Blocks + Gutenberg
natif, jamais Elementor**.
